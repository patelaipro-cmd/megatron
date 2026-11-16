"""Regression tests for read-only unmapped ESPN team inventory."""
import unittest
from scripts.inventory_domination_unmapped_teams import build

class UnmappedTeamInventoryTests(unittest.TestCase):
    def test_groups_raw_teams_without_creating_aliases(self):
        snapshot={"raw_fixtures":[
            {"league":"PT1","mapping_status":"unmapped","home_raw":"A","away_raw":"B"},
            {"league":"PT1","mapping_status":"unmapped","home_raw":"A","away_raw":"C"},
            {"league":"E0","mapping_status":"mapped","home_raw":"D","away_raw":"E"},
            {"league":"NL1","mapping_status":"unmapped","home_raw":"X","away_raw":"Y"}]}
        report=build(snapshot)
        self.assertEqual(report["raw_n"],4)
        self.assertEqual(report["unmapped_fixtures_n"],3)
        self.assertEqual(report["league_summary"]["PT1"]["unmapped_fixtures"],2)
        self.assertEqual(report["league_summary"]["PT1"]["unique_raw_teams"],3)
        self.assertEqual(next(x for x in report["teams"] if x["team_raw"]=="A")["fixtures_n"],2)
        self.assertTrue(all(x["mapping_status"]=="UNVERIFIED" and not x["canonical_team"] for x in report["teams"]))
        self.assertEqual(report["decision"],"NO_GO")

if __name__=="__main__":unittest.main()
