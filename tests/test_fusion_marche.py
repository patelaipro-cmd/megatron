import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from exp017_fusion import ajuster, fusionner  # noqa: E402


class FusionTests(unittest.TestCase):
    def test_poids_unitaire_rend_le_bookmaker(self):
        book = {"H": 0.5, "D": 0.3, "A": 0.2}
        p = fusionner({"H": 0.2, "D": 0.3, "A": 0.5}, book, [0.0, 1.0, 0.0, 0.0])
        for o in "HDA":
            self.assertAlmostEqual(p[o], book[o])

    def test_ajustement_fait_au_moins_aussi_bien_que_chaque_source(self):
        import math
        books = [{"H": 0.6, "D": 0.25, "A": 0.15}, {"H": 0.3, "D": 0.3, "A": 0.4}]
        v5s = [{"H": 0.2, "D": 0.3, "A": 0.5}, {"H": 0.5, "D": 0.3, "A": 0.2}, {"H": 0.4, "D": 0.35, "A": 0.25}]
        rows = [{"v5_cal": v5s[i % 3], "bookmaker": books[i % 2], "issue": "HDAHHDAHAH"[i % 10]} for i in range(300)]
        th = ajuster(rows)
        ll = lambda f: -sum(math.log(f(r)[r["issue"]]) for r in rows)  # noqa: E731
        fus = ll(lambda r: fusionner(r["v5_cal"], r["bookmaker"], th))
        self.assertLessEqual(fus, ll(lambda r: r["bookmaker"]) + 1e-9)
        self.assertLessEqual(fus, ll(lambda r: r["v5_cal"]) + 1e-9)

if __name__ == "__main__":
    unittest.main()
