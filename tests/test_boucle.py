import unittest
from unittest.mock import patch

from megatron.boucle import boucler
from scripts.boucle_domination import resoudre_nom


def analyse(p2=0.7, decision="GO"):
    return {"niveaux": {"probabilites": {"victoire_par_2_ou_plus": p2}},
            "decision": {"decision": decision, "bloquants": [], "raisons": []}}


class BoucleTest(unittest.TestCase):
    def test_noms_paris_et_alias_audit_sans_inclusion(self):
        self.assertEqual(resoudre_nom("Paris Saint-Germain", {"Paris FC", "Paris SG"}, "F1", {}), "Paris SG")
        self.assertIsNone(resoudre_nom("Paris", {"Paris FC", "Paris SG"}, "F1", {}))
        self.assertIsNone(resoudre_nom("Borussia Dortmund", {"Dortmund"}, "D1", {}))
        audit = {"noms": {"espn:D1": {"Borussia Dortmund": "Dortmund"}}}
        self.assertEqual(resoudre_nom("Borussia Dortmund", {"Dortmund"}, "D1", audit), "Dortmund")
        self.assertIsNone(resoudre_nom("Borussia Dortmund", {"Dortmund"}, "F1", audit))

    def test_objectif_cinq_uniques_et_arret(self):
        seen = []
        def run(f):
            seen.append(f["id"])
            return analyse()
        with patch("megatron.syndicate.ZONE_GO_VALIDEE", True):
            r = boucler([{"id": n} for n in [0, 0, 1, 2, 3, 4, 5]], run, lot=2)
        self.assertEqual(seen, [0, 1, 2, 3, 4])
        self.assertEqual(r["statut"], "OBJECTIF_ATTEINT")

    def test_pas_de_forcage_si_zone_non_validee(self):
        with patch("megatron.syndicate.ZONE_GO_VALIDEE", False):
            r = boucler([{"id": n} for n in range(23)], lambda _: analyse(), lot=10)
        self.assertEqual(r["confirmes"], 0)
        self.assertEqual(len(r["passages"]), 3)
        self.assertEqual(r["statut"], "CALENDRIER_EPUISE")
        self.assertIn("ZONE_GO_NON_VALIDEE", r["blocages_globaux"])

    def test_refus_du_quota_sans_seuil_ou_preuves(self):
        variants = [analyse(.59), analyse(decision="WATCH"), analyse(), analyse()]
        variants[2]["decision"]["bloquants"] = ["données périmées"]
        variants[3]["decision"]["raisons"] = ["compositions manquantes"]
        with patch("megatron.syndicate.ZONE_GO_VALIDEE", True):
            r = boucler([{"id": n} for n in range(4)], lambda f: variants[f["id"]])
        self.assertEqual(r["confirmes"], 0)

    def test_vide_erreurs_et_parametres(self):
        self.assertEqual(boucler([], lambda _: None)["manquants"], 5)
        def fail(_):
            raise ValueError("historique absent")
        self.assertEqual(len(boucler([{"id": 1}], fail)["erreurs"]), 1)
        with self.assertRaises(ValueError):
            boucler([], fail, objectif=4)
