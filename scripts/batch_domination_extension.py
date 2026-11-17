"""Batch reconstruction of eligible pre-2008 V1 league-seasons.

Uses frozen EXP-009 as exclusion, historical rolling feature generator, and
writes only experimental artifacts. 2026/27 is explicitly excluded.
"""
import argparse,csv,json,subprocess,sys
from pathlib import Path

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--plan',type=Path,required=True)
    p.add_argument('--output-dir',type=Path,required=True)
    p.add_argument('--max-seasons',type=int,default=5)
    a=p.parse_args()
    plan=json.loads(a.plan.read_text())
    eligible=[r for r in plan['eligible_full_seasons'] if int(r['season'][:4])<2008]
    if not eligible: raise ValueError('No eligible historical seasons')
    if a.max_seasons<1: raise ValueError('max-seasons must be positive')
    selected=eligible[:a.max_seasons]
    summary=[]
    for r in selected:
        division,season=r['division'],r['season']
        path=a.output_dir/f"{division}_{season.replace('/','-')}.csv"
        subprocess.run([sys.executable,'scripts/extend_domination_features.py',
                        '--division',division,'--season',season,'--output',str(path)],check=True)
        with path.open(newline='',encoding='utf-8') as f:
            rows=list(csv.DictReader(f))
        if len(rows)!=r['matches']:
            raise AssertionError(f"count mismatch for {division} {season}")
        summary.append({'division':division,'season':season,'matches':len(rows),'path':str(path)})
    report={'selected_seasons':len(summary),'generated_matches':sum(r['matches'] for r in summary),
            'eligible_pre2008_seasons':len(eligible),'excluded_2026_27':True,
            'runs':summary,'production_unchanged':True}
    a.output_dir.mkdir(parents=True,exist_ok=True)
    (a.output_dir/'batch_summary.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))

if __name__=='__main__':main()
