import csv
import tempfile
import unittest
from pathlib import Path
from scripts.audit_h2h_quality import audit

class TestH2HQuality(unittest.TestCase):
    def test_existing_inputs_blocked(self):
        result = audit("data/fixtures_h2h_2026-11-23.csv", "data/h2h_verifies_2026-11-23.csv")
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["fixture_rows"], 15)
        self.assertTrue(any(x["dataset"] == "fixtures" for x in result["issues"]))
        self.assertTrue(any(x["dataset"] == "history" for x in result["issues"]))

    def test_traceable_inputs_can_proceed_to_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixtures = Path(tmp) / "fixtures.csv"
            history = Path(tmp) / "history.csv"
            with fixtures.open("w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=["home","away","date","kickoff","timezone","competition","fixture_id","status"])
                w.writeheader()
                w.writerow(dict(home="Alpha",away="Beta",date="2026-11-23",kickoff="18:00",timezone="Africa/Kinshasa",competition="League",fixture_id="id-1",status="scheduled"))
            with history.open("w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=["MatchDate","HomeTeam","AwayTeam","FTHome","FTAway","source_url","competition","match_type","verified_at"])
                w.writeheader()
                w.writerow(dict(MatchDate="2026-01-01",HomeTeam="Alpha",AwayTeam="Beta",FTHome="2",FTAway="1",source_url="https://example.org/fixture/1",competition="League",match_type="official",verified_at="2026-11-22"))
            self.assertEqual(audit(fixtures,history)["status"], "READY_FOR_REVIEW")

if __name__ == "__main__":
    unittest.main()
