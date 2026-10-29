import unittest

from megatron import models
from megatron.agents import StatsAgent


class CalibrationTest(unittest.TestCase):
    def test_identite_et_somme(self):
        p = {"H": 0.5, "D": 0.27, "A": 0.23}
        same = models.calibrer_1x2(p, 1.0, 0.0, 0.0)
        for o in p:
            self.assertAlmostEqual(same[o], p[o], 9)
        cal = models.calibrer_1x2(p, *StatsAgent.CALIBRATION)
        self.assertAlmostEqual(sum(cal.values()), 1.0, 9)
        self.assertGreater(cal["H"], p["H"])  # b > 1 : le favori se renforce

    def test_version(self):
        self.assertEqual(StatsAgent.VERSION, "poisson-v5-cal")


if __name__ == "__main__":
    unittest.main()
