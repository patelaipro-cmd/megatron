"""Collecte externe : analyse des réponses et écriture, sans réseau (données fictives)."""

import csv
import importlib.util
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("collecte_externe", ROOT / "scripts" / "collecte_externe.py")
ce = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ce)

# 29/10/2026 12:00 UTC : heure multiple de 6, horizon complet de 72 h.
MAINTENANT = datetime(2026, 10, 29, 12, tzinfo=timezone.utc).timestamp()
LIGUES = {34: "F1", 7: "UEFA:UEFA Champions League"}


def evenement(eid, tid, debut, statut="notstarted", nom="Ligue 1"):
    return {"id": eid, "startTimestamp": int(debut), "status": {"type": statut},
            "tournament": {"uniqueTournament": {"id": tid, "name": nom}, "category": {"name": "France"}},
            "homeTeam": {"name": f"Domicile {eid}"}, "awayTeam": {"name": f"Exterieur {eid}"}}


COMPO = {"confirmed": True,
         "home": {"players": [{"player": {"id": 1, "name": "Titulaire Fictif"}, "position": "F", "substitute": False},
                              {"player": {"id": 2, "name": "Remplacant Fictif"}, "position": "M", "substitute": True}],
                  "missingPlayers": [{"player": {"id": 3, "name": "Blesse Fictif", "position": "D"},
                                      "type": "missing", "reason": 1, "description": "Knee injury"}]},
         "away": {"players": [], "missingPlayers": [{"player": {"id": 4, "name": "Doute Fictif"}, "type": "doubtful"}]}}


def faux_reseau(evenements, compos, fpl=None, elo=""):
    def lire(url):
        if "scheduled-events" in url:
            return json.dumps({"events": evenements}).encode()
        if "/lineups" in url:
            eid = int(url.split("/event/")[1].split("/")[0])
            if eid not in compos:
                raise RuntimeError("HTTP 404")
            return json.dumps(compos[eid]).encode()
        if "fantasy" in url:
            return json.dumps(fpl).encode()
        if "clubelo" in url:
            return elo.encode()
        raise AssertionError(url)
    return lire


class TestSofascore(unittest.TestCase):
    def test_filtre_ligue_statut_horizon(self):
        evs = [evenement(1, 34, MAINTENANT + 3600), evenement(2, 99, MAINTENANT + 3600),
               evenement(3, 34, MAINTENANT + 3600, statut="inprogress"), evenement(4, 34, MAINTENANT + 100 * 3600),
               evenement(5, 7, MAINTENANT + 7200, nom="UEFA Champions League")]
        m = ce.matchs_a_venir(evs, MAINTENANT, MAINTENANT + 72 * 3600, LIGUES)
        self.assertEqual([x["event_id"] for x in m], [1, 5])
        self.assertEqual(m[1]["division"], "UEFA:UEFA Champions League")
        self.assertEqual(m[0]["coup_envoi"], "2026-10-29T13:00:00+00:00")

    def test_compo_confirmee_et_absents(self):
        match = ce.matchs_a_venir([evenement(1, 34, MAINTENANT + 3600)], 0, 1e12, LIGUES)[0]
        lignes = ce.lignes_compo(match, COMPO, "t")
        statuts = {(l["cote"], l["joueur"]): (l["statut"], l["motif"]) for l in lignes}
        self.assertEqual(statuts[("H", "Titulaire Fictif")], ("titulaire", ""))
        self.assertEqual(statuts[("H", "Remplacant Fictif")], ("remplacant", ""))
        self.assertEqual(statuts[("H", "Blesse Fictif")], ("absent", "Knee injury"))
        self.assertEqual(statuts[("A", "Doute Fictif")], ("incertain", ""))

    def test_compo_probable_non_publiee(self):
        match = ce.matchs_a_venir([evenement(1, 34, MAINTENANT + 3600)], 0, 1e12, LIGUES)[0]
        lignes = ce.lignes_compo(match, {**COMPO, "confirmed": False}, "t")
        self.assertEqual({l["statut"] for l in lignes}, {"absent", "incertain"})

    def test_horizon_reduit_hors_heures_multiples_de_6(self):
        apres = MAINTENANT + 3600  # 13:00 UTC
        evs = [evenement(1, 34, apres + 2 * 3600), evenement(2, 34, apres + 10 * 3600)]
        lignes = ce.collecter_sofascore(apres, LIGUES, faux_reseau(evs, {1: COMPO, 2: COMPO}), pause=0)
        self.assertEqual({l["event_id"] for l in lignes}, {1})

    def test_toutes_compos_illisibles_est_une_erreur(self):
        evs = [evenement(1, 34, MAINTENANT + 3600)]
        with self.assertRaises(RuntimeError):
            ce.collecter_sofascore(MAINTENANT, LIGUES, faux_reseau(evs, {}), pause=0)


class TestAutresSources(unittest.TestCase):
    def test_fpl_garde_les_joueurs_non_disponibles(self):
        boot = {"teams": [{"id": 1, "name": "Club Fictif"}],
                "elements": [{"id": 10, "web_name": "Apte", "team": 1, "status": "a", "news": ""},
                             {"id": 11, "web_name": "Blesse", "team": 1, "status": "i", "news": "Knee - Expected back 1 Nov",
                              "news_added": "2026-10-28T10:00:00Z", "chance_of_playing_next_round": 0},
                             {"id": 12, "web_name": "Suspendu", "team": 1, "status": "s", "news": "Suspended"}]}
        lignes = ce.lignes_fpl(boot, "t")
        self.assertEqual([(l["joueur"], l["statut"]) for l in lignes], [("Blesse", "blesse"), ("Suspendu", "suspendu")])

    def test_clubelo_division_niveau_1(self):
        texte = "Rank,Club,Country,Level,Elo,From,To\n1,Club A,ENG,1,2000,2026-10-28,2026-10-29\n" \
                "None,Club B,ENG,2,1500,2026-10-28,2026-10-29\n5,Club C,CRO,1,1600,2026-10-28,2026-10-29\n"
        self.assertEqual([r["division"] for r in ce.lignes_clubelo(texte)], ["E0", "", ""])

    def test_saison_courante(self):
        self.assertEqual(ce.saison_courante(MAINTENANT), "2026-27")
        self.assertEqual(ce.saison_courante(datetime(2027, 3, 1, tzinfo=timezone.utc).timestamp()), "2026-27")


class TestCollecte(unittest.TestCase):
    def test_bout_en_bout_dedoublonnage_et_isolation(self):
        evs = [evenement(1, 34, MAINTENANT + 3600)]
        lire = faux_reseau(evs, {1: COMPO}, fpl={"teams": [], "elements": []},
                           elo="Rank,Club,Country,Level,Elo,From,To\n1,Club A,FRA,1,1800,x,y\n")
        conf = {"sofascore": [{"id": 34, "division": "F1", "nom": "Ligue 1", "pays": "France"}], "understat": []}
        with tempfile.TemporaryDirectory() as d:
            dossier = Path(d)
            m1 = ce.collecter(dossier, ["sofascore", "clubelo", "inconnue"], MAINTENANT, lire, conf, pause=0)
            self.assertEqual(m1["sources"]["sofascore"]["statut"], "ok")
            self.assertEqual(m1["sources"]["inconnue"]["statut"], "erreur")
            fichier = dossier / m1["sources"]["sofascore"]["fichier"]
            lignes = list(csv.DictReader(fichier.read_text(encoding="utf-8").splitlines()))
            self.assertEqual(len(lignes), 4)
            self.assertTrue(all(l["collecte_le"] == "2026-10-29T12:00:00+00:00" for l in lignes))
            vus = list(csv.DictReader((dossier / "sofascore" / "tournois_vus.csv").read_text(encoding="utf-8").splitlines()))
            self.assertEqual(vus, [{"id": "34", "nom": "Ligue 1", "pays": "France", "suivi": "True"}])
            m2 = ce.collecter(dossier, ["sofascore"], MAINTENANT + 3600, lire, conf, pause=0)
            self.assertEqual(m2["sources"]["sofascore"]["fichier"], "inchange")
            self.assertEqual(len(list((dossier / "sofascore").rglob("*.csv"))), 2)


class TestConfiguration(unittest.TestCase):
    def test_ligues_ont_un_historique(self):
        conf = ce.charger_config()
        ids = [l["id"] for l in conf["sofascore"]]
        self.assertEqual(len(ids), len(set(ids)))
        divisions = {l["division"] for l in conf["sofascore"] if l["division"]}
        connues = {"E0", "E1", "E2", "E3", "EC", "SC0", "SC1", "SC2", "SC3", "D1", "D2", "I1", "I2", "SP1", "SP2",
                   "F1", "F2", "N1", "B1", "P1", "T1", "G1", "AUT", "SUI", "DEN", "SWE", "NOR", "FIN", "POL",
                   "ROM", "RUS", "IRL", "ARG", "BRA", "MEX", "USA", "JAP", "CHN"}
        self.assertEqual(divisions, connues)



class TestEspn(unittest.TestCase):
    def faux(self, appels, publie=True, complet=True):
        debut = datetime.fromtimestamp(MAINTENANT + 3600, tz=timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
        loin = datetime.fromtimestamp(MAINTENANT + 5 * 3600, tz=timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
        joueurs = [{"starter": True, "athlete": {"id": "8", "displayName": "Titulaire Fictif"}, "position": {"abbreviation": "F"}},
                   {"starter": False, "athlete": {"id": "9", "displayName": "Remplacant Fictif"}, "position": {"abbreviation": "D"}}]

        def lire(url):
            appels.append(url)
            if "/scoreboard" in url:
                return json.dumps({"events": [{"id": "1", "date": debut}, {"id": "2", "date": loin}]}).encode()
            if "/summary?event=1" in url:
                bloc = {"team": {"displayName": "Club Fictif"}, "formation": "4-3-3"}
                rosters = [{**bloc, "roster": joueurs} if publie else bloc]
                if publie and complet:
                    rosters = [{"team": {"displayName": team}, "roster": [
                        {"starter": True, "athlete": {"id": f"{team}-{i}", "displayName": f"Joueur {i}"}}
                        for i in range(11)]} for team in ("A", "B")]
                return json.dumps({"rosters": rosters}).encode()
            raise AssertionError(url)
        return lire

    def test_compo_une_fois_par_match(self):
        conf = {"espn": [{"slug": "fra.1", "division": "F1"}]}
        with tempfile.TemporaryDirectory() as d:
            dossier, appels = Path(d), []
            m = ce.collecter(dossier, ["espn"], MAINTENANT, self.faux(appels, publie=False), conf, pause=0)
            self.assertEqual((m["sources"]["espn"]["statut"], m["sources"]["espn"]["lignes"]), ("ok", 0))  # pas encore publiée
            m = ce.collecter(dossier, ["espn"], MAINTENANT + 600, self.faux(appels), conf, pause=0)
            r = m["sources"]["espn"]
            self.assertEqual((r["matchs_proches"], r["lignes"]), (1, 22))
            lignes = list(csv.DictReader((dossier / r["fichier"]).read_text(encoding="utf-8").splitlines()))
            self.assertTrue(ce.deux_onze_complets(lignes))
            self.assertTrue(all(l["source"] == "espn" for l in lignes))
            appels.clear()
            ce.collecter(dossier, ["espn"], MAINTENANT + 1200, self.faux(appels), conf, pause=0)
            self.assertFalse(any("summary" in u for u in appels))  # déjà faite

    def test_partielle_retentee_sans_compter_doublons(self):
        etat, appels = {}, []
        conf = {"espn": [{"slug": "fra.1", "division": "F1"}]}
        r = ce.collecter_espn(MAINTENANT, conf, etat, self.faux(appels, complet=False), pause=0)
        self.assertEqual(etat["espn"]["compos_faites"], [])
        self.assertFalse(ce.deux_onze_complets(r["compos"] * 22))
        appels.clear()
        r = ce.collecter_espn(MAINTENANT + 600, conf, etat, self.faux(appels), pause=0)
        self.assertTrue(any("summary" in u for u in appels))
        self.assertTrue(ce.deux_onze_complets(r["compos"]))
        self.assertEqual(etat["espn"]["compos_faites"], ["1"])

    def test_erreur_match_ne_perd_pas_compos_precedentes(self):
        original = self.faux([])
        def lire(url):
            if "scoreboard" in url:
                data = json.loads(original(url))
                data["events"][1]["date"] = data["events"][0]["date"]
                return json.dumps(data).encode()
            if "event=2" in url:
                raise TimeoutError("fixture hors réseau")
            return original(url)
        r = ce.collecter_espn(MAINTENANT, {"espn": [{"slug": "fra.1", "division": "F1"}]}, {}, lire, pause=0)
        self.assertEqual(len(r["compos"]), 22)
        self.assertEqual(len(r["erreurs_ligues"]), 1)

    def test_tous_calendriers_en_echec(self):
        def lire(url):
            raise RuntimeError("HTTP 404")
        with tempfile.TemporaryDirectory() as d:
            m = ce.collecter(Path(d), ["espn"], MAINTENANT, lire, {"espn": [{"slug": "xxx.9", "division": None}]}, pause=0)
            self.assertEqual(m["sources"]["espn"]["statut"], "erreur")


_spec2 = importlib.util.spec_from_file_location("lire_externe", ROOT / "scripts" / "lire_externe.py")
le = importlib.util.module_from_spec(_spec2)
_spec2.loader.exec_module(le)


class TestLecture(unittest.TestCase):
    def test_dernier_instantane_avant_le_coup_envoi(self):
        evs = [evenement(1, 34, MAINTENANT + 3 * 3600)]
        conf = {"sofascore": [{"id": 34, "division": "F1", "nom": "Ligue 1", "pays": "France"}], "understat": []}
        compo_tardive = {**COMPO, "home": {**COMPO["home"], "missingPlayers": []}}
        with tempfile.TemporaryDirectory() as d:
            dossier = Path(d)
            ce.collecter(dossier, ["sofascore"], MAINTENANT, faux_reseau(evs, {1: COMPO}), conf, pause=0)
            ce.collecter(dossier, ["sofascore"], MAINTENANT + 7200, faux_reseau(evs, {1: compo_tardive}), conf, pause=0)
            avant = datetime(2026, 10, 29, 13, tzinfo=timezone.utc)
            noms = {l["joueur"] for l in le.joueurs(dossier, "Domicile 1", avant)}
            self.assertIn("Blesse Fictif", noms)  # l'instantané de 14 h est postérieur : ignoré
            apres = datetime(2026, 10, 29, 15, tzinfo=timezone.utc)
            self.assertNotIn("Blesse Fictif", {l["joueur"] for l in le.joueurs(dossier, "Domicile 1", apres)})
            self.assertEqual(le.joueurs(dossier, "Domicile 1", datetime(2026, 10, 29, 11, tzinfo=timezone.utc)), [])
            self.assertEqual(le.statut(dossier)["instantanes"], {"sofascore": 2})



class TestApiFootball(unittest.TestCase):
    def faux(self, appels):
        debut = int(MAINTENANT + 3600)
        fixtures = {"response": [
            {"fixture": {"id": 1, "date": "2026-10-29T13:00:00+00:00", "timestamp": debut, "status": {"short": "NS"}},
             "league": {"id": 61, "name": "Ligue 1", "country": "France"}},
            {"fixture": {"id": 2, "date": "2026-10-29T13:00:00+00:00", "timestamp": debut, "status": {"short": "NS"}},
             "league": {"id": 999, "name": "Autre", "country": "X"}}]}
        blessures = {"response": [{"player": {"id": 7, "name": "Blesse Fictif", "type": "Missing Fixture", "reason": "Knee Injury"},
                                   "team": {"name": "Club Fictif"}, "fixture": {"id": 1, "date": "2026-10-29T13:00:00+00:00"},
                                   "league": {"id": 61, "name": "Ligue 1", "country": "France"}}]}
        compo = {"response": [{"team": {"name": "Club Fictif"}, "formation": "4-3-3",
                               "startXI": [{"player": {"id": 8, "name": "Titulaire Fictif", "pos": "F"}}],
                               "substitutes": [{"player": {"id": 9, "name": "Remplacant Fictif", "pos": "D"}}]}]}

        def lire(chemin):
            appels.append(chemin)
            if chemin == "/status":
                return {"response": {"subscription": {"plan": "Free"}, "requests": {"current": 1, "limit_day": 100}}}
            if chemin.startswith("/fixtures?date"):
                return fixtures
            if chemin.startswith("/injuries"):
                return blessures
            if chemin.startswith("/fixtures/lineups"):
                return compo
            raise AssertionError(chemin)
        return lire

    def test_premier_passage_puis_heure_suivante(self):
        conf = {"sofascore": [], "understat": [], "apifootball": [{"id": 61, "division": "F1", "nom": "Ligue 1"}]}
        with tempfile.TemporaryDirectory() as d:
            dossier, appels = Path(d), []
            m = ce.collecter(dossier, ["apifootball"], MAINTENANT, self.faux(appels), conf)
            r = m["sources"]["apifootball"]
            self.assertEqual(r["statut"], "ok")
            self.assertEqual((r["calendrier"], r["blessures"], r["compos"]), (1, 1, 2))  # même blessure renvoyée pour J et J+1 : une ligne
            self.assertEqual(appels[-1], "/fixtures/lineups?fixture=1")
            self.assertEqual(r["requetes_jour"], 6)
            appels.clear()
            m2 = ce.collecter(dossier, ["apifootball"], MAINTENANT + 3600, self.faux(appels), conf)
            self.assertEqual(appels, [])  # 13 h : calendrier connu, compo déjà faite, pas une heure de blessures
            self.assertEqual(m2["sources"]["apifootball"]["compos"], 0)

    def test_erreur_api_dans_champ_errors(self):
        class Rep:
            def __init__(self): self.b = json.dumps({"errors": {"plan": "Free plans do not have access to this season"}}).encode()
            def read(self): return self.b
            def __enter__(self): return self
            def __exit__(self, *a): return False
        import unittest.mock as um
        with um.patch.object(ce.urllib.request, "urlopen", return_value=Rep()) as uo:
            with self.assertRaisesRegex(RuntimeError, "Free plans"):
                ce.lecteur_apifootball("cle-fictive")("/status")
            req = uo.call_args[0][0]
            self.assertNotIn("cle-fictive", req.full_url)
            self.assertEqual(req.get_header("X-apisports-key"), "cle-fictive")

    def test_compo_partielle_retentee_dans_budget(self):
        with tempfile.TemporaryDirectory() as tmp:
            etat, appels = {}, []
            conf = {"apifootball": [{"id": 61}]}
            lire = self.faux(appels)
            ce.collecter_apifootball(Path(tmp), MAINTENANT, conf, etat, lire)
            self.assertEqual(etat["apifootball"]["compos_faites"], [])
            appels.clear()
            ce.collecter_apifootball(Path(tmp), MAINTENANT + 600, conf, etat, lire)
            self.assertIn("/fixtures/lineups?fixture=1", appels)
            etat["apifootball"]["requetes"] = ce.APIFOOTBALL_BUDGET_JOUR
            # Hors heure de blessures : aucun appel supplémentaire au plafond.
            appels.clear()
            ce.collecter_apifootball(Path(tmp), MAINTENANT + 3600, conf, etat, lire)
            self.assertEqual(appels, [])

    def test_sans_secret_la_source_est_ignoree(self):
        import os
        import unittest.mock as um
        with tempfile.TemporaryDirectory() as d, um.patch.dict(os.environ, {"API_FOOTBALL_KEY": ""}):
            m = ce.collecter(Path(d), ["apifootball"], MAINTENANT, config={"sofascore": [], "understat": []})
            self.assertEqual(m["sources"]["apifootball"]["statut"], "ignore")


if __name__ == "__main__":
    unittest.main()
