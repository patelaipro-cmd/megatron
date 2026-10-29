"""EXP-010 : recalibration p'_o ∝ p_o^b · exp(c_o) du 1X2 de poisson-v5.

Usage : python scripts/exp010_calibration.py --sortie docs/experiences/EXP-010
Lit les prévisions v5 d'EXP-008 (dev : colonne 270|2|0.35 ; validation et test : candidat).
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from megatron import backtest  # noqa: E402
from megatron.ledger import OUTCOMES, score  # noqa: E402

LIGUES = ("F1", "E0", "D1", "SP1", "I1")
EXP8 = Path(__file__).resolve().parent.parent / "docs" / "experiences" / "EXP-008"


def load(role: str, col: str) -> list[dict]:
    rows = []
    for lg in LIGUES:
        for r in backtest.read_predictions(EXP8 / role / lg / "predictions.csv"):
            rows.append({"ligue": lg, "issue": r["issue"], "v5": r[col], "bookmaker": r["bookmaker"]})
    return rows


def calibrate(p: dict[str, float], b: float, c: tuple[float, float]) -> dict[str, float]:
    z = {"H": b * math.log(max(p["H"], 1e-6)) + c[0], "D": b * math.log(max(p["D"], 1e-6)) + c[1],
         "A": b * math.log(max(p["A"], 1e-6))}
    m = max(z.values())
    e = {o: math.exp(v - m) for o, v in z.items()}
    s = sum(e.values())
    return {o: e[o] / s for o in OUTCOMES}


def fit(rows: list[dict], iters: int = 50) -> tuple[float, tuple[float, float]]:
    """Newton sur (b, c_H, c_D) : log-vraisemblance multinomiale concave."""
    th = [1.0, 0.0, 0.0]
    for _ in range(iters):
        g = [0.0] * 3
        h = [[0.0] * 3 for _ in range(3)]
        for r in rows:
            q = calibrate(r["v5"], th[0], (th[1], th[2]))
            lg = {o: math.log(max(r["v5"][o], 1e-6)) for o in OUTCOMES}
            # dérivées de z_o par rapport à (b, c_H, c_D)
            dz = {"H": (lg["H"], 1.0, 0.0), "D": (lg["D"], 0.0, 1.0), "A": (lg["A"], 0.0, 0.0)}
            mean = [sum(q[o] * dz[o][k] for o in OUTCOMES) for k in range(3)]
            y = r["issue"]
            for k in range(3):
                g[k] += dz[y][k] - mean[k]
                for j in range(3):
                    h[k][j] -= sum(q[o] * dz[o][k] * dz[o][j] for o in OUTCOMES) - mean[k] * mean[j]
        step = _solve(h, g)
        th = [t - s for t, s in zip(th, step)]
        if max(abs(s) for s in step) < 1e-10:
            break
    return th[0], (th[1], th[2])


def _solve(a, b):
    n = len(b)
    m = [row[:] + [b[i]] for i, row in enumerate(a)]
    for c in range(n):
        piv = max(range(c, n), key=lambda r: abs(m[r][c]))
        m[c], m[piv] = m[piv], m[c]
        for r in range(n):
            if r != c:
                f = m[r][c] / m[c][c]
                m[r] = [x - f * y for x, y in zip(m[r], m[c])]
    return [m[i][n] / m[i][i] for i in range(n)]


def evaluate(rows: list[dict], b: float, c: tuple[float, float]) -> dict:
    for r in rows:
        r["v5_cal"] = calibrate(r["v5"], b, c)
    common = [r for r in rows if r["bookmaker"]]
    out = {k: {m: v for m, v in score([(r[k], r["issue"]) for r in common]).items() if m != "calibration"} | (
        {"calibration": score([(r[k], r["issue"]) for r in common])["calibration"]} if k != "bookmaker" else {})
        for k in ("v5", "v5_cal", "bookmaker")}
    out["cal_moins_brut"] = backtest.paired_bootstrap(rows, "v5_cal", "v5")
    out["cal_moins_bookmaker"] = backtest.paired_bootstrap(common, "v5_cal", "bookmaker")
    out["brut_moins_bookmaker"] = backtest.paired_bootstrap(common, "v5", "bookmaker")
    out["par_ligue"] = {lg: backtest.paired_bootstrap([r for r in rows if r["ligue"] == lg], "v5_cal", "v5")
                        for lg in LIGUES}
    return out


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--sortie", required=True)
    a = p.parse_args()
    dev = load("dev", "270|2|0.35")
    b, c = fit(dev)
    res = {"parametres": {"b": round(b, 6), "c_H": round(c[0], 6), "c_D": round(c[1], 6)}, "n_dev": len(dev)}
    for role, rows in (("dev", dev), ("validation", load("validation", "candidat")), ("test", load("test", "candidat"))):
        res[role] = evaluate(rows, b, c)
    t = res["test"]
    res["criteres"] = {"K1": res["validation"]["cal_moins_brut"]["ic95"][1] < 0,
                       "K2": t["cal_moins_brut"]["ic95"][1] < 0,
                       "K3": sum(v["ecart"] < 0 for v in t["par_ligue"].values()) >= 4,
                       "K4": t["v5_cal"]["rps"] <= t["v5"]["rps"]}
    out = Path(a.sortie)
    out.mkdir(parents=True, exist_ok=True)
    (out / "resultats.json").write_text(json.dumps(res, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({k: res[k] for k in ("parametres", "criteres")}, ensure_ascii=False))
    for role in ("dev", "validation", "test"):
        r = res[role]
        print(role, r["v5"]["log_loss"], r["v5_cal"]["log_loss"], r["bookmaker"]["log_loss"], r["cal_moins_brut"],
              r["v5"]["rps"], r["v5_cal"]["rps"])
    print({lg: v["ecart"] for lg, v in t["par_ligue"].items()}, t["cal_moins_bookmaker"], t["brut_moins_bookmaker"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
