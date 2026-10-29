"""Extrait les cotes plus/moins de 2,5 buts de Matches.csv (xgabora/Club-Football-Match-Data).

Usage : python scripts/extraire_cotes_buts.py chemin/vers/Matches.csv [--sortie data/cotes_buts_2000-2026.csv]
Filtre : F1, E0, D1, SP1, I1, matchs depuis le 01/07/2000 ayant les deux cotes Over25 et Under25.
Les matchs se relient à data/matches_top5_2000-2026.csv par (Division, MatchDate, HomeTeam, AwayTeam).
"""

import argparse
import csv
from pathlib import Path

DIVISIONS = {"F1", "E0", "D1", "SP1", "I1"}
COLUMNS = ["Division", "MatchDate", "HomeTeam", "AwayTeam", "Over25", "Under25"]
OUT = Path(__file__).resolve().parent.parent / "data" / "cotes_buts_2000-2026.csv"


def main(src: str, dest: Path = OUT, since: str = "2000-07-01") -> None:
    with open(src, newline="", encoding="utf-8") as fh, dest.open("w", newline="", encoding="utf-8") as out:
        w = csv.writer(out)
        w.writerow(COLUMNS)
        n = 0
        for r in csv.DictReader(fh):
            if r["Division"] in DIVISIONS and r["MatchDate"] >= since and r["Over25"] and r["Under25"]:
                w.writerow([r[c] for c in COLUMNS])
                n += 1
    print(f"{n} lignes écrites dans {dest}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("source")
    ap.add_argument("--sortie", type=Path, default=OUT)
    a = ap.parse_args()
    main(a.source, a.sortie)
