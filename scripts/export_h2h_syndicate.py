#!/usr/bin/env python3
"""Export H2H extraction to a compact SYNDICATE-ready, read-only CSV."""
import argparse
import csv
import json

def export(rows, output):
    with open(output, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["date", "match", "h2h_1", "h2h_2", "h2h_3", "h2h_count", "status"])
        writer.writeheader()
        for item in rows:
            values = []
            for h in item["h2h"][:3]:
                values.append(f"{h['date']} | {h['home']} {h['score']} {h['away']}")
            values += [""] * (3 - len(values))
            writer.writerow(dict(date=item["fixture_date"], match=f"{item['home']} - {item['away']}",
                                 h2h_1=values[0], h2h_2=values[1], h2h_3=values[2],
                                 h2h_count=item["count"], status=item["status"]))

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--input", default="h2h-results.json")
    p.add_argument("--output", default="syndicate-h2h.csv")
    a = p.parse_args()
    with open(a.input, encoding="utf-8") as f:
        export(json.load(f), a.output)
