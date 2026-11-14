"""EXP-022 : chronologie, provenance, XI complets, comparateur de rotations."""

import csv
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from megatron import compositions_prematch as cp
from scripts.exp022_compositions import convertir_compos, convertir_sofascore, importer_externes, importer_sofascore, main


def fictif(match_id, coup, collecte, *, source="sportsgambler", statut="probable", changes=0,
           equipe="Club Alpha", autre="Club Beta"):
    base = [f"A{i}" for i in range(11)]
    actuel = base[:11-changes] + [f"N{i}" for i in range(changes)]
    sources = {"sportsgambler": "https://www.sportsgambler.com/lineups/football/",
               "pianetafanta": "https://www.pianetafanta.it/probabili-formazioni-fantacalcio",
               "sofascore": "https://api.sofascore.com/api/v1/event/123/lineups",
               "officiel": "https://www.club-alpha.fr/actualites/composition"}
    return {"match_id": match_id, "domicile": equipe, "exterieur": autre, "competition": "Fictive",
            "coup_envoi": coup, "collecte_le": collecte, "publie_le": None,
            "source": source, "source_url": sources[source], "statut": statut,
            "organisme": "Club Alpha" if source == "officiel" else "",
            "equipes": {"H": {"titulaires": actuel, "banc": [], "absents": []},
                        "A": {"titulaires": [f"B{i}" for i in range(11)], "banc": [], "absents": []}}}


class TestSnapshots(unittest.TestCase):
    def setUp(self):
        self.ko = "2099-02-20T15:00:00Z"
        self.cap = "2099-02-20T13:00:00Z"
        self.fiche = fictif("x:14", self.ko, self.cap)

    def test_prevision_distincte_de_confirmation(self):
        r = cp.valider(self.fiche, au="2099-02-20T14:00:00Z")
        self.assertEqual(r["statut"], "probable")
        self.assertTrue(r["equipes"]["H"]["xi_complet"])
        self.assertFalse(r["ajustement_probabilites"])
        with self.assertRaises(ValueError):
            cp.valider({**self.fiche, "statut": "confirmee_officielle"})
        off = fictif("x:14", self.ko, self.cap, source="officiel", statut="confirmee_officielle")
        self.assertEqual(cp.valider(off)["statut"], "confirmee_officielle")

    def test_dates_fuite_et_identite_source(self):
        for changement in ({"collecte_le": self.ko}, {"collecte_le": "2099-02-20T16:00:00Z"},
                           {"collecte_le": "2099-02-20T13:00:00"},
                           {"publie_le": "2099-02-20T14:00:00Z"},
                           {"source_url": "https://sportsgambler.com.evil.example/lineups"},
                           {"source_url": "http://sportsgambler.com"}):
            with self.subTest(changement=changement), self.assertRaises(ValueError):
                cp.valider({**self.fiche, **changement})
        with self.assertRaises(ValueError):
            cp.valider(self.fiche, au="2099-02-20T12:00:00Z")

    def test_incomplet_et_doublons(self):
        m = json.loads(json.dumps(self.fiche))
        m["equipes"]["H"]["titulaires"] = ["A1", "A1"]
        with self.assertRaises(ValueError):
            cp.valider(m)
        m["equipes"]["H"]["titulaires"] = ["A1"]
        self.assertFalse(cp.valider(m)["equipes"]["H"]["xi_complet"])
        m["statut"] = "confirmee_fournisseur"
        with self.assertRaises(ValueError):
            cp.valider(m)

    def test_archive_et_rotation_anti_fuite(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "archive.jsonl"
            for i in range(3):
                f = fictif(f"h:{i}", f"2099-02-{10+i:02d}T15:00:00Z", f"2099-02-{10+i:02d}T14:00:00Z",
                           source="sofascore", statut="confirmee_fournisseur")
                self.assertEqual(cp.ajouter(path, f)["statut"], "ajoute")
            self.assertEqual(cp.ajouter(path, f)["statut"], "doublon")
            avec_conflit = {**f, "exterieur": "Club Gamma"}
            with self.assertRaises(ValueError):
                cp.ajouter(path, avec_conflit)
            # L'ancien onze ne doit pas être doublé par une deuxième source du même match.
            same = fictif("h:2", "2099-02-12T15:00:00Z", "2099-02-12T14:02:00Z",
                          source="officiel", statut="confirmee_officielle")
            cp.ajouter(path, same)
            cur = fictif("x:14", self.ko, self.cap, changes=4)
            cp.ajouter(path, cur)
            # Une composition du match courant capturée après l'heure d'analyse est hors jeu.
            newer = fictif("x:14", self.ko, "2099-02-20T14:30:00Z", source="officiel", statut="confirmee_officielle")
            cp.ajouter(path, newer)
            r = cp.analyser(cp.charger(path), "x:14", "2099-02-20T13:30:00Z")
            self.assertEqual(r["statut_composition"], "probable")
            self.assertEqual(r["equipes"]["H"]["historiques_confirmes"], 3)
            self.assertEqual(r["equipes"]["H"]["changements_vs_dernier_xi"], 4)
            self.assertEqual(len(r["equipes"]["H"]["habituels_non_titulaires"]), 4)
            self.assertTrue(r["equipes"]["H"]["signal_changements_massifs"])
            self.assertIn("INCONNU", r["equipes"]["H"]["motif_non_selection"])
            self.assertFalse(r["ajustement_probabilites"])
            later = cp.analyser(cp.charger(path), "x:14", "2099-02-20T14:35:00Z")
            self.assertEqual(later["statut_composition"], "confirmee_officielle")


def lignes_csv(event="321", date="2099-01-04T15:00:00Z", collecte="2099-01-04T13:00:00Z", incomplet=False):
    result = []
    for cote, equipe in (("H", "Fiction A"), ("A", "Fiction B")):
        for i in range(10 if incomplet and cote == "H" else 11):
            result.append({"event_id": event, "division": "F1", "coup_envoi": date,
                           "domicile": "Fiction A", "exterieur": "Fiction B", "collecte_le": collecte,
                           "cote": cote, "equipe": equipe, "joueur": f"{cote}{i}", "joueur_id": str(i+100 if cote == "H" else i+200),
                           "poste": "M", "statut": "titulaire", "motif": "", "compo_confirmee": "True"})
    return result


class TestImportSofascore(unittest.TestCase):
    def test_ordre_equipes_et_completude(self):
        obj = convertir_sofascore(lignes_csv(), canal="sofascore")
        self.assertEqual(obj["match_id"], "sofa:321")
        self.assertEqual(cp.valider(obj)["equipes"]["A"]["titulaires"][0]["nom"], "A0")
        self.assertIsNone(convertir_sofascore(lignes_csv(incomplet=True), canal="sofascore"))
        with self.assertRaises(ValueError):
            convertir_sofascore(lignes_csv() + lignes_csv(event="322"), canal="sofascore")

    def test_import_en_bout_et_audit_tardifs(self):
        with tempfile.TemporaryDirectory() as d:
            dossier, archive = Path(d) / "externe", Path(d) / "out.jsonl"
            source = dossier / "sofascore" / "2099-01-04"
            source.mkdir(parents=True)
            rows = lignes_csv() + lignes_csv(event="322", collecte="2099-01-04T16:00:00Z")
            with (source / "1300.csv").open("w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=rows[0].keys())
                w.writeheader()
                w.writerows(rows)
            sortie = importer_sofascore(dossier, archive, au="2099-01-04T14:00:00Z")["import"]
            self.assertEqual((sortie["ajoutes"], sortie["tardifs"], sortie["erreurs"]), (1, 1, 0))
            self.assertEqual(len(cp.charger(archive)), 1)
            self.assertEqual(importer_sofascore(dossier, archive, au="2099-01-04T14:00:00Z")["import"]["doublons"], 1)
            sortie_cli = io.StringIO()
            with redirect_stdout(sortie_cli):
                self.assertEqual(main(["analyser", "--archive", str(archive), "--match-id", "non", "--au", "2099-01-04T14:00:00Z"]), 0)
            self.assertEqual(json.loads(sortie_cli.getvalue())["statut"], "ABSENT")

    def test_espn_af_exigent_domicile_exterieur_et_onze(self):
        rows = []
        for nom in ("Fiction A", "Fiction B"):
            for i in range(11):
                rows.append({"event_id": "504", "fixture_id": "504", "ligue": "fra.1",
                             "coup_envoi": "2099-01-04T15:00:00Z", "collecte_le": "2099-01-04T14:00:00Z",
                             "domicile": "Fiction A", "exterieur": "Fiction B", "equipe": nom,
                             "joueur": f"{nom}-{i}", "joueur_id": f"{nom}-{i}",
                             "poste": "M", "statut": "titulaire"})
        self.assertEqual(convertir_compos(rows, canal="espn/compos")["source"], "espn")
        self.assertEqual(convertir_compos(rows, canal="apifootball/compos")["source"], "api-football")
        sans = [{k: v for k, v in r.items() if k not in ("domicile", "exterieur")} for r in rows]
        self.assertIsNone(convertir_compos(sans, canal="espn/compos"))
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            fichier = base / "espn" / "compos" / "2099-01-04" / "1400.csv"
            fichier.parent.mkdir(parents=True)
            with fichier.open("w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=rows[0])
                w.writeheader()
                w.writerows(rows)
            r = importer_externes(base, base / "captures.jsonl", au="2099-01-04T14:05:00Z")
            self.assertEqual(r["import"]["ajoutes"], 1)


if __name__ == "__main__":
    unittest.main()
