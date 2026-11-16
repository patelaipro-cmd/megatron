"""Discover available, uncovered league-seasons for experimental V1 reconstruction.

Read-only planning: only seasons whose *entire* league-season is absent from the
frozen EXP-009 feature set are eligible for this first extension. Mixed seasons
are flagged and not silently skipped or overwritten.
"""
import argparse,csv,json
from collections import defaultdict
from pathlib import Path
from megatron import data
from megatron.data import season_of

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    with open('docs/experiences/EXP-009/variables.csv',newline='',encoding='utf-8') as f:
        existing={r['match_id'] for r in csv.DictReader(f)}
    groups=defaultdict(list)
    for m in data.load(data.CURRENT):
        groups[(m.division,season_of(m.day))].append(m.match_id)
    eligible=[]; mixed=[]; covered=[]
    for (division,season),ids in sorted(groups.items()):
        have=sum(mid in existing for mid in ids)
        row={'division':division,'season':season,'matches':len(ids),'already_featured':have}
        if have==0: eligible.append(row)
        elif have==len(ids): covered.append(row)
        else: mixed.append(row)
    report={'eligible_full_seasons':eligible,'mixed_seasons_manual_review':mixed,
            'already_covered_seasons':len(covered),
            'eligible_matches':sum(r['matches'] for r in eligible),
            'mixed_missing_matches':sum(r['matches']-r['already_featured'] for r in mixed),
            'warning':'No model fitting, no change to frozen EXP-009 features'}
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps({'eligible_seasons':len(eligible),'eligible_matches':report['eligible_matches'],
                      'mixed_seasons':len(mixed),'mixed_missing_matches':report['mixed_missing_matches']},ensure_ascii=False))
    print('eligible:',[(r['division'],r['season'],r['matches']) for r in eligible])

if __name__=='__main__':
    main()
