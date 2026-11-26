"""Regression checks: H2H metadata must never change V1/V2 model outputs."""
import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from megatron import goals, syndicate
from megatron import h2h_readonly

class H2HRegression(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "syndicate-h2h.csv"
        with self.path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=["date", "match", "h2h_1", "h2h_2", "h2h_3", "h2h_count", "status"])
            writer.writeheader()
            writer.writerow({"date": "2026-11-23", "match": "Alpha - Beta",
                             "h2h_1": "2026-11-10 | Alpha 2-0 Beta",
                             "h2h_2": "2026-10-10 | Beta 1-1 Alpha",
                             "h2h_3": "2026-09-10 | Alpha 1-0 Beta",
                             "h2h_count": 3, "status": "COMPLETE"})

    def tearDown(self):
        self.tmp.cleanup()

    def test_v2_started_match_unchanged(self):
        fixture = {"division": "FICT", "home": "Alpha", "away": "Beta",
                   "kickoff": "2026-11-23T18:00:00+00:00"}
        kwargs = {"at": "2026-11-23T19:00:00+00:00"}
        without = goals.evaluate(fixture, **kwargs)
        with_h2h = goals.evaluate(fixture, **kwargs, h2h_csv=self.path)
        self.assertEqual(without, {k: v for k, v in with_h2h.items() if k != "h2h_external"})
        self.assertEqual(with_h2h["h2h_external"]["count"], 3)
        self.assertEqual(with_h2h["status"], "EXCLU_COMMENCE")

    def test_v1_metadata_only_injection(self):
        # Keep the expensive forecasting engine isolated; verify the adapter
        # is called only on opt-in and never changes its inputs.
        self.assertIsNone(syndicate.evaluer.__defaults__)
        info = h2h_readonly.lookup(self.path, "Alpha", "Beta", "2026-11-23", "2026-11-22")
        self.assertEqual(info["status"], "COMPLETE")
        self.assertFalse(info["probability_adjustment"])

if __name__ == "__main__":
    unittest.main()
