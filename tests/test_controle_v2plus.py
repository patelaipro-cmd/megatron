"""Contrôles V+2 : anti-fuite, sources datées, aucun ajustement de probabilité."""
import unittest
from datetime import date, datetime, timedelta, timezone

from megatron import controle_v2plus, data, syndicate
from scripts.exp021_signaux_v2plus import cohortes, entrainer, marge_2plus, mesures
from megatron.marges import calculer


def match(jour, domicile, exterieur, buts_h, buts_a):
    d = date.fromisoformat(jour)
    return data.Match("F1", d, datetime(d.year, d.month, d.day, 12, tzinfo=timezone.utc),
                      domicile, exterieur, buts_h, buts_a,
                      "H" if buts_h > buts_a else "A" if buts_h < buts_a else "D", None)


class TestControleV2Plus(unittest.TestCase):
    def setUp(self):
        self.hist = [match("2026-10-01", "Nancy", "Equipe A", 1, 0),
                     match("2026-10-03", "Equipe B", "Nancy", 1, 2),
                     match("2026-10-05", "Nancy", "Equipe C", 1, 0),
                     match("2026-10-07", "Equipe D", "Nancy", 1, 4),
                     match("2026-10-09", "Nancy", "Equipe E", 1, 0)]
        self.ko = datetime(2026, 11, 14, 17, tzinfo=timezone.utc)
        self.at = self.ko - timedelta(hours=1)

    def test_signal_quatre_victoires_courtes_sur_cinq_et_strict_avant_jour(self):
        hist = self.hist + [match("2026-11-14", "Nancy", "Equipe F", 9, 0)]
        out = controle_v2plus.resume_victoires(hist, "Nancy", self.ko.date())
        self.assertEqual(out["victoires_sur_5_matchs"], 5)
        self.assertEqual(out["victoires_courtes_sur_5"], 4)
        self.assertEqual(out["victoires_2plus_sur_5"], 1)
        self.assertTrue(out["signal_victoires_courtes"])
        self.assertEqual(len(out["cinq_dernieres_victoires"]), 5)
        self.assertTrue(all(x["date"] < "2026-11-14" for x in out["cinq_derniers_matchs"]))

    def test_absence_de_cinq_matchs_ne_donne_pas_alerte(self):
        out = controle_v2plus.resume_victoires(self.hist[:2], "Nancy", self.ko.date())
        self.assertFalse(out["signal_victoires_courtes"])
        self.assertEqual(out["statut"], "DONNEES_INSUFFISANTES")

    def test_source_avec_date_et_lien_requis_et_tardive_refusee(self):
        ligne = {"controle": "rotation_et_xi_habituel", "etat": "alerte",
                 "constat": "groupe remanié", "source_url": "https://example.org/avant-match",
                 "publie_le": "2026-11-14T12:30:00+00:00", "collecte_le": "2026-11-14T14:00:00+00:00"}
        r = controle_v2plus.evaluer(self.hist, "Nancy", self.ko, self.at, [ligne])
        self.assertFalse(r["ajustement_probabilites"])
        self.assertFalse(r["bloquant_automatique"])
        self.assertEqual(r["points"][0]["verification"], "DECLARATIF_NON_VERIFIE")
        self.assertEqual(r["points"][1]["etat"], "inconnu")
        with self.assertRaises(ValueError):
            controle_v2plus.evaluer(self.hist, "Nancy", self.ko, self.at,
                                     [{**ligne, "collecte_le": "2026-11-14T17:01:00+00:00"}])
        with self.assertRaises(ValueError):
            controle_v2plus.evaluer(self.hist, "Nancy", self.ko, self.at,
                                     [{**ligne, "source_url": "invalide"}])

    def test_signaux_ne_changent_pas_probabilites(self):
        n = syndicate.niveaux(2.1, 0.7)
        before = dict(n["probabilites"])
        controle_v2plus.evaluer(self.hist, "Nancy", self.ko, self.at)
        self.assertEqual(n["probabilites"], before)


class TestExperience(unittest.TestCase):
    def test_probabilite_marge_rapide_egale_reference(self):
        for f, a in [(0.6, 1.2), (1.9, 0.8), (3.4, 2.3)]:
            self.assertAlmostEqual(marge_2plus(f, a), calculer(f, a)["niveaux"]["H"]["victoire_par_2_ou_plus"], places=9)

    def test_experience_sans_leakage_au_meme_jour(self):
        matchs = [match("2026-10-01", "A", "B", 1, 0),
                  match("2026-10-02", "A", "B", 1, 0),
                  match("2026-10-03", "A", "B", 1, 0),
                  match("2026-10-04", "A", "B", 1, 0),
                  match("2026-10-05", "A", "B", 1, 0),
                  match("2026-10-06", "A", "B", 1, 0),
                  match("2026-10-06", "A", "C", 6, 0)]
        vars_ = {m.match_id: {"favori_dom": "1", "lam_fav": "2", "lam_adv": "1", "saison": "2026/27"}
                 for m in matchs}
        out = cohortes(matchs, vars_)
        self.assertEqual(len(out), 2)
        self.assertEqual([r["ratio"] for r in out], [0.0, 0.0])

    def test_apprentissage_statistique_n_inclus_pas_resultats_du_test(self):
        train = [{"ratio": 0.0, "p": 0.4, "y": 0}, {"ratio": 1.0, "p": 0.4, "y": 1}] * 40
        mean = 0.5
        beta = entrainer(train, mean)
        self.assertGreater(beta, 0)
        s = mesures(train, beta, mean)
        self.assertLess(s["candidat"]["log_loss"], s["reference"]["log_loss"])


if __name__ == "__main__":
    unittest.main()
