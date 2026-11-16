import unittest
from scripts.collect_domination_historical_e1_sp2 import parse_csv,collect

class HistoricalImportTests(unittest.TestCase):
    def test_validates_scores_division_and_duplicates(self):
        csv_data=("Div,Date,HomeTeam,AwayTeam,FTHG,FTAG\n"
                  "E1,15/08/2025,Alpha,Beta,3,0\n"
                  "E1,15/08/2025,Alpha,Beta,3,0\n"
                  "SP2,16/08/2025,Gamma,Delta,1,1\n"
                  "E1,17/08/2025,Epsilon,Zeta,,1\n").encode()
        rows,bad=parse_csv(csv_data,"E1","2526")
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["home_win_3plus"],1)
        self.assertEqual(bad["duplicate"],1)
        self.assertEqual(bad["wrong_division"],1)
        self.assertEqual(bad["missing_score"],1)
    def test_incomplete_sources_never_promote(self):
        report=collect(lambda url: b"Div,Date,HomeTeam,AwayTeam,FTHG,FTAG\n")
        self.assertFalse(report["complete"])
        self.assertEqual(report["decision"],"NO_GO")
        self.assertEqual(len(report["errors"]),6)
if __name__=="__main__":unittest.main()
