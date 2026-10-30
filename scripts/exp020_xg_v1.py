"""EXP-020 : xg-v1 recalibré à la place de poisson-v5-cal pour le 1X2 statistique.
Protocole figé : docs/experiences/EXP-020-promotion-xg-v1.md.

Usage : python scripts/exp020_xg_v1.py --xg <externe/understat/historique de donnees-externes> --sortie docs/experiences/EXP-020
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from exp010_calibration import LIGUES, calibrate, fit  # noqa: E402
from exp018_xg import DEV, EXP8, FIGE_016, TEST, VALIDATION, lire_xg, relier  # noqa: E402
from megatron import backtest, data, models  # noqa: E402
from megatron.agents import StatsAgent  # noqa: E402
from megatron.dynamique import Reglage, derouler  # noqa: E402
from megatron.ledger import score  # noqa: E402

CSV = ROOT / "data" / "matches_top5_2000-2026.csv"
W = 0.5  # figé par EXP-018
B_V5, C_V5 = StatsAgent.CALIBRATION[0], StatsAgent.CALIBRATION[1:]


def v5_cal() -> dict[str, dict]:
    out = {}
    for role in ("validation", "test"):
        for lg in LIGUES:
            for r in backtest.read_predictions(EXP8 / role / lg / "predictions.csv"):
                if r["candidat"]:
                    out[r["match_id"]] = calibrate(r["candidat"], B_V5, C_V5)
    return out


def evaluer(rows: list[dict]) -> dict:
    sc = lambda k, rr: {m: v for m, v in score([(r[k], r["issue"]) for r in rr]).items() if m != "calibration"}  # noqa: E731
    cotes = [r for r in rows if r["bookmaker"]]
    return {"n": len(rows), "scores": {k: sc(k, rows) for k in ("xg_cal", "xg", "v5_cal")},
            "calibration_xg_cal": score([(r["xg_cal"], r["issue"]) for r in rows])["calibration"],
            "calibration_v5_cal": score([(r["v5_cal"], r["issue"]) for r in rows])["calibration"],
            "xg_cal_moins_v5_cal": backtest.paired_bootstrap(rows, "xg_cal", "v5_cal"),
            "xg_brut_moins_v5_cal": backtest.paired_bootstrap(rows, "xg", "v5_cal"),
            "xg_cal_moins_xg_brut": backtest.paired_bootstrap(rows, "xg_cal", "xg"),
            "par_ligue": {lg: backtest.paired_bootstrap([r for r in rows if r["ligue"] == lg], "xg_cal", "v5_cal")
                          for lg in LIGUES},
            "avec_cotes": {"n": len(cotes), "bookmaker": sc("bookmaker", cotes),
                           "xg_cal_moins_bookmaker": backtest.paired_bootstrap(cotes, "xg_cal", "bookmaker"),
                           "v5_cal_moins_bookmaker": backtest.paired_bootstrap(cotes, "v5_cal", "bookmaker")}}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--xg", type=Path, required=True)
    p.add_argument("--sortie", type=Path, required=True)
    a = p.parse_args(argv)
    matchs = data.load(CSV)
    xg, liaison = relier(lire_xg(a.xg), matchs)
    preds = derouler(matchs, Reglage(w=W, **FIGE_016), xg=xg)
    dev = [{"v5": preds[m.match_id][0], "issue": m.result} for m in matchs
           if data.season_of(m.day) in DEV and m.match_id in preds]
    b, c = fit(dev)
    ref = v5_cal()
    out = {"protocole": "docs/experiences/EXP-020-promotion-xg-v1.md", "w": W,
           "liaison": {k: v for k, v in liaison.items() if k != "noms"},
           "recalibration": {"b": round(b, 6), "c_H": round(c[0], 6), "c_D": round(c[1], 6), "n_dev": len(dev)}}
    for role, periode in (("validation", VALIDATION), ("test", TEST)):
        rows = []
        for m in matchs:
            if data.season_of(m.day) in periode and m.match_id in preds and m.match_id in ref:
                px = preds[m.match_id][0]
                rows.append({"ligue": m.division, "issue": m.result, "xg": px, "xg_cal": calibrate(px, b, c),
                             "v5_cal": ref[m.match_id], "bookmaker": models.bookmaker(m) if m.odds else None})
        out[role] = evaluer(rows)
    v, t = out["validation"], out["test"]
    out["criteres"] = {
        "Z1_validation_ic_haut_negatif": v["xg_cal_moins_v5_cal"]["ic95"][1] < 0,
        "Z2_test_ic_haut_negatif": t["xg_cal_moins_v5_cal"]["ic95"][1] < 0,
        "Z3_test_4_ligues_sur_5": sum(x["ecart"] < 0 for x in t["par_ligue"].values()) >= 4,
        "Z4_test_rps": t["scores"]["xg_cal"]["rps"] <= t["scores"]["v5_cal"]["rps"]}
    out["verdict"] = "CANDIDAT" if all(out["criteres"].values()) else "REJETE"
    a.sortie.mkdir(parents=True, exist_ok=True)
    (a.sortie / "resultats.json").write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("liaison", "recalibration", "criteres", "verdict")}, ensure_ascii=False))
    for role in ("validation", "test"):
        r = out[role]
        print(role, r["n"], r["scores"], r["xg_cal_moins_v5_cal"], r["xg_brut_moins_v5_cal"], r["xg_cal_moins_xg_brut"],
              r["avec_cotes"]["xg_cal_moins_bookmaker"], r["avec_cotes"]["v5_cal_moins_bookmaker"])
    print({lg: x["ecart"] for lg, x in t["par_ligue"].items()})
    return 0


if __name__ == "__main__":
    sys.exit(main())
