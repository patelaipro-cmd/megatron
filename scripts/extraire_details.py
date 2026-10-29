"""Extrait les détails de match de Matches.csv (xgabora/Club-Football-Match-Data) pour les angles morts.

Usage : python scripts/extraire_details.py chemin/vers/Matches.csv [--sortie data/details_2000-2026.csv]
Filtre : F1, E0, D1, SP1, I1, matchs depuis le 01/07/2000. Colonnes : score à la mi-temps, cartons
rouges, corners, fautes, handicap asiatique (taille et cotes Bet365 selon le README d'origine).
Les matchs se relient à data/matches_top5_2000-2026.csv par (Division, MatchDate, HomeTeam, AwayTeam).
Elo et Form* d'origine ne sont pas repris : leur date de calcul n'est pas documentée (risque de fuite).
"""

import argparse
import csv
from pathlib import Path

DIVISIONS = {"F1", "E0", "D1", "SP1", "I1"}
KEYS = ["Division", "MatchDate", "HomeTeam", "AwayTeam"]
COUNTS = ["HTHome", "HTAway", "HomeRed", "AwayRed", "HomeCorners", "AwayCorners", "HomeFouls", "AwayFouls"]
HANDICAP = ["HandiSize", "HandiHome", "HandiAway"]
OUT = Path(__file__).resolve().parent.parent / "data" / "details_2000-2026.csv"


def main(src: str, dest: Path = OUT, since: str = "2000-07-01") -> None:
    with open(src, newline="", encoding="utf-8") as fh, dest.open("w", newline="", encoding="utf-8") as out:
        w = csv.writer(out)
        w.writerow(KEYS + COUNTS + HANDICAP)
        n = 0
        for r in csv.DictReader(fh):
            if r["Division"] in DIVISIONS and r["MatchDate"] >= since:
                w.writerow([r[c] for c in KEYS] + [str(int(float(r[c]))) if r[c] else "" for c in COUNTS]
                           + [r[c] for c in HANDICAP])
                n += 1
    print(f"{n} lignes écrites dans {dest}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("source")
    ap.add_argument("--sortie", type=Path, default=OUT)
    a = ap.parse_args()
    main(a.source, a.sortie)
