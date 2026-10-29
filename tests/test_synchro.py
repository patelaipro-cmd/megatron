import json
import shutil
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path

from megatron import checkpoint, suivi, synchro
from megatron.agents import StatsAgent
from megatron.store import MemoryStore, parse_dt

KO = parse_dt("2099-01-01T12:00:00Z")


def _memoire(root: Path, matches=("FICTIF:1",)) -> MemoryStore:
    st = MemoryStore(root)
    for m in matches:
        suivi.prevoir(st, {"match_id": m, "xg_home": 1.4, "xg_away": 1.0}, KO, agents=[StatsAgent()],
                      now=KO - timedelta(hours=2))
    checkpoint.save(st, resume="test", prochaines_actions=[])
    return st


class SynchroVerifierTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)

    def test_clean_memory_ok(self):
        _memoire(self.tmp / "a")
        rep = synchro.verifier(self.tmp / "a")
        self.assertTrue(rep["ok"], rep)
        self.assertFalse([a for a in rep["alertes"] if "depuis le checkpoint" in a], rep["alertes"])
        st = MemoryStore(self.tmp / "a")  # second checkpoint : remplace le premier dans « travail »
        checkpoint.save(st, resume="test 2", prochaines_actions=[])
        rep = synchro.verifier(self.tmp / "a")
        self.assertFalse([a for a in rep["alertes"] if "depuis le checkpoint" in a], rep["alertes"])

    def test_divergent_branches_merged_by_union_are_refused(self):
        # deux environnements prévoient le même match, puis leurs lignes sont réunies
        _memoire(self.tmp / "codex")
        _memoire(self.tmp / "claude")
        perf = (self.tmp / "codex" / "performances.jsonl").read_text(encoding="utf-8")
        with (self.tmp / "claude" / "performances.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(perf)
        rep = synchro.verifier(self.tmp / "claude")
        self.assertFalse(rep["ok"])
        self.assertTrue(any("pred:FICTIF:1" in e and "double" in e for e in rep["erreurs"]), rep["erreurs"])
        self.assertTrue(any("modifiée depuis le checkpoint" in a for a in rep["alertes"]), rep["alertes"])

    def test_conflict_markers_and_duplicate_ids(self):
        st = _memoire(self.tmp / "a")
        path = st.root / "performances.jsonl"
        lines = path.read_text(encoding="utf-8").splitlines()
        path.write_text("\n".join(["<<<<<<< HEAD", lines[0], "=======", *lines, ">>>>>>> autre"]) + "\n",
                        encoding="utf-8")
        rep = synchro.verifier(st.root)
        self.assertFalse(rep["ok"])
        self.assertEqual(sum("marqueur de conflit" in e for e in rep["erreurs"]), 3)
        self.assertTrue(any("en double" in e and "identifiant" in e for e in rep["erreurs"]))

    def test_contradiction_unknown_supersedes_and_late_prediction(self):
        st = _memoire(self.tmp / "a")
        st.record("decisions", "stack", "A", source="t", supersede=False)
        st.record("decisions", "stack", "B", source="t", supersede=False)
        line = {"domain": "travail", "id": "zzz", "key": "k", "meta": {}, "observed_at": None,
                "recorded_at": "2026-01-01T00:00:00+00:00", "source": "t", "status": "declare",
                "supersedes": "inconnu", "value": 1}
        late = {"domain": "performances", "id": "late1", "key": "pred:X:v", "meta": {}, "observed_at": None,
                "recorded_at": "2099-01-01T13:00:00+00:00", "source": "t", "status": "verifie",
                "supersedes": None, "value": {"match_id": "X", "kickoff": "2099-01-01T12:00:00+00:00",
                                              "probs": {"H": .5, "D": .3, "A": .2}, "model_version": "v"}}
        with (st.root / "travail.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(line) + "\n")
        with (st.root / "performances.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(late) + "\n")
        errs = synchro.verifier(st.root)["erreurs"]
        self.assertTrue(any("contradiction sur stack" in e for e in errs), errs)
        self.assertTrue(any("inconnu" in e for e in errs), errs)
        self.assertTrue(any("pred:X:v" in e and "après le coup d'envoi" in e for e in errs), errs)

    def test_missing_checkpoint_is_alert_not_error(self):
        st = MemoryStore(self.tmp / "vide")
        rep = synchro.verifier(st.root)
        self.assertTrue(rep["ok"])
        self.assertTrue(any("aucun checkpoint" in a for a in rep["alertes"]))

    def test_cli_exit_code(self):
        from megatron.__main__ import main
        import contextlib
        import io
        _memoire(self.tmp / "a")
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(["--memoire", str(self.tmp / "a"), "synchro", "verifier"]), 0)
            with (self.tmp / "a" / "decisions.jsonl").open("a", encoding="utf-8") as fh:
                fh.write("{pas du json\n")
            self.assertEqual(main(["--memoire", str(self.tmp / "a"), "synchro", "verifier"]), 1)
