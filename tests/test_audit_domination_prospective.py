"""Regression tests for the read-only V1 prospective auditor."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from megatron.store import MemoryStore

ROOT=Path(__file__).resolve().parents[1]

class ProspectiveAuditTests(unittest.TestCase):
    def test_pre_kickoff_and_post_kickoff_are_separated(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            store=MemoryStore(root/'memoire')
            kickoff='2026-11-10T15:00:00+00:00'
            for suffix,when in [('valid','2026-11-10T14:00:00+00:00'),
                                ('late','2026-11-10T15:01:00+00:00')]:
                mid=f'E0:2026-11-10:Home-{suffix}'
                store.record('performances',f'pred:{mid}:H_MARGE_2PLUS:v1',
                    {'match_id':mid,'kickoff':kickoff,'market':'H_MARGE_2PLUS',
                     'data_cutoff':'2026-11-10T13:00:00+00:00',
                     'probs':{'oui':0.7,'non':0.3}},source='fixture',
                    recorded_at=when,supersede=False)
                store.record('performances',f'result:{mid}',
                    {'match_id':mid,'outcome':'H','score':[3,0]},
                    source='two independent sources',
                    recorded_at='2026-11-10T17:00:00+00:00',
                    observed_at='2026-11-10T17:00:00+00:00')
            out=root/'audit.json'
            proc=subprocess.run([sys.executable,str(ROOT/'scripts/audit_domination_prospective.py'),
                '--registre',str(root/'memoire'),'--output',str(out)],
                cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(proc.returncode,0,proc.stderr)
            report=json.loads(out.read_text())
            self.assertEqual(report['decision'],'NO_GO')
            self.assertEqual(report['exclusions']['temporal_violation'],1)
            group=report['groups']['E0:margin_2']
            self.assertEqual(group['resolved_n'],1)
            self.assertEqual(group['p60_n'],1)
            self.assertEqual(group['p60_wins'],1)
            self.assertTrue(group['p60_insufficient'])

if __name__=='__main__':
    unittest.main()
