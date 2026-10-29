"""Lecture des données de la branche `donnees-externes` sans fuite temporelle.

Préparer une copie locale (lecture seule, hors de main) :
    git fetch origin donnees-externes
    git worktree add --detach ../megatron-externe origin/donnees-externes

Usage :
    python scripts/lire_externe.py --dossier ../megatron-externe/externe statut
    python scripts/lire_externe.py --dossier ../megatron-externe/externe joueurs --equipe '<nom Sofascore>' --avant '<date avec fuseau>'

`joueurs` rend le dernier instantané Sofascore collecté strictement avant `--avant`
qui contient l'équipe (compo si confirmée, absents et incertains). Une ligne
lue ici reste un fait déclaratif à citer avec sa source et sa date de collecte ;
elle ne modifie aucune probabilité.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime
from pathlib import Path


def instant(texte: str) -> datetime:
    d = datetime.fromisoformat(texte)
    if d.tzinfo is None:
        raise ValueError("date avec fuseau requise")
    return d


def joueurs(dossier: Path, equipe: str, avant: datetime, source: str = "sofascore") -> list[dict]:
    """Lignes de l'équipe dans le dernier instantané collecté avant `avant` qui la mentionne."""
    for fichier in sorted((dossier / source).glob("*/*.csv"), reverse=True):
        lignes = list(csv.DictReader(fichier.read_text(encoding="utf-8").splitlines()))
        if not lignes or instant(lignes[0]["collecte_le"]) >= avant:
            continue
        retenues = [l for l in lignes if l.get("equipe") == equipe]
        if retenues:
            return retenues
    return []


def statut(dossier: Path) -> dict:
    manifeste = dossier / "manifeste.json"
    out = json.loads(manifeste.read_text(encoding="utf-8")) if manifeste.exists() else {}
    out["instantanes"] = {s.name: len(list(s.glob("*/*.csv"))) for s in sorted(dossier.iterdir()) if s.is_dir()}
    return out


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--dossier", required=True, type=Path)
    sub = p.add_subparsers(dest="commande", required=True)
    sub.add_parser("statut")
    j = sub.add_parser("joueurs")
    j.add_argument("--equipe", required=True)
    j.add_argument("--avant", required=True, type=instant)
    j.add_argument("--source", default="sofascore", choices=("sofascore", "fpl"))
    a = p.parse_args(argv)
    if a.commande == "statut":
        print(json.dumps(statut(a.dossier), indent=1, ensure_ascii=False))
        return 0
    lignes = joueurs(a.dossier, a.equipe, a.avant, a.source)
    if not lignes:
        print("aucune donnée collectée avant cette date pour cette équipe", file=sys.stderr)
        return 1
    w = csv.DictWriter(sys.stdout, fieldnames=list(lignes[0]))
    w.writeheader()
    w.writerows(lignes)
    return 0


if __name__ == "__main__":
    sys.exit(main())
