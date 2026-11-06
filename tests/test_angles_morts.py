"""Angles morts du favori : données fictives uniquement."""

import random
import unittest
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone

from megatron import angles_morts as am
from megatron.data import Match


def fictive(seed=3, teams=12, seasons=2, start=date(2030, 8, 1)):
    rng = random.Random(seed)
    names = [f"Équipe{i:02d}" for i in range(teams)]
    matches, details, day = [], {}, start
    for _ in range(seasons):
        for h in names:
            for a in names:
                if h == a:
                    continue
                sh, sa = rng.randint(1, 9), rng.randint(0, 7)
                gh, ga = min(sh, rng.randint(0, 3)), min(sa, rng.randint(0, 2))
                m = Match("X1", day, datetime(day.year, day.month, day.day, 15, tzinfo=timezone.utc), h, a, gh, ga,
                          "H" if gh > ga else "A" if ga > gh else "D", None, (sh + 5, sa + 4, sh, sa))
                matches.append(m)
                details[m.match_id] = {"HTHome": float(min(gh, 1)), "HTAway": float(min(ga, 1)),
                                       "HomeRed": float(rng.random() < 0.1), "AwayRed": float(rng.random() < 0.1),
                                       "HomeCorners": float(rng.randint(2, 9)), "AwayCorners": float(rng.randint(1, 8))}
                day += timedelta(days=1)
    return matches, details, day


class AnglesMortsTest(unittest.TestCase):
    def setUp(self):
        self.matches, self.details, self.day = fictive()

    def test_treize_angles_et_trois_questions(self):
        self.assertEqual(len(am.ANGLES), 13)
        self.assertEqual(set(am.QUESTIONS), {"defaite", "nul", "ecart"})
        self.assertEqual(len(am.AXES), 4)
        self.assertEqual({a.mesure for a in am.ANGLES} <= {"historique", "partiel", "externe"}, True)
        self.assertEqual(len(am.couverture()), 13)

    def test_scenario_exige_fait_source_mecanisme(self):
        ok = am.Scenario("favori_exterieur", "nul", "fait", "source", "mécanisme")
        self.assertEqual(ok.ajustement, 0.0)
        for champ in ("fait", "source", "mecanisme"):
            kw = {"fait": "f", "source": "s", "mecanisme": "m", champ: " "}
            with self.assertRaises(ValueError):
                am.Scenario("favori_exterieur", "nul", **kw)
        with self.assertRaises(ValueError):
            am.Scenario("inconnu", "nul", "f", "s", "m")
        with self.assertRaises(ValueError):
            am.Scenario("ecart_trompeur", "defaite", "f", "s", "m")  # cet angle ne répond qu'à l'écart

    def test_ajustement_sans_experience_refuse(self):
        with self.assertRaises(ValueError):
            am.Scenario("favori_exterieur", "nul", "f", "s", "m", ajustement=0.02)
        am.Scenario("favori_exterieur", "nul", "f", "s", "m", ajustement=0.02, experience="EXP-009")

    def test_probabilites_questions(self):
        p = am.probabilites_questions(2.0, 0.8)
        self.assertLess(p["defaite"], p["ecart"])
        self.assertLess(p["nul"], p["ecart"])
        self.assertAlmostEqual(am.probabilites_questions(1.2, 1.2)["defaite"],
                               1 - am.probabilites_questions(1.2, 1.2)["nul"] - am.probabilites_questions(1.2, 1.2)["defaite"], 6)
        self.assertEqual(am.issues_questions(2, 1), {"defaite": False, "nul": False, "ecart": True})
        self.assertEqual(am.issues_questions(3, 1), {"defaite": False, "nul": False, "ecart": False})

    def test_analyse_structure_et_probabilites_inchangees(self):
        out = am.analyser(self.matches, self.details, "Équipe00", "Équipe01", self.day, 1.1, 1.6)
        self.assertEqual(out["favori"], "Équipe01")
        self.assertFalse(out["favori_a_domicile"])
        p = am.probabilites_questions(1.6, 1.1)
        for q in am.QUESTIONS:
            self.assertEqual(out["questions"][q]["probabilite"], round(p[q], 4))
            for s in out["questions"][q]["scenarios"]:
                self.assertTrue(s["fait"] and s["source"] and s["mecanisme"])
                self.assertEqual(s["ajustement"], 0.0)
                self.assertGreater(s["valeur"], 0)
        self.assertEqual(set(out["comparateur"]["axes"]), set(am.AXES))
        self.assertIsNotNone(out["comparateur"]["dernier_h2h"])
        externes = {a["angle"] for a in out["a_verifier_hors_data"]}
        self.assertIn("dependance_joueur", externes)
        self.assertIn("style_gene", externes)

    def test_anti_fuite(self):
        with self.assertRaises(AssertionError):
            am.analyser(self.matches, self.details, "Équipe00", "Équipe01", self.matches[-1].day, 1.1, 1.6)
        # modifier les matchs du jour prédit ou après ne change rien
        past = [m for m in self.matches if m.day < self.day - timedelta(days=30)]
        cut = self.day - timedelta(days=30)
        a = am.analyser(past, self.details, "Équipe03", "Équipe04", cut, 1.4, 1.0)
        later = dict(self.details)
        for m in self.matches:
            if m.day >= cut:
                later[m.match_id] = {**later[m.match_id], "HomeRed": 5.0, "HTHome": 9.0}
        b = am.analyser(past, later, "Équipe03", "Équipe04", cut, 1.4, 1.0)
        self.assertEqual(a, b)

    def test_trois_h2h_ordre_et_marges_orientees(self):
        base = self.matches[0]
        def match(n, home, away, gh, ga):
            day = date(2030, 1, n)
            return replace(base, day=day, kickoff=datetime(2030, 1, n, tzinfo=timezone.utc),
                           home=home, away=away, home_goals=gh, away_goals=ga, shots=None)
        oldest = match(1, "F", "A", 9, 0)
        short = match(2, "F", "A", 2, 1)
        wide = match(3, "A", "F", 1, 4)
        loss = match(4, "A", "F", 2, 0)
        details = {wide.match_id: {"HTHome": 1, "HTAway": 1, "HomeRed": 1, "AwayRed": 0}}
        original = [wide, oldest, loss, short]
        out = am.comparateur_h2h(original, [], details, "F", "A", self.day, {})
        rows = out["derniers_3_h2h"]
        self.assertEqual([r["match_id"] for r in rows], [loss.match_id, wide.match_id, short.match_id])
        self.assertEqual(original, [wide, oldest, loss, short])
        self.assertEqual([r["marge_favori"] for r in rows], [-2, 3, 1])
        self.assertEqual([r["marge_2plus"] for r in rows], [False, True, False])
        self.assertEqual([r["marge_3plus"] for r in rows], [False, True, False])
        self.assertEqual(rows[1]["score"], [1, 4])
        self.assertFalse(rows[1]["favori_a_domicile"])
        self.assertEqual(rows[1]["construction_ecart"]["rouges_adversaire"], 1)
        self.assertTrue(rows[1]["construction_ecart"]["seuil_2plus_atteint_en_seconde_periode"])
        self.assertIsNone(rows[0]["construction_ecart"]["marge_mi_temps_favori"])
        self.assertEqual(out["couverture_3_h2h"]["statut"], "TROIS_PRESENTS")

    def test_h2h_insuffisants_et_details_partiels(self):
        m = self.matches[0]
        for count in (0, 1):
            out = am.comparateur_h2h([m] * count, [], {m.match_id: {"HTHome": 1, "HomeRed": 0}},
                                     m.home, m.away, self.day, {})
            self.assertEqual(len(out["derniers_3_h2h"]), count)
            self.assertEqual(out["couverture_3_h2h"]["manquants"], 3 - count)
            self.assertEqual(out["couverture_3_h2h"]["statut"], "HISTORIQUE_INSUFFISANT")
            if count:
                self.assertIsNone(out["dernier_h2h"]["mi_temps"])
                self.assertIn("rouges", out["derniers_3_h2h"][0]["informations_manquantes"])

    def test_h2h_doublons_autres_equipes_et_futur_refuses(self):
        m = self.matches[0]
        with self.assertRaises(ValueError):
            am.comparateur_h2h([m, m], [], {}, m.home, m.away, self.day, {})
        with self.assertRaises(ValueError):
            am.comparateur_h2h([m], [], {}, "Autre", m.away, self.day, {})
        for day in (m.day, m.day - timedelta(days=1)):
            with self.assertRaises(AssertionError):
                am.comparateur_h2h([m], [], {}, m.home, m.away, day, {})


if __name__ == "__main__":
    unittest.main()
