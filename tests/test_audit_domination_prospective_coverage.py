"""Coverage auditor regression: pre-kickoff validity and missing fixture."""
import tempfile
import unittest
from pathlib import Path
from megatron.store import MemoryStore
from scripts.audit_domination_prospective_coverage import audit

class ProspectiveCoverageTests(unittest.TestCase):
    def test_covered_partial_late_and_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            store=MemoryStore(root)
            kickoff="2026-11-16T15:00:00+00:00"
            fixtures=[{"match_id":f"E0:2026-11-16:H-{name}","kickoff":kickoff} for name in ("full","partial","late","missing")]
            for name,markets,when in [
                ("full",("H_MARGE_2PLUS","H_MARGE_3PLUS"),"2026-11-16T14:00:00+00:00"),
                ("partial",("H_MARGE_2PLUS",),"2026-11-16T14:00:00+00:00"),
                ("late",("H_MARGE_2PLUS","H_MARGE_3PLUS"),"2026-11-16T15:01:00+00:00")]:
                for market in markets:
                    mid=f"E0:2026-11-16:H-{name}"
                    store.record("performances",f"pred:{mid}:{market}:v1",
                        {"match_id":mid,"kickoff":kickoff,"market":market,
                         "data_cutoff":"2026-11-16T13:00:00+00:00",
                         "probs":{"oui":0.6,"non":0.4}},
                        source="test",recorded_at=when,supersede=False)
            report=audit(root,fixtures)
            self.assertEqual(report["fixtures_n"],4)
            for status in ("covered_2plus_3plus","partial_prediction","invalid_timing","no_prediction"):
                self.assertEqual(report["status_counts"][status],1)
            self.assertEqual(report["decision"],"NO_GO")

    def test_future_fixture_is_not_a_missing_prediction(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            fixture={"match_id":"E0:2026-11-23:A-B","kickoff":"2026-11-23T15:00:00+00:00"}
            report=audit(root,[fixture],observed_at="2026-11-16T15:00:00+00:00")
            self.assertEqual(report["status_counts"]["not_yet_in_initial_window"],1)
            self.assertNotIn("no_prediction",report["status_counts"])

    def test_archived_snapshot_can_be_reaudited_after_window(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            fixture={"match_id":"E0:2026-11-23:A-B","kickoff":"2026-11-23T15:00:00+00:00"}
            report=audit(root,[fixture],observed_at="2026-11-16T15:00:00+00:00",
                         as_of="2026-11-23T14:00:00+00:00")
            self.assertEqual(report["status_counts"]["no_prediction"],1)

    def test_as_of_excludes_predictions_recorded_later(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            mid="E0:2026-11-23:H-A"
            kickoff="2026-11-23T15:00:00+00:00"
            store=MemoryStore(root)
            for market in ("H_MARGE_2PLUS","H_MARGE_3PLUS"):
                store.record("performances",f"pred:{mid}:{market}:v1",
                    {"match_id":mid,"kickoff":kickoff,"market":market,
                     "data_cutoff":"2026-11-23T12:00:00+00:00",
                     "probs":{"oui":0.6,"non":0.4}},
                    source="test",recorded_at="2026-11-23T14:00:00+00:00",supersede=False)
            fixture={"match_id":mid,"kickoff":kickoff}
            before=audit(root,[fixture],as_of="2026-11-23T13:30:00+00:00")
            after=audit(root,[fixture],as_of="2026-11-23T14:30:00+00:00")
            self.assertEqual(before["status_counts"]["no_prediction"],1)
            self.assertEqual(after["status_counts"]["covered_2plus_3plus"],1)

if __name__=="__main__":
    unittest.main()
