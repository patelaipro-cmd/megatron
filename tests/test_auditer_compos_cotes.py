import math
import unittest
from scripts.auditer_compos_cotes import auditer, instant

AU = instant("2026-10-30T19:59:00Z")


def compo(event="1", heure="19:00", n=11):
    return [{"event_id": event, "division": "F1", "coup_envoi": "2026-10-30T20:00:00Z",
             "collecte_le": f"2026-10-30T{heure}:00Z", "equipe": team,
             "statut": "titulaire", "joueur_id": str(j)}
            for team in ("A", "B") for j in range(n)]


def cote(heure, h=2, event="1", book="Book", type_ligne="courante"):
    return {"evenement_id": event, "division": "F1", "coup_envoi": "2026-10-30T20:00:00Z",
            "collecte_le": f"2026-10-30T{heure}:00Z", "source": "espn", "type_ligne": type_ligne,
            "bookmaker": book, "domicile": "A", "exterieur": "B", "cote_H": h, "cote_D": 3, "cote_A": 4}


class TestAuditComposCotes(unittest.TestCase):
    def test_paire_sans_marge_et_mouvement_signe(self):
        r = auditer(compo() + compo(heure="19:10"), [cote("18:55"), cote("19:05", 1.5)], AU)
        self.assertEqual(r["matchs_avec_compos_completes"], 1)
        self.assertEqual(r["matchs_apparies"], 1)
        p = r["paires"][0]
        self.assertAlmostEqual(sum(p["probabilites_sans_marge_apres"].values()), 1)
        self.assertGreater(p["mouvement_points"]["H"], 0)
        self.assertAlmostEqual(sum(p["mouvement_points"].values()), 0, places=5)
        self.assertEqual(p["premiere_compo_complete_collectee_le"], "2026-10-30T19:00:00+00:00")

    def test_pas_de_remplacement_par_ouverture_ou_autre_bookmaker(self):
        r = auditer(compo(), [cote("18:55", type_ligne="ouverture"), cote("18:55", book="Autre"), cote("19:05")], AU)
        self.assertEqual(r["paires_match_bookmaker"], 0)

    def test_incomplet_repetitions_et_deux_matchs_simultanes(self):
        cs = compo() * 2 + compo(event="2") + compo(event="3", n=10)
        odds = [cote(t, event=e) for e in ("1", "2", "3") for t in ("18:55", "19:05")]
        r = auditer(cs, odds, AU)
        self.assertEqual(r["matchs_avec_compos_completes"], 2)
        self.assertEqual(r["matchs_apparies"], 2)

    def test_apres_coup_envoi_et_capture_simultanee_exclues(self):
        r = auditer(compo(), [cote("18:55"), cote("19:00"), cote("20:01")], AU)
        self.assertEqual(r["paires_match_bookmaker"], 0)
        self.assertEqual(r["exclusions_lignes_ou_captures"]["cote_hors_temps"], 1)

    def test_dates_naives_cotes_non_finies_et_contradictions(self):
        for v in (math.nan, math.inf, 1):
            r = auditer(compo(), [cote("18:55", v), cote("19:05")], AU)
            self.assertEqual(r["paires_match_bookmaker"], 0)
        r = auditer(compo(), [cote("18:55"), cote("18:55", 2.1), cote("19:05")], AU)
        self.assertEqual(r["series_non_appariees"]["cotes_contradictoires"], 1)
        with self.assertRaises(ValueError):
            instant("2026-10-30T19:00:00")


if __name__ == "__main__":
    unittest.main()
