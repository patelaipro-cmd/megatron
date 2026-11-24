import csv
import tempfile
import unittest
from pathlib import Path
from scripts.h2h_evidence_register import build_register, main

class TestH2HEvidenceRegister(unittest.TestCase):
    def test_existing_historical_data_is_not_self_verified(self):
        rows = build_register("data/h2h_verifies_2026-11-23.csv")
        self.assertGreater(len(rows), 0)
        self.assertTrue(all(row["verification_status"] == "UNVERIFIED" for row in rows))
        self.assertTrue(all("source_url" in row["missing_evidence"] for row in rows))

    def test_metadata_does_not_imply_verification(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "history.csv"
            with path.open("w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=["MatchDate","HomeTeam","AwayTeam",
                    "FTHome","FTAway","source_url","verified_at","match_type","competition"])
                w.writeheader()
                w.writerow(dict(MatchDate="2025-01-01",HomeTeam="A",AwayTeam="B",
                    FTHome=2,FTAway=1,source_url="https://example.org/a",
                    verified_at="2026-11-23",match_type="official",competition="League"))
            row = build_register(path)[0]
            self.assertEqual(row["missing_evidence"], [])
            self.assertEqual(row["verification_status"], "UNVERIFIED")

if __name__ == "__main__":
    unittest.main()
