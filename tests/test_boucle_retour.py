import csv
import tempfile
import unittest
from datetime import date
from pathlib import Path

from megatron.ledger import DOMAIN
from megatron.store import MemoryStore
from scripts import boucle_retour as br

MID = "E0:2026-11-07:Leeds-Tottenham"
MID2 = "E0:2026-11-08:Arsenal-Hull"


def pred(store, mid, version, probs):
    store.record(DOMAIN, f"pred:{mid}:{version}", {"match_id": mid, "model_version": version, "market": "1X2",
                                                   "probs": probs, "kickoff": "2026-11-07T12:30:00+00:00"},
                 source="test", status="verifie")


def syndicate(store, mid, moment, decision, favori, p):
    store.record("football", f"syndicate:{mid}:{moment}", {"match_id": mid, "moment": moment, "resume": {
        "decision": decision, "niveaux": {"favori": favori, "probabilites": {"victoire_simple": p, "victoire_par_2_ou_plus": 0.3}}}},
        source="test", status="verifie")


class BoucleRetourTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.store = MemoryStore(self.tmp / "memoire")
        pred(self.store, MID, "poisson-v5-cal", {"H": 0.5, "D": 0.3, "A": 0.2})
        pred(self.store, MID2, "poisson-v5-cal", {"H": 0.7, "D": 0.2, "A": 0.1})
        syndicate(self.store, MID, "initial", "WATCH", "H", 0.55)
        syndicate(self.store, MID, "T-5", "PASS", "H", 0.48)
        syndicate(self.store, MID2, "initial", "WATCH", "H", 0.7)
        pred(self.store, "E0:2026-11-01:Leeds-Hull", "poisson-v5-cal", {"H": 0.5, "D": 0.3, "A": 0.2})  # hors fenêtre
        self.admis = self.tmp / "admis.csv"
        with self.admis.open("w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["Division", "MatchDate", "HomeTeam", "AwayTeam", "FTHome", "FTAway", "OddHome", "OddDraw", "OddAway"])
            w.writerow(["E0", "2026-11-07", "Leeds", "Tottenham", "1", "0", "2.0", "3.5", "4.0"])
        self.quarantaine = self.tmp / "q.csv"
        with self.quarantaine.open("w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["Division", "HomeTeam", "AwayTeam", "score_espn", "date_espn", "raison"])
            w.writerow(["E0", "Leeds", "Tottenham", "2-2", "2026-11-07", "SOURCE_UNIQUE : espn"])  # l'officiel prime
            w.writerow(["E0", "Arsenal", "Hull", "0-1", "2026-11-08", "SOURCE_UNIQUE : espn"])

    def bilan(self, provisoire=True):
        fiches = br.cohorte(self.store, date(2026, 11, 6), date(2026, 11, 8))
        return br.bilan(fiches, br.lire_resultats(self.admis, self.quarantaine if provisoire else None))

    def test_officiel_prime_et_provisoire_marque(self):
        b = self.bilan()
        self.assertEqual((b["n_predits"], b["n_officiels"], b["n_provisoires"]), (2, 1, 1))
        lignes = {ln["match_id"]: ln for ln in b["lignes"]}
        self.assertEqual(lignes[MID]["score"], "1-0")
        self.assertEqual(lignes[MID2]["statut"], "provisoire")

    def test_sans_provisoire_le_match_reste_sans_resultat(self):
        b = self.bilan(provisoire=False)
        self.assertEqual(b["sans_resultat"], [MID2])

    def test_scores_et_syndicate_dernier_moment(self):
        b = self.bilan()
        v5 = b["modeles"]["poisson-v5-cal"]
        self.assertEqual(v5["n"], 2)
        self.assertEqual(v5["reussite_choix"], 0.5)
        self.assertEqual(b["modeles"]["bookmaker-b365"]["n"], 1)
        self.assertEqual(b["syndicate"]["syndicate_final"]["PASS"]["favori_gagne"], 1)
        self.assertEqual(b["syndicate"]["syndicate_final"]["WATCH"]["favori_gagne"], 0)
        self.assertEqual(b["syndicate"]["syndicate_initial"]["WATCH"]["n"], 2)
        self.assertEqual(b["plus_grosses_surprises"][0]["match_id"], MID2)
        self.assertTrue(any("aucun poids modifié" in x for x in b["lecons"]))

    def test_cotes_dk_derniere_capture_avant_coup_envoi(self):
        d = self.tmp / "cotes" / "espn" / "2026-11-07"
        d.mkdir(parents=True)
        tete = ["collecte_le", "type_ligne", "division", "coup_envoi", "domicile", "exterieur", "cote_H", "cote_D", "cote_A", "marche"]
        with (d / "0000.csv").open("w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(tete)
            w.writerow(["2026-11-07T10:00:00+00:00", "courante", "E0", "2026-11-07T12:30+00:00", "Leeds United", "Tottenham Hotspur", "3", "3", "3", "1X2"])
            w.writerow(["2026-11-07T12:25:00+00:00", "courante", "E0", "2026-11-07T12:30+00:00", "Leeds United", "Tottenham Hotspur", "2", "4", "4", "1X2"])
            w.writerow(["2026-11-07T12:40:00+00:00", "courante", "E0", "2026-11-07T12:30+00:00", "Leeds United", "Tottenham Hotspur", "1.1", "9", "9", "1X2"])
        noms = {"espn:E0": {"Leeds United": "Leeds", "Tottenham Hotspur": "Tottenham"}}
        dk = br.lire_cotes_dk(self.tmp / "cotes", date(2026, 11, 6), date(2026, 11, 8), noms)
        self.assertAlmostEqual(dk[("E0", "Leeds", "Tottenham")]["H"], 0.5)


if __name__ == "__main__":
    unittest.main()
