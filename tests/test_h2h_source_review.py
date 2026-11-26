import csv
import unittest
from pathlib import Path

class TestH2HSourceReview(unittest.TestCase):
    def test_review_register_is_fail_closed(self):
        path = Path("data/h2h-source-review-2026-11-23.csv")
        with path.open(encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f))
        self.assertEqual(len(rows), 25)
        self.assertEqual(sum(r["review_status"] == "CORROBORATED_2_SOURCES" for r in rows), 17)
        self.assertEqual(sum(r["review_status"] == "UNVERIFIED" for r in rows), 8)
        self.assertTrue(all(r["review_status"] != "VERIFIED" for r in rows))
        self.assertTrue(all(r["source_1"] and r["source_2"] for r in rows
                            if r["review_status"] == "CORROBORATED_2_SOURCES"))
        friendly = [r for r in rows if r["date"] == "2026-07-17" and r["home"] == "Jong AZ"]
        self.assertEqual(len(friendly), 1)
        self.assertIn("friendly", friendly[0]["match_type"])

if __name__ == "__main__":
    unittest.main()
