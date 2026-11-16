"""Admission gate must never promote an exploratory league by mapping alone."""
import unittest
from scripts.audit_domination_league_admission import assess

class LeagueAdmissionTests(unittest.TestCase):
    def test_missing_reference_blocks(self):
        snapshot={"leagues":["E0","E1"],"league_counts":{"E0":{"raw":2,"mapped":2,"unmapped":0},"E1":{"raw":3,"mapped":0,"unmapped":3}}}
        report=assess(snapshot,{"noms":{"espn:E0":{"A":"A"}}},{"E0":"eng.1"})
        e1=next(x for x in report["leagues"] if x["league"]=="E1")
        self.assertEqual(e1["admission"],"BLOCKED_EXPLORATORY")
        self.assertIn("LEAGUE_REFERENCE_MISSING",e1["blockers"])
        self.assertEqual(report["exploratory_blocked"],1)
    def test_full_mapping_still_cannot_promote_uncalibrated_league(self):
        snapshot={"leagues":["E1"],"league_counts":{"E1":{"raw":3,"mapped":3,"unmapped":0}}}
        report=assess(snapshot,{"noms":{"espn:E1":{"A":"A"}}},{})
        self.assertEqual(report["leagues"][0]["admission"],"BLOCKED_EXPLORATORY")
        self.assertIn("2PLUS_3PLUS_CALIBRATION_NOT_VERIFIED",report["leagues"][0]["blockers"])

if __name__=="__main__":unittest.main()
