"""Ligne de commande : python -m megatron <commande>."""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict
from pathlib import Path

from . import backtest, checkpoint, data, inventory, llm
from .agents import fuse
from .store import MemoryStore

ROOT = Path(__file__).resolve().parent.parent


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="megatron")
    parser.add_argument("--memoire", default=str(ROOT / "memoire"))
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("reprise", help="affiche le dernier checkpoint")
    sub.add_parser("inventaire", help="régénère docs/registre-depots.md")
    lp = sub.add_parser("llm", help="connexion LLM : statut des fournisseurs ou appel de test")
    lp.add_argument("action", choices=["statut", "test"])
    lp.add_argument("--fournisseur", default="gemini", choices=sorted(llm.PROVIDERS))
    f = sub.add_parser("fusion", help="Méthode de Fusion sur un match (JSON)")
    f.add_argument("tache", help='ex. {"match_id": "x", "xg_home": 1.6, "xg_away": 0.9}')
    b = sub.add_parser("backtest", help="protocole chronologique dev / validation / test")
    b.add_argument("--division", default="F1")
    b.add_argument("--dev", default="2022/23")
    b.add_argument("--val", default="2023/24")
    b.add_argument("--test", default="2024/25,2025/26")
    b.add_argument("--half-lives", default="90,180,365,730")
    b.add_argument("--shrinks", default="1,3,10")
    b.add_argument("--dixon-coles", default="0", help="valeurs testées sur le dev, ex. 0,1")
    b.add_argument("--a-priori", default="moyenne", help="a priori des équipes nouvelles testés, ex. moyenne,faibles3")
    b.add_argument("--fixe", help="candidat déjà figé, ex. 90,3,0 ou 90,3,0,faibles3 : saute la recherche sur le dev")
    b.add_argument("--reference", help="modèle de référence évalué en parallèle, ex. 90,3,0")
    b.add_argument("--sortie", help="dossier où écrire resultats.json et predictions.csv")
    bs = sub.add_parser("bootstrap", help="bootstrap apparié groupé sur plusieurs predictions.csv")
    bs.add_argument("fichiers", nargs="+")
    bs.add_argument("--saisons", default="2024/25,2025/26")
    bs.add_argument("--a", default="candidat")
    bs.add_argument("--b", default="reference")
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
    elif args.cmd == "llm":
        if args.action == "statut":
            print(json.dumps(llm.status(), indent=2, ensure_ascii=False))
        else:
            rep = llm.complete(args.fournisseur, [{"role": "user", "content": "Réponds juste : ok"}],
                               max_tokens=5, use_cache=False)
            print(json.dumps(asdict(rep), indent=2, ensure_ascii=False))
    elif args.cmd == "fusion":
        result = fuse(json.loads(args.tache))
        result["reponses"] = [asdict(r) for r in result["reponses"]]
        print(json.dumps(result, indent=2, ensure_ascii=False))
    elif args.cmd == "backtest":
        print(json.dumps(run_backtest(args), indent=2, ensure_ascii=False))
    elif args.cmd == "bootstrap":
        keep = set(args.saisons.split(","))
        rows = [r for f in args.fichiers for r in backtest.read_predictions(Path(f)) if r["saison"] in keep]
        print(json.dumps(backtest.paired_bootstrap(rows, args.a, args.b), ensure_ascii=False))
    return 0


def _config(text: str) -> backtest.Config:
    hl, k, *rest = text.split(",")
    dc = bool(int(rest[0])) if rest else False
    return (float(hl), float(k), dc) + ((rest[1],) if len(rest) > 1 else ())


def run_backtest(args) -> dict:
    matches = data.load(divisions={args.division})
    out = {"division": args.division, "donnees": str(data.DEFAULT_CSV.name)}
    if args.fixe:
        candidate = _config(args.fixe)
    else:
        grid = backtest.grid_search(matches, args.division, {args.dev},
                                    [float(x) for x in args.half_lives.split(",")],
                                    [float(x) for x in args.shrinks.split(",")],
                                    [bool(int(x)) for x in args.dixon_coles.split(",")],
                                    tuple(args.a_priori.split(",")))
        out["grille_dev"] = grid
        candidate = (grid[0]["half_life"], grid[0]["shrink"], grid[0]["dixon_coles"], grid[0]["a_priori"])
    configs = {"candidat": candidate}
    if args.reference:
        configs["reference"] = _config(args.reference)
    out["modeles"] = {name: dict(zip(("half_life", "shrink", "dixon_coles", "a_priori"), c))
                      for name, c in configs.items()}
    all_rows = []
    for role, seasons in (("dev", args.dev), ("validation", args.val), ("test", args.test)):
        rows = backtest.predict_seasons(matches, args.division, set(seasons.split(",")), configs)
        all_rows += rows
        out[role] = {"saisons": seasons, **backtest.summarize(rows)}
        if args.reference:
            out[role]["bootstrap_candidat_moins_reference"] = backtest.paired_bootstrap(rows, "candidat", "reference")
    if args.sortie:
        folder = Path(args.sortie)
        folder.mkdir(parents=True, exist_ok=True)
        backtest.write_predictions(all_rows, folder / "predictions.csv")
        (folder / "resultats.json").write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return out


if __name__ == "__main__":
    raise SystemExit(main())
