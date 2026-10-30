import unittest
from datetime import date, datetime, timedelta, timezone

from megatron.agents import poisson_1x2
from megatron.data import Match
from megatron.dynamique import Filtre, Reglage, derouler, issues


def match(jour, dom, ext, bd, be, ligue="E0", tirs=None):
    r = "H" if bd > be else "A" if be > bd else "D"
    return Match(ligue, jour, datetime(jour.year, jour.month, jour.day, 12, tzinfo=timezone.utc), dom, ext, bd, be, r,
                 None, tirs)


class DynamiqueTests(unittest.TestCase):
    def test_issues_identiques_a_poisson_1x2(self):
        for lh, la in ((1.4, 1.1), (0.3, 2.9), (2.5, 2.5)):
            a, b = issues(lh, la), poisson_1x2(lh, la)
            for o in "HDA":
                self.assertAlmostEqual(a[o], b[o], places=12)

    def test_prevision_n_utilise_pas_le_jour_meme(self):
        j = date(2020, 8, 1)
        base = [match(j - timedelta(days=7), "A", "B", 1, 1), match(j - timedelta(days=7), "C", "D", 0, 0)]
        avec = base + [match(j, "A", "B", 5, 0), match(j, "C", "D", 0, 4)]
        p1 = derouler(base + [match(j, "A", "B", 0, 0)], Reglage())
        p2 = derouler(avec, Reglage())
        self.assertEqual(p1["E0:2020-08-01:A-B"], p2["E0:2020-08-01:A-B"])

    def test_match_futur_ou_score_futur_modifie_sans_effet_sur_le_passe(self):
        j = date(2020, 8, 1)
        base = [match(j, "A", "B", 1, 0, tirs=(9, 5, 4, 2)), match(j + timedelta(days=7), "B", "A", 2, 2)]
        futur = [match(j + timedelta(days=14), "A", "B", 6, 0, tirs=(30, 1, 15, 0))]
        modifie = [match(j + timedelta(days=7), "B", "A", 0, 5, tirs=(1, 20, 0, 12))]
        p0 = derouler(base, Reglage())
        p1 = derouler(base + futur, Reglage())
        for k in p0:
            self.assertEqual(p0[k], p1[k])
        self.assertEqual(p0["E0:2020-08-01:A-B"], derouler(base[:1] + modifie, Reglage())["E0:2020-08-01:A-B"])

    def test_victoire_large_releve_attaque_et_variance_decroit(self):
        f = Filtre(Reglage(w=0))
        j = date(2020, 8, 1)
        f.mettre_a_jour(match(j, "A", "B", 4, 0))
        a, b = f.equipes[("E0", "A", "a")], f.equipes[("E0", "B", "a")]
        self.assertGreater(a.m, b.m)
        self.assertLess(a.p, Reglage().p0)

    def test_variance_derive_avec_le_temps_et_au_1er_juillet(self):
        r = Reglage(q=0.001, q_saison=0.05)
        f = Filtre(r)
        f.mettre_a_jour(match(date(2021, 5, 1), "A", "B", 1, 0))
        p = f.equipes[("E0", "A", "a")].p
        self.assertAlmostEqual(f._equipe("E0", "A", "a", date(2021, 5, 11)).p, p + 0.01)
        self.assertAlmostEqual(f._equipe("E0", "A", "a", date(2021, 7, 1)).p, p + 0.001 * 61 + 0.05)

    def test_promu_part_sous_la_moyenne_de_la_ligue(self):
        j = date(2020, 8, 1)
        ms = [match(j + timedelta(days=7 * i), "A", "B", 2, 1) for i in range(5)]
        ms.append(match(j + timedelta(days=60), "A", "N", 0, 0))  # N : nouvelle équipe
        sans = derouler(ms, Reglage(c=0))["E0:2020-09-30:A-N"]
        avec = derouler(ms, Reglage(c=0.3))["E0:2020-09-30:A-N"]
        self.assertGreater(avec[0]["H"], sans[0]["H"])

    def test_tirs_cadres_servent_apres_le_premier_rapport(self):
        j = date(2020, 8, 1)
        ms = [match(j, "A", "B", 1, 1, tirs=(10, 10, 4, 4)), match(j + timedelta(days=7), "A", "B", 0, 0, tirs=(20, 2, 9, 0))]
        p_w = derouler(ms + [match(j + timedelta(days=14), "A", "B", 0, 0)], Reglage(w=0.35))
        p_0 = derouler(ms + [match(j + timedelta(days=14), "A", "B", 0, 0)], Reglage(w=0))
        k = "E0:2020-08-15:A-B"
        self.assertGreater(p_w[k][0]["H"], p_0[k][0]["H"])

    def test_mode_xg_remplace_les_buts_par_les_xg(self):
        j = date(2020, 8, 1)
        ms = [match(j, "A", "B", 0, 0, tirs=(20, 2, 9, 0)), match(j + timedelta(days=7), "A", "B", 0, 0)]
        k = "E0:2020-08-08:A-B"
        sans = derouler(ms, Reglage(w=1.0), xg={})[k]
        avec = derouler(ms, Reglage(w=1.0), xg={"E0:2020-08-01:A-B": (3.0, 0.2)})[k]
        self.assertGreater(avec[0]["H"], sans[0]["H"])
        buts = derouler(ms, Reglage(w=0.0))[k]  # mode xG sans xG : buts seuls, tirs ignorés
        self.assertEqual(sans, buts)

    def test_liaison_understat_par_vote_sur_les_matchs_communs(self):
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
        from exp018_xg import relier
        j = date(2020, 8, 1)
        ms = [match(j, "Man City", "Spurs", 2, 0), match(j + timedelta(days=7), "Spurs", "Man City", 1, 1)]
        xg = [{"division": "E0", "jour": j, "dom": "Manchester City", "ext": "Tottenham", "bd": 2, "be": 0, "xg": (2.1, 0.4)},
              {"division": "E0", "jour": j + timedelta(days=8), "dom": "Tottenham", "ext": "Manchester City", "bd": 1, "be": 1,
               "xg": (0.9, 1.7)},
              {"division": "E0", "jour": j + timedelta(days=30), "dom": "Tottenham", "ext": "Manchester City", "bd": 0, "be": 0,
               "xg": (1.0, 1.0)}]
        lie, info = relier(xg, ms)
        self.assertEqual(lie, {"E0:2020-08-01:Man City-Spurs": (2.1, 0.4), "E0:2020-08-08:Spurs-Man City": (0.9, 1.7)})
        self.assertEqual(info["non_relie"], 1)


if __name__ == "__main__":
    unittest.main()
