"""Modèle xg-v1-cal : données fictives uniquement."""

import csv
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from megatron import xg as X
from megatron.data import Match
from megatron.dynamique import derouler

CHAMPS = ["league", "date", "home_team", "away_team", "home_goals", "away_goals", "home_xg", "away_xg", "collecte_le"]


def fictifs(n_jours=60):
    equipes = ["Alpha", "Beta", "Gamma", "Delta"]
    matchs, jour = [], date(2030, 8, 1)
    for i in range(n_jours):
        h, a = equipes[i % 4], equipes[(i + 1 + i // 4) % 4]
        if h == a:
            a = equipes[(i + 2) % 4]
        gh, ga = (i * 7) % 4, (i * 3) % 3
        matchs.append(Match("E0", jour, datetime(jour.year, jour.month, jour.day, 15, tzinfo=timezone.utc), h, a,
                            gh, ga, "H" if gh > ga else "A" if ga > gh else "D", None))
        jour += timedelta(days=1)
    return matchs


def ecrire(dossier: Path, matchs, collecte="2030-12-01T00:00:00+00:00", nom="matchs_equipes_2030-31.csv",
           renommer=lambda t: f"FC {t}"):
    dossier.mkdir(parents=True, exist_ok=True)
    with (dossier / nom).open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(CHAMPS)
        for m in matchs:
            w.writerow(["ENG-Premier League", f"{m.day} 15:00:00", renommer(m.home), renommer(m.away), m.home_goals,
                        m.away_goals, m.home_goals + 0.3, m.away_goals + 0.2, collecte])


class XgTest(unittest.TestCase):
    def setUp(self):
        self.matchs = fictifs()
        self.tmp = tempfile.TemporaryDirectory()
        self.dossier = Path(self.tmp.name) / "courant"
        ecrire(self.dossier, self.matchs)

    def tearDown(self):
        self.tmp.cleanup()

    def test_liaison_par_noms_differents(self):
        lie, info = X.relier(X.charger([self.dossier]), self.matchs)
        self.assertEqual(info["relies"], len(self.matchs))
        self.assertEqual(lie[self.matchs[0].match_id], (self.matchs[0].home_goals + 0.3, self.matchs[0].away_goals + 0.2))

    def test_collecte_la_plus_recente_et_borne_temporelle(self):
        autre = Path(self.tmp.name) / "historique"
        ecrire(autre, self.matchs[:5], collecte="2030-11-01T00:00:00+00:00", nom="matchs_equipes_vieux.csv")
        lignes = X.charger([autre, self.dossier])
        self.assertEqual(len(lignes), len(self.matchs))
        self.assertTrue(all(r["collecte_le"] == datetime(2030, 12, 1, tzinfo=timezone.utc) for r in lignes))
        borne = X.charger([autre, self.dossier], avant=datetime(2030, 11, 15, tzinfo=timezone.utc))
        self.assertEqual(len(borne), 5)
        self.assertEqual(X.charger([self.dossier], avant=datetime(2030, 12, 1, tzinfo=timezone.utc)), [])

    def test_identique_a_derouler(self):
        lie, _ = X.relier(X.charger([self.dossier]), self.matchs)
        cible = self.matchs[40]
        attendu = derouler(self.matchs, X.REGLAGE, xg=lie)[cible.match_id]
        lh, la, vus = X.intensites(self.matchs, lie, "E0", cible.home, cible.away, cible.day)
        self.assertEqual((lh, la), attendu[1:])
        self.assertEqual(vus, 40)

    def test_anti_fuite(self):
        lie, _ = X.relier(X.charger([self.dossier]), self.matchs)
        cible = self.matchs[30]
        a = X.intensites(self.matchs, lie, "E0", cible.home, cible.away, cible.day)
        futurs = {m.match_id: (9.0, 9.0) for m in self.matchs[30:]}
        b = X.intensites(self.matchs, {**lie, **futurs}, "E0", cible.home, cible.away, cible.day)
        self.assertEqual(a, b)

    def test_agent_hors_production(self):
        from megatron.agents import default_agents

        self.assertNotIn("xg", {a.name for a in default_agents()})
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "m.csv"
            with p.open("w", newline="", encoding="utf-8") as fh:
                w = csv.writer(fh)
                w.writerow(["Division", "MatchDate", "MatchTime", "HomeTeam", "AwayTeam", "FTHome", "FTAway", "FTResult",
                            "OddHome", "OddDraw", "OddAway"])
                for m in self.matchs:
                    w.writerow(["E0", m.day.isoformat(), "15:00", m.home, m.away, m.home_goals, m.away_goals, m.result, "", "", ""])
            rep = X.XgAgent([self.dossier], csv_path=p).ask(
                {"division": "E0", "home": "Alpha", "away": "Beta", "date": "2030-09-20"})
        self.assertEqual(rep.status, "ok", rep.raison)
        self.assertEqual(rep.version, "xg-v1-cal")
        self.assertAlmostEqual(sum(rep.probs.values()), 1.0)


if __name__ == "__main__":
    unittest.main()
