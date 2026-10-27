"""Ligne de commande : python -m megatron <commande>."""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict
from pathlib import Path

from . import checkpoint, inventory
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
