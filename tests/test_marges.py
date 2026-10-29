import math
import tempfile
import unittest
from unittest import mock

from megatron import marges
from megatron.ledger import Ledger
from megatron.store import MemoryStore


class MargesTests(unittest.TestCase):
    def test_scores_distincts_du_total_et_direction(self):
        for score, expected in [([2, 1], [False, False, False, False]),
                                ([4, 1], [True, True, False, False]),
                                ([1, 4], [False, False, True, True]),
                                ([3, 1], [True, False, False, False]),
                                ([0, 0], [False] * 4)]:
            with self.subTest(score=score):
                self.assertEqual([marges.resoudre(score, k) == 'oui' for k in marges.MARGES], expected)

    def test_scores_invalides_refuses(self):
        for sc in (None, [1], [-1, 0], [1.5, 0], ['2', 0], [True, 0]):
            with self.subTest(sc=sc), self.assertRaises(ValueError):
                marges.resoudre(sc, 'H_MARGE_2PLUS')
        with self.assertRaises(ValueError):
            marges.resoudre([2, 0], '2+')

    def test_reference_poisson_exacte_adversaire_zero(self):
        rep = marges.calculer(2, 0)
        n = rep['niveaux']['H']
        for key, expected in [('victoire_simple', 1-math.exp(-2)),
                              ('victoire_par_2_ou_plus', 1-3*math.exp(-2)),
                              ('victoire_par_3_ou_plus', 1-5*math.exp(-2))]:
            self.assertAlmostEqual(n[key], expected, places=12)
        self.assertEqual(rep['niveaux']['A']['victoire_simple'], 0)

    def test_niveaux_emboites_et_probabilites_valides(self):
        for h, a in [(0, 0), (1.4, 1.1), (5, .3), (.1, 8), (10, 10)]:
            rep = marges.calculer(h, a)
            self.assertAlmostEqual(sum(rep['1X2'].values()), 1, places=12)
            self.assertLess(rep['masse_tronquee'], 1e-12)
            for side in ('H', 'A'):
                n = rep['niveaux'][side]
                self.assertLessEqual(n['victoire_par_3_ou_plus'], n['victoire_par_2_ou_plus'])
                self.assertLessEqual(n['victoire_par_2_ou_plus'], n['victoire_simple'])
            for p in rep['marches'].values():
                self.assertAlmostEqual(sum(p.values()), 1, places=12)
                self.assertTrue(all(0 <= x <= 1 for x in p.values()))

    def test_symetrie_domicile_exterieur(self):
        x, y = marges.calculer(1.9, .7), marges.calculer(.7, 1.9)
        for k, p in x['niveaux']['H'].items():
            self.assertAlmostEqual(p, y['niveaux']['A'][k], places=12)

    def test_intensites_invalides_refusees(self):
        for rate in (float('nan'), float('inf'), -1, 10.1, True, '1.5'):
            with self.subTest(rate=rate), self.assertRaises(ValueError):
                marges.calculer(rate, 1)

    def test_registre_marge_evaluee_total_ancien_inchange(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Ledger(MemoryStore(tmp))
            for market in ('H_MARGE_2PLUS', 'A_MARGE_3PLUS', '2+', '3+'):
                ledger.predict('fictif', '2099-01-01T12:00:00Z', {'oui': .4, 'non': .6},
                               model_version='brut-test', source='test', recorded_at='2099-01-01T10:00:00Z', market=market)
            ledger.result('fictif', 'H', source='test', observed_at='2099-01-01T14:00:00Z', goals=(2, 1))
            self.assertEqual(ledger.outcomes('H_MARGE_2PLUS'), {'fictif': 'non'})
            self.assertEqual(ledger.outcomes('A_MARGE_3PLUS'), {'fictif': 'non'})
            self.assertEqual(ledger.outcomes('2+'), {'fictif': 'oui'})
            self.assertEqual(ledger.outcomes('3+'), {'fictif': 'oui'})
            self.assertEqual(ledger.evaluate('brut-test', market='H_MARGE_2PLUS')['n'], 1)
            self.assertAlmostEqual(ledger.evaluate('brut-test', market='H_MARGE_2PLUS')['log_loss'], -math.log(.6), places=6)

    def test_issue_sans_score_ne_resout_pas_marge(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Ledger(MemoryStore(tmp))
            ledger.predict('fictif', '2099-01-01T12:00:00Z', {'oui': .4, 'non': .6},
                           model_version='test', source='test', recorded_at='2099-01-01T10:00:00Z', market='H_MARGE_2PLUS')
            ledger.result('fictif', 'H', source='test', observed_at='2099-01-01T14:00:00Z')
            self.assertEqual(ledger.outcomes('H_MARGE_2PLUS'), {})
            self.assertEqual(ledger.evaluate('test', market='H_MARGE_2PLUS')['n'], 0)

    def test_cli_experimentale_sans_ecriture(self):
        from megatron.__main__ import main
        with mock.patch('builtins.print') as printer, mock.patch('megatron.store.MemoryStore.record') as record:
            self.assertEqual(main(['marges', '--xg-home', '2', '--xg-away', '0']), 0)
            self.assertIn('EXPERIMENTAL_NON_CALIBRE', printer.call_args[0][0])
            record.assert_not_called()
            self.assertEqual(main(['marges', '--xg-home', 'nan', '--xg-away', '1']), 2)
