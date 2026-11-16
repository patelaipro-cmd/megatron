"""Tests hors réseau de la première source score LIVE ESPN."""

import json
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock

from scripts import collecter_score_t15_espn as collecteur


NOW = datetime.fromisoformat("2026-11-16T20:15:00+01:00")
KICK = datetime.fromisoformat("2026-11-16T20:00:00+01:00")


def fixture(event_id="123"):
    return {"ligue": "esp.2", "event_id": event_id, "coup_envoi": KICK}


def event(event_id="123"):
    return {"id": event_id, "date": "2026-11-16T19:00:00Z",
            "status": {"type": {"state": "in", "name": "STATUS_IN_PROGRESS", "completed": False},
                       "period": 1, "displayClock": "15:00"},
            "competitions": [{"competitors": [
                {"homeAway": "home", "score": "1", "team": {"displayName": "Granada"}},
                {"homeAway": "away", "score": "0", "team": {"displayName": "Cádiz"}}]}]}


def donnees(events=None):
    return json.dumps({"events": [event()] if events is None else events}).encode()


class ESPNLiveEvidenceTests(unittest.TestCase):
    def test_capture_reelle_une_source_ne_devient_jamais_watch(self):
        r = collecteur.collecter([fixture()], au=NOW, lire=lambda url: donnees())[0]
        self.assertEqual(r["score"], {"H": 1, "A": 0})
        self.assertEqual(r["minute_jeu"], 15)
        self.assertEqual(r["statut"], "REFUS")
        self.assertIsNone(r["V1_DOMINATION"])
        self.assertIsNone(r["V2_GOALS"])
        self.assertEqual(r["score_sources_independantes"], 1)
        self.assertEqual(len(r["sha256_reponse_espn"]), 64)

    def test_pas_de_requete_hors_fenetre_ni_de_reconstruction(self):
        def ne_pas_appeler(url):
            raise AssertionError("aucune requête attendue")
        for minute in (-180, -5, 0, 19):
            with self.subTest(minute=minute):
                now = KICK + timedelta(minutes=minute)
                r = collecteur.collecter([fixture()], au=now, lire=ne_pas_appeler)[0]
                self.assertIn("HORS_FENETRE", r["motif"])
                self.assertNotIn("score", r)
                self.assertEqual(r["score_sources_independantes"], 0)

    def test_le_statut_final_et_la_periode_deux_refusent(self):
        for attr, value in (("period", 2), ("displayClock", "46:00")):
            with self.subTest(attr=attr):
                e = event()
                e["status"][attr] = value
                r = collecteur.collecter([fixture()], au=NOW, lire=lambda u: donnees([e]))[0]
                self.assertNotIn("score", r)
        e = event()
        e["status"]["type"]["name"] = "STATUS_FINAL"
        self.assertNotIn("score", collecteur.collecter([fixture()], au=NOW, lire=lambda u: donnees([e]))[0])

    def test_score_invalide_ou_equipes_incompletes(self):
        for score in ("", "1.5", -1, True):
            with self.subTest(score=score):
                e = event()
                e["competitions"][0]["competitors"][0]["score"] = score
                r = collecteur.collecter([fixture()], au=NOW, lire=lambda u: donnees([e]))[0]
                self.assertNotIn("score", r)
        e = event()
        e["competitions"][0]["competitors"].pop()
        self.assertNotIn("score", collecteur.collecter([fixture()], au=NOW, lire=lambda u: donnees([e]))[0])

    def test_identifiant_ou_kickoff_differents(self):
        e = event()
        e["date"] = "2026-11-16T19:10:00Z"
        r = collecteur.collecter([fixture()], au=NOW, lire=lambda u: donnees([e]))[0]
        self.assertIn("désaccord", r["motif"])
        r = collecteur.collecter([fixture()], au=NOW, lire=lambda u: donnees([event("456")]))[0]
        self.assertIn("absent", r["motif"])

    def test_minute_incoherente_refuse(self):
        e = event()
        e["status"]["displayClock"] = "12:00"
        self.assertNotIn("score", collecteur.collecter([fixture()], au=NOW, lire=lambda u: donnees([e]))[0])
        e["status"]["displayClock"] = "15:00"
        self.assertIn("score", collecteur.collecter([fixture()], au=NOW, lire=lambda u: donnees([e]))[0])

    def test_erreur_http_produit_refus_sans_crash(self):
        def erreur(_):
            raise OSError("indisponible")
        r = collecteur.collecter([fixture()], au=NOW, lire=erreur)[0]
        self.assertEqual(r["statut"], "REFUS")
        self.assertIn("ESPN_INUTILISABLE", r["motif"])
        self.assertEqual(r["score_sources_independantes"], 0)

    def test_cache_une_requete_par_ligue_et_jour(self):
        compteur = []
        def lire(url):
            compteur.append(url)
            return donnees([event("123"), event("124")])
        r = collecteur.collecter([fixture("123"), fixture("124")], au=NOW, lire=lire)
        self.assertEqual(len(compteur), 1)
        self.assertEqual(len(r), 2)
        self.assertTrue(all("score" in ligne for ligne in r))

    def test_validation_liste_et_fuseaux(self):
        d = {"fixtures": [{"ligue": "esp.2", "event_id": "123", "coup_envoi": KICK.isoformat()}]}
        self.assertEqual(len(collecteur.valider_fixtures(d, {"esp.2"})), 1)
        with self.assertRaisesRegex(ValueError, "double"):
            collecteur.valider_fixtures({"fixtures": d["fixtures"] * 2}, {"esp.2"})
        with self.assertRaisesRegex(ValueError, "fuseau"):
            collecteur.valider_fixtures({"fixtures": [{**d["fixtures"][0], "coup_envoi": "2026-11-16T20:00:00"}]}, {"esp.2"})
        with self.assertRaisesRegex(ValueError, "non configurée"):
            collecteur.valider_fixtures({"fixtures": [{**d["fixtures"][0], "ligue": "evil/slash"}]}, {"esp.2"})
        with self.assertRaisesRegex(ValueError, "50"):
            collecteur.valider_fixtures({"fixtures": d["fixtures"] * 51}, {"esp.2"})

    def test_decouverte_vrais_evenements_futurs_seulement(self):
        now = KICK - timedelta(hours=2)
        a_venir = event("124")
        a_venir["status"]["type"]["state"] = "pre"
        deja_commence = event("125")
        trop_loin = event("126")
        trop_loin["date"] = "2026-11-17T02:00:00Z"
        trop_loin["status"]["type"]["state"] = "pre"
        observe = []
        def lire(url):
            observe.append(url)
            return donnees([a_venir, deja_commence, trop_loin])
        r = collecteur.reperer_prochains({"esp.2"}, au=now, lire=lire)
        self.assertEqual(r["matchs_trouves"], 1)
        self.assertEqual(r["fixtures"][0]["event_id"], "124")
        self.assertEqual(len(observe), 1)
        self.assertEqual(r["statut"], "LISTE_PROSPECTIVE_ESPN_NON_VALIDEE_MULTI_SOURCE")

    def test_decouverte_indisponible_ne_fabrique_pas_de_matchs(self):
        def indisponible(_):
            raise OSError("ESPN injoignable")
        r = collecteur.reperer_prochains({"esp.2"}, au=KICK, lire=indisponible)
        self.assertEqual(r["matchs_trouves"], 0)
        self.assertEqual(len(r["erreurs"]), 1)
        self.assertEqual(r["fixtures"], [])

    def test_decouverte_exclut_reports_et_horizon_invalide(self):
        now = KICK - timedelta(hours=2)
        reporte = event("127")
        reporte["status"]["type"].update(state="pre", name="STATUS_POSTPONED")
        r = collecteur.reperer_prochains({"uefa.nations"}, au=now,
                                         lire=lambda u: donnees([reporte]), horizon_h=24)
        self.assertEqual(r["matchs_trouves"], 0)
        with self.assertRaisesRegex(ValueError, "24"):
            collecteur.reperer_prochains({"uefa.nations"}, au=now,
                                         lire=lambda u: donnees([]), horizon_h=25)

    def test_sortie_decouverte_ne_remplace_pas_un_fichier_existant(self):
        with tempfile.TemporaryDirectory() as tmp:
            fichier = Path(tmp) / "fixtures.json"
            exemple = {"decouverte_le": NOW.isoformat(), "matchs_trouves": 1,
                       "erreurs": [], "fixtures": [{"event_id": "123"}]}
            with mock.patch.object(collecteur, "reperer_prochains", return_value=exemple):
                with mock.patch("builtins.print"):
                    self.assertEqual(collecteur.main(["--decouvrir", "--sortie-fixtures", str(fichier)]), 0)
                contenu = fichier.read_text(encoding="utf-8")
                with self.assertRaises(FileExistsError):
                    collecteur.main(["--decouvrir", "--sortie-fixtures", str(fichier)])
                self.assertEqual(fichier.read_text(encoding="utf-8"), contenu)


if __name__ == "__main__":
    unittest.main()
