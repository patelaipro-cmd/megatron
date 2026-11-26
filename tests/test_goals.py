import unittest
from datetime import date, datetime, timedelta, timezone
from unittest.mock import patch, Mock
from megatron import goals
from megatron.data import Match

class GoalsTests(unittest.TestCase):
    def setUp(self):
        self.fixture = dict(division='F1', home='A', away='B', kickoff='2026-11-16T21:00:00+01:00')
        self.at = '2026-11-16T20:00:00+01:00'
        self.history = [Match('F1', date(2026,11,15)-timedelta(days=i), datetime(2026,11,15,tzinfo=timezone.utc)-timedelta(days=i), 'A','B',2,2,'D',None) for i in range(10)]

    def run_model(self, rates, **kwargs):
        with patch('megatron.goals.models.fit_maher', return_value=Mock(rates=Mock(return_value=rates))) as fit:
            r = goals.evaluate(self.fixture, at=self.at, history=self.history, **kwargs)
            self.assertTrue(all(m.day < date(2026,11,16) for m in fit.call_args.args[0]))
            return r

    def test_balanced_high_goals_without_v1(self):
        with patch('megatron.syndicate.evaluer', side_effect=AssertionError('V1 called')):
            r = self.run_model((2.5,2.5))
        self.assertIn('OVER_3_5',r['candidates'])
        self.assertEqual(r['status'],'WATCH')
        self.assertNotIn('UNDER_1_5',r['candidates'])
        self.assertFalse(r['automatic_activation'])

    def test_closed_balanced_match(self):
        self.assertIn('UNDER_1_5',self.run_model((0.2,0.2))['candidates'])

    def test_future_results_excluded(self):
        self.history += [Match('F1',date(2026,11,17),datetime(2026,11,17,tzinfo=timezone.utc),'A','B',9,9,'D',None)]
        self.assertEqual(self.run_model((1,1))['data_cutoff'],'2026-11-15')

    def test_missing_and_stale(self):
        self.assertEqual(goals.evaluate(self.fixture,at=self.at,history=[])['status'],'DONNEES_INSUFFISANTES')
        self.fixture['kickoff']='2027-01-02T21:00:00+01:00'
        self.assertEqual(goals.evaluate(self.fixture,at='2027-01-02T20:00:00+01:00',history=self.history)['status'],'A_ACTUALISER')

    def test_started(self):
        self.assertEqual(goals.evaluate(self.fixture,at='2026-11-16T21:00:00+01:00')['status'],'EXCLU_COMMENCE')

    def test_threshold_and_rates(self):
        for threshold in (0.4, 1.1, float('nan')):
            with self.assertRaises(ValueError): goals.evaluate(self.fixture,at=self.at,threshold=threshold)
        with self.assertRaises(ValueError): goals.probabilities(-1,2)

    def test_market_meanings(self):
        self.assertEqual(goals.MARKETS,{'OVER_2_5':3,'OVER_3_5':4,'OVER_4_5':5,'UNDER_1_5':2})
        p=goals.probabilities(2,2)
        self.assertGreater(p['OVER_3_5'][0],p['OVER_4_5'][0])
        self.assertAlmostEqual(p['UNDER_1_5'][0],1-goals.marches.probs_buts_calibrees(2,2)['2+']['oui'])

    def test_h2h_metadata_does_not_change_v2_probabilities(self):
        import csv
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "h2h.csv"
            with path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=["date","match","h2h_1","h2h_2","h2h_3","h2h_count","status"])
                writer.writeheader()
                writer.writerow({"date":"2026-11-16","match":"A - B","h2h_1":"2026-11-15 | A 2-2 B",
                                 "h2h_2":"2026-11-14 | B 1-1 A","h2h_3":"2026-11-13 | A 1-0 B",
                                 "h2h_count":3,"status":"COMPLETE"})
            baseline = self.run_model((2.5, 2.5))
            enriched = self.run_model((2.5, 2.5), h2h_csv=path)
            self.assertEqual(baseline, {k:v for k,v in enriched.items() if k != "h2h_external"})
            self.assertEqual(enriched["h2h_external"]["count"], 3)

    def test_full_calendar(self):
        with patch('megatron.goals.evaluate',return_value={'status':'PASS'}) as evaluate:
            r=goals.screen([self.fixture,self.fixture],at=self.at)
        self.assertEqual(evaluate.call_count,2)
        self.assertEqual(len(r['results']),2)
