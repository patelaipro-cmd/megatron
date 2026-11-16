"""Tests déterministes du module LIVE T+15, sans réseau ni données réelles."""

import copy
import json
import math
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from megatron import live_t15
from megatron.__main__ import main


DEMO = Path(__file__).parent / "fixtures" / "live_t15_demo.json"


def exemple():
    return json.loads(DEMO.read_text(encoding="utf-8"))


class LiveT15Tests(unittest.TestCase):
    def test_v1_et_v2_sont_distincts_et_emboites(self):
        r = live_t15.evaluer(exemple())
        self.assertEqual(r["statut"], "WATCH")
        self.assertEqual(r["phase"], "LIVE_T15")
        self.assertFalse(r["poids_modifies"])
        self.assertFalse(r["activation_automatique"])
        self.assertFalse(r["registre_prospectif_modifie"])
        self.assertEqual(r["validation"], "NON_CALIBRE_EN_DIRECT")
        self.assertEqual(r["nature"], "REJEU_NON_PROSPECTIF")
        m = r["V1_DOMINATION"]["marges_brutes"]
        self.assertLessEqual(m["H_MARGE_3PLUS"], m["H_MARGE_2PLUS"])
        self.assertLessEqual(m["A_MARGE_3PLUS"], m["A_MARGE_2PLUS"])
        self.assertAlmostEqual(sum(r["V1_DOMINATION"]["1X2_brut"].values()), 1.0, places=10)
        o = r["V2_GOALS"]["over_match_brut"]
        self.assertGreaterEqual(o["OVER_1_5"], o["OVER_2_5"])
        self.assertGreaterEqual(o["OVER_2_5"], o["OVER_3_5"])
        self.assertAlmostEqual(sum(r["V2_GOALS"]["repartition"].values()), 1.0, places=10)

    def test_score_conditionne_over_deja_acquis(self):
        d = exemple()
        d["score"] = {"H": 4, "A": 0}
        r = live_t15.evaluer(d)
        self.assertTrue(all(p == 1.0 for p in r["V2_GOALS"]["over_match_brut"].values()))
        self.assertLess(r["V1_DOMINATION"]["marges_brutes"]["H_MARGE_3PLUS"], 1.0)

    def test_taux_nuls_scores_figes(self):
        d = exemple()
        d["baseline"]["lambda_H"] = 0
        d["baseline"]["lambda_A"] = 0
        r = live_t15.evaluer(d)
        self.assertAlmostEqual(r["V1_DOMINATION"]["1X2_brut"]["H"], 1.0)
        self.assertEqual(r["V1_DOMINATION"]["marges_brutes"]["H_MARGE_2PLUS"], 0.0)
        self.assertEqual(r["V2_GOALS"]["over_match_brut"]["OVER_1_5"], 0.0)

    def test_score_zero_et_total_poisson_reference(self):
        d = exemple()
        d["score"] = {"H": 0, "A": 0}
        r = live_t15.evaluer(d)
        mu = (1.8 + .9) * 75 / 90
        p_over_1_5 = 1 - math.exp(-mu) * (1 + mu)
        self.assertAlmostEqual(r["V2_GOALS"]["over_match_brut"]["OVER_1_5"], p_over_1_5, places=12)

    def test_valeurs_numeriques_invalides_refusees(self):
        for value in (float("nan"), -1, 10.1, True, "1.5"):
            with self.subTest(value=value):
                d = exemple()
                d["baseline"]["lambda_H"] = value
                with self.assertRaises(ValueError):
                    live_t15.evaluer(d)
        d = exemple()
        d["score"]["H"] = 1.5
        with self.assertRaises(ValueError):
            live_t15.evaluer(d)

    def test_absence_baseline_refuse_sans_probabilites(self):
        d = exemple()
        del d["baseline"]
        r = live_t15.evaluer(d)
        self.assertEqual(r["statut"], "REFUS")
        self.assertIsNone(r["V1_DOMINATION"])
        self.assertIsNone(r["V2_GOALS"])

    def test_taux_post_kickoff_refuses(self):
        d = exemple()
        d["baseline"]["calcule_le"] = d["observed_at"]
        r = live_t15.evaluer(d)
        self.assertEqual(r["statut"], "REFUS")
        self.assertIn("fuite temporelle", " ".join(r["motifs"]))

    def test_xi_ulterieurs_au_snapshot_refuses(self):
        d = exemple()
        d["verification"]["xi_collecte_le"] = "2026-11-15T20:30:00+01:00"
        r = live_t15.evaluer(d)
        self.assertEqual(r["statut"], "REFUS")
        self.assertIn("fuite temporelle", " ".join(r["motifs"]))

    def test_score_perime_refus(self):
        d = exemple()
        d["verification"]["score_collecte_le"] = "2026-11-15T20:10:00+01:00"
        r = live_t15.evaluer(d)
        self.assertEqual(r["statut"], "REFUS")
        self.assertIn("score périmé", " ".join(r["motifs"]))

    def test_xi_et_incidents_bloquent(self):
        for path, value in (("xi_officiels", False), ("xi_identiques_hypothese_base", False),
                            ("cartons_rouges", {"H": 1, "A": 0}), ("var_en_cours", True),
                            ("conflit_sources", True), ("score_sources", ["une seule"])):
            with self.subTest(path=path):
                d = exemple()
                d["verification"][path] = value
                r = live_t15.evaluer(d)
                self.assertEqual(r["statut"], "REFUS")
                self.assertIsNone(r["V1_DOMINATION"])

    def test_t15_fenetre_et_horloge(self):
        d = exemple()
        d["minute"] = 22
        with self.assertRaisesRegex(ValueError, "hors T\\+15"):
            live_t15.evaluer(d)
        d = exemple()
        d["observed_at"] = "2026-11-15T20:40:00+01:00"
        with self.assertRaisesRegex(ValueError, "heure de relevé incohérente"):
            live_t15.evaluer(d)

    def test_bascule_domicile_exterieur(self):
        d = exemple()
        p = live_t15.evaluer(d)["V1_DOMINATION"]
        inverse = copy.deepcopy(d)
        inverse["score"] = {"H": d["score"]["A"], "A": d["score"]["H"]}
        inverse["baseline"]["lambda_H"] = d["baseline"]["lambda_A"]
        inverse["baseline"]["lambda_A"] = d["baseline"]["lambda_H"]
        q = live_t15.evaluer(inverse)["V1_DOMINATION"]
        self.assertAlmostEqual(p["1X2_brut"]["H"], q["1X2_brut"]["A"], places=12)
        self.assertAlmostEqual(p["marges_brutes"]["H_MARGE_2PLUS"],
                               q["marges_brutes"]["A_MARGE_2PLUS"], places=12)

    def test_journal_distinct_append_only_et_dedoublonnage(self):
        r = live_t15.evaluer(exemple())
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "live_t15.jsonl"
            live_t15.enregistrer_journal(dest, r)
            self.assertEqual(len(dest.read_text(encoding="utf-8").splitlines()), 1)
            with self.assertRaisesRegex(ValueError, "doublon"):
                live_t15.enregistrer_journal(dest, r)
            with self.assertRaisesRegex(ValueError, "doublon"):
                live_t15.enregistrer_journal(dest, live_t15.evaluer(exemple()))
            r2 = live_t15.evaluer({**exemple(), "score": {"H": 2, "A": 0}})
            live_t15.enregistrer_journal(dest, r2)
            self.assertEqual(len(dest.read_text(encoding="utf-8").splitlines()), 2)
            with self.assertRaises(ValueError):
                live_t15.enregistrer_journal(Path(tmp) / "performances.jsonl", r)

    def test_cli_sans_ecriture_par_defaut(self):
        with mock.patch("builtins.print") as printer, mock.patch("megatron.store.MemoryStore.record") as record:
            self.assertEqual(main(["live-t15", str(DEMO)]), 0)
            self.assertIn("LIVE_T15", printer.call_args.args[0])
            record.assert_not_called()


if __name__ == "__main__":
    unittest.main()
