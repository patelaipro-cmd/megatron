"""EXP-019 : marchés 2+ / 3+ buts sur les taux poisson-v5 (Platt) contre poisson-v4-platt.

Usage : python scripts/exp019_buts_v5.py --sortie docs/experiences/EXP-019
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from megatron import data, marches  # noqa: E402

TRAIN = {f"{y}/{str(y + 1)[-2:]}" for y in range(2008, 2020)}
TEST = {f"{y}/{str(y + 1)[-2:]}" for y in range(2020, 2026)}
LIGUES = ("F1", "E0", "D1", "SP1", "I1")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--sortie", required=True)
    out = Path(p.parse_args().sortie)
    goals = {m.match_id: m.home_goals + m.away_goals for m in data.load(data.CURRENT)}
    cotes = marches.load_cotes()
    with (ROOT / "docs/experiences/EXP-009/variables.csv").open(newline="", encoding="utf-8") as fh:
        v5 = {r["match_id"]: (r["saison"], float(r["lam_fav"]) + float(r["lam_adv"])) for r in csv.DictReader(fh)}
    v4 = {}
    for lg in LIGUES:
        for r in marches.read_predictions(ROOT / f"docs/experiences/EXP-007/{lg}/predictions_buts.csv"):
            v4[(r["match_id"], r["marche"])] = r["poisson-v4"]["oui"]
    res = {"non_joints": sum(1 for k in v5 if k not in goals)}
    for marche, seuil in marches.MARCHES_BUTS.items():
        rows = []
        for mid, (saison, lam) in v5.items():
            if mid not in goals:
                continue
            rows.append({"match_id": mid, "saison": saison, "issue": "oui" if goals[mid] >= seuil else "non",
                         "brut": marches.total_au_moins(lam, seuil)})
        a, b = marches.fit_platt([(r["brut"], int(r["issue"] == "oui")) for r in rows if r["saison"] in TRAIN])
        test = []
        for r in rows:
            if r["saison"] not in TEST or (r["match_id"], marche) not in v4:
                continue
            bk = marches.bookmaker_3plus(cotes.get(r["match_id"])) if marche == "3+" else None
            test.append({"match_id": r["match_id"], "issue": r["issue"],
                         "poisson-v5-platt": marches.platt(r["brut"], a, b),
                         "poisson-v4-platt": marches.platt(v4[(r["match_id"], marche)], *marches.PLATT_V4[marche]),
                         "bookmaker": bk})
        scores = {k: marches.score_binaire([(r[k], r["issue"]) for r in test])
                  for k in ("poisson-v5-platt", "poisson-v4-platt")}
        par_ligue = {lg: marches.bootstrap([r for r in test if r["match_id"].startswith(lg + ":")],
                                           "poisson-v5-platt", "poisson-v4-platt") for lg in LIGUES}
        b1 = marches.bootstrap(test, "poisson-v5-platt", "poisson-v4-platt")
        calib = [c for c in scores["poisson-v5-platt"]["calibration"] if c["n"] >= 500]
        res[marche] = {
            "platt_v5": {"a": round(a, 6), "b": round(b, 6)},
            "n_apprentissage": sum(r["saison"] in TRAIN for r in rows), "n_test": len(test),
            "scores": scores, "B1_v5_moins_v4": b1, "B1": b1["ic95"][1] < 0,
            "B2_par_ligue": par_ligue, "B2": sum(v["ecart"] < 0 for v in par_ligue.values()) >= 4,
            "B3_ecart_max": max((abs(c["ecart"]) for c in calib), default=None),
            "B3": bool(calib) and all(abs(c["ecart"]) <= 0.03 for c in calib),
            "info_v5_moins_bookmaker": marches.bootstrap(test, "poisson-v5-platt", "bookmaker") if marche == "3+" else None,
        }
        print(marche, res[marche]["platt_v5"], scores["poisson-v5-platt"]["log_loss"], scores["poisson-v4-platt"]["log_loss"],
              b1, {k: v["ecart"] for k, v in par_ligue.items()}, res[marche]["B3_ecart_max"],
              res[marche]["info_v5_moins_bookmaker"])
    out.mkdir(parents=True, exist_ok=True)
    (out / "resultats.json").write_text(json.dumps(res, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
