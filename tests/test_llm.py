import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from megatron import llm
from megatron.agents import LLMAgent


def fake(text, calls):
    def fn(model, messages, **params):
        calls.append(model)
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=text))],
                               usage={"prompt_tokens": 42, "completion_tokens": 17})
    return fn


class LLMTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.patch_cache = mock.patch.object(llm, "CACHE_DIR", Path(self.tmp.name))
        self.patch_cache.start()
        self.patch_env = mock.patch.dict(os.environ, {"GEMINI_API_KEY": "cle-de-test"})
        self.patch_env.start()

    def tearDown(self):
        self.patch_env.stop()
        self.patch_cache.stop()
        self.tmp.cleanup()

    def test_measured_tokens_and_cache_avoid_second_call(self):
        calls = []
        fn = fake('{"H":0.5,"D":0.3,"A":0.2,"raison":"x"}', calls)
        msg = [{"role": "user", "content": "q"}]
        first = llm.complete("gemini", msg, completion_fn=fn)
        second = llm.complete("gemini", msg, completion_fn=fn)
        self.assertEqual((first.status, first.tokens_entree, first.tokens_sortie), ("ok", 42, 17))
        self.assertTrue(second.cache)
        self.assertEqual(len(calls), 1)

    def test_agent_parses_and_renormalises(self):
        agent = LLMAgent("gemini", completion_fn=fake('{"H":5,"D":3,"A":2,"raison":"forme"}', []))
        r = agent.ask({"match_id": "m"})
        self.assertEqual(r.status, "ok")
        self.assertAlmostEqual(sum(r.probs.values()), 1.0)
        self.assertEqual((r.appels, r.tokens_mesure), (1, "mesure"))

    def test_non_json_answer_is_an_error_not_an_opinion(self):
        r = LLMAgent("gemini", completion_fn=fake("je pense que domicile", [])).ask({})
        self.assertEqual(r.status, "erreur")
        self.assertIsNone(r.probs)

    def test_missing_key_never_calls(self):
        calls = []
        with mock.patch.dict(os.environ, {}, clear=True):
            r = llm.complete("deepseek", [{"role": "user", "content": "q"}], completion_fn=fake("{}", calls))
        self.assertEqual(r.status, "indisponible")
        self.assertEqual(calls, [])

    def test_local_llamacpp_needs_no_key_and_targets_local_server(self):
        seen = {}

        def fn(model, messages, **params):
            seen.update(params, model=model)
            return fake("ok", [])(model, messages)
        with mock.patch.dict(os.environ, {}, clear=True):
            r = llm.complete("llamacpp", [{"role": "user", "content": "q"}], completion_fn=fn)
        self.assertEqual((r.status, r.cout_usd), ("ok", 0.0))
        self.assertEqual(seen["api_base"], llm.LLAMACPP_BASE)
        self.assertTrue(seen["model"].startswith("openai/"))

    def test_status_lists_every_provider_without_network(self):
        rows = llm.status(check_network=False)
        self.assertEqual({r["fournisseur"] for r in rows}, set(llm.PROVIDERS))
        self.assertNotIn("cle-de-test", json.dumps(rows))


if __name__ == "__main__":
    unittest.main()
