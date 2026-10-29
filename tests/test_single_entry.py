import contextlib
import io
import tempfile
import unittest
from datetime import timedelta
from unittest.mock import patch

from megatron import suivi
from megatron.__main__ import main
from megatron.agents import AgentResponse, StatsAgent
from megatron.ledger import Ledger
from megatron.store import MemoryStore, now_utc, parse_dt


class EntrySafetyTests(unittest.TestCase):
    def test_non_finite_probabilities_leave_no_prediction(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = MemoryStore(tmp)
            for value in (float("nan"), float("inf"), -float("inf")):
                with self.subTest(value=value), self.assertRaises(ValueError):
                    Ledger(store).predict("m", "2030-01-01T12:00:00Z",
                        {"H": value, "D": .3, "A": .2}, model_version="v1",
                        source="test", recorded_at="2030-01-01T10:00:00Z")
                self.assertEqual(store.active("performances"), [])

    def test_crossing_kickoff_leaves_store_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = MemoryStore(tmp)
            before = parse_dt("2030-01-01T11:59:59Z")
            after = parse_dt("2030-01-01T12:00:00Z")
            with patch("megatron.suivi.now_utc", side_effect=[before, after]), patch(
                "megatron.suivi.fuse", return_value={"probs": {"H": .5, "D": .3, "A": .2}}
            ), self.assertRaises(ValueError):
                suivi.prevoir(store, {"match_id": "m"}, after)
            self.assertEqual(store.active("performances"), [])

    def test_fusion_separates_model_versions_and_is_order_independent(self):
        a = AgentResponse(agent="stats", status="ok", version="poisson-v1")
        b = AgentResponse(agent="stats", status="ok", version="poisson-v4")
        c = AgentResponse(agent="other", status="ok", version="model-x")
        self.assertNotEqual(suivi.fusion_version({"reponses": [a]}),
                            suivi.fusion_version({"reponses": [b]}))
        self.assertEqual(suivi.fusion_version({"reponses": [b, c]}),
                         suivi.fusion_version({"reponses": [c, b]}))

    def test_cli_default_never_constructs_remote_agents(self):
        with tempfile.TemporaryDirectory() as tmp, patch(
            "megatron.agents.default_agents", side_effect=AssertionError("remote agents forbidden")
        ), patch("socket.create_connection", side_effect=AssertionError("network forbidden")), contextlib.redirect_stdout(io.StringIO()):
            code = main(["--memoire", tmp, "prevoir",
                         '{"match_id":"SIMULATION","xg_home":1.6,"xg_away":0.9}',
                         "--coup-envoi", (now_utc() + timedelta(hours=2)).isoformat()])
            self.assertEqual(code, 0)
            preds = Ledger(MemoryStore(tmp))._predictions()
            self.assertEqual(len(preds), 2)
            self.assertTrue(all(p.value["data_cutoff"] is None for p in preds))

    def test_second_result_requires_explicit_correction(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = MemoryStore(tmp)
            led = Ledger(store)
            led.predict("m", "2030-01-01T12:00:00Z", {"H": .5, "D": .3, "A": .2}, model_version="v1",
                        source="test", recorded_at="2030-01-01T10:00:00Z")
            led.result("m", "H", source="test", observed_at="2030-01-01T14:00:00Z")
            for outcome in ("H", "A"):
                with self.subTest(outcome=outcome), self.assertRaises(ValueError):
                    led.result("m", outcome, source="test", observed_at="2030-01-01T15:00:00Z")
            self.assertEqual(store.active("performances", "result:m")[0].value["outcome"], "H")
            led.result("m", "A", source="test", observed_at="2030-01-01T15:00:00Z", correction=True)
            self.assertEqual(store.active("performances", "result:m")[0].value["outcome"], "A")
            self.assertEqual(len(store.history("performances", "result:m")), 2)

    def test_strict_five_hour_window(self):
        ko = parse_dt("2030-01-01T20:00:00Z")
        task = {"match_id": "m", "xg_home": 1.4, "xg_away": 1.1}
        with tempfile.TemporaryDirectory() as tmp:
            store = MemoryStore(tmp)
            for early in (ko - timedelta(hours=5, seconds=1), ko - timedelta(days=2)):
                with self.subTest(now=early), self.assertRaises(ValueError):
                    suivi.prevoir(store, task, ko, agents=[StatsAgent()], now=early)
            self.assertEqual(store.active("performances"), [])
            out = suivi.prevoir(store, task, ko, agents=[StatsAgent()], now=ko - timedelta(hours=5))
            self.assertEqual(len(out["enregistre"]), 2)

    def test_window_rechecked_after_agents(self):
        ko = parse_dt("2030-01-01T20:00:00Z")
        with tempfile.TemporaryDirectory() as tmp:
            store = MemoryStore(tmp)
            with patch("megatron.suivi.now_utc", side_effect=[ko - timedelta(hours=1), ko]), patch(
                "megatron.suivi.fuse", return_value={"probs": {"H": .5, "D": .3, "A": .2}}
            ), self.assertRaises(ValueError):
                suivi.prevoir(store, {"match_id": "m"}, ko)
            self.assertEqual(store.active("performances"), [])
