"""Garde-fous de l'audit de couverture du futur pilote LIVE T+15."""

import csv
import io
import json
import tempfile
import unittest
from pathlib import Path

from scripts.auditer_pilote_live import auditer, charger_dossier, instant


AU = "2026-11-16T06:00:00+01:00"
KO_PASSE = "2026-11-15T17:30:00+00:00"
KO_FUTUR = "2026-11-16T20:00:00+01:00"
COLONNES = ("collecte_le", "event_id", "ligue", "coup_envoi", "domicile", "exterieur",
            "equipe", "joueur", "joueur_id", "statut", "source")


def csv_xi(*, event="1", ko=KO_PASSE, collecte="2026-11-15T16:56:00+00:00",
           h=True, a=True, orientation=True, joueur_doublon=False):
    sortie = io.StringIO()
    colonnes = COLONNES if orientation else tuple(x for x in COLONNES if x not in ("domicile", "exterieur"))
    writer = csv.DictWriter(sortie, fieldnames=colonnes)
    writer.writeheader()
    for equipe, present in (("Home", h), ("Away", a)):
        if not present:
            continue
        for i in range(11):
            r = {"collecte_le": collecte, "event_id": event, "ligue": "test.1", "coup_envoi": ko,
                 "domicile": "Home", "exterieur": "Away", "equipe": equipe,
                 "joueur": f"{equipe} {i}", "joueur_id": f"{equipe}-{0 if joueur_doublon else i}",
                 "statut": "titulaire", "source": "espn"}
            writer.writerow({k: r[k] for k in colonnes})
    return sortie.getvalue().encode()


def rapport(liste, *, au=AU, cible=50):
    return auditer([(f"capture-{i}.csv", x) for i, x in enumerate(liste)],
                   {"execution_le": "2026-11-16T05:00:00+00:00", "sources": {"espn": {"statut": "ok"}}},
                   au=au, cible=cible)


class PilotLiveAuditTests(unittest.TestCase):
    def test_50_archives_historiques_n_equivalent_pas_a_50_watch(self):
        r = rapport([csv_xi(event=str(i)) for i in range(50)])
        self.assertEqual(r["matchs_xi_historiques_uniques"], 50)
        self.assertEqual(r["matchs_xi_historiques_orientes"], 50)
        self.assertEqual(r["watch_live"], 0)
        self.assertEqual(r["progression_pilote"], "0/50")
        self.assertEqual(r["decision"], "REFUS")

    def test_dedoublonnage_du_meme_evenement(self):
        r = rapport([csv_xi(), csv_xi(collecte="2026-11-15T16:57:00+00:00")])
        self.assertEqual(r["captures_xi_valides"], 2)
        self.assertEqual(r["matchs_xi_historiques_uniques"], 1)
        self.assertEqual(r["exemples_historiques"][0]["xi_collecte_le"], "2026-11-15T16:57:00+00:00")

    def test_collecte_post_kickoff_et_future_refusees(self):
        r = rapport([csv_xi(collecte=KO_PASSE),
                     csv_xi(event="2", ko=KO_FUTUR, collecte="2026-11-16T07:00:00+01:00")])
        self.assertEqual(r["matchs_xi_historiques_uniques"], 0)
        self.assertEqual(r["matchs_xi_futurs_uniques"], 0)
        self.assertEqual(r["anomalies_captures"]["XI collecté après le coup d'envoi"], 1)
        self.assertEqual(r["anomalies_captures"]["XI futur au moment de l'audit"], 1)

    def test_xi_incomplet_et_doublonne_refuse(self):
        r = rapport([csv_xi(a=False), csv_xi(event="2", joueur_doublon=True)])
        self.assertEqual(r["captures_xi_valides"], 0)
        self.assertEqual(r["matchs_xi_historiques_uniques"], 0)
        self.assertGreaterEqual(sum(r["anomalies_captures"].values()), 2)

    def test_schema_historique_deux_xi_sans_orientation(self):
        r = rapport([csv_xi(orientation=False)])
        self.assertEqual(r["matchs_xi_historiques_uniques"], 1)
        self.assertEqual(r["matchs_xi_historiques_orientes"], 0)
        self.assertFalse(r["exemples_historiques"][0]["orientation_HA_verifiee"])

    def test_futur_avec_deux_xi_ne_produit_aucune_prevision_directe(self):
        r = rapport([csv_xi(ko=KO_FUTUR, collecte="2026-11-16T05:30:00+01:00")])
        self.assertEqual(r["matchs_xi_futurs_uniques"], 1)
        self.assertEqual(len(r["candidats_xi_futurs"]), 1)
        self.assertEqual(r["matchs_reellement_prets_t15"], 0)
        self.assertEqual(r["watch_live"], 0)

    def test_fichier_invalide_ou_fuseau_absent(self):
        r = rapport([b"cle,nom\nvaleur,autre\n", csv_xi(collecte="2026-11-15T16:56:00")])
        self.assertEqual(r["captures_xi_valides"], 0)
        self.assertTrue(r["anomalies_captures"])
        with self.assertRaisesRegex(ValueError, "fuseau"):
            instant("2026-11-16T06:00:00")

    def test_lecture_dossier_reel_sans_ecrire(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            dest = base / "espn" / "compos" / "2026-11-15"
            dest.mkdir(parents=True)
            (dest / "1656.csv").write_bytes(csv_xi())
            (base / "manifeste.json").write_text(json.dumps({"sources": {"espn": {"statut": "ok"}}}), encoding="utf-8")
            fichiers, manifeste = charger_dossier(base)
            self.assertEqual(len(fichiers), 1)
            self.assertEqual(rapport([fichiers[0][1]])["captures_xi_valides"], 1)
            self.assertEqual(manifeste["sources"]["espn"]["statut"], "ok")

    def test_cible_invalide(self):
        with self.assertRaisesRegex(ValueError, "cible"):
            rapport([], cible=0)


if __name__ == "__main__":
    unittest.main()
