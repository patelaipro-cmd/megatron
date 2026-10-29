import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from megatron import jeton, suivi, synchro
from megatron.ledger import Ledger
from megatron.store import MemoryStore, parse_dt


class JetonTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = MemoryStore(self.tmp.name)
        self.ko = parse_dt("2099-01-01T12:00:00Z")
        self.before = parse_dt("2099-01-01T10:00:00Z")
        self.p = {"H": .5, "D": .3, "A": .2}

    def init(self):
        return jeton.initialiser(self.store, "codex", source="test fictif")

    def pred(self, ledger, match="fictif"):
        return ledger.predict(match, self.ko, self.p, model_version="test", source="test fictif", recorded_at=self.before)

    def test_simulations_sans_jeton_restent_utilisables(self):
        self.pred(Ledger(self.store))
        self.assertFalse(jeton.statut(self.store)["protege"])

    def test_memoire_reelle_sans_jeton_refuse(self):
        with mock.patch.object(jeton, "REAL_MEMORY", self.store.root):
            with self.assertRaises(jeton.JetonError):
                self.pred(Ledger(self.store))
        self.assertFalse((self.store.root / "performances.jsonl").exists())
        self.assertFalse((self.store.root / ".registre.lock").exists())

    def test_initialisation_unique_et_statut(self):
        e = self.init()
        before = (self.store.root / "travail.jsonl").read_bytes()
        self.assertEqual(jeton.statut(self.store)["id"], e.id)
        with self.assertRaises(jeton.JetonError):
            self.init()
        self.assertEqual((self.store.root / "travail.jsonl").read_bytes(), before)

    def test_non_detenteur_et_id_perime_refuses(self):
        e = self.init()
        for access, ident in [(None, None), ("claude", e.id), ("codex", None), ("codex", "ancien")]:
            with self.subTest(access=access, ident=ident), self.assertRaises(jeton.JetonError):
                self.pred(Ledger(self.store, acces=access, jeton_id=ident))
        self.assertFalse((self.store.root / "performances.jsonl").exists())

    def test_transfert_garde_historique_et_revoque_ancien_acces(self):
        old = self.init()
        codex = Ledger(self.store, acces="codex", jeton_id=old.id)
        self.pred(codex)
        new = jeton.transmettre(self.store, "codex", old.id, "claude", source="test relais")
        self.assertEqual(new.supersedes, old.id)
        self.assertEqual(new.value["precedent"], old.id)
        self.assertEqual(len(self.store.history("travail", jeton.KEY)), 2)
        with self.assertRaises(jeton.JetonError):
            self.pred(codex, "autre")
        claude = Ledger(self.store, acces="claude", jeton_id=new.id)
        claude.result("fictif", "H", source="score fictif", observed_at="2099-01-01T14:00:00Z")
        self.assertEqual(claude.evaluate("test")["n"], 1)

    def test_transfert_par_non_detenteur_refuse(self):
        e = self.init()
        with self.assertRaises(jeton.JetonError):
            jeton.transmettre(self.store, "claude", e.id, "codex", source="test")
        self.assertEqual(jeton.statut(self.store)["id"], e.id)

    def test_refus_avant_appel_agent(self):
        e = self.init()
        with mock.patch("megatron.suivi.fuse") as fuse:
            with self.assertRaises(jeton.JetonError):
                suivi.prevoir(self.store, {"match_id": "fictif"}, self.ko,
                              acces="claude", jeton_id=e.id, now=self.before)
        fuse.assert_not_called()

    def test_prevoir_et_resultat_avec_jeton(self):
        from megatron.agents import StatsAgent
        e = self.init()
        out = suivi.prevoir(self.store, {"match_id": "fictif", "xg_home": 1.5, "xg_away": .8},
                            self.ko, agents=[StatsAgent()], now=self.before, acces="codex", jeton_id=e.id)
        self.assertEqual(len(out["enregistre"]), 2)
        suivi.resultat(self.store, "fictif", "2-0", source="test fictif", observed_at="2099-01-01T14:00:00Z",
                       acces="codex", jeton_id=e.id)
        before = (self.store.root / "performances.jsonl").read_bytes()
        with self.assertRaises(ValueError):
            suivi.prevoir(self.store, {"match_id": "fictif", "xg_home": 1.5, "xg_away": .8},
                          self.ko, agents=[StatsAgent()], now=self.before, acces="codex", jeton_id=e.id)
        self.assertEqual((self.store.root / "performances.jsonl").read_bytes(), before)

    def test_verrou_interprocessus_et_nettoyage(self):
        e = self.init()
        code = """import sys
from megatron import jeton
from megatron.store import MemoryStore
try:
    with jeton.ecriture(MemoryStore(sys.argv[1]), 'codex', sys.argv[2]):
        pass
except jeton.JetonError:
    raise SystemExit(23)
"""
        with jeton.ecriture(self.store, "codex", e.id):
            r = subprocess.run([sys.executable, "-c", code, str(self.store.root), e.id], capture_output=True, text=True)
            self.assertEqual(r.returncode, 23, r.stderr)
            with self.assertRaises(jeton.JetonError):
                jeton.transmettre(self.store, "codex", e.id, "claude", source="test")
        self.assertFalse((self.store.root / ".registre.lock").exists())
        self.pred(Ledger(self.store, acces="codex", jeton_id=e.id))

    def test_jetons_divergents_refuses_meme_si_valeur_identique(self):
        e = self.init()
        self.store.record("travail", jeton.KEY, e.value, source="branche divergente", supersede=False)
        with self.assertRaises(jeton.JetonError):
            self.pred(Ledger(self.store, acces="codex", jeton_id=e.id))
        self.assertFalse(synchro.verifier(self.store.root)["ok"])

    def test_cli_transfert_et_ecriture_sans_jeton(self):
        from megatron.__main__ import main
        e = self.init()
        with mock.patch("builtins.print"):
            rc = main(["--memoire", str(self.store.root), "resultat", "fictif", "H", "--source", "test"])
            self.assertEqual(rc, 2)
            rc = main(["--memoire", str(self.store.root), "jeton", "transmettre", "--acces", "codex",
                       "--jeton", e.id, "--a", "claude", "--source", "test"])
            self.assertEqual(rc, 0)
        self.assertEqual(jeton.statut(self.store)["detenteur"], "claude")

    def test_jeton_malforme_refuse_et_signale(self):
        self.store.record("travail", jeton.KEY, {"detenteur": "inconnu"}, source="corruption fictive")
        with self.assertRaises(jeton.JetonError):
            jeton.statut(self.store)
        self.assertFalse(synchro.verifier(self.store.root)["ok"])

    def test_statut_ne_cree_pas_de_dossier(self):
        from megatron.__main__ import main
        missing = self.store.root / "absent"
        with mock.patch("builtins.print"):
            self.assertEqual(main(["--memoire", str(missing), "jeton", "statut"]), 0)
        self.assertFalse(missing.exists())
