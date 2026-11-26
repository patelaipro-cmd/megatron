#!/usr/bin/env python3
"""Per-result H2H evidence register. Never self-certifies historical scores."""
import argparse
import csv
import json
from pathlib import Path

def build_register(history_path):
    rows = []
    with Path(history_path).open(encoding="utf-8-sig", newline="") as f:
        for line, row in enumerate(csv.DictReader(f), 2):
            source_url = (row.get("source_url") or "").strip()
            checked_at = (row.get("verified_at") or "").strip()
            match_type = (row.get("match_type") or "").strip()
            competition = (row.get("competition") or "").strip()
            # Evidence metadata alone is insufficient: only an independent
            # review may promote a row to VERIFIED.
            missing = [key for key, value in (("source_url", source_url),
                       ("verified_at", checked_at), ("match_type", match_type),
                       ("competition", competition)) if not value]
            rows.append({"line": line, "date": row.get("MatchDate", ""),
                "home": row.get("HomeTeam", ""), "away": row.get("AwayTeam", ""),
                "score": f"{row.get('FTHome', '')}-{row.get('FTAway', '')}",
                "source_url": source_url, "verified_at": checked_at,
                "match_type": match_type, "competition": competition,
                "missing_evidence": missing, "verification_status": "UNVERIFIED"})
    return rows

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--history", default="data/h2h_verifies_2026-11-23.csv")
    p.add_argument("--output", default="h2h-evidence-register.csv")
    args = p.parse_args()
    rows = build_register(args.history)
    fields = ["line", "date", "home", "away", "score", "source_url",
              "verified_at", "match_type", "competition",
              "missing_evidence", "verification_status"]
    with Path(args.output).open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for row in rows:
            w.writerow({**row, "missing_evidence": "|".join(row["missing_evidence"])})
    print(json.dumps({"rows": len(rows), "verified": 0,
                      "unverified": len(rows), "output": args.output}))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
