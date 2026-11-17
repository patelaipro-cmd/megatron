"""Generate V1 pre-match features for one *previously uncovered* league-season.

Experimental only. Reuses EXP-009's historical, strictly earlier-day Maher fitting.
Does not overwrite frozen EXP-009 variables.csv or train/promote any model.

Example:
  PYTHONPATH=. python scripts/extend_domination_features.py --division E0 --season 2007/08 --output artifacts/domination_v1/E0_2007-08.csv
"""
from __future__ import annotations
import argparse
import csv
from pathlib import Path
from scripts.exp009_angles import _job, LIGUES
from megatron import data
from megatron.data import season_of

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--division',required=True,choices=LIGUES)
    p.add_argument('--season',required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--allow-empty',action='store_true',help='skip unavailable league-season with explicit status')
    a=p.parse_args()
    existing=set()
    with open('docs/experiences/EXP-009/variables.csv',newline='',encoding='utf-8') as f:
        existing={r['match_id'] for r in csv.DictReader(f)}
    target=[m for m in data.load(data.CURRENT,divisions={a.division}) if season_of(m.day)==a.season]
    if not target:
        if a.allow_empty:
            print(f'SKIP no historical matches: {a.division} {a.season}')
            return
        raise ValueError('No matches in selected league-season')
    if any(m.match_id in existing for m in target):
        raise ValueError('Selected season overlaps frozen EXP-009 features; refusing to overwrite')
    rows=_job((a.division,a.season))
    expected={m.match_id for m in target}
    produced=[r['match_id'] for r in rows]
    if len(produced)!=len(set(produced)) or set(produced)!=expected:
        raise AssertionError('Incomplete or duplicate generated features')
    if any(r['match_id'] in existing for r in rows):
        raise AssertionError('Overlap with frozen features')
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f'generated {len(rows)} strict-prior-day prematch features for {a.division} {a.season}')
    print('EXPERIMENTAL; no model trained or deployed')

if __name__=='__main__':
    main()
