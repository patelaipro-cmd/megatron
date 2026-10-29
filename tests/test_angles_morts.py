"""Angles morts du favori : données fictives uniquement."""

import random
import unittest
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


if __name__ == "__main__":
    unittest.main()
