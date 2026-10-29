"""Préparation des entraînements : comptage et seuils, sans rien apprendre ni écrire."""
import csv
import tempfile
import unittest
from datetime import date
from pathlib import Path

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
                w.writerow(["collecte_le", "coup_envoi", "ligue", "equipe", "joueur", "statut"])
                w.writerow(["2026-10-29T19:17:00Z", "2026-10-29T19:45:00+00:00", "ita.1", "A", "x", "titulaire"])
                w.writerow(["2026-10-29T19:17:00Z", "2026-10-29T18:00:00+00:00", "ita.1", "B", "y", "titulaire"])
            ext = pe.couverture_externe(Path(d), pe.datetime(2026, 10, 29, 23, 59, tzinfo=pe.timezone.utc))
        self.assertEqual(ext["matchs_compo_avant_coup_envoi"], 1)


if __name__ == "__main__":
    unittest.main()
