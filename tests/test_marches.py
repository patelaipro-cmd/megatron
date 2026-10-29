import math
import unittest

from megatron import marches


class MarchesButsTests(unittest.TestCase):
    def test_total_poisson(self):
        lam = 2.6
        p0, p1, p2 = (math.exp(-lam) * lam ** k / math.factorial(k) for k in range(3))
        out = marches.probs_buts(1.5, 1.1)
        self.assertAlmostEqual(out["2+"]["oui"], 1 - p0 - p1)
        self.assertAlmostEqual(out["3+"]["oui"], 1 - p0 - p1 - p2)
        self.assertLess(out["3+"]["oui"], out["2+"]["oui"])
        for m in out.values():
            self.assertAlmostEqual(m["oui"] + m["non"], 1)

    def test_issue(self):
        self.assertEqual(marches.issue_buts("2+", 1, 1), "oui")
        self.assertEqual(marches.issue_buts("3+", 1, 1), "non")
        self.assertEqual(marches.issue_buts("3+", 3, 0), "oui")

    def test_bookmaker_margin_removed(self):
        p = marches.bookmaker_3plus((1.9, 1.9))
        self.assertAlmostEqual(p["oui"], 0.5)
        self.assertIsNone(marches.bookmaker_3plus(None))

    def test_cotes_file_joins_history(self):
        cotes = marches.load_cotes()
        self.assertGreater(len(cotes), 37000)
        self.assertIn("F1:2005-07-29:Paris SG-Metz", cotes)

    def test_bilan_criteria(self):
        good = {"oui": .8, "non": .2}
        flat = {"oui": .5, "non": .5}
        rows = [{"match_id": f"{d}:2020-01-0{i % 9 + 1}:A-B", "saison": "2019/20", "marche": m,
                 "issue": "oui", "poisson-v4": good, "frequences": flat, "bookmaker": None}
                for d in ("F1", "E0", "D1", "SP1", "I1") for i in range(10) for m in ("2+", "3+")]
        b = marches.bilan(rows)
        self.assertTrue(b["2+"]["M1"])
        self.assertTrue(b["2+"]["M2"])
        self.assertFalse(b["2+"]["M3"])  # aucune tranche de 500 prévisions : M3 non démontré
