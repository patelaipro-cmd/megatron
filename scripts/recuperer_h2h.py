#!/usr/bin/env python3
"""Extract up to three prior H2H fixtures from MEGATRON historical CSVs."""
import argparse
import csv
import json
import re
import unicodedata
from datetime import date
from pathlib import Path

DEFAULT_SOURCES = [
    "data/matches_top5_2000-2026.csv",
    "data/matches_autres_2000-2026.csv",
    "data/complement_openfootball_2026-27.csv",
    "data/complement_resultats_2026-27.csv",
]

def normalize(value):
    value = unicodedata.normalize("NFKD", value.casefold())
    value = "".join(c for c in value if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]", "", value)

def aliases(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    groups = {}
    for canonical, names in data.items():
        if canonical.startswith("_") or not isinstance(names, list):
            continue
        group = {normalize(x) for x in [canonical, *names]}
        for name in group:
            groups[name] = group
    return groups

def equivalent(left, right, groups):
    a, b = normalize(left), normalize(right)
    return a == b or (a in groups and b in groups[a])

def load(sources):
    records = {}
    for source in sources:
        path = Path(source)
        if not path.exists():
            continue
        with path.open(encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                try:
                    day = date.fromisoformat(row["MatchDate"][:10])
                    home, away = row["HomeTeam"].strip(), row["AwayTeam"].strip()
                    gh, ga = int(row["FTHome"]), int(row["FTAway"])
                except (ValueError, TypeError, KeyError, AttributeError):
                    continue
                key = (day.isoformat(), normalize(home), normalize(away), gh, ga)
                records.setdefault(key, dict(date=day.isoformat(), home=home, away=away,
                                             score=f"{gh}-{ga}", source=str(path)))
    return list(records.values())

def retrieve(home, away, before, records, groups, limit=3):
    matches = [r for r in records if r["date"] < before and (
        (equivalent(home, r["home"], groups) and equivalent(away, r["away"], groups)) or
        (equivalent(home, r["away"], groups) and equivalent(away, r["home"], groups)))]
    matches.sort(key=lambda r: (r["date"], r["home"], r["away"]), reverse=True)
    return matches[:limit]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixtures", required=True, help="CSV with home,away,date columns")
    parser.add_argument("--output", default="h2h-results.json")
    parser.add_argument("--sources", nargs="+", default=DEFAULT_SOURCES)
    parser.add_argument("--aliases", default="data/noms_equipes.json")
    parser.add_argument("--coverage-output", default="h2h-coverage.csv")
    args = parser.parse_args()
    groups = aliases(args.aliases)
    records = load(args.sources)
    if not records:
        parser.error("No historical records available")
    output = []
    with open(args.fixtures, encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            home, away = row["home"].strip(), row["away"].strip()
            before = date.fromisoformat(row["date"][:10]).isoformat()
            matches = retrieve(home, away, before, records, groups)
            output.append(dict(home=home, away=away, fixture_date=before,
                               h2h=matches, count=len(matches),
                               status="COMPLETE" if len(matches) == 3 else "DATA LIMITED"))
    Path(args.output).write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with open(args.coverage_output, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["home", "away", "fixture_date", "count", "missing", "status"])
        writer.writeheader()
        for entry in output:
            writer.writerow({
                "home": entry["home"], "away": entry["away"],
                "fixture_date": entry["fixture_date"], "count": entry["count"],
                "missing": 3 - entry["count"], "status": entry["status"],
            })
    print(f"{len(output)} fixtures, {sum(x['count'] for x in output)} H2H found; "
          f"{sum(3-x['count'] for x in output)} missing")

if __name__ == "__main__":
    main()
