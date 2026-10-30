"""Préparation des entraînements : comptage et seuils, sans rien apprendre ni écrire."""
import csv
import tempfile
import unittest
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from scripts import preparer_entrainement as pe


class TestPreparation(unittest.TestCase):
    def test_etat_reel_non_admissible_et_rien_ecrit(self):
        with tempfile.TemporaryDirectory() as d:
            memoire = Path(d) / "memoire"
            etat = pe.preparer(date(2026, 10, 29), None, memoire)
            self.assertFalse(any(memoire.rglob("*.jsonl")))  # aucune écriture
        self.assertFalse(etat["entrainement_lance"])
        c = etat["candidats"]
        self.assertEqual(c["donnees_fraiches"]["statut"], "ADMISSIBLE")
        self.assertEqual(c["EXP-014_validation_calibrations_2026_27"]["statut"], "NON_ADMISSIBLE")
        self.assertIn("non fournie", c["EXP-013_ponderation_absences"]["raisons"][0])
        self.assertEqual(c["cohorte_prospective"]["statut"], "NON_ADMISSIBLE")

    def test_donnees_perimees_detectees(self):
        etat = pe.preparer(date(2026, 12, 31), None, Path(tempfile.mkdtemp()) / "m")
        self.assertEqual(etat["candidats"]["donnees_fraiches"]["statut"], "NON_ADMISSIBLE")

    def test_compo_collectee_apres_coup_envoi_ignoree(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "espn" / "compos" / "2026-10-29" / "1917.csv"
            f.parent.mkdir(parents=True)
            with f.open("w", newline="") as h:
                w = csv.writer(h)
                w.writerow(["collecte_le", "coup_envoi", "ligue", "equipe", "joueur", "statut", "event_id"])
                w.writerow(["2026-10-29T19:17:00Z", "2026-10-29T19:45:00+00:00", "ita.1", "A", "x", "titulaire", "1"])
                w.writerow(["2026-10-29T19:17:00Z", "2026-10-29T18:00:00+00:00", "ita.1", "B", "y", "titulaire", "2"])
            ext = pe.couverture_externe(Path(d), pe.datetime(2026, 10, 29, 23, 59, tzinfo=pe.timezone.utc))
        self.assertEqual(ext["matchs_compo_avant_coup_envoi"], 1)

    def test_matchs_simultanes_et_doublons_instantanes(self):
        with tempfile.TemporaryDirectory() as d:
            dossier = Path(d)
            for heure in ("1800", "1810"):
                f = dossier / "espn/compos/2026-10-29" / (heure + ".csv")
                f.parent.mkdir(parents=True, exist_ok=True)
                with f.open("w", newline="") as h:
                    w = csv.writer(h)
                    w.writerow(["collecte_le", "coup_envoi", "ligue", "event_id"])
                    for identifiant in ("1", "2", ""):
                        w.writerow(["2026-10-29T18:00:00Z", "2026-10-29T19:00:00Z", "ita.1", identifiant])
                    # La première ligne ne suffit pas à dater tout le fichier.
                    w.writerow(["2026-10-29T20:00:00Z", "2026-10-29T21:00:00Z", "ita.1", "futur"])
            ext = pe.couverture_externe(dossier, pe.datetime(2026, 10, 29, 19, tzinfo=pe.timezone.utc))
        self.assertEqual(ext["matchs_compo_avant_coup_envoi"], 2)
        self.assertEqual(ext["lignes_compos_sans_identifiant"], 2)

    def test_cohorte_identifiants_complets_et_plusieurs_marches(self):
        entries = []
        for match in ("simple", "I1:2026-10-29:Fiorentina:Atalanta", "I1:2026-10-30:Autre:Match"):
            for marche in ("1X2", "2+", "3+"):
                entries.append(SimpleNamespace(key=f"pred:{match}:{marche}:v1", value={"match_id": match}))
        for match in ("simple", "I1:2026-10-29:Fiorentina:Atalanta"):
            entries.append(SimpleNamespace(key=f"result:{match}", value={"match_id": match}))
        with patch.object(pe, "MemoryStore") as store:
            store.return_value.active.return_value = entries
            out = pe.cohorte_prospective(Path("non-utilise"))
        self.assertEqual(out, {"predictions": 9, "matchs_predits": 3, "matchs_avec_resultat": 2})


if __name__ == "__main__":
    unittest.main()
