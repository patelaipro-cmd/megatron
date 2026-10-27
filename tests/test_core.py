import json
import math
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path

from megatron import checkpoint, inventory
from megatron.agents import AgentResponse, LLMAgent, StatsAgent, fuse, poisson_1x2
from megatron.ledger import Ledger, TemporalLeakError
from megatron.store import MemoryStore, parse_dt

ROOT = Path(__file__).resolve().parent.parent


class TmpStore(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.store = MemoryStore(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()


class StoreTests(TmpStore):
    def test_supersede_keeps_history(self):
        a = self.store.record("decisions", "format", "jsonl", source="test")
        b = self.store.record("decisions", "format", "sqlite", source="test")
        self.assertEqual(b.supersedes, a.id)
        self.assertEqual([e.value for e in self.store.active("decisions", "format")], ["sqlite"])
        self.assertEqual(len(self.store.history("decisions", "format")), 2)

    def test_contradiction_detected(self):
        self.store.record("football", "psg:absent:x", True, source="site A")
        self.store.record("football", "psg:absent:x", False, source="site B", supersede=False)
        self.assertIn("psg:absent:x", self.store.contradictions("football"))

    def test_provenance_and_domain_required(self):
        with self.assertRaises(ValueError):
            self.store.record("football", "k", 1, source="")
        with self.assertRaises(ValueError):
            self.store.record("divers", "k", 1, source="s")

    def test_stale(self):
        self.store.record("football", "forme", "WWD", source="s", observed_at="2026-01-01T00:00:00+00:00")
        old = self.store.stale("football", timedelta(days=30), at=parse_dt("2026-10-27T00:00:00+00:00"))
        self.assertEqual(len(old), 1)

    def test_persists_across_instances(self):
        self.store.record("technique", "python", "3.13", source="test")
        again = MemoryStore(self._tmp.name)
        self.assertEqual(again.search("python")[0].value, "3.13")


class LedgerTests(TmpStore):
    KO = "2026-11-01T20:00:00+00:00"

    def test_prediction_after_kickoff_rejected(self):
        with self.assertRaises(TemporalLeakError):
            Ledger(self.store).predict("m1", self.KO, {"H": .5, "D": .3, "A": .2}, model_version="v0",
                                       source="t", recorded_at="2026-11-01T20:00:00+00:00")

    def test_data_cutoff_after_kickoff_rejected(self):
        with self.assertRaises(TemporalLeakError):
            Ledger(self.store).predict("m1", self.KO, {"H": .5, "D": .3, "A": .2}, model_version="v0",
                                       source="t", recorded_at="2026-11-01T10:00:00+00:00",
                                       data_cutoff="2026-11-02T00:00:00+00:00")

    def test_prediction_is_immutable(self):
        led = Ledger(self.store)
        args = dict(model_version="v0", source="t", recorded_at="2026-11-01T10:00:00+00:00")
        led.predict("m1", self.KO, {"H": .5, "D": .3, "A": .2}, **args)
        with self.assertRaises(ValueError):
            led.predict("m1", self.KO, {"H": .6, "D": .2, "A": .2}, **args)

    def test_result_before_kickoff_rejected(self):
        led = Ledger(self.store)
        led.predict("m1", self.KO, {"H": .5, "D": .3, "A": .2}, model_version="v0", source="t",
                    recorded_at="2026-11-01T10:00:00+00:00")
        with self.assertRaises(TemporalLeakError):
            led.result("m1", "H", source="t", observed_at="2026-11-01T19:00:00+00:00")

    def test_metrics(self):
        led = Ledger(self.store)
        led.predict("m1", self.KO, {"H": .5, "D": .3, "A": .2}, model_version="v0", source="t",
                    recorded_at="2026-11-01T10:00:00+00:00")
        led.predict("m2", self.KO, {"H": .2, "D": .3, "A": .5}, model_version="v0", source="t",
                    recorded_at="2026-11-01T10:00:00+00:00")
        led.result("m1", "H", source="t", observed_at="2026-11-01T22:00:00+00:00")
        led.result("m2", "D", source="t", observed_at="2026-11-01T22:00:00+00:00")
        ev = led.evaluate("v0")
        # m1 : (0.5-1)²+0.3²+0.2² = 0.38 ; m2 : 0.2²+(0.3-1)²+0.5² = 0.78
        self.assertAlmostEqual(ev["brier"], (0.38 + 0.78) / 2, places=6)
        self.assertAlmostEqual(ev["log_loss"], -(math.log(.5) + math.log(.3)) / 2, places=6)
        self.assertEqual(ev["n"], 2)
        self.assertEqual(sum(b["n"] for b in ev["calibration"]), 6)


class AgentTests(unittest.TestCase):
    def test_poisson_sums_to_one_and_favours_stronger_side(self):
        p = poisson_1x2(1.8, 0.7)
        self.assertAlmostEqual(sum(p.values()), 1.0, places=9)
        self.assertGreater(p["H"], p["A"])

    def test_llm_without_key_is_unavailable_not_invented(self):
        r = LLMAgent("gemini", "MEGATRON_TEST_ABSENT_KEY").ask({})
        self.assertEqual(r.status, "indisponible")
        self.assertIsNone(r.probs)
        self.assertEqual(r.appels, 0)

    def test_fusion_degraded_mode_documents_missing_agents(self):
        res = fuse({"match_id": "m", "xg_home": 1.5, "xg_away": 1.0},
                   [StatsAgent(), LLMAgent("deepseek", "MEGATRON_TEST_ABSENT_KEY"),
                    LLMAgent("gemini", "MEGATRON_TEST_ABSENT_KEY")])
        self.assertEqual(res["mode"], "degrade")
        self.assertEqual(sorted(res["agents_manquants"]), ["deepseek", "gemini"])
        self.assertIn("gemini", res["indisponibles"])
        self.assertEqual(res["probs"], poisson_1x2(1.5, 1.0))

    def test_fusion_flags_disagreement_and_shared_sources(self):
        class Fixed:
            def __init__(self, name, probs):
                self.name, self.probs = name, probs

            def ask(self, task):
                return AgentResponse(agent=self.name, status="ok", probs=self.probs, sources=["fbref"], appels=1)

        res = fuse({}, [Fixed("deepseek", {"H": .6, "D": .2, "A": .2}),
                        Fixed("gemini", {"H": .3, "D": .3, "A": .4})])
        self.assertTrue(res["a_verifier"])
        self.assertEqual(res["avis_non_independants"], [["deepseek", "gemini"]])
        self.assertAlmostEqual(res["probs"]["H"], .45)


class CheckpointTests(TmpStore):
    def test_save_and_resume(self):
        self.store.record("decisions", "stockage", "jsonl append-only", source="test", status="verifie")
        saved = checkpoint.save(self.store, resume="socle posé", prochaines_actions=["brancher LiteLLM"])
        loaded = checkpoint.load(self.store)
        self.assertEqual(saved["id"], loaded["id"])
        self.assertEqual(loaded["decisions_actives"][0]["cle"], "stockage")
        self.assertLess(len(json.dumps(loaded)), 4000)


class InventoryTests(unittest.TestCase):
    def test_counts_and_duplicates(self):
        rows, counts = inventory.build(ROOT / "docs" / "inventaires", ROOT / "docs" / "evaluations.json")
        self.assertEqual(sum(counts.values()), 542)
        self.assertEqual(len(rows), 516)
        self.assertEqual(sum("," in r["inventaires"] for r in rows), 24)
        self.assertTrue(all(r["classement"] in inventory.CLASSES for r in rows))


if __name__ == "__main__":
    unittest.main()


class ModelTests(unittest.TestCase):
    @staticmethod
    def _m(day, home, away, hg, ag):
        from datetime import date, datetime, timezone
        from megatron.data import Match
        d = date.fromisoformat(day)
        res = "H" if hg > ag else "A" if ag > hg else "D"
        return Match("X1", d, datetime(d.year, d.month, d.day, 12, tzinfo=timezone.utc),
                     home, away, hg, ag, res, (2.0, 3.5, 4.0))

    def _league(self):
        teams = ["Fort", "B", "C", "D"]
        out, day = [], 1
        for _ in range(5):
            for h in teams:
                for a in teams:
                    if h != a:
                        hg, ag = (3, 0) if h == "Fort" else (0, 2) if a == "Fort" else (1, 1)
                        out.append(self._m(f"2024-01-{day:02d}", h, a, hg, ag) if day <= 28
                                   else self._m(f"2024-02-{day - 28:02d}", h, a, hg, ag))
                        day = day % 56 + 1
        return sorted(out, key=lambda m: m.day)

    def test_history_on_match_day_is_rejected(self):
        from datetime import date
        from megatron import models
        hist = [self._m("2024-03-01", "A", "B", 1, 0)]
        with self.assertRaises(AssertionError):
            models.fit_maher(hist, date(2024, 3, 1), half_life=180, shrink=1)
        with self.assertRaises(AssertionError):
            models.frequencies(hist, date(2024, 3, 1))

    def test_maher_ranks_dominant_team(self):
        from datetime import date
        from megatron import models
        fit = models.fit_maher(self._league(), date(2024, 6, 1), half_life=365, shrink=1)
        self.assertGreater(fit.attack["Fort"], 1.5)
        self.assertLess(fit.defence["Fort"], 0.5)
        p = models.poisson_v1(fit, self._m("2024-06-01", "Fort", "B", 0, 0))
        self.assertGreater(p["H"], 0.7)
        self.assertAlmostEqual(sum(p.values()), 1.0, places=9)

    def test_bookmaker_margin_removed(self):
        from megatron import models
        p = models.bookmaker(self._m("2024-06-01", "A", "B", 0, 0))
        self.assertAlmostEqual(sum(p.values()), 1.0, places=9)
        self.assertGreater(p["H"], p["A"])

    def test_rps(self):
        from megatron.ledger import rps
        self.assertAlmostEqual(rps({"H": 1, "D": 0, "A": 0}, "H"), 0.0)
        self.assertAlmostEqual(rps({"H": 1, "D": 0, "A": 0}, "A"), 1.0)
        self.assertAlmostEqual(rps({"H": .5, "D": .3, "A": .2}, "D"), (0.25 + 0.04) / 2)

    def test_season_and_data_file(self):
        from datetime import date
        from megatron import data
        self.assertEqual(data.season_of(date(2024, 8, 10)), "2024/25")
        self.assertEqual(data.season_of(date(2025, 5, 10)), "2024/25")
        ms = data.load(divisions={"F1"})
        self.assertEqual(len([m for m in ms if data.season_of(m.day) == "2022/23"]), 380)
        self.assertEqual(ms, sorted(ms, key=lambda m: (m.kickoff, m.match_id)))


class StatsAgentHistoryTests(unittest.TestCase):
    def test_poisson_v1_from_history(self):
        r = StatsAgent().ask({"division": "F1", "home": "Paris SG", "away": "Le Havre", "date": "2026-08-01"})
        self.assertEqual(r.status, "ok", r.raison)
        self.assertIn("poisson-v1", r.conclusion)
        self.assertGreater(r.probs["H"], 0.6)

    def test_invalid_date_is_error_not_invented(self):
        r = StatsAgent().ask({"division": "F1", "home": "x", "away": "y", "date": "pas-une-date"})
        self.assertEqual(r.status, "erreur")
