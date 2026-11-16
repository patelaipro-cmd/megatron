"""Tests du plan de fenêtres réelles : aucune capture/probabilité simulée."""

import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

from scripts import planifier_controles_t15 as plan


KICK = datetime.fromisoformat("2026-11-16T15:00:00+00:00")
NOW = datetime.fromisoformat("2026-11-16T08:00:00+00:00")
URL = f"{plan.BASE}/uefa.nations/scoreboard?dates=20261116"


def document(ids=("401",), capture=NOW, kickoff=KICK):
    return {
        "statut": "LISTE_PROSPECTIVE_ESPN_NON_VALIDEE_MULTI_SOURCE",
        "decouverte_le": capture.isoformat(), "matchs_trouves": len(ids),
        "tronques": 0, "erreurs": [],
        "fixtures": [{"ligue": "uefa.nations", "event_id": identifiant,
                      "coup_envoi": kickoff.isoformat()} for identifiant in ids],
        "sources_capturees": [{"url": URL, "collecte_le": capture.isoformat(),
                              "sha256": "a" * 64}],
    }


class PlanDeControlesTests(unittest.TestCase):
    def test_plan_une_fixture_six_etapes_et_t15_a_heure_kinshasa(self):
        r = plan.planifier(document(), au=NOW)
        self.assertEqual(r["fixtures"], 1)
        self.assertEqual(r["controles"], 6)
        self.assertEqual(r["echeances_passees_sans_capture"], 0)
        self.assertEqual(r["statut"], "PLAN_MANUEL_NON_ACTIVE")
        self.assertEqual(r["watch"], 0)
        self.assertIsNone(r["v1_probability"])
        self.assertIsNone(r["v2_probability"])
        controle = next(x for x in r["details"] if x["etape"] == "T+15")
        self.assertEqual(controle["heure_cible_kinshasa"], "2026-11-16T16:15:00+01:00")
        self.assertEqual(controle["fenetre_t15_debut_utc"], "2026-11-16T15:12:00+00:00")
        self.assertEqual(controle["fenetre_t15_fin_utc"], "2026-11-16T15:18:00+00:00")

    def test_taches_hors_delai_ni_fausse_capture_ni_retro_prediction(self):
        r = plan.planifier(document(), au=KICK + timedelta(minutes=25))
        self.assertEqual(r["echeances_passees_sans_capture"], 6)
        self.assertEqual(len(r["lots_max_5"]), 0)
        self.assertTrue(all(c["statut"] == "ECHEANCE_PASSEE_SANS_CAPTURE"
                            for c in r["details"]))

    def test_fenetre_t15_est_conservee_jusqua_minute_18(self):
        r = plan.planifier(document(), au=KICK + timedelta(minutes=17))
        self.assertEqual(r["echeances_passees_sans_capture"], 5)
        self.assertEqual(r["lots_max_5"][0]["etape"], "T+15")

    def test_lots_ne_depasse_jamais_cinq(self):
        r = plan.planifier(document(ids=tuple(str(i) for i in range(6))), au=NOW)
        t15 = [x for x in r["lots_max_5"] if x["etape"] == "T+15"]
        self.assertEqual([len(x["match_ids"]) for x in t15], [5, 1])

    def test_sources_absentes_futures_ou_post_match_refusees(self):
        d = document()
        d["sources_capturees"] = []
        with self.assertRaisesRegex(ValueError, "preuves brutes"):
            plan.planifier(d, au=NOW)
        d = document(capture=KICK + timedelta(minutes=1))
        with self.assertRaisesRegex(ValueError, "prospective"):
            plan.planifier(d, au=KICK + timedelta(minutes=30))
        with self.assertRaisesRegex(ValueError, "futur"):
            plan.planifier(document(capture=NOW + timedelta(minutes=1)), au=NOW)

    def test_echec_en_cas_de_troncature_conflit_ou_mauvais_hash(self):
        for champ, valeur in (("tronques", 1), ("erreurs", ["HTTP 500"])):
            d = document()
            d[champ] = valeur
            with self.assertRaisesRegex(ValueError, "incomplète"):
                plan.planifier(d, au=NOW)
        d = document()
        d["sources_capturees"][0]["sha256"] = "fausse"
        with self.assertRaisesRegex(ValueError, "empreinte"):
            plan.planifier(d, au=NOW)

    def test_ecriture_unique_n_ecrase_pas_la_preuve(self):
        with tempfile.TemporaryDirectory() as tmp:
            entree, sortie = Path(tmp) / "entree.json", Path(tmp) / "sortie.json"
            entree.write_text(json.dumps(document()), encoding="utf-8")
            with mock.patch.object(plan, "planifier", return_value={"statut": "PLAN_MANUEL_NON_ACTIVE"}):
                with mock.patch("builtins.print"):
                    self.assertEqual(plan.main(["--entree", str(entree), "--sortie", str(sortie)]), 0)
                    with self.assertRaises(FileExistsError):
                        plan.main(["--entree", str(entree), "--sortie", str(sortie)])


if __name__ == "__main__":
    unittest.main()
