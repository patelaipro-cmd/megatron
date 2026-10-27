"""Ligne de commande : python -m megatron <commande>."""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict
from pathlib import Path

from . import backtest, checkpoint, data, inventory
from .agents import fuse
from .store import MemoryStore

ROOT = Path(__file__).resolve().parent.parent


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="megatron")
    parser.add_argument("--memoire", default=str(ROOT / "memoire"))
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("reprise", help="affiche le dernier checkpoint")
    sub.add_parser("inventaire", help="régénère docs/registre-depots.md")
    f = sub.add_parser("fusion", help="Méthode de Fusion sur un match (JSON)")
    f.add_argument("tache", help='ex. {"match_id": "x", "xg_home": 1.6, "xg_away": 0.9}')
    b = sub.add_parser("backtest", help="protocole chronologique dev / validation / test")
    b.add_argument("--division", default="F1")
    b.add_argument("--dev", default="2022/23")
    b.add_argument("--val", default="2023/24")
    b.add_argument("--test", default="2024/25,2025/26")
    b.add_argument("--half-lives", default="90,180,365,730")
    b.add_argument("--shrinks", default="1,3,10")
    b.add_argument("--fixe", help="hyperparamètres déjà figés, ex. 365,3 : saute la recherche sur le dev")
    b.add_argument("--sortie", help="dossier où écrire resultats.json et predictions.csv")
    args = parser.parse_args(argv)

    if args.cmd == "reprise":
        ckpt = checkpoint.load(MemoryStore(args.memoire))
        print(json.dumps(ckpt, indent=2, ensure_ascii=False) if ckpt else "aucun checkpoint")
    elif args.cmd == "inventaire":
        rows, counts = inventory.build(ROOT / "docs" / "inventaires", ROOT / "docs" / "evaluations.json")
        (ROOT / "docs" / "registre-depots.md").write_text(inventory.render_markdown(rows, counts), encoding="utf-8")
        with (ROOT / "docs" / "registre-depots.csv").open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        print(f"{sum(counts.values())} entrées, {len(rows)} dépôts uniques")
    elif args.cmd == "fusion":
        result = fuse(json.loads(args.tache))
        result["reponses"] = [asdict(r) for r in result["reponses"]]
        print(json.dumps(result, indent=2, ensure_ascii=False))
    elif args.cmd == "backtest":
        print(json.dumps(run_backtest(args), indent=2, ensure_ascii=False))
    return 0


def run_backtest(args) -> dict:
    matches = data.load(divisions={args.division})
    out = {"division": args.division, "donnees": str(data.DEFAULT_CSV.name)}
    if args.fixe:
        hl, k = (float(x) for x in args.fixe.split(","))
    else:
        grid = backtest.grid_search(matches, args.division, {args.dev},
                                    [float(x) for x in args.half_lives.split(",")],
                                    [float(x) for x in args.shrinks.split(",")])
        out["grille_dev"] = grid
        hl, k = grid[0]["half_life"], grid[0]["shrink"]
    out["hyperparametres"] = {"half_life": hl, "shrink": k}
    all_rows = []
    for role, seasons in (("dev", args.dev), ("validation", args.val), ("test", args.test)):
        rows = backtest.predict_seasons(matches, args.division, set(seasons.split(",")), half_life=hl, shrink=k)
        all_rows += rows
        out[role] = {"saisons": seasons, **backtest.summarize(rows)}
    if args.sortie:
        folder = Path(args.sortie)
        folder.mkdir(parents=True, exist_ok=True)
        backtest.write_predictions(all_rows, folder / "predictions.csv")
        (folder / "resultats.json").write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return out


if __name__ == "__main__":
    raise SystemExit(main())
