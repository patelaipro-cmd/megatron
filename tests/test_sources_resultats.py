"""Collecte brute des résultats : hors réseau, lecteur fictif."""
import json
import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path

from scripts import collecte_resultats_espn, sources_resultats as sr


def lecteur(appels):
    def lire(url, headers=None):
        appels.append((url, headers or {}))
        if "espn" in url:
            if "eng.1" in url and url.endswith("20261025"):
                raise OSError("panne")
            return json.dumps({"events": [{"id": "9", "date": "2026-10-24T14:00Z", "extra": "x" * 50,
                                           "status": {"type": {"completed": True, "name": "STATUS_FULL_TIME"}},
                                           "competitions": [{"competitors": [
                                               {"homeAway": "home", "score": "2", "team": {"displayName": "A", "logo": "l"}},
                                               {"homeAway": "away", "score": "1", "team": {"displayName": "B"}}]}]}]}).encode()
        if "api-sports" in url:
            return json.dumps({"errors": [], "response": [{"fixture": {"id": 1, "date": "2026-10-24T14:00:00+00:00",
                                                                       "status": {"short": "FT"}},
                                                           "teams": {"home": {"name": "A"}, "away": {"name": "B"}},
                                                           "goals": {"home": 2, "away": 1}, "score": {"fulltime": {"home": 2, "away": 1}},
                                                           "league": {"round": "R 9"}}]}).encode()
        return b"Div,Date,HomeTeam\n"
    return lire


class TestSourcesResultats(unittest.TestCase):
    def test_trois_familles_et_panne_notee(self):
        appels = []
        with tempfile.TemporaryDirectory() as d:
            m = sr.collecter(Path(d), date(2026, 10, 24), date(2026, 10, 25), ["espn", "apifootball", "footballdata"],
                             cle="secret", pause=0, lire=lecteur(appels))
            pages = json.loads((Path(d) / "espn_scoreboards.json").read_text())
            fx = json.loads((Path(d) / "apifootball_fixtures.json").read_text())
            self.assertTrue((Path(d) / "footballdata_E0.csv").exists())
            texte = "".join(f.read_text() for f in Path(d).iterdir())
        self.assertEqual(m["sources"]["espn"]["pages"], 9)
        self.assertEqual(len(m["sources"]["espn"]["erreurs"]), 1)
        self.assertNotIn("extra", json.dumps(pages))  # réduit aux champs utiles
        self.assertEqual(fx["E0"][0]["buts_domicile"], 2)
        self.assertNotIn("secret", texte)  # la clé ne passe qu'en en-tête
        self.assertTrue(all("secret" not in u for u, _ in appels))
        ev = next(iter(pages.values()))["events"][0]
        self.assertEqual(collecte_resultats_espn.decode_event(ev, "eng.1", datetime(2026, 10, 29, tzinfo=timezone.utc))["hg"], 2)

    def test_sans_cle_api_football_ignoree(self):
        with tempfile.TemporaryDirectory() as d:
            m = sr.collecter(Path(d), date(2026, 10, 24), date(2026, 10, 24), ["apifootball"], cle="", pause=0, lire=lecteur([]))
        self.assertEqual(m["sources"]["apifootball"]["statut"], "ignore")

    def test_meme_adresse_que_le_collecteur_espn(self):
        self.assertEqual(sr.ESPN, collecte_resultats_espn.ENDPOINT)
        self.assertEqual({d: s for d, (s, _) in sr.LIGUES.items()}, collecte_resultats_espn.LEAGUES)


if __name__ == "__main__":
    unittest.main()
