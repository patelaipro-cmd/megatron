"""EXP-017 : fusion log-linéaire poisson-v5-cal + bookmaker. Protocole figé :
docs/experiences/EXP-017-fusion-marche.md.

Usage : python scripts/exp017_fusion.py --dev <dossier des prévisions v5 dev> --sortie docs/experiences/EXP-017
<dossier>/<ligue>/predictions.csv : sortie de scripts/grille_multi.py (config 270|2|0.35) sur 2008/09-2015/16.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from exp010_calibration import LIGUES, _solve, calibrate  # noqa: E402
from megatron import backtest  # noqa: E402
from megatron.agents import StatsAgent  # noqa: E402
from megatron.ledger import OUTCOMES, score  # noqa: E402

EXP8 = ROOT / "docs" / "experiences" / "EXP-008"
B_V5, C_V5 = StatsAgent.CALIBRATION[0], StatsAgent.CALIBRATION[1:]
CONTROLE_DEV = (0.991185, 14604)  # log-loss et effectif dev de 270|2|0.35 dans EXP-008/dev/resultats.json


def fusionner(v5: dict, book: dict, th: list[float]) -> dict[str, float]:
    a, b, ch, cd = th
    z = {o: a * math.log(max(v5[o], 1e-6)) + b * math.log(max(book[o], 1e-6)) + {"H": ch, "D": cd, "A": 0.0}[o]
         for o in OUTCOMES}
    m = max(z.values())
    e = {o: math.exp(v - m) for o, v in z.items()}
    s = sum(e.values())
    return {o: e[o] / s for o in OUTCOMES}


def ajuster(rows: list[dict], iters: int = 50) -> list[float]:
    """Newton sur (α, β, c_H, c_D) : log-vraisemblance multinomiale concave."""
    th = [0.5, 0.5, 0.0, 0.0]
    for _ in range(iters):
        g = [0.0] * 4
        h = [[0.0] * 4 for _ in range(4)]
        for r in rows:
            q = fusionner(r["v5_cal"], r["bookmaker"], th)
            dz = {o: (math.log(max(r["v5_cal"][o], 1e-6)), math.log(max(r["bookmaker"][o], 1e-6)),
                      float(o == "H"), float(o == "D")) for o in OUTCOMES}
            moy = [sum(q[o] * dz[o][k] for o in OUTCOMES) for k in range(4)]
            for k in range(4):
                g[k] += dz[r["issue"]][k] - moy[k]
                for j in range(4):
                    h[k][j] -= sum(q[o] * dz[o][k] * dz[o][j] for o in OUTCOMES) - moy[k] * moy[j]
        pas = _solve(h, g)
        th = [t - s for t, s in zip(th, pas)]
        if max(abs(s) for s in pas) < 1e-10:
            break
    return th


def charger(dossier: Path, col: str) -> list[dict]:
    rows = []
    for lg in LIGUES:
        for r in backtest.read_predictions(dossier / lg / "predictions.csv"):
            rows.append({"ligue": lg, "match_id": r["match_id"], "issue": r["issue"], "v5": r[col],
                         "v5_cal": calibrate(r[col], B_V5, C_V5), "bookmaker": r["bookmaker"]})
    return rows


def evaluer(rows: list[dict], th: list[float]) -> dict:
    avec = [r for r in rows if r["bookmaker"]]
    for r in avec:
        r["fus"] = fusionner(r["v5_cal"], r["bookmaker"], th)
    sc = lambda k: score([(r[k], r["issue"]) for r in avec])  # noqa: E731
    return {"n": len(rows), "n_avec_cotes": len(avec),
            "scores": {k: {m: v for m, v in sc(k).items() if m != "calibration"} for k in ("fus", "bookmaker", "v5_cal")},
            "calibration_fus": sc("fus")["calibration"],
            "fus_moins_bookmaker": backtest.paired_bootstrap(avec, "fus", "bookmaker"),
            "fus_moins_v5_cal": backtest.paired_bootstrap(avec, "fus", "v5_cal"),
            "v5_cal_moins_bookmaker": backtest.paired_bootstrap(avec, "v5_cal", "bookmaker"),
            "par_ligue": {lg: backtest.paired_bootstrap([r for r in avec if r["ligue"] == lg], "fus", "bookmaker")
                          for lg in LIGUES}}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dev", type=Path, required=True)
    p.add_argument("--sortie", type=Path, required=True)
    a = p.parse_args(argv)
    dev = charger(a.dev, "270|2|0.35")
    ll = -sum(math.log(max(r["v5"][r["issue"]], 1e-15)) for r in dev if r["v5"]) / sum(1 for r in dev if r["v5"])
    n = sum(1 for r in dev if r["v5"] and r["bookmaker"])
    if abs(ll - CONTROLE_DEV[0]) > 1e-5:
        raise SystemExit(f"prévisions dev non conformes à EXP-008 : log-loss {ll:.6f} ≠ {CONTROLE_DEV[0]}")
    th = ajuster([r for r in dev if r["v5"] and r["bookmaker"]])
    out = {"protocole": "docs/experiences/EXP-017-fusion-marche.md",
           "controle_dev": {"log_loss_v5": round(ll, 6), "n_avec_cotes": n},
           "parametres": {"alpha_v5cal": round(th[0], 6), "beta_bookmaker": round(th[1], 6),
                          "c_H": round(th[2], 6), "c_D": round(th[3], 6)},
           "dev": evaluer([r for r in dev if r["v5"]], th)}
    for role in ("validation", "test"):
        out[role] = evaluer(charger(EXP8 / role, "candidat"), th)
    v, t = out["validation"], out["test"]
    out["criteres"] = {
        "M1_validation_ic_haut_negatif": v["fus_moins_bookmaker"]["ic95"][1] < 0,
        "M2_test_ic_haut_negatif": t["fus_moins_bookmaker"]["ic95"][1] < 0,
        "M3_test_4_ligues_sur_5": sum(x["ecart"] < 0 for x in t["par_ligue"].values()) >= 4,
        "M4_test_rps": t["scores"]["fus"]["rps"] <= t["scores"]["bookmaker"]["rps"]}
    out["verdict"] = "CANDIDAT" if all(out["criteres"].values()) else "REJETE"
    a.sortie.mkdir(parents=True, exist_ok=True)
    (a.sortie / "resultats.json").write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("controle_dev", "parametres", "criteres", "verdict")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
