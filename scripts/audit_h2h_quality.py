#!/usr/bin/env python3
"""Fail-closed audit of fixture identity and independently traceable H2H records."""
import argparse
import csv
import json
from pathlib import Path

REQUIRED_FIXTURE = ("home", "away", "date", "kickoff", "timezone", "competition", "fixture_id", "status")
REQUIRED_HISTORY = ("MatchDate", "HomeTeam", "AwayTeam", "FTHome", "FTAway", "source_url", "competition", "match_type", "verified_at")

def audit(fixtures, history):
    issues = []
    fixture_count = history_count = 0
    with Path(fixtures).open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = sorted(set(REQUIRED_FIXTURE) - set(reader.fieldnames or ()))
        if missing:
            issues.append({"dataset": "fixtures", "issue": "missing_columns", "columns": missing})
        for number, row in enumerate(reader, 2):
            fixture_count += 1
            if not missing and (any(not row.get(k, "").strip() for k in REQUIRED_FIXTURE) or row["status"].lower() not in ("scheduled", "not_started")):
                issues.append({"dataset": "fixtures", "line": number, "issue": "unverified_fixture"})
    with Path(history).open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = sorted(set(REQUIRED_HISTORY) - set(reader.fieldnames or ()))
        if missing:
            issues.append({"dataset": "history", "issue": "missing_columns", "columns": missing})
        for number, row in enumerate(reader, 2):
            history_count += 1
            if not missing and any(not row.get(k, "").strip() for k in REQUIRED_HISTORY):
                issues.append({"dataset": "history", "line": number, "issue": "missing_provenance"})
    return {"status": "BLOCKED" if issues else "READY_FOR_REVIEW", "fixture_rows": fixture_count,
            "history_rows": history_count, "issues": issues}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixtures", default="data/fixtures_h2h_2026-11-23.csv")
    parser.add_argument("--history", default="data/h2h_verifies_2026-11-23.csv")
    parser.add_argument("--output", default="h2h-quality-audit.json")
    args = parser.parse_args()
    report = audit(args.fixtures, args.history)
    Path(args.output).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{report['status']}: {report['fixture_rows']} fixtures, {report['history_rows']} historic rows, {len(report['issues'])} issue groups")
    return 1 if report["status"] == "BLOCKED" else 0

if __name__ == "__main__":
    raise SystemExit(main())
