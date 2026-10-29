"""Recoupement des résultats : noms reliés par matchs communs, admission à deux familles, quarantaine."""
import csv
import json
import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path

from scripts import verifier_resultats as vr

NOW = datetime(2026, 10, 29, 20, tzinfo=timezone.utc)
# référence (noms de data/) : deux journées communes pour relier les noms
REF = [("2026-09-13", "Man United", "Arsenal", 1, 0), ("2026-09-13", "Chelsea", "Spurs", 2, 2),
       ("2026-09-20", "Arsenal", "Chelsea", 3, 1), ("2026-09-20", "Spurs", "Man United", 0, 2)]
NOMS = {"espn": {"Man United": "Manchester United", "Spurs": "Tottenham Hotspur"},
        "apifootball": {"Man United": "Manchester United", "Spurs": "Tottenham"},
        "footballdata": {}}


def ev(eid, jour, h, a, hg, ag, fini=True):
    return {"id": str(eid), "date": f"{jour}T14:00Z",
            "status": {"type": {"completed": fini, "name": "STATUS_FULL_TIME" if fini else "STATUS_SCHEDULED"}},
            "competitions": [{"competitors": [{"homeAway": "home", "score": str(hg), "team": {"displayName": h}},
                                              {"homeAway": "away", "score": str(ag), "team": {"displayName": a}}]}]}


class TestVerifier(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        d = Path(self.tmp.name)
        self.base = d / "base.csv"
        with self.base.open("w", newline="") as f:
            w = csv.writer(f)
            w.writerow(vr.COLUMNS)
            for j, h, a, hg, ag in REF:
                w.writerow(["E0", j, "15:00:00", h, a, hg, ag, "H" if hg > ag else "A" if ag > hg else "D"] + [""] * 7)
        self.brut = d / "brut"
        self.brut.mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def ecrire(self, nouveaux, espn_ok=True, api=True, fd=True):
        n = lambda fam, x: NOMS[fam].get(x, x)
        tous = [(j, h, a, hg, ag) for j, h, a, hg, ag in REF] + nouveaux
        pages = {}
        for i, (j, h, a, hg, ag) in enumerate(tous):
            if not espn_ok and j > "2026-09-20":
                continue
            url = vr.espn.ENDPOINT.format(slug="eng.1", jour=j.replace("-", ""))
            pages.setdefault(url, {"events": []})["events"].append(ev(i, j, n("espn", h), n("espn", a), hg, ag))
        (self.brut / "espn_scoreboards.json").write_text(json.dumps(pages))
        if api:
            fx = [{"fixture_id": 100 + i, "date": f"{j}T14:00:00+00:00", "statut": "FT", "domicile": n("apifootball", h),
                   "exterieur": n("apifootball", a), "buts_domicile": hg, "buts_exterieur": ag}
                  for i, (j, h, a, hg, ag) in enumerate(tous)]
            (self.brut / "apifootball_fixtures.json").write_text(json.dumps({"E0": fx}))
        if fd:
            with (self.brut / "footballdata_E0.csv").open("w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["Div", "Date", "Time", "HomeTeam", "AwayTeam", "FTHG", "FTAG", "HS", "AS", "HST", "AST", "B365H", "B365D", "B365A"])
                for j, h, a, hg, ag in tous:
                    y, m, dd = j.split("-")
                    w.writerow(["E0", f"{dd}/{m}/{y}", "15:00", h, a, hg, ag, 10, 8, 4, 3, 2.1, 3.4, 3.5])

    def verifier(self):
        return vr.verifier(self.brut, date(2026, 9, 21), date(2026, 10, 28), base=[self.base], maintenant=NOW)

    def test_admis_si_deux_familles_concordent_noms_relies_par_matchs_communs(self):
        self.ecrire([("2026-10-04", "Arsenal", "Spurs", 2, 0)])
        r = self.verifier()
        self.assertEqual(len(r["admis"]), 1)
        a = r["admis"][0]
        self.assertEqual((a["HomeTeam"], a["AwayTeam"], a["FTHome"], a["FTAway"], a["FTResult"]), ("Arsenal", "Spurs", 2, 0, "H"))
        self.assertEqual(a["familles"], "espn+apifootball+footballdata")
        self.assertEqual((a["OddHome"], a["HomeTarget"]), ("2.1", "4"))  # cotes et tirs de football-data
        self.assertEqual(r["noms"]["espn:E0"]["Tottenham Hotspur"], "Spurs")
        self.assertEqual(r["compteurs"]["deja_connus"], 12)  # 4 matchs connus × 3 familles, aucun doublon admis

    def test_desaccord_de_score_en_quarantaine(self):
        self.ecrire([("2026-10-04", "Arsenal", "Spurs", 2, 0)])
        fx = json.loads((self.brut / "apifootball_fixtures.json").read_text())
        fx["E0"][-1]["buts_domicile"] = 3
        (self.brut / "apifootball_fixtures.json").write_text(json.dumps(fx))
        r = self.verifier()
        self.assertEqual(r["admis"], [])
        self.assertIn("DESACCORD_SCORE", r["quarantaine"][0]["raison"])

    def test_source_unique_en_quarantaine(self):
        self.ecrire([("2026-10-04", "Arsenal", "Spurs", 2, 0)], api=False, fd=False)
        r = self.verifier()
        self.assertEqual(r["admis"], [])
        self.assertIn("SOURCE_UNIQUE", r["quarantaine"][0]["raison"])

    def test_sans_espn_deux_autres_familles_suffisent(self):
        self.ecrire([("2026-10-04", "Arsenal", "Spurs", 2, 0)], espn_ok=False)
        r = self.verifier()
        self.assertEqual(r["admis"][0]["familles"], "apifootball+footballdata")

    def test_date_trop_eloignee_en_quarantaine(self):
        self.ecrire([("2026-10-04", "Arsenal", "Spurs", 2, 0)])
        fx = json.loads((self.brut / "apifootball_fixtures.json").read_text())
        fx["E0"][-1]["date"] = "2026-10-08T14:00:00+00:00"
        (self.brut / "apifootball_fixtures.json").write_text(json.dumps(fx))
        self.assertIn("DESACCORD_DATE", self.verifier()["quarantaine"][0]["raison"])

    def test_conflit_avec_historique_rejete_et_match_non_termine_ignore(self):
        self.ecrire([("2026-10-04", "Arsenal", "Spurs", 2, 0)])
        fx = json.loads((self.brut / "apifootball_fixtures.json").read_text())
        fx["E0"][0]["buts_domicile"] = 5  # Man United - Arsenal connu 1-0 : la source contredit l'historique
        fx["E0"].append({"fixture_id": 999, "date": "2026-10-25T14:00:00+00:00", "statut": "NS", "domicile": "Chelsea",
                         "exterieur": "Manchester United", "buts_domicile": None, "buts_exterieur": None})
        (self.brut / "apifootball_fixtures.json").write_text(json.dumps(fx))
        r = self.verifier()
        self.assertEqual(len(r["admis"]), 1)
        self.assertEqual([x["raison"][:18] for x in r["rejets"]], ["CONFLIT_HISTORIQUE"])
        self.assertFalse(any(q["HomeTeam"] == "Chelsea" for q in r["quarantaine"]))

    def test_nom_inconnu_rejete_sans_approximation(self):
        self.ecrire([("2026-10-04", "Arsenal", "Spurs", 2, 0), ("2026-10-11", "Arsenal", "Burnley", 1, 1)])
        r = self.verifier()
        self.assertEqual(len(r["admis"]), 1)
        self.assertTrue(any("NOM_NON_RELIE" in x["raison"] for x in r["rejets"]))


if __name__ == "__main__":
    unittest.main()
