"""Read-only H2H enrichment for SYNDICATE V1/V2, with strict temporal cutoffs."""
import csv
from datetime import date
from pathlib import Path
from scripts.recuperer_h2h import normalize

def lookup(path, home, away, kickoff, at):
    """Return metadata only. No probabilities or decisions are changed."""
    cutoff = min(date.fromisoformat(str(kickoff)[:10]), date.fromisoformat(str(at)[:10]))
    with Path(path).open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            match = row["match"].split(" - ", 1)
            if len(match) != 2 or [normalize(x) for x in match] != [normalize(home), normalize(away)]:
                continue
            if date.fromisoformat(row["date"][:10]) != date.fromisoformat(str(kickoff)[:10]):
                continue
            selected = []
            for field in ("h2h_1", "h2h_2", "h2h_3"):
                value = row.get(field, "")
                if value and date.fromisoformat(value[:10]) < cutoff:
                    selected.append(value)
            return {"matches": selected, "count": len(selected),
                    "status": "COMPLETE" if len(selected) == 3 else "DATA LIMITED",
                    "verification_status": "UNVERIFIED",
                    "verified": False,
                    "cutoff": cutoff.isoformat(), "probability_adjustment": False}
    return {"matches": [], "count": 0, "status": "DATA LIMITED",
            "verification_status": "UNVERIFIED", "verified": False,
            "cutoff": cutoff.isoformat(), "probability_adjustment": False}
