import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import collecte_cotes as cc  # noqa: E402

MAINTENANT = datetime(2026, 10, 31, 11, 0, tzinfo=timezone.utc)


def evenement(eid, debut, etat="pre", ml=("-120", "+295", "+310")):
    return {"id": eid, "date": debut, "competitions": [{
        "status": {"type": {"state": etat}},
        "competitors": [{"homeAway": "home", "team": {"displayName": "Chelsea"}},
                        {"homeAway": "away", "team": {"displayName": "Manchester United"}}],
        "odds": [{"provider": {"name": "DraftKings"},
                  "moneyline": {"home": {"open": {"odds": "-105"}, "close": {"odds": ml[0]}},
                                "draw": {"open": {"odds": "+280"}, "close": {"odds": ml[1]}},
                                "away": {"open": {"odds": "+300"}, "close": {"odds": ml[2]}}}}]}]}


def lecteur(evs, fixtures=b"Div,Date,Time,HomeTeam,AwayTeam,B365H,B365D,B365A,PSH,PSD,PSA,B365>2.5,B365<2.5,AHh,B365AHH\n"
                             b"E0,31/10/2026,12:30,Chelsea,Man United,1.80,3.90,4.20,1.83,3.95,4.30,1.6,2.3,-0.5,1.9\n"
                             b"E0,27/10/2026,20:00,Arsenal,Spurs,1.5,4.2,6.0,1.5,4.3,6.2,1.4,2.9,-1,1.9\n"
                             b"N1,31/10/2026,13:00,Ajax,PSV,2.0,3.5,3.4,2.1,3.5,3.3,1.5,2.4,0,1.9\n"):
    def lire(url):
        if "football-data" in url:
            return fixtures
        return json.dumps({"events": evs if "eng.1" in url and "20261031" in url else []}).encode()
    return lire


class CotesTests(unittest.TestCase):
    def test_conversion_americaine(self):
        self.assertEqual(cc.americaine("-120"), 1.8333)
        self.assertEqual(cc.americaine("+295"), 3.95)
        self.assertEqual(cc.americaine(295), 3.95)
        self.assertIsNone(cc.americaine(None))
        self.assertIsNone(cc.americaine("EVEN"))

    def test_horizons(self):
        self.assertEqual(cc.horizon(60), "T-60")
        self.assertEqual(cc.horizon(30), "T-30")
        self.assertEqual(cc.horizon(4), "T-5")
        self.assertEqual(cc.horizon(120), "hors_fenetre")
        self.assertEqual(cc.horizon(-3), "hors_fenetre")  # commencé : jamais une cote d'avant-match

    def test_collecte_garde_la_premiere_capture_par_horizon_et_ignore_les_matchs_commences(self):
        evs = [evenement("1", "2026-10-31T12:00Z"), evenement("2", "2026-10-31T10:30Z", etat="in"),
               evenement("3", "2026-10-31T19:00Z")]
        with tempfile.TemporaryDirectory() as d:
            j = cc.collecter(Path(d), MAINTENANT, lire=lecteur(evs))
            self.assertEqual(j["espn_par_horizon"]["T-60"], 1)
            self.assertEqual(j["espn_par_horizon"]["hors_fenetre"], 1)  # match de 19:00 : instantané horaire
            self.assertEqual(j["erreurs"], [])
            j2 = cc.collecter(Path(d), MAINTENANT.replace(minute=10), lire=lecteur(evs))  # 50 min : déjà saisi
            self.assertEqual(j2["espn_par_horizon"]["T-60"], 0)
            self.assertEqual(j2["espn_par_horizon"]["hors_fenetre"], 0)  # moins de 55 min après le précédent
            self.assertEqual(j2["football_data"], "inchange")
            lignes = (Path(d) / "cotes" / "espn" / "2026-10-31" / "1100.csv").read_text().splitlines()
            self.assertIn("1.8333,3.95,4.1", lignes[1])
            self.assertTrue(all(",2," not in l.split("DraftKings")[1][:40] for l in lignes[1:]))  # événement 2 absent
            fd = (Path(d) / "cotes" / "football-data" / "2026-10-31" / "1100.csv").read_text().splitlines()
            self.assertEqual(len(fd), 3)  # E0 à venir seulement (pas le 27/10), B365 et PS ; ni plus/moins ni handicap
            self.assertEqual(len((Path(d) / "cotes" / "journal.jsonl").read_text().splitlines()), 2)

    def test_erreur_source_journalisee_sans_arret(self):
        def lire(url):
            raise TimeoutError("lent")
        with tempfile.TemporaryDirectory() as d:
            j = cc.collecter(Path(d), MAINTENANT, lire=lire)
            self.assertEqual(len(j["erreurs"]), 11)
            self.assertEqual(j["espn"], 0)


if __name__ == "__main__":
    unittest.main()
