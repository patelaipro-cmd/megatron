"""Registre prospectif : moments, jeton claude, 1X2 et marges avant match, résultats à deux familles."""
import csv
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from megatron import jeton
from megatron.ledger import DOMAIN
from megatron.store import MemoryStore
from scripts import registre_prospectif as rp

KO = datetime(2026, 11, 1, 16, 30, tzinfo=timezone.utc)
NOMS = {"espn:E0": {"Arsenal": "Arsenal", "Chelsea": "Chelsea"}}


def lecteur(etat="pre", home="Arsenal"):
    def lire(url):
        if "eng.1" not in url or not url.endswith(KO.strftime("%Y%m%d")):
            return {"events": []}
        return {"events": [{"id": "1", "date": KO.isoformat(), "competitions": [{
            "status": {"type": {"state": etat}},
            "competitors": [{"homeAway": "home", "team": {"displayName": home}},
                            {"homeAway": "away", "team": {"displayName": "Chelsea"}}]}]}]}
    return lire


class TestRegistre(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.reg = Path(self.tmp.name) / "registre"

    def tearDown(self):
        self.tmp.cleanup()

    def run_at(self, minutes, **kw):
        return rp.executer(self.reg, None, KO - timedelta(minutes=minutes), lire=kw.pop("lire", lecteur()), noms=NOMS, **kw)

    def test_initial_puis_t30_t5_et_fenetres_manquees(self):
        self.assertEqual(self.run_at(400)["enregistres"], [])  # trop tôt
        r = self.run_at(120)
        self.assertEqual([x["moment"] for x in r["enregistres"]], ["initial"])
        self.assertEqual(self.run_at(100)["enregistres"], [])  # initial déjà fait
        self.assertEqual([x["moment"] for x in self.run_at(30)["enregistres"]], ["T-30"])
        self.assertEqual([x["moment"] for x in self.run_at(5)["enregistres"]], ["T-5"])
        store = MemoryStore(self.reg)
        cles = sorted(e.key for e in store.active(DOMAIN))
        mid = "E0:2026-11-01:Arsenal-Chelsea"
        self.assertEqual(len(cles), 3)  # 1X2 v5-cal + marges 2+ et 3+ du favori, une seule fois
        self.assertTrue(any(k == f"pred:{mid}:poisson-v5-cal" for k in cles))
        self.assertTrue(all(e.recorded_at < KO.isoformat() for e in store.active(DOMAIN)))
        st = jeton.statut(store)
        self.assertEqual((st["initialise"], st["detenteur"]), (True, "claude"))
        self.assertFalse(r["activation_automatique"])

    def test_t5_sans_initial_refuse_et_match_commence_ignore(self):
        self.assertEqual(self.run_at(5)["enregistres"], [])
        self.assertEqual(self.run_at(120, lire=lecteur(etat="in"))["enregistres"], [])

    def test_nom_non_relie_note_sans_approximation(self):
        r = self.run_at(120, lire=lecteur(home="Arsenal FC"))
        self.assertEqual(r["enregistres"], [])
        self.assertIn("nom non relié", r["notes"][0])

    def test_resultat_seulement_confirme_et_apres_coup_envoi(self):
        self.run_at(120)
        admis = Path(self.tmp.name) / "admis.csv"
        with admis.open("w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["Division", "MatchDate", "MatchTime", "HomeTeam", "AwayTeam", "FTHome", "FTAway",
                                                  "FTResult", "OddHome", "OddDraw", "OddAway", "HomeShots", "AwayShots", "HomeTarget", "AwayTarget"])
            w.writerow(["E0", "2026-11-01", "17:30:00", "Arsenal", "Chelsea", 2, 0, "H"] + [""] * 7)
        r = rp.executer(self.reg, None, KO + timedelta(hours=20), admis, lire=lecteur(etat="post"), noms=NOMS)
        self.assertEqual(r["resultats_saisis"], ["E0:2026-11-01:Arsenal-Chelsea"])
        r = rp.executer(self.reg, None, KO + timedelta(hours=44), admis, lire=lecteur(etat="post"), noms=NOMS)
        self.assertEqual(r["resultats_saisis"], [])  # jamais deux fois

    def test_xg_v1_en_observation_seulement_xg_collectes_avant(self):
        from megatron import data

        externe = Path(self.tmp.name) / "externe"
        dossier = externe / "understat"
        dossier.mkdir(parents=True)
        recents = [m for m in data.load(data.CURRENT, divisions={"E0"}) if data.season_of(m.day) == "2025/26"]
        with (dossier / "matchs_equipes_2025-26.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["league", "date", "home_team", "away_team", "home_goals", "away_goals", "home_xg", "away_xg",
                        "collecte_le"])
            for i, m in enumerate(recents):  # la moitié collectée après l'instant d'enregistrement : ignorée
                quand = "2026-07-01T00:00:00+00:00" if i % 2 else "2026-12-01T00:00:00+00:00"
                w.writerow(["ENG-Premier League", f"{m.day} 15:00:00", m.home, m.away, m.home_goals, m.away_goals,
                            1.1, 0.9, quand])
        r = rp.executer(self.reg, externe, KO - timedelta(minutes=120), lire=lecteur(), noms=NOMS)
        self.assertEqual([x["moment"] for x in r["enregistres"]], ["initial"])
        store = MemoryStore(self.reg)
        mid = "E0:2026-11-01:Arsenal-Chelsea"
        (e,) = store.active(DOMAIN, f"pred:{mid}:xg-v1-cal")
        self.assertAlmostEqual(sum(e.value["probs"].values()), 1.0, places=6)
        self.assertIn("hors fusion", e.source)
        self.assertEqual(len(store.active(DOMAIN)), 4)  # v5-cal + xg-v1-cal + marges 2+ et 3+
        lie = rp.xg_relies(externe, data.load(data.CURRENT), KO - timedelta(minutes=120))
        self.assertEqual(len(lie), (len(recents) + 1) // 2)
        rp.executer(self.reg, externe, KO - timedelta(minutes=100), lire=lecteur(), noms=NOMS)
        self.assertEqual(len(store.active(DOMAIN)), 4)  # jamais deux fois

    def test_sans_xg_rien_ecrit_et_note(self):
        r = rp.executer(self.reg, Path(self.tmp.name) / "vide", KO - timedelta(minutes=120), lire=lecteur(), noms=NOMS)
        self.assertEqual([x["moment"] for x in r["enregistres"]], ["initial"])
        self.assertEqual(MemoryStore(self.reg).active(DOMAIN, "pred:E0:2026-11-01:Arsenal-Chelsea:xg-v1-cal"), [])

    def test_jeton_detenu_par_codex_bloque(self):
        store = MemoryStore(self.reg)
        jeton.initialiser(store, "codex", source="test")
        with self.assertRaises(jeton.JetonError):
            self.run_at(120)


if __name__ == "__main__":
    unittest.main()
