"""Reconstruit data/matches_top5_2020-2026.csv depuis Matches.csv (xgabora/Club-Football-Match-Data).

Usage : python scripts/extraire_donnees.py chemin/vers/Matches.csv
Filtre : F1, E0, D1, SP1, I1, matchs à partir du 01/07/2020. Les comptes (buts, tirs) sont écrits en entiers.
"""

import csv
import sys
from pathlib import Path

DIVISIONS = {"F1", "E0", "D1", "SP1", "I1"}
COLUMNS = ["Division", "MatchDate", "MatchTime", "HomeTeam", "AwayTeam", "FTHome", "FTAway", "FTResult",
           "OddHome", "OddDraw", "OddAway", "HomeShots", "AwayShots", "HomeTarget", "AwayTarget"]
COUNTS = {"FTHome", "FTAway", "HomeShots", "AwayShots", "HomeTarget", "AwayTarget"}
OUT = Path(__file__).resolve().parent.parent / "data" / "matches_top5_2020-2026.csv"


def main(src: str) -> None:
    with open(src, newline="", encoding="utf-8") as fh, OUT.open("w", newline="", encoding="utf-8") as out:
        w = csv.writer(out)
        w.writerow(COLUMNS)
        n = 0
        for r in csv.DictReader(fh):
            if r["Division"] in DIVISIONS and r["MatchDate"] >= "2020-07-01":
                w.writerow([str(int(float(r[c]))) if c in COUNTS and r[c] else r[c] for c in COLUMNS])
                n += 1
    print(f"{n} lignes écrites dans {OUT}")


if __name__ == "__main__":
    main(sys.argv[1])
