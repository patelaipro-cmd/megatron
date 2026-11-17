import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from daily import normalize
class NormalizationTests(unittest.TestCase):
 def test_missing_teams(self):
  self.assertIsNone(normalize({"utcDate":"2026-11-17T12:00:00Z"},"PL"))
 def test_valid_match(self):
  m={"utcDate":"2026-11-17T12:00:00Z","homeTeam":{"id":1,"name":"Home"},"awayTeam":{"id":2,"name":"Away"}}
  self.assertEqual(normalize(m,"PL")["home_name"],"Home")
 def test_same_team_rejected(self):
  m={"utcDate":"2026-11-17T12:00:00Z","homeTeam":{"id":1},"awayTeam":{"id":1}}
  self.assertIsNone(normalize(m,"PL"))
if __name__=="__main__":unittest.main()
