"""Build a strictly audited experimental V1 feature dataset.

The pre-2008 reconstruction is merged with frozen EXP-009 without modifying it.
This stage prepares training data; it does not fit or promote a model.
"""
import argparse,csv,hashlib,json
from pathlib import Path
from megatron import data
from megatron.data import season_of

def read(path):
    with path.open(newline='',encoding='utf-8') as f:
        reader=csv.DictReader(f)
        return reader.fieldnames,list(reader)

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--historical',type=Path,required=True)
    p.add_argument('--frozen',type=Path,default=Path('docs/experiences/EXP-009/variables.csv'))
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    old_fields,old=read(a.historical)
    new_fields,new=read(a.frozen)
    if old_fields!=new_fields: raise ValueError('Schema mismatch between historical and frozen features')
    all_rows=old+new
    ids=[r['match_id'] for r in all_rows]
    if len(ids)!=len(set(ids)): raise ValueError('Duplicate match IDs')
    scores={m.match_id:m for m in data.load(data.CURRENT)}
    if set(ids)-scores.keys(): raise ValueError('Feature rows without historical match scores')
    if any(int(r['saison'][:4])>=2026 for r in all_rows):
        raise ValueError('2026/27 must remain excluded from experimental training')
    if any(season_of(scores[r['match_id']].day)!=r['saison'] for r in all_rows):
        raise ValueError('Season mismatch')
    if len(old)!=len(set(r['match_id'] for r in old)): raise ValueError('Duplicate historical rows')
    if len(new)!=32544: raise ValueError('Frozen EXP-009 unexpectedly changed size')
    all_rows.sort(key=lambda r:(scores[r['match_id']].day,r['match_id']))
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=new_fields)
        writer.writeheader()
        writer.writerows(all_rows)
    audit={'status':'training_input_only','historical_pre2008':len(old),'frozen_exp009':len(new),
           'combined':len(all_rows),'score_matches':len(scores),'missing_scores':0,
           'duplicate_ids':0,'sha256':hashlib.sha256(a.output.read_bytes()).hexdigest(),
           'no_2026_27':True,'trained':False,'promoted':False}
    a.output.with_suffix('.audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    print(json.dumps(audit))

if __name__=='__main__':main()
