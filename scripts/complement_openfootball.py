"""Complète la saison en cours avec openfootball/football.json (domaine public, CC0).

Usage : python scripts/complement_openfootball.py [--saison 2026-27]
Les noms d'équipes openfootball sont reliés à ceux de xgabora en comparant les
matchs communs (même date, même score) de cette saison et de la précédente ;
un nom non relié bloque l'écriture.
Seuls les matchs postérieurs au dernier jour de data/matches_top5_2000-2026.csv
sont écrits, sans cotes ni tirs (absents de la source).
"""

import argparse
import csv
import json
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / "data" / "matches_top5_2000-2026.csv"
URL = "https://raw.githubusercontent.com/openfootball/football.json/master/{saison}/{code}.json"
LEAGUES = {"E0": "en.1", "F1": "fr.1", "D1": "de.1", "SP1": "es.1", "I1": "it.1"}
COLUMNS = ["Division", "MatchDate", "MatchTime", "HomeTeam", "AwayTeam", "FTHome", "FTAway", "FTResult",
           "OddHome", "OddDraw", "OddAway", "HomeShots", "AwayShots", "HomeTarget", "AwayTarget"]


def played(saison: str, code: str) -> list[dict]:
    with urllib.request.urlopen(URL.format(saison=saison, code=code), timeout=30) as resp:
        data = json.load(resp)
    out = []
    for m in data["matches"]:
        sc = m.get("score")
        ft = sc.get("ft") if isinstance(sc, dict) else sc  # deux formats : {"ft": [h, a]} ou [h, a]
        if isinstance(ft, list) and len(ft) == 2:
            out.append({**m, "ft": tuple(ft)})
    return out


def name_map(division: str, of_matches: list[dict], base: list[dict]) -> dict[str, str]:
    """Vote : chaque match commun (date, score) relie domicile et extérieur ; un nom ↔ un nom.

    1er passage : matchs dont (date, score) est unique ce jour-là. Passages suivants :
    un (date, score) partagé est tranché par l'équipe adverse déjà reliée.
    """
    by_key = defaultdict(list)
    for r in base:
        if r["Division"] == division:
            by_key[(r["MatchDate"], int(r["FTHome"]), int(r["FTAway"]))].append(r)
    mapping: dict[str, str] = {}
    for _ in range(5):
        votes: dict[str, Counter] = defaultdict(Counter)
        for m in of_matches:
            cands = by_key.get((m["date"], *m["ft"]), [])
            if len(cands) > 1 and mapping:
                cands = [c for c in cands if mapping.get(m["team1"]) == c["HomeTeam"]
                         or mapping.get(m["team2"]) == c["AwayTeam"]]
            if len(cands) == 1:
                votes[m["team1"]][cands[0]["HomeTeam"]] += 1
                votes[m["team2"]][cands[0]["AwayTeam"]] += 1
        new = {}
        for of_name, c in votes.items():
            (best, n), *rest = c.most_common()
            if not rest or n > rest[0][1]:
                new[of_name] = best
        if new == mapping:
            break
        mapping = new
    if len(set(mapping.values())) != len(mapping):
        raise SystemExit(f"{division} : correspondance ambiguë {mapping}")
    return mapping


def hour_offset(division: str, of_matches: list[dict], base: list[dict], mapping: dict[str, str]) -> int:
    """Décalage horaire médian openfootball → convention xgabora, mesuré sur les matchs communs."""
    times = {(r["MatchDate"], r["HomeTeam"]): r["MatchTime"] for r in base if r["Division"] == division}
    diffs = sorted(int(times[k][:2]) - int(m["time"][:2]) for m in of_matches
                   if m.get("time") and (k := (m["date"], mapping.get(m["team1"]))) in times and times[k])
    return diffs[len(diffs) // 2] if diffs else 0


def previous(saison: str) -> str:
    start = int(saison[:4]) - 1
    return f"{start}-{str(start + 1)[-2:]}"


def main(saison: str, dest: Path) -> None:
    with BASE.open(newline="", encoding="utf-8") as fh:
        base = list(csv.DictReader(fh))
    last = max(r["MatchDate"] for r in base)
    rows, problems, report = [], [], {}
    for div, code in LEAGUES.items():
        matches = played(saison, code)
        common = [m for m in matches if m["date"] <= last] + played(previous(saison), code)
        mapping = name_map(div, common, base)
        offset = hour_offset(div, common, base, mapping)
        report[div] = {"noms_relies": len(mapping), "decalage_h": offset}
        for m in matches:
            if m["date"] <= last:
                continue
            missing = [t for t in (m["team1"], m["team2"]) if t not in mapping]
            if missing:
                problems.append(f"{div} {m['date']} : {missing} sans correspondance")
                continue
            hg, ag = m["ft"]
            res = "H" if hg > ag else "A" if ag > hg else "D"
            hhmm = ""
            if m.get("time"):
                hh, mm = m["time"].split(":")[:2]
                hhmm = f"{(int(hh) + offset) % 24:02d}:{mm}:00"  # jour inchangé : aucun match près de minuit
            rows.append([div, m["date"], hhmm, mapping[m["team1"]], mapping[m["team2"]],
                         hg, ag, res] + [""] * 7)
    if problems:
        raise SystemExit("\n".join(problems))
    rows.sort(key=lambda r: (r[1], r[2], r[0], r[3]))
    with dest.open("w", newline="", encoding="utf-8") as out:
        w = csv.writer(out)
        w.writerow(COLUMNS)
        w.writerows(rows)
    print(f"{len(rows)} matchs après le {last} écrits dans {dest}")
    for div, info in report.items():
        print(div, info)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--saison", default="2026-27")
    ap.add_argument("--sortie", type=Path, default=ROOT / "data" / "complement_openfootball_2026-27.csv")
    a = ap.parse_args()
    main(a.saison, a.sortie)
