"""EXP-018 : xG Understat dans les forces d'équipes (xg-v1), fusionné avec les cotes, jugé contre le
bookmaker. Protocole figé : docs/experiences/EXP-018-xg.md.

Usage : python scripts/exp018_xg.py --xg <externe/understat/historique de donnees-externes> --sortie docs/experiences/EXP-018
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from exp010_calibration import LIGUES, calibrate  # noqa: E402
from exp017_fusion import ajuster, fusionner  # noqa: E402
from megatron import backtest, data, models  # noqa: E402
from megatron.agents import StatsAgent  # noqa: E402
from megatron.dynamique import Reglage, derouler  # noqa: E402
from megatron.ledger import score  # noqa: E402

CSV = ROOT / "data" / "matches_top5_2000-2026.csv"
EXP8 = ROOT / "docs" / "experiences" / "EXP-008"
DIVISION = {"ENG-Premier League": "E0", "ESP-La Liga": "SP1", "ITA-Serie A": "I1", "GER-Bundesliga": "D1",
            "FRA-Ligue 1": "F1"}
saisons = lambda a, b: {f"{x}/{str(x + 1)[-2:]}" for x in range(a, b + 1)}  # noqa: E731
DEV, VALIDATION, TEST = saisons(2015, 2017), saisons(2018, 2020), saisons(2021, 2025)
FIGE_016 = dict(q=0.0001, q_saison=0.0, p0=0.05, c=0.15, correction=False)  # réglage figé d'EXP-016
GRILLE_W = (0.25, 0.5, 0.75, 1.0)
B_V5, C_V5 = StatsAgent.CALIBRATION[0], StatsAgent.CALIBRATION[1:]


def lire_xg(dossier: Path) -> list[dict]:
    out = []
    for f in sorted(dossier.glob("matchs_equipes_*.csv")):
        with f.open(newline="", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                out.append({"division": DIVISION[r["league"]], "jour": date.fromisoformat(r["date"][:10]),
                            "dom": r["home_team"], "ext": r["away_team"], "bd": int(float(r["home_goals"])),
                            "be": int(float(r["away_goals"])), "xg": (float(r["home_xg"]), float(r["away_xg"]))})
    return out


def relier(xg: list[dict], matchs: list[data.Match]) -> tuple[dict, dict]:
    """Noms Understat → data/ par vote sur les matchs communs (date ± 1 j, même score), puis liaison."""
    par_jour = defaultdict(list)
    for m in matchs:
        par_jour[(m.division, m.day)].append(m)
    proches = lambda r: [m for d in (-1, 0, 1) for m in par_jour[(r["division"], r["jour"] + timedelta(days=d))]]  # noqa: E731
    votes = defaultdict(Counter)
    for r in xg:
        cands = [m for m in proches(r) if (m.home_goals, m.away_goals) == (r["bd"], r["be"])]
        for m in cands:  # un vote par candidat : les faux couples se diluent
            votes[(r["division"], r["dom"])][m.home] += 1
            votes[(r["division"], r["ext"])][m.away] += 1
    noms = {k: c.most_common(1)[0][0] for k, c in votes.items()}
    lie, rejets = {}, Counter()
    for r in xg:
        h, a = noms.get((r["division"], r["dom"])), noms.get((r["division"], r["ext"]))
        ms = [m for m in proches(r) if (m.home, m.away) == (h, a)]
        if len(ms) != 1:
            rejets["non_relie"] += 1
        elif (ms[0].home_goals, ms[0].away_goals) != (r["bd"], r["be"]):
            rejets["score_different"] += 1
        else:
            lie[ms[0].match_id] = r["xg"]
    return lie, {"lignes_understat": len(xg), "relies": len(lie), **rejets,
                 "noms": {f"{k[0]}:{k[1]}": v for k, v in sorted(noms.items())}}


def _ll(rows, k):
    return sum(-math.log(max(r[k][r["issue"]], 1e-15)) for r in rows) / len(rows)


def lignes(matchs, periode, preds: dict[str, dict]) -> list[dict]:
    out = []
    for m in matchs:
        if data.season_of(m.day) in periode and m.odds:
            out.append({"ligue": m.division, "match_id": m.match_id, "issue": m.result,
                        "bookmaker": models.bookmaker(m), **{k: p[m.match_id][0] for k, p in preds.items()}})
    return out


def fusion(rows: list[dict], cle: str, th: list[float], nom: str) -> None:
    for r in rows:
        r[nom] = fusionner(r[cle], r["bookmaker"], th)


def ajuster_sur(rows: list[dict], cle: str) -> list[float]:
    return ajuster([{"v5_cal": r[cle], "bookmaker": r["bookmaker"], "issue": r["issue"]} for r in rows])


def evaluer(rows: list[dict]) -> dict:
    sc = lambda k: {m: v for m, v in score([(r[k], r["issue"]) for r in rows]).items() if m != "calibration"}  # noqa: E731
    return {"n": len(rows), "scores": {k: sc(k) for k in ("fus_xg", "fus_ref", "bookmaker", "xg", "ref")},
            "calibration_fus_xg": score([(r["fus_xg"], r["issue"]) for r in rows])["calibration"],
            "fus_xg_moins_bookmaker": backtest.paired_bootstrap(rows, "fus_xg", "bookmaker"),
            "fus_xg_moins_fus_ref": backtest.paired_bootstrap(rows, "fus_xg", "fus_ref"),
            "xg_moins_ref": backtest.paired_bootstrap(rows, "xg", "ref"),
            "par_ligue": {lg: backtest.paired_bootstrap([r for r in rows if r["ligue"] == lg], "fus_xg", "bookmaker")
                          for lg in LIGUES}}


def contre_v5(preds_xg: dict) -> dict:
    """Information : xg-v1 seul − v5-cal sur les matchs d'EXP-008 communs (validation et test d'EXP-008)."""
    rows = []
    for role in ("validation", "test"):
        for lg in LIGUES:
            for r in backtest.read_predictions(EXP8 / role / lg / "predictions.csv"):
                if data.season_of(date.fromisoformat(r["match_id"].split(":")[1])) in VALIDATION | TEST:
                    rows.append({"issue": r["issue"], "xg": preds_xg[r["match_id"]][0],
                                 "v5_cal": calibrate(r["candidat"], B_V5, C_V5)})
    return backtest.paired_bootstrap(rows, "xg", "v5_cal")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--xg", type=Path, required=True)
    p.add_argument("--sortie", type=Path, required=True)
    a = p.parse_args(argv)
    matchs = data.load(CSV)
    xg, liaison = relier(lire_xg(a.xg), matchs)
    print({k: v for k, v in liaison.items() if k != "noms"}, flush=True)
    fin_dev = date(2018, 7, 1)
    avant = [m for m in matchs if m.day < fin_dev]
    grille = []
    for w in GRILLE_W:
        pr = derouler(avant, Reglage(w=w, **FIGE_016), garder=lambda m: data.season_of(m.day) in DEV, xg=xg)
        rows = [{"issue": m.result, "p": pr[m.match_id][0]} for m in avant if m.match_id in pr]
        grille.append({"w": w, "log_loss_dev": round(_ll(rows, "p"), 6), "n": len(rows)})
    w = min(grille, key=lambda g: g["log_loss_dev"])["w"]
    preds = {"xg": derouler(matchs, Reglage(w=w, **FIGE_016), xg=xg), "ref": derouler(matchs, Reglage(w=0.35, **FIGE_016))}
    dev = lignes(matchs, DEV, preds)
    th_xg, th_ref = ajuster_sur(dev, "xg"), ajuster_sur(dev, "ref")
    out = {"protocole": "docs/experiences/EXP-018-xg.md", "liaison": liaison, "grille_w": grille, "w_fige": w,
           "fusion_xg": dict(zip(("alpha_xg", "beta_cotes", "c_H", "c_D"), (round(x, 6) for x in th_xg))),
           "fusion_ref": dict(zip(("alpha_dyn", "beta_cotes", "c_H", "c_D"), (round(x, 6) for x in th_ref))),
           "xg_matchs_par_saison": dict(sorted(Counter(data.season_of(date.fromisoformat(k.split(":")[1])) for k in xg).items()))}
    for role, periode in (("dev", DEV), ("validation", VALIDATION), ("test", TEST)):
        rows = lignes(matchs, periode, preds)
        fusion(rows, "xg", th_xg, "fus_xg")
        fusion(rows, "ref", th_ref, "fus_ref")
        out[role] = evaluer(rows)
    out["xg_seul_moins_v5_cal_2018_2026"] = contre_v5(preds["xg"])
    v, t = out["validation"], out["test"]
    out["criteres"] = {
        "X1_validation_ic_haut_negatif": v["fus_xg_moins_bookmaker"]["ic95"][1] < 0,
        "X2_test_ic_haut_negatif": t["fus_xg_moins_bookmaker"]["ic95"][1] < 0,
        "X3_test_4_ligues_sur_5": sum(x["ecart"] < 0 for x in t["par_ligue"].values()) >= 4,
        "X4_test_rps": t["scores"]["fus_xg"]["rps"] <= t["scores"]["bookmaker"]["rps"]}
    out["verdict"] = "CANDIDAT" if all(out["criteres"].values()) else "REJETE"
    a.sortie.mkdir(parents=True, exist_ok=True)
    (a.sortie / "resultats.json").write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("grille_w", "w_fige", "fusion_xg", "fusion_ref", "criteres", "verdict")},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
