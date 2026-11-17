import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from model import btts,score
class ModelTests(unittest.TestCase):
 def test_probability(self):
  self.assertTrue(0<btts(1.5,1.1,1.2,1.4)<1)
 def test_missing_history(self):
  self.assertIsNone(score([],"1","2","PL"))
if __name__=="__main__":unittest.main()
