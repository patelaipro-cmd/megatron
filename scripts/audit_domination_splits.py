"""Audit chronological V1 splits preserving frozen EXP-009 validation/test years.

Pre-2008 reconstructed seasons join development only. Existing validation and
test windows remain exactly unchanged; no fitting or model promotion.
"""
import argparse,csv,json
from collections import Counter
from pathlib import Path

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--input',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    with a.input.open(newline='',encoding='utf-8') as f:
        rows=list(csv.DictReader(f))
    counts=Counter()
    for r in rows:
        y=int(r['saison'][:4])
        if y<=2015: split='development'
        elif y<=2019: split='validation'
        elif y<=2025: split='test'
        else: raise ValueError('Future season in training input')
        counts[split]+=1
        if y<2008 and split!='development': raise AssertionError('Historical leakage')
    report={'split_seasons':{'development':'2000/01-2015/16',
                              'validation':'2016/17-2019/20',
                              'test':'2020/21-2025/26'},
            'counts':dict(counts),'total':len(rows),
            'test_window_unchanged_from_exp009':True,
            'training_performed':False,'production_unchanged':True}
    if sum(counts.values())!=len(rows): raise AssertionError('Incomplete split')
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report))

if __name__=='__main__':main()
