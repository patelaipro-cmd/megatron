"""Contrat de remplacement API-Football par cinq sources Web, sans réseau."""

import importlib.util
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from megatron.sources_prematch import SITES, importer_source, valider_fiche

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("exp022", ROOT / "scripts" / "exp022_compositions.py")
exp022 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(exp022)

KO = "2026-11-14T20:45:00+01:00"
AVANT = "2026-11-14T18:00:00+01:00"
AU = "2026-11-14T18:10:00+01:00"


def base(source="sportsmole", genre="analyse", url="https://www.sportsmole.co.uk/football/preview/foo.html"):
    return {"source": source, "type": genre, "source_url": url, "match_id": "test:100",
            "domicile": "Alpha", "exterieur": "Beta", "competition": "Ligue Test",
            "coup_envoi": KO, "collecte_le": AVANT, "publie_le": None,
            "donnees": {"enjeu": "Première place du groupe"}}


class SourcesPrematch(unittest.TestCase):
    def test_les_cinq_sites_definis(self):
        self.assertEqual(set(SITES), {"sportsmole", "sportsgambler", "pianetafanta", "180score", "xpertstats"})

    def test_analyse_datee_et_sans_modification_modele(self):
        fiche = valider_fiche(base(), au=AU)
        self.assertEqual(fiche["donnees"]["enjeu"], "Première place du groupe")
        self.assertFalse(fiche["ajustement_probabilites"])

    def test_refus_domaine_usurpe_date_fuite_et_publication_future(self):
        for mutation in ({"source_url": "https://sportsmole.co.uk.evil.test/preview"},
                         {"collecte_le": KO},
                         {"collecte_le": "2026-11-14T19:00:00+01:00"},
                         {"publie_le": "2026-11-14T19:00:00+01:00"}):
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                valider_fiche({**base(), **mutation}, au=AU)

    def test_classement_historique_h2h_anti_fuite(self):
        fiche = base("xpertstats", "h2h", "https://xpertstats.com/faq")
        fiche["donnees"] = {"rencontres": [
            {"date": "2026-10-02T18:00:00+01:00", "domicile": "Beta", "exterieur": "Alpha",
             "buts_domicile": 1, "buts_exterieur": 1,
             "classement_avant": {"au": "2026-10-01T12:00:00+01:00",
                                    "rang_domicile": 3, "rang_exterieur": 1,
                                    "source_url": "https://xpertstats.com/faq"}}]}
        self.assertEqual(valider_fiche(fiche, au=AU)["donnees"]["rencontres"][0]["classement_avant"]["rang_domicile"], 3)
        fiche["donnees"]["rencontres"][0]["classement_avant"]["au"] = "2026-10-03T12:00:00+01:00"
        with self.assertRaisesRegex(ValueError, "après le H2H"):
            valider_fiche(fiche, au=AU)

    def test_classement_actuel_ne_devient_pas_classement_historique(self):
        fiche = base("180score", "classement", "https://180score.com/football/match/test/")
        fiche["donnees"] = {"classement_au": AVANT, "rang_domicile": 1,
                            "rang_exterieur": 4, "portee": "classement général de Ligue Test"}
        self.assertEqual(valider_fiche(fiche, au=AU)["donnees"]["rang_exterieur"], 4)
        fiche["donnees"]["classement_au"] = KO
        with self.assertRaises(ValueError):
            valider_fiche(fiche, au=AU)

    def test_prediction_un_x_deux_ne_signifie_pas_v_plus_deux(self):
        fiche = base("180score", "prediction", "https://180score.com/football/match/test/")
        fiche["donnees"] = {"marche": "1X2", "probabilites": {"H": .65, "D": .22, "A": .13}}
        r = valider_fiche(fiche, au=AU)
        self.assertEqual(r["donnees"]["statut"], "PREDICTION_FOURNISSEUR_NON_CALIBREE")
        fiche["donnees"]["marche"] = "MARGE_2PLUS"
        with self.assertRaises(ValueError):
            valider_fiche(fiche, au=AU)

    def test_xi_probable_pas_officiel_et_pas_xi_xpertstats(self):
        joueurs = [f"Joueur {j}" for j in range(11)]
        fiche = base("pianetafanta", "xi", "https://www.pianetafanta.it/probabili-formazioni-fantacalcio")
        fiche["donnees"] = {"statut": "probable", "equipes": {
            "H": {"titulaires": joueurs}, "A": {"titulaires": joueurs}}}
        self.assertEqual(valider_fiche(fiche, au=AU)["donnees"]["statut"], "probable")
        fiche["donnees"]["statut"] = "confirmee_fournisseur"
        with self.assertRaises(ValueError):
            valider_fiche(fiche, au=AU)
        fiche["source"] = "xpertstats"
        fiche["source_url"] = "https://xpertstats.com/faq"
        with self.assertRaises(ValueError):
            valider_fiche(fiche, au=AU)

    def test_import_append_only_traçabilite_et_exp022(self):
        joueurs = [f"Joueur {j}" for j in range(11)]
        fiche = base("sportsgambler", "xi", "https://www.sportsgambler.com/lineups/football/")
        fiche["donnees"] = {"statut": "probable", "equipes": {
            "H": {"titulaires": joueurs}, "A": {"titulaires": joueurs}}}
        now = datetime.fromisoformat(AU).timestamp()
        with tempfile.TemporaryDirectory() as d:
            dest = Path(d)
            imports = dest / "imports" / "sportsgambler"
            imports.mkdir(parents=True)
            (imports / "fiche.json").write_text(json.dumps(fiche), encoding="utf-8")
            a = importer_source(dest, "sportsgambler", now)
            b = importer_source(dest, "sportsgambler", now)
            self.assertEqual((a["nouvelles"], b["nouvelles"]), (1, 0))
            archive = dest / "archive.jsonl"
            c = exp022.importer_sites(dest, archive, au=AU)
            self.assertEqual((c["xi"], c["ajoutes"], c["erreurs"]), (1, 1, 0))
            self.assertEqual(exp022.importer_sites(dest, archive, au=AU)["doublons"], 1)
            self.assertEqual(json.loads(archive.read_text().splitlines()[0])["statut"], "probable")

    def test_pas_de_fiches_ne_simule_pas_succes(self):
        with tempfile.TemporaryDirectory() as d:
            resultat = importer_source(Path(d), "180score", datetime.now(timezone.utc).timestamp())
            self.assertEqual(resultat["statut"], "attente")


if __name__ == "__main__":
    unittest.main()
