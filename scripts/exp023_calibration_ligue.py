"""EXP-023 : recalibration 1X2 par ligue. Protocole : docs/experiences/EXP-023-calibration-par-ligue.md.

Usage : python scripts/exp023_calibration_ligue.py --brut docs/experiences/EXP-022/brut --sortie docs/experiences/EXP-023
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
from exp022_autres_ligues import B5, C5, LIGUES, calibration_ok, charger  # noqa: E402
from megatron import backtest  # noqa: E402
from megatron.ledger import score  # noqa: E402


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--brut", type=Path, required=True)
    p.add_argument("--sortie", type=Path, required=True)
    a = p.parse_args(argv)
    d = charger(a.brut)
    out = {"protocole": "docs/experiences/EXP-023-calibration-par-ligue.md", "par_ligue": {}}
    couvertes = []
    for lg in LIGUES:
        part = {k: [r for r in v if r["ligue"] == lg] for k, v in d.items()}
        b, c = fit(part["dev"])
        for rows in part.values():
            for r in rows:
                r["A"], r["C"] = calibrate(r["v5"], B5, C5), calibrate(r["v5"], b, c)
        k1 = backtest.paired_bootstrap(part["validation"], "C", "A")
        m = "C" if k1["ic95"][1] < 0 else "A"
        t = part["test"]
        cl = [r for r in t if r["bookmaker"]]
        k2 = backtest.paired_bootstrap(t, m, "frequences")
        k3, tranches = calibration_ok(t, m)
        res = {"parametres_C": {"b": round(b, 6), "c_H": round(c[0], 6), "c_D": round(c[1], 6)},
               "n": {k: len(v) for k, v in part.items()}, "K1_C_moins_A_validation": k1, "modele": m,
               "C_moins_A_test": backtest.paired_bootstrap(t, "C", "A"),
               "log_loss_test": {k: score([(r[k], r["issue"]) for r in t])["log_loss"] for k in ("A", "C", "frequences")},
               "K2_M_moins_frequences": k2, "K3": k3, "tranches_hors_tolerance": [x for x in tranches if not x["ok"]],
               "M_moins_bookmaker": backtest.paired_bootstrap(cl, m, "bookmaker") if cl else None}
        out["par_ligue"][lg] = res
        if k2["ic95"][1] < 0 and k3:
            couvertes.append(lg)
        print(lg, m, res["parametres_C"], k1, res["C_moins_A_test"], k3,
              [(x["issue"], x["tranche"], x["prevu"], x["observe"]) for x in res["tranches_hors_tolerance"]], flush=True)
    out["ligues_couvertes"] = couvertes
    a.sortie.mkdir(parents=True, exist_ok=True)
    (a.sortie / "resultats.json").write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print("couvertes", len(couvertes), couvertes)
    return 0


if __name__ == "__main__":
    sys.exit(main())
