"""Tests hermetiques du pilote Apify, sans connexion et sans depense."""
import importlib.util
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
s = importlib.util.spec_from_file_location("pilote_apify", ROOT / "scripts" / "pilote_apify.py")
m = importlib.util.module_from_spec(s)
s.loader.exec_module(m)

T = int(datetime(2026, 11, 3, 12, tzinfo=timezone.utc).timestamp())


def match(i, **kw):
    return {"type": "match", "sport": "football", "id": i, "tournamentId": 17,
            "statusType": "notstarted", "startTimestamp": T + 3600,
            "homeTeam": "A", "awayTeam": "B", **kw}


class TestPiloteApify(unittest.TestCase):
    def test_audit_ante_match_ne_devient_pas_entrainement(self):
        data = [match(1, lineups={"confirmed": True, "home": {
            "missingPlayers": [{"player": {"name": "X"}}]}})]
        r = m.auditer(data, fin_run="2026-11-03T12:00:00Z", ligues={17})
        self.assertEqual((r["matchs_ligues_megatron"], r["matchs_prospectifs_observes_avant_coup_envoi"]), (1, 1))
        self.assertEqual((r["compositions_confirmees_dans_dataset"], r["joueurs_absents_declares"]), (1, 1))
        self.assertFalse(r["exploitable_entrainement"])
        self.assertEqual(r["alertes"], [])

    def test_fin_run_apres_coup_envoi_est_exclue(self):
        r = m.auditer([match(1)], fin_run="2026-11-03T14:00:00Z")
        self.assertEqual(r["matchs_prospectifs_observes_avant_coup_envoi"], 0)

    def test_doublons_score_invalide_et_date_absente(self):
        a = match(1)
        b = dict(a, statusType="finished", homeScore=-1, awayScore=2, startTimestamp=None)
        r = m.auditer([a, b], ligues={17})
        self.assertEqual((r["doublons"], r["scores_finaux_incoherents"]), (1, 1))
        self.assertIn("DATES_INCOMPLETES", r["alertes"])
        self.assertIn("FIN_RUN_ABSENTE : aucune preuve de disponibilite avant match", r["alertes"])

    def test_non_football_et_equipes_non_suivies(self):
        r = m.auditer([dict(match(1), sport="tennis"), match(2)], ligues={22})
        self.assertEqual(r["matchs_football"], 1)
        self.assertIn("AUCUNE_LIGUE_MEGATRON_RETENUE", r["alertes"])

    def test_readonly_fait_juste_deux_get_sur_run_existant(self):
        calls = []
        def lire(url, token):
            calls.append((url, token))
            if "/runs/last" in url:
                return {"data": {"id": "r1", "finishedAt": "2026-11-03T12:00:00Z",
                                 "defaultDatasetId": "ds1"}}
            return [match(1)]
        items, fin, run = m.charger_dernier_run("client~tache", "secret", lire=lire)
        self.assertEqual((len(items), run), (1, "r1"))
        self.assertEqual(len(calls), 2)
        self.assertTrue(all("/run-sync" not in x[0] and "/actor-runs" not in x[0] for x in calls))
        self.assertTrue(all("secret" not in x[0] for x in calls))

    def test_mode_fichier_sans_cle(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "items.json"
            rapport = Path(tmp) / "rapport.json"
            f.write_text(json.dumps([match(1)]), encoding="utf-8")
            self.assertEqual(m.main(["--fichier", str(f), "--fin-run",
                                     "2026-11-03T12:00:00Z", "--rapport", str(rapport)]), 0)
            self.assertEqual(json.loads(rapport.read_text())["matchs_football"], 1)


if __name__ == "__main__":
    unittest.main()
