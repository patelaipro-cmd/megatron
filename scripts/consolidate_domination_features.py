"""Consolidate experimental pre-2008 V1 features without modifying frozen EXP-009.

Refuse duplicates, missing rows, mismatched league-seasons, post-2008 data and
overlap with frozen EXP-009. Outputs a reproducible CSV and audit JSON.
"""
from __future__ import annotations
import argparse,csv,hashlib,json
from pathlib import Path

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--plan',type=Path,required=True)
    p.add_argument('--batch-dir',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    plan=json.loads(a.plan.read_text(encoding='utf-8'))
    eligible=[r for r in plan['eligible_full_seasons'] if int(r['season'][:4])<2008]
    with open('docs/experiences/EXP-009/variables.csv',newline='',encoding='utf-8') as f:
        frozen={r['match_id'] for r in csv.DictReader(f)}
    combined=[]; seen=set(); fields=None
    for item in eligible:
        division,season=item['division'],item['season']
        path=a.batch_dir/f"{division}_{season.replace('/','-')}.csv"
        if not path.is_file():
            raise FileNotFoundError(f'Missing eligible league-season: {path}')
        with path.open(newline='',encoding='utf-8') as f:
            reader=csv.DictReader(f)
            if fields is None: fields=reader.fieldnames
            if reader.fieldnames!=fields: raise ValueError(f'Schema mismatch: {path}')
            rows=list(reader)
        if len(rows)!=item['matches']: raise ValueError(f'Incomplete league-season: {path}')
        for row in rows:
            mid=row['match_id']
            if mid in seen or mid in frozen: raise ValueError(f'Duplicate or frozen overlap: {mid}')
            if row['division']!=division or row['saison']!=season:
                raise ValueError(f'League-season mismatch: {mid}')
            seen.add(mid)
            combined.append(row)
    expected=sum(x['matches'] for x in eligible)
    if len(combined)!=expected: raise AssertionError('Incomplete batch consolidation')
    combined.sort(key=lambda r:r['match_id'])
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=fields)
        writer.writeheader()
        writer.writerows(combined)
    digest=hashlib.sha256(a.output.read_bytes()).hexdigest()
    report={'status':'experimental_only','pre2008_seasons':len(eligible),
            'pre2008_matches':len(combined),'sha256':digest,
            'frozen_overlap':0,'duplicate_ids':0,
            'excludes_2026_27':True,'model_promoted':False}
    a.output.with_suffix('.audit.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report))

if __name__=='__main__':main()
