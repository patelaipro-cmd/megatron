"""Collecte unique de l'historique Transfermarkt (dcaribou/transfermarkt-datasets) pour EXP-013.

Usage (workflow `transfermarkt-historique`, serveurs GitHub : les fichiers sont hébergés sur R2,
inaccessible depuis l'environnement cloud) :
  python scripts/collecte_transfermarkt_historique.py --sortie <externe/>
Écrit <sortie>/transfermarkt/historique/<table>.csv.gz, filtrés sur les 5 championnats (matchs,
compositions, apparitions, joueurs, valeurs des joueurs vus, clubs), et manifeste.json.
Données figées au 06/07/2026 (projet en pause). Compositions = connues ~1 h avant le coup d'envoi ;
apparitions et valeurs = à dater avant usage (seul le passé d'un match sert à le prévoir).
"""
from __future__ import annotations

import argparse
import csv
import gzip
import io
import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE = "https://pub-e682421888d945d684bcae8890b0ec20.r2.dev/data/"
LIGUES = {"GB1": "E0", "ES1": "SP1", "IT1": "I1", "L1": "D1", "FR1": "F1"}
csv.field_size_limit(sys.maxsize)


def lignes(table: str):
    req = urllib.request.Request(BASE + f"{table}.csv.gz", headers={"User-Agent": "MEGATRON-collecte/1.0"})
    with urllib.request.urlopen(req, timeout=600) as r:
        brut = r.read()
    yield from csv.DictReader(io.TextIOWrapper(gzip.GzipFile(fileobj=io.BytesIO(brut)), encoding="utf-8", newline=""))


def filtrer(table: str, dossier: Path, garder, cle: str | None = None) -> tuple[int, int, set[str]]:
    """Écrit les lignes gardées ; renvoie (lignes lues, lignes gardées, valeurs de ``cle`` gardées)."""
    valeurs, n, k = set(), 0, 0
    chemin = dossier / f"{table}.csv.gz"
    with gzip.open(chemin, "wt", encoding="utf-8", newline="") as out:
        w = None
        for r in lignes(table):
            n += 1
            if not garder(r):
                continue
            if w is None:
                w = csv.DictWriter(out, fieldnames=list(r))
                w.writeheader()
            w.writerow(r)
            k += 1
            if cle and r.get(cle):
                valeurs.add(r[cle])
    return n, k, valeurs


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--sortie", type=Path, required=True)
    a = p.parse_args(argv)
    dossier = a.sortie / "transfermarkt" / "historique"
    dossier.mkdir(parents=True, exist_ok=True)
    manifeste = {"source": BASE, "ligues": LIGUES, "collecte_le": datetime.now(timezone.utc).isoformat(), "tables": {}}

    def noter(table, n, k):
        manifeste["tables"][table] = {"lignes_source": n, "lignes_gardees": k}
        print(table, manifeste["tables"][table], flush=True)

    try:
        n, k, ids = filtrer("games", dossier, lambda r: r.get("competition_id") in LIGUES, cle="game_id")
        noter("games", n, k)
        joueurs: set[str] = set()
        for table in ("game_lineups", "appearances"):
            n, k, vus = filtrer(table, dossier, lambda r: r.get("game_id") in ids, cle="player_id")
            joueurs |= vus
            noter(table, n, k)
        for table in ("players", "player_valuations"):
            noter(table, *filtrer(table, dossier, lambda r: r.get("player_id") in joueurs)[:2])
        noter("clubs", *filtrer("clubs", dossier, lambda r: True)[:2])
        code = 0
    except Exception as exc:  # manifeste écrit quoi qu'il arrive
        manifeste["erreur"] = f"{type(exc).__name__}: {exc}"[:300]
        code = 1
    (dossier / "manifeste.json").write_text(json.dumps(manifeste, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return code


if __name__ == "__main__":
    sys.exit(main())
