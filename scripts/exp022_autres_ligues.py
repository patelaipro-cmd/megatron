"""EXP-022 : poisson-v5 sur 17 autres championnats. Protocole : docs/experiences/EXP-022-autres-ligues.md.

Usage : python scripts/exp022_autres_ligues.py --brut docs/experiences/EXP-022/brut --sortie docs/experiences/EXP-022
(--brut : sortie de grille_multi --configs "v5=270,2,0,moyenne,cadres,0.35" sur 2008/09-2025/26).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from exp010_calibration import calibrate, fit  # noqa: E402
from megatron import backtest  # noqa: E402
from megatron.agents import StatsAgent  # noqa: E402
from megatron.ledger import score  # noqa: E402

LIGUES = ("E1", "E2", "E3", "EC", "SC0", "SC1", "SC2", "SC3", "SP2", "I2", "F2", "D2", "N1", "P1", "B1", "T1", "G1")
saisons = lambda a, b: {f"{x}/{str(x + 1)[-2:]}" for x in range(a, b + 1)}  # noqa: E731
PERIODES = {"dev": saisons(2008, 2015), "validation": saisons(2016, 2019), "test": saisons(2020, 2025)}
B5, C5 = StatsAgent.CALIBRATION[0], StatsAgent.CALIBRATION[1:]


def charger(brut: Path) -> dict[str, list[dict]]:
    out = {p: [] for p in PERIODES}
    for lg in LIGUES:
        for r in backtest.read_predictions(brut / lg / "predictions.csv"):
            if not r["v5"] or not r["frequences"]:
                continue
            for p, s in PERIODES.items():
                if r["saison"] in s:
                    out[p].append({"ligue": lg, "issue": r["issue"], "v5": r["v5"], "frequences": r["frequences"],
                                   "bookmaker": r["bookmaker"]})
    return out


def calibration_ok(rows: list[dict], k: str, mini: int = 200) -> tuple[bool, list]:
    tranches = []
    for o in ("H", "D", "A"):
        for t in range(10):
            dans = [r for r in rows if t / 10 <= r[k][o] < (t + 1) / 10 or (t == 9 and r[k][o] == 1)]
            if len(dans) >= mini:
                moy = sum(r[k][o] for r in dans) / len(dans)
                obs = sum(r["issue"] == o for r in dans) / len(dans)
                tranches.append({"issue": o, "tranche": t / 10, "n": len(dans), "prevu": round(moy, 4),
                                 "observe": round(obs, 4), "ok": abs(obs - moy) <= 0.05})
    return all(x["ok"] for x in tranches), tranches


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--brut", type=Path, required=True)
    p.add_argument("--sortie", type=Path, required=True)
    a = p.parse_args(argv)
    d = charger(a.brut)
    b, c = fit(d["dev"])
    for rows in d.values():
        for r in rows:
            r["A"], r["B"] = calibrate(r["v5"], B5, C5), calibrate(r["v5"], b, c)
    out = {"protocole": "docs/experiences/EXP-022-autres-ligues.md",
           "recalibration_B": {"b": round(b, 6), "c_H": round(c[0], 6), "c_D": round(c[1], 6), "n_dev": len(d["dev"])},
           "n": {k: len(v) for k, v in d.items()}}
    v = d["validation"]
    out["L1_B_moins_A_validation"] = backtest.paired_bootstrap(v, "B", "A")
    m = "B" if out["L1_B_moins_A_validation"]["ic95"][1] < 0 else "A"
    out["modele_retenu"] = m
    t = d["test"]
    sc = lambda rows, k: {x: y for x, y in score([(r[k], r["issue"]) for r in rows]).items() if x != "calibration"}  # noqa: E731
    out["test_reunies"] = {k: sc(t, k) for k in ("A", "B", "v5", "frequences")}
    cotes = [r for r in t if r["bookmaker"]]
    out["test_reunies"]["M_moins_bookmaker"] = backtest.paired_bootstrap(cotes, m, "bookmaker")
    out["test_reunies"]["M_moins_frequences"] = backtest.paired_bootstrap(t, m, "frequences")
    out["par_ligue"], couvertes = {}, []
    for lg in LIGUES:
        rows = [r for r in t if r["ligue"] == lg]
        cl = [r for r in rows if r["bookmaker"]]
        l2 = backtest.paired_bootstrap(rows, m, "frequences")
        l3, tranches = calibration_ok(rows, m)
        out["par_ligue"][lg] = {"n": len(rows), "log_loss_M": sc(rows, m)["log_loss"], "M_moins_frequences": l2,
                                "M_moins_bookmaker": backtest.paired_bootstrap(cl, m, "bookmaker") if cl else None,
                                "L2": l2["ic95"][1] < 0, "L3": l3, "tranches": tranches}
        if l2["ic95"][1] < 0 and l3:
            couvertes.append(lg)
    out["ligues_couvertes"] = couvertes
    a.sortie.mkdir(parents=True, exist_ok=True)
    (a.sortie / "resultats.json").write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("recalibration_B", "n", "L1_B_moins_A_validation", "modele_retenu",
                                           "ligues_couvertes")}, ensure_ascii=False))
    print(json.dumps(out["test_reunies"], ensure_ascii=False))
    for lg, x in out["par_ligue"].items():
        print(lg, x["n"], x["log_loss_M"], x["M_moins_frequences"], x["M_moins_bookmaker"], x["L2"], x["L3"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
