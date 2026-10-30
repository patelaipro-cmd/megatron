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


class PlattTests(unittest.TestCase):
    def test_recovers_known_parameters(self):
        import random
        rng = random.Random(3)
        a0, b0 = 0.2, 0.6
        pairs = []
        for _ in range(4000):
            p = rng.uniform(0.1, 0.9)
            q = 1 / (1 + math.exp(-(a0 + b0 * math.log(p / (1 - p)))))
            pairs.append((p, rng.random() < q))
        a, b = marches.fit_platt(pairs)
        self.assertAlmostEqual(a, a0, delta=0.1)
        self.assertAlmostEqual(b, b0, delta=0.1)

    def test_identity_keeps_probability(self):
        self.assertAlmostEqual(marches.platt(0.37, 0.0, 1.0)["oui"], 0.37)


class LedgerMarketTests(unittest.TestCase):
    def test_goal_market_prediction_and_resolution(self):
        import tempfile

        from megatron import suivi
        from megatron.ledger import Ledger, pred_key
        from megatron.store import MemoryStore

        with tempfile.TemporaryDirectory() as tmp:
            store = MemoryStore(tmp)
            led = Ledger(store)
            ko, rec = "2030-01-01T12:00:00Z", "2030-01-01T10:00:00Z"
            led.predict("m", ko, {"H": .5, "D": .3, "A": .2}, model_version="v", source="t", recorded_at=rec)
            led.predict("m", ko, {"oui": .6, "non": .4}, model_version="v", source="t", recorded_at=rec, market="3+")
            self.assertTrue(store.active("performances", pred_key("m", "v")))
            self.assertTrue(store.active("performances", pred_key("m", "v", "3+")))
            with self.assertRaises(ValueError):  # issues du 1X2 refusées sur un marché de buts
                led.predict("m2", ko, {"H": .5, "D": .3, "A": .2}, model_version="v", source="t",
                            recorded_at=rec, market="3+")
            with self.assertRaises(ValueError):
                led.predict("m2", ko, {"oui": .6, "non": .4}, model_version="v", source="t",
                            recorded_at=rec, market="4+")
            suivi.resultat(store, "m", "2-1", source="t", observed_at="2030-01-01T14:00:00Z")
            self.assertEqual(led.outcomes("3+"), {"m": "oui"})
            self.assertEqual(led.evaluate("v", market="3+")["n"], 1)
            self.assertEqual(led.evaluate("v")["n"], 1)
            self.assertEqual(len(led._predictions("m", market="1X2")), 1)

    def test_outcome_only_leaves_goal_markets_unresolved(self):
        import tempfile

        from megatron.ledger import Ledger
        from megatron.store import MemoryStore

        with tempfile.TemporaryDirectory() as tmp:
            led = Ledger(MemoryStore(tmp))
            led.predict("m", "2030-01-01T12:00:00Z", {"oui": .6, "non": .4}, model_version="v", source="t",
                        recorded_at="2030-01-01T10:00:00Z", market="2+")
            led.result("m", "H", source="t", observed_at="2030-01-01T14:00:00Z")
            self.assertEqual(led.outcomes("2+"), {})
            with self.assertRaises(ValueError):  # score incohérent avec l'issue
                led.result("m", "H", source="t", observed_at="2030-01-01T14:00:00Z", correction=True, goals=(0, 1))


class PrevoirButsTests(unittest.TestCase):
    def test_prevoir_records_goal_markets_and_bilan_scores_them(self):
        import tempfile
        from datetime import datetime, timedelta, timezone
        from pathlib import Path

        from megatron import suivi, systeme
        from megatron.agents import StatsAgent
        from megatron.store import MemoryStore

        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "h.csv"
            last = systeme.synthetic_history(csv_path)
            ko = datetime(last.year, last.month, last.day, 15, tzinfo=timezone.utc) + timedelta(days=7)
            task = {"match_id": "FICTIF:buts", "division": systeme.DIVISION, "home": "Alpha FC",
                    "away": "Zeta Rovers", "date": ko.date().isoformat()}
            store = MemoryStore(Path(tmp) / "m")
            out = suivi.prevoir(store, task, ko, agents=[StatsAgent(csv_path)], now=ko - timedelta(hours=2))
            self.assertEqual(out["enregistre_buts"], ["2+:agent:stats:poisson-v5-platt",
                                                      "3+:agent:stats:poisson-v5-platt"])
            with self.assertRaises(ValueError):
                suivi.prevoir(store, task, ko, agents=[StatsAgent(csv_path)], now=ko - timedelta(hours=1))
            suivi.resultat(store, "FICTIF:buts", "1-1", source="t", observed_at=ko + timedelta(hours=2))
            b = suivi.bilan(store, now=ko + timedelta(days=1))
            self.assertEqual(b["marches_buts"]["2+"]["agent:stats:poisson-v5-platt"]["n"], 1)
            self.assertEqual(b["marches_buts"]["3+"]["agent:stats:poisson-v5-platt"]["n"], 1)
            self.assertEqual(b["communs"]["n"], 1)  # le 1X2 reste compté à part
