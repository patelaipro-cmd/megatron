"""Backtest 1X2 sur plusieurs ligues et saisons réunies (EXP-008).

Chaque (ligue, saison) est prédite avec le seul passé, en parallèle. Écrit
<sortie>/<ligue>/predictions.csv (relisible par ``python -m megatron bootstrap``)
et <sortie>/resultats.json (scores des 5 ligues réunies, triés par log-loss).

Grille : --grille 90,180:2,3:0.15,0.25 (demi-vies:rétrécissements:poids des cadres).
Modèles nommés : --configs candidat=135,5,0,moyenne,cadres,0.25;reference=90,3,0,moyenne,cadres,0.25
"""

from __future__ import annotations

import argparse
import json
import sys
from multiprocessing import Pool
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from megatron import backtest, data  # noqa: E402

LIGUES = ("F1", "E0", "D1", "SP1", "I1")


def _job(args: tuple) -> tuple[str, list[dict]]:
    division, season, configs, source = args
    matches = data.load(source or data.CURRENT, divisions={division})
    return division, backtest.predict_seasons(matches, division, {season}, configs)


def configs_from(args) -> dict[str, backtest.Config]:
    if args.configs:
        out = {}
        for item in args.configs.split(";"):
            name, text = item.split("=")
            hl, k, dc, prior, proxy, w = text.split(",")
            out[name] = (float(hl), float(k), bool(int(dc)), prior, proxy, float(w))
        return out
    hls, ks, ws = (part.split(",") for part in args.grille.split(":"))
    return {f"{hl}|{k}|{w}": (float(hl), float(k), False, "moyenne", "cadres", float(w))
            for hl in hls for k in ks for w in ws}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--saisons", required=True)
    p.add_argument("--ligues", default=",".join(LIGUES))
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--grille")
    g.add_argument("--configs")
    p.add_argument("--sortie", required=True)
    p.add_argument("--processus", type=int, default=4)
    p.add_argument("--donnees", default=None, help="CSV au format data/ (défaut : data.CURRENT) ; EXP-022")
    args = p.parse_args()
    configs = configs_from(args)
    jobs = [(d, s, configs, args.donnees) for d in args.ligues.split(",") for s in args.saisons.split(",")]
    by_league: dict[str, list[dict]] = {}
    with Pool(args.processus) as pool:
        for division, rows in pool.imap_unordered(_job, jobs):
            by_league.setdefault(division, []).extend(rows)
            print(f"{division} : {len(rows)} matchs", file=sys.stderr, flush=True)
    out = Path(args.sortie)
    all_rows = []
    par_ligue = {}
    for division in sorted(by_league):
        rows = sorted(by_league[division], key=lambda r: r["match_id"])
        (out / division).mkdir(parents=True, exist_ok=True)
        backtest.write_predictions(rows, out / division / "predictions.csv")
        par_ligue[division] = backtest.summarize(rows)
        all_rows += rows
    total = backtest.summarize(all_rows)
    classement = sorted((k for k in total if k in configs), key=lambda k: total[k]["log_loss"])
    result = {"saisons": args.saisons, "ligues": sorted(by_league), "configs": {k: list(v) for k, v in configs.items()},
              "classement": [{"modele": k, **total[k]} for k in classement],
              "bases": {k: total[k] for k in total if k not in configs}, "par_ligue": par_ligue}
    (out / "resultats.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for r in result["classement"][:5]:
        print(r["modele"], r["log_loss"], r["rps"], r["n"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
