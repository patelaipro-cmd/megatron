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
                   [StatsAgent(), LLMAgent("claude", "MEGATRON_TEST_ABSENT_KEY")])
        self.assertEqual(res["mode"], "degrade")
        self.assertEqual(res["agents_manquants"], ["claude"])
        self.assertIn("claude", res["indisponibles"])
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
        p = models.predict_1x2(fit, self._m("2024-06-01", "Fort", "B", 0, 0))
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
    def test_poisson_v4_from_history(self):
        r = StatsAgent().ask({"division": "F1", "home": "Paris SG", "away": "Le Havre", "date": "2026-08-01"})
        self.assertEqual(r.status, "ok", r.raison)
        self.assertIn("poisson-v5-cal", r.conclusion)
        self.assertGreater(r.probs["H"], 0.6)

    def test_invalid_date_is_error_not_invented(self):
        r = StatsAgent().ask({"division": "F1", "home": "x", "away": "y", "date": "pas-une-date"})
        self.assertEqual(r.status, "erreur")


class DixonColesTests(unittest.TestCase):
    def test_rho_zero_equals_poisson(self):
        from megatron.models import dixon_coles_1x2
        p, q = dixon_coles_1x2(1.4, 1.1, 0.0), poisson_1x2(1.4, 1.1)
        for o in "HDA":
            self.assertAlmostEqual(p[o], q[o], places=12)

    def test_negative_rho_raises_draws(self):
        from megatron.models import dixon_coles_1x2
        self.assertGreater(dixon_coles_1x2(1.4, 1.1, -0.1)["D"], poisson_1x2(1.4, 1.1)["D"])
        self.assertAlmostEqual(sum(dixon_coles_1x2(1.4, 1.1, -0.1).values()), 1.0, places=9)

    def test_rho_estimated_negative_when_low_draws_overrepresented(self):
        from megatron.models import MaherFit, estimate_rho
        fit = MaherFit(1.2, 1.0, {"A": 1.0, "B": 1.0}, {"A": 1.0, "B": 1.0})
        rows = [("A", "B", 0, 0, 1.0)] * 30 + [("A", "B", 1, 1, 1.0)] * 30 + [("A", "B", 1, 0, 1.0)] * 10
        self.assertLess(estimate_rho(fit, rows), 0)

    def test_paired_bootstrap_sign(self):
        from megatron.backtest import paired_bootstrap
        good, bad = {"H": .6, "D": .2, "A": .2}, {"H": .2, "D": .2, "A": .6}
        rows = [{"issue": "H", "a": good, "b": bad}] * 20 + [{"issue": "A", "a": bad, "b": good}] * 5
        res = paired_bootstrap(rows, "a", "b", draws=200)
        self.assertLess(res["ecart"], 0)
        self.assertLess(res["ic95"][1], 0)


class NewcomerPriorTests(unittest.TestCase):
    def _m(self, day, home, away, hg, ag):
        return ModelTests._m(day, home, away, hg, ag)

    def _history(self):
        # saison 2023/24 : 4 équipes établies, Faible très faible ; saison 2024/25 : Promu arrive
        teams = ["Fort", "B", "C", "Faible"]
        goals = {"Fort": 3, "B": 1, "C": 1, "Faible": 0}
        out = []
        for i in range(40):
            h, a = teams[i % 4], teams[(i + 1 + i // 4) % 4]
            if h != a:
                out.append(self._m(f"2023-{9 + i // 10:02d}-{1 + i % 10:02d}", h, a, goals[h], goals[a]))
        out.append(self._m("2024-08-10", "Promu", "B", 1, 1))
        return out

    def test_moyenne_prior_reproduces_v1(self):
        from datetime import date
        from megatron import models
        h = self._history()
        a = models.fit_maher(h, date(2024, 8, 20), half_life=90, shrink=3)
        b = models.fit_maher(h, date(2024, 8, 20), half_life=90, shrink=3, newcomer_prior="moyenne")
        self.assertEqual(a, b)

    def test_faibles3_pulls_newcomer_down(self):
        from datetime import date
        from megatron import models
        h = self._history()
        v1 = models.fit_maher(h, date(2024, 8, 20), half_life=90, shrink=3)
        v3 = models.fit_maher(h, date(2024, 8, 20), half_life=90, shrink=3, newcomer_prior="faibles3")
        self.assertLess(v3.attack["Promu"] / v3.defence["Promu"], v1.attack["Promu"] / v1.defence["Promu"])
        self.assertLess(v3.new_attack / v3.new_defence, 1.0)
        self.assertEqual((v1.new_attack, v1.new_defence), (1.0, 1.0))

    def test_unknown_prior_rejected(self):
        from datetime import date
        from megatron import models
        with self.assertRaises(ValueError):
            models.fit_maher([], date(2024, 1, 1), half_life=90, shrink=3, newcomer_prior="x")

    def test_read_predictions_roundtrip(self):
        from megatron import backtest
        rows = [{"match_id": "m", "saison": "2024/25", "issue": "H", "frequences": {"H": .5, "D": .3, "A": .2},
                 "bookmaker": None, "candidat": {"H": .6, "D": .2, "A": .2}}]
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "p.csv"
            backtest.write_predictions(rows, path)
            back = backtest.read_predictions(path)
        self.assertIsNone(back[0]["bookmaker"])
        self.assertAlmostEqual(back[0]["candidat"]["H"], 0.6)


class SystemeTests(unittest.TestCase):
    def test_fictional_match_end_to_end_degraded(self):
        from megatron import systeme

        rep = systeme.run([LLMAgent("claude", "MEGATRON_TEST_ABSENT_KEY")])
        self.assertTrue(rep["succes"], rep["verifications"])
        self.assertEqual(rep["fusion_mode"], "degrade")
        self.assertEqual(rep["version"], 'fusion-v1:[["stats","poisson-v5-cal"]]')

    def test_fictional_match_full_mode_with_fake_llms(self):
        import os
        from types import SimpleNamespace
        from unittest import mock

        from megatron import systeme

        def fake(**kw):
            msg = SimpleNamespace(content='{"H":0.5,"D":0.3,"A":0.2,"raison":"fictif","sources":["faux"]}')
            return SimpleNamespace(choices=[SimpleNamespace(message=msg)],
                                   usage={"prompt_tokens": 10, "completion_tokens": 5})

        env = {"ANTHROPIC_API_KEY": "faux"}
        with tempfile.TemporaryDirectory() as cache, mock.patch.dict(os.environ, env), \
                mock.patch("megatron.llm.CACHE_DIR", Path(cache)):
            rep = systeme.run([LLMAgent("claude", completion_fn=fake)])
        self.assertTrue(rep["succes"], rep["verifications"])
        self.assertEqual(rep["fusion_mode"], "complet")
        self.assertTrue(rep["version"].startswith('fusion-v1:[["claude",'), rep["version"])
        self.assertIn('["stats","poisson-v5-cal"]', rep["version"])


class ProxyTirsTests(unittest.TestCase):
    """EXP-004 : pseudo-buts à partir des tirs, sans fuite temporelle."""

    @classmethod
    def setUpClass(cls):
        from datetime import date

        from megatron import data

        cls.day = date(2023, 1, 15)
        cls.history = [m for m in data.load(divisions={"F1"}) if m.day < cls.day]

    def test_shots_loaded(self):
        self.assertTrue(all(m.shots for m in self.history))

    def test_zero_weight_is_poisson_v1(self):
        from megatron import models

        a = models.fit_maher(self.history, self.day, half_life=90, shrink=3)
        b = models.fit_maher(self.history, self.day, half_life=90, shrink=3, proxy="tirs", proxy_weight=0.0)
        self.assertEqual(a.rates("Paris SG", "Lens"), b.rates("Paris SG", "Lens"))

    def test_pseudo_goals_keep_goal_scale(self):
        from megatron import models

        rows = [(m.home, m.away, m.home_goals, m.away_goals, 1.0) for m in self.history]
        pseudo = models._pseudo_goals(rows, self.history, models.PROXIES["cadres"], 1.0)
        self.assertAlmostEqual(sum(r[2] + r[3] for r in pseudo), sum(r[2] + r[3] for r in rows), places=6)

    def test_future_shots_never_used(self):
        from dataclasses import replace

        from megatron import backtest, data

        league = self.history
        target = [m for m in data.load(divisions={"F1"}) if m.day == self.day]
        self.assertTrue(target)
        altered = [replace(m, shots=(99, 0, 99, 0)) for m in target]
        cfg = {"v4": (90.0, 3.0, False, "moyenne", "cadres", 0.5)}
        a = backtest.predict_seasons(league + target, "F1", {"2022/23"}, cfg)
        b = backtest.predict_seasons(league + altered, "F1", {"2022/23"}, cfg)
        self.assertEqual([r["v4"] for r in a if r["match_id"] in {m.match_id for m in target}],
                         [r["v4"] for r in b if r["match_id"] in {m.match_id for m in target}])

    def test_dixon_coles_refused_with_pseudo_goals(self):
        from megatron import models

        with self.assertRaises(ValueError):
            models.fit_maher(self.history, self.day, half_life=90, shrink=3, dixon_coles=True, proxy_weight=0.5)


class SuiviTests(TmpStore):
    """Boucle prévoir → résultat → bilan, sur un historique fictif."""

    def setUp(self):
        super().setUp()
        from datetime import datetime, timezone

        from megatron import systeme

        self.csv = Path(self._tmp.name) / "fictif.csv"
        last = systeme.synthetic_history(self.csv)
        self.kickoff = datetime(last.year, last.month, last.day, 15, tzinfo=timezone.utc) + timedelta(days=7)
        self.task = {"match_id": "FICTIF:1", "division": "FICTIF", "home": "Alpha FC", "away": "Zeta Rovers",
                     "date": self.kickoff.date().isoformat()}
        self.agents = [StatsAgent(self.csv), LLMAgent("claude", "MEGATRON_TEST_ABSENT_KEY")]

    def test_full_loop(self):
        from megatron import suivi

        before = self.kickoff - timedelta(hours=3)
        out = suivi.prevoir(self.store, self.task, self.kickoff, agents=self.agents, now=before)
        self.assertEqual(out["enregistre"], [suivi.fusion_version({"reponses": [AgentResponse(agent="stats", status="ok", version="poisson-v5-cal")]}), "agent:stats:poisson-v5-cal"])
        self.assertIn("claude", out["indisponibles"])
        with self.assertRaises(ValueError):  # pas de réécriture
            suivi.prevoir(self.store, self.task, self.kickoff, agents=self.agents, now=before)
        with self.assertRaises(TemporalLeakError):
            suivi.resultat(self.store, "FICTIF:1", "2-0", source="t", observed_at=before)
        suivi.resultat(self.store, "FICTIF:1", "2-0", source="t", observed_at=self.kickoff + timedelta(hours=2))
        b = suivi.bilan(self.store, now=self.kickoff + timedelta(days=1))
        self.assertEqual(b["versions"][out["enregistre"][0]]["n"], 1)
        self.assertEqual(b["communs"]["n"], 1)
        self.assertEqual(b["resultats_a_saisir"], [])

    def test_refused_after_kickoff_writes_nothing(self):
        from megatron import suivi

        with self.assertRaises(ValueError):
            suivi.prevoir(self.store, self.task, self.kickoff, agents=self.agents,
                          now=self.kickoff + timedelta(minutes=1))
        self.assertEqual(self.store.active("performances"), [])

    def test_pending_results_listed(self):
        from megatron import suivi

        suivi.prevoir(self.store, self.task, self.kickoff, agents=self.agents, now=self.kickoff - timedelta(hours=1))
        b = suivi.bilan(self.store, now=self.kickoff + timedelta(days=1))
        self.assertEqual(b["resultats_a_saisir"], ["FICTIF:1"])

    def test_outcome_parsing(self):
        from megatron import suivi

        self.assertEqual([suivi.outcome_of(x) for x in ("2-1", "0:0", "1-3", "d")], ["H", "D", "A", "D"])


class DonneesCompletesTests(unittest.TestCase):
    def test_full_history_contains_experiment_extract(self):
        from megatron import data

        full = {m.match_id: m for m in data.load(data.CURRENT[0])}
        exp = data.load()
        self.assertTrue(all(full[m.match_id] == m for m in exp))
        self.assertEqual(min(m.day for m in full.values()).year, 2000)

    def test_current_season_complement_merges_without_duplicates(self):
        from megatron import data

        base, extra = (data.load(p) for p in data.CURRENT)
        self.assertGreater(min(m.day for m in extra), max(m.day for m in base))
        self.assertTrue(all(m.odds is None and m.shots is None for m in extra))
        teams = {(m.division, t) for m in base for t in (m.home, m.away)}
        self.assertTrue(all((m.division, t) in teams for m in extra for t in (m.home, m.away)))
        self.assertEqual(len(data.load(data.CURRENT)), len(base) + len(extra))

    def test_duplicate_files_refused(self):
        from megatron import data

        with self.assertRaises(ValueError):
            data.load([data.DEFAULT_CSV, data.DEFAULT_CSV])


class FournisseurUniqueTests(unittest.TestCase):
    def test_claude_seul_fournisseur_par_defaut(self):
        from megatron.agents import EXPECTED_FUSION, default_agents
        self.assertEqual([a.name for a in default_agents()], ["stats", "claude"])
        self.assertEqual(EXPECTED_FUSION, ("stats", "claude"))
