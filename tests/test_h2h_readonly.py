import csv
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from megatron.h2h_readonly import lookup

class TestH2HReadonly(unittest.TestCase):
    def test_temporal_cutoff_and_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "h2h.csv"
            with path.open("w", newline="", encoding="utf-8") as h:
                w = csv.DictWriter(h, fieldnames=["date","match","h2h_1","h2h_2","h2h_3","h2h_count","status"])
                w.writeheader()
                w.writerow({"date":"2026-11-23","match":"Alpha - Beta",
                            "h2h_1":"2026-11-22 | Alpha 2-1 Beta",
                            "h2h_2":"2026-11-20 | Beta 0-1 Alpha",
                            "h2h_3":"2026-11-19 | Alpha 1-1 Beta",
                            "h2h_count":3,"status":"COMPLETE"})
            r = lookup(path,"Alpha","Beta","2026-11-23T18:00:00+01:00","2026-11-21T10:00:00+01:00")
            self.assertEqual(r["count"],2)
            self.assertEqual(r["status"],"DATA LIMITED")
            self.assertEqual(r["verification_status"], "UNVERIFIED")
            self.assertFalse(r["verified"])
            self.assertFalse(r["probability_adjustment"])
            self.assertEqual(lookup(path,"Other","Beta","2026-11-23","2026-11-22")["count"],0)
            complete = lookup(path,"Alpha","Beta","2026-11-23","2026-11-23")
            self.assertEqual(complete["count"],3)
            self.assertEqual(complete["status"], "COMPLETE")
            self.assertFalse(complete["verified"])

if __name__ == "__main__":
    unittest.main()
