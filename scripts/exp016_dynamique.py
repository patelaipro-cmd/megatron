"""EXP-016 : forces d'équipes dynamiques (dyn-v1) contre poisson-v5-cal. Protocole figé :
docs/experiences/EXP-016-forces-dynamiques.md.

Usage : python scripts/exp016_dynamique.py --sortie docs/experiences/EXP-016 [--processus 4]
1. Grille de 192 réglages (le protocole annonçait 384 : erreur de compte, 4·3·2·2·2·2 = 192) sur dev (2008/09-2015/16, log-loss 1X2, 5 ligues réunies), un cran
   de plus sur q si l'optimum touche un bord (une seule fois).
2. Recalibration p'∝p^b·exp(c) (forme EXP-010) apprise sur les prévisions dev du réglage figé.
3. Validation et test sur exactement les matchs d'EXP-008 ; critères D1-D4 contre v5-cal.
"""
from __future__ import annotations

import argparse
import itertools
import json
import math
import sys
import time
from multiprocessing import Pool
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from exp010_calibration import LIGUES, calibrate, fit  # noqa: E402
from megatron import backtest, data  # noqa: E402
from megatron.agents import StatsAgent  # noqa: E402
from megatron.dynamique import Reglage, derouler  # noqa: E402
from megatron.ledger import OUTCOMES, score  # noqa: E402

CSV = ROOT / "data" / "matches_top5_2000-2026.csv"
EXP8 = ROOT / "docs" / "experiences" / "EXP-008"
DEV = {f"{a}/{str(a + 1)[-2:]}" for a in range(2008, 2016)}
FIN_DEV = "2016-07-01"
GRILLE = {"q": [0.0002, 0.0005, 0.001, 0.002], "q_saison": [0.0, 0.01, 0.03], "p0": [0.05, 0.15],
          "w": [0.0, 0.35], "c": [0.0, 0.15], "correction": [False, True]}
B_V5, C_V5 = StatsAgent.CALIBRATION[0], StatsAgent.CALIBRATION[1:]

_MATCHS: list = []


def _init(matchs):
    global _MATCHS
    _MATCHS = matchs


def _ll(p: dict, y: str) -> float:
    return -math.log(max(p[y], 1e-15))


def evaluer_dev(r: Reglage) -> dict:
    jusqu = [m for m in _MATCHS if m.day.isoformat() < FIN_DEV]
    preds = derouler(jusqu, r, garder=lambda m: data.season_of(m.day) in DEV)
    res = {m.match_id: m.result for m in jusqu if m.match_id in preds}
    ll = sum(_ll(preds[k][0], y) for k, y in res.items()) / len(res)
    return {"reglage": r.__dict__, "nom": r.nom, "log_loss": round(ll, 6), "n": len(res)}


def grille(matchs, qs, processus: int) -> list[dict]:
    regs = [Reglage(q=q, q_saison=qs_, p0=p0, w=w, c=c, correction=cor)
            for q, qs_, p0, w, c, cor in itertools.product(qs, GRILLE["q_saison"], GRILLE["p0"], GRILLE["w"],
                                                            GRILLE["c"], GRILLE["correction"])]
    with Pool(processus, initializer=_init, initargs=(matchs,)) as pool:
        return sorted(pool.map(evaluer_dev, regs, chunksize=1), key=lambda x: x["log_loss"])


def niveaux(lh: float, la: float) -> tuple[str, list[float]]:
    """Favori (côté au λ le plus fort) et P(victoire par ≥1, ≥2, ≥3 buts) sous Poisson indépendant."""
    lf, lo, fav = (lh, la, "H") if lh >= la else (la, lh, "A")
    pf = [math.exp(-lf) * lf ** i / math.factorial(i) for i in range(11)]
    po = [math.exp(-lo) * lo ** i / math.factorial(i) for i in range(11)]
    return fav, [sum(pf[i] * po[j] for i in range(11) for j in range(11) if i - j >= k) for k in (1, 2, 3)]


def comparer(role: str, preds: dict, matchs: dict, b: float, c: tuple) -> dict:
    rows = []
    for lg in LIGUES:
        for r in backtest.read_predictions(EXP8 / role / lg / "predictions.csv"):
            p = preds.get(r["match_id"])
            if p is None:
                raise SystemExit(f"{r['match_id']} absent du déroulé dyn-v1")
            rows.append({"ligue": lg, "match_id": r["match_id"], "issue": r["issue"], "bookmaker": r["bookmaker"],
                         "v5_cal": calibrate(r["candidat"], B_V5, C_V5), "dyn": p[0], "dyn_cal": calibrate(p[0], b, c),
                         "lh": p[1], "la": p[2]})
    common = [r for r in rows if r["bookmaker"]]
    sc = lambda k, rs: score([(r[k], r["issue"]) for r in rs])  # noqa: E731
    out = {"n": len(rows),
           "scores": {k: {m: v for m, v in sc(k, rows).items() if m != "calibration"} for k in ("dyn", "dyn_cal", "v5_cal")},
           "calibration_dyn_cal": sc("dyn_cal", rows)["calibration"],
           "dyn_cal_moins_v5_cal": backtest.paired_bootstrap(rows, "dyn_cal", "v5_cal"),
           "dyn_brut_moins_v5_cal": backtest.paired_bootstrap(rows, "dyn", "v5_cal"),
           "par_ligue": {lg: backtest.paired_bootstrap([r for r in rows if r["ligue"] == lg], "dyn_cal", "v5_cal")
                         for lg in LIGUES},
           "avec_cotes": {"n": len(common), "dyn_cal_moins_bookmaker": backtest.paired_bootstrap(common, "dyn_cal", "bookmaker"),
                          "v5_cal_moins_bookmaker": backtest.paired_bootstrap(common, "v5_cal", "bookmaker")}}
    # niveaux de victoire du favori dyn-v1 (information : v5 n'a pas de λ dans EXP-008, pas de comparaison)
    niv = {k: [0.0, 0.0, 0] for k in ("1+", "2+", "3+")}
    for r in rows:
        h, a = (int(x) for x in [matchs[r["match_id"]].home_goals, matchs[r["match_id"]].away_goals])
        fav, ps = niveaux(r["lh"], r["la"])
        marge = h - a if fav == "H" else a - h
        for (k, acc), p, s in zip(niv.items(), ps, (1, 2, 3)):
            y = marge >= s
            acc[0] += -math.log(max(p if y else 1 - p, 1e-15))
            acc[1] += p
            acc[2] += y
    out["niveaux_favori_dyn"] = {k: {"log_loss": round(v[0] / len(rows), 6), "p_moyenne": round(v[1] / len(rows), 4),
                                     "frequence": round(v[2] / len(rows), 4)} for k, v in niv.items()}
    return out


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--sortie", type=Path, required=True)
    p.add_argument("--processus", type=int, default=4)
    a = p.parse_args(argv)
    t0 = time.time()
    matchs = data.load(CSV)
    res = grille(matchs, GRILLE["q"], a.processus)
    extension = None
    q_opt = res[0]["reglage"]["q"]
    if q_opt in (GRILLE["q"][0], GRILLE["q"][-1]):
        extension = GRILLE["q"][0] / 2 if q_opt == GRILLE["q"][0] else GRILLE["q"][-1] * 2
        res = sorted(res + grille(matchs, [extension], a.processus), key=lambda x: x["log_loss"])
    meilleur = Reglage(**res[0]["reglage"])
    print(f"grille : {len(res)} réglages en {time.time() - t0:.0f} s ; meilleur {meilleur.nom} {res[0]['log_loss']}", flush=True)

    preds = derouler(matchs, meilleur)
    dev = [{"issue": m.result, "v5": preds[m.match_id][0]} for m in matchs if data.season_of(m.day) in DEV]
    b, c = fit(dev)
    out = {"protocole": "docs/experiences/EXP-016-forces-dynamiques.md", "donnees": str(CSV.relative_to(ROOT)),
           "grille": {"n": len(res), "extension_q": extension, "dix_meilleurs": res[:10], "pire": res[-1]},
           "reglage_fige": meilleur.__dict__,
           "recalibration_dev": {"b": round(b, 6), "c_H": round(c[0], 6), "c_D": round(c[1], 6), "n": len(dev),
                                 "log_loss_brut": round(sum(_ll(r["v5"], r["issue"]) for r in dev) / len(dev), 6),
                                 "log_loss_cal": round(sum(_ll(calibrate(r["v5"], b, c), r["issue"]) for r in dev) / len(dev), 6)}}
    par_id = {m.match_id: m for m in matchs}
    for role in ("validation", "test"):
        out[role] = comparer(role, preds, par_id, b, c)
    v, t = out["validation"], out["test"]
    out["criteres"] = {
        "D1_validation_ic_haut_negatif": v["dyn_cal_moins_v5_cal"]["ic95"][1] < 0,
        "D2_test_ic_haut_negatif": t["dyn_cal_moins_v5_cal"]["ic95"][1] < 0,
        "D3_test_4_ligues_sur_5": sum(x["ecart"] < 0 for x in t["par_ligue"].values()) >= 4,
        "D4_test_rps": t["scores"]["dyn_cal"]["rps"] <= t["scores"]["v5_cal"]["rps"]}
    out["verdict"] = "CANDIDAT" if all(out["criteres"].values()) else "REJETE"
    out["duree_s"] = round(time.time() - t0)
    a.sortie.mkdir(parents=True, exist_ok=True)
    (a.sortie / "resultats.json").write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("reglage_fige", "recalibration_dev", "criteres", "verdict")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
