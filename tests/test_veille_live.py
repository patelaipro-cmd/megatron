import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from megatron import live_t15, veille_live
from megatron.__main__ import main


DEMO = Path(__file__).parent / "fixtures" / "veille_live_demo.json"


def dossier():
    return json.loads(DEMO.read_text(encoding="utf-8"))


class VeilleLiveTests(unittest.TestCase):
    def test_cinq_jalons_et_timezone(self):
        p = veille_live.planifier("2026-11-16T20:00:00+01:00", au="2026-11-16T18:00:00+01:00")
        self.assertEqual([x["checkpoint"] for x in p], ["T-3h", "T-60", "T-30", "T-5", "T+15"])
        self.assertEqual(p[0]["prevu_le"], "2026-11-16T17:00:00+01:00")
        self.assertFalse(p[0]["a_venir"])
        self.assertTrue(p[-1]["a_venir"])

    def test_concordance_3_sources_plus_xi(self):
        r = veille_live.assembler_t15(dossier())
        self.assertEqual(r["score"], {"H": 1, "A": 0})
        self.assertEqual(len(r["verification"]["score_sources"]), 3)
        self.assertEqual(live_t15.evaluer(r)["statut"], "REFUS")
        self.assertEqual(live_t15.evaluer(r, simulation=True)["statut"], "WATCH")
        self.assertEqual(r["qualite_preuves"].split(" : ")[0], "DECLARATIVE_NON_AUDITEE")

    def test_sources_contradictoires_refusees(self):
        d = dossier()
        d["scores"][1]["score"]["A"] = 1
        with self.assertRaisesRegex(ValueError, "conflit score"):
            veille_live.assembler_t15(d)

    def test_source_trop_ancienne_refusee(self):
        d = dossier()
        d["scores"][1]["collecte_le"] = "2026-11-15T20:05:00+01:00"
        with self.assertRaisesRegex(ValueError, "moins de trois"):
            veille_live.assembler_t15(d)

    def test_source_future_refusee(self):
        d = dossier()
        d["scores"][1]["collecte_le"] = "2026-11-15T20:20:00+01:00"
        with self.assertRaisesRegex(ValueError, "fuite temporelle"):
            veille_live.assembler_t15(d)

    def test_mauvais_domaine_refuse(self):
        d = dossier()
        d["scores"][1]["source_url"] = "https://example.com/fiction/score"
        with self.assertRaisesRegex(ValueError, "non attribuable"):
            veille_live.assembler_t15(d)

    def test_rotation_xi_bloque_probabilites(self):
        d = dossier()
        d["xi_officiel"]["titulaires"]["H"][10] = "H12"
        r = veille_live.assembler_t15(d)
        self.assertFalse(r["verification"]["xi_identiques_hypothese_base"])
        ev = live_t15.evaluer(r, simulation=True)
        self.assertEqual(ev["statut"], "REFUS")

    def test_fausse_source_officielle_ne_debloque_pas_mode_normal(self):
        d = dossier()
        d["xi_officiel"]["source_url"] = "https://example.net/not-official"
        d["xi_officiel"]["organisme"] = "Organisation inventée"
        r = veille_live.assembler_t15(d)
        self.assertEqual(live_t15.evaluer(r)["statut"], "REFUS")
        self.assertEqual(live_t15.evaluer(r, simulation=True)["authentification"], "NON_VERIFIEE")

    def test_url_avec_session_refusee(self):
        d = dossier()
        d["xi_officiel"]["source_url"] += "?session=secret"
        with self.assertRaisesRegex(ValueError, "session"):
            veille_live.assembler_t15(d)

    def test_xi_officiel_releve_apres_coup_denvoi_refuse(self):
        d = dossier()
        d["xi_officiel"]["collecte_le"] = "2026-11-15T20:03:00+01:00"
        with self.assertRaisesRegex(ValueError, "trop tard"):
            veille_live.assembler_t15(d)

    def test_carton_rouge_refuse(self):
        d = dossier()
        d["scores"][0]["cartons_rouges"]["H"] = 1
        with self.assertRaisesRegex(ValueError, "incident live"):
            veille_live.assembler_t15(d)

    def test_cli_pas_d_ecriture_sans_sortie(self):
        with mock.patch("builtins.print") as printer:
            self.assertEqual(main(["veille-live", "assembler", "--entree", str(DEMO)]), 2)
            self.assertEqual(main(["veille-live", "assembler", "--entree", str(DEMO), "--simulation"]), 0)
            self.assertIn("V1_DOMINATION", printer.call_args.args[0])
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "instantane.json"
            with mock.patch("builtins.print"):
                self.assertEqual(main(["veille-live", "assembler", "--entree", str(DEMO), "--sortie", str(output), "--simulation"]), 0)
            before = output.read_bytes()
            with mock.patch("builtins.print"):
                self.assertEqual(main(["veille-live", "assembler", "--entree", str(DEMO), "--sortie", str(output), "--simulation"]), 2)
            self.assertEqual(output.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
