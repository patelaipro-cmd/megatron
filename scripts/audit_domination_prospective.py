"""Read-only prospective V1 audit of existing immutable ledger entries.

Does not create predictions, change model weights or promote anything.
"""
import argparse,json,math
from collections import defaultdict
from pathlib import Path
from megatron.ledger import DOMAIN,market_of
from megatron.store import MemoryStore,parse_dt

MARKETS=('MARGE_2PLUS','MARGE_3PLUS')

def wilson(k,n):
    if not n:return None
    z=1.959963984540054
    p=k/n;d=1+z*z/n
    c=(p+z*z/(2*n))/d
    h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
    return [round(max(0,c-h),4),round(min(1,c+h),4)]

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--registre',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    store=MemoryStore(a.registre)
    entries=store.active(DOMAIN)
    results={e.value['match_id']:e for e in entries if e.key.startswith('result:')}
    groups=defaultdict(list)
    version_counts=defaultdict(int)
    predicted_counts=defaultdict(int)
    probability_bins=defaultdict(lambda: defaultdict(int))
    excluded=defaultdict(int)
    for e in entries:
        if not e.key.startswith('pred:'):continue
        v=e.value;market=market_of(v)
        if not any(market.endswith('_'+m) for m in MARKETS):continue
        league=v['match_id'].split(':',1)[0]
        margin=2 if market.endswith('MARGE_2PLUS') else 3
        predicted_counts[f'{league}:margin_{margin}']+=1
        version_counts[str(v.get('model_version','unknown'))]+=1
        kickoff=parse_dt(v['kickoff'])
        if parse_dt(e.recorded_at)>=kickoff or (v.get('data_cutoff') and parse_dt(v['data_cutoff'])>=kickoff):
            excluded['temporal_violation']+=1;continue
        mid=v['match_id'];res=results.get(mid)
        if res is None or not res.value.get('score'):
            excluded['no_verified_score']+=1;continue
        if not res.observed_at or parse_dt(res.observed_at)<=kickoff:
            excluded['result_not_after_kickoff']+=1;continue
        home,away=res.value['score']
        side=market.split('_',1)[0]
        if side not in ('H','A'):
            excluded['unknown_favorite_side']+=1;continue
        diff=(home-away) if side=='H' else (away-home)
        margin=2 if market.endswith('MARGE_2PLUS') else 3
        prob=v['probs']['oui']
        if not (0<=prob<=1):
            excluded['invalid_probability']+=1;continue
        groups[(league,margin)].append((prob,int(diff>=margin)))
    report={'decision':'NO_GO','source':'prospective_ledger_read_only',
            'exclusions':dict(excluded),'groups':{},'production_modified':False}
    all_margins=defaultdict(list)
    for (league,margin),rows in sorted(groups.items()):
        all_margins[margin].extend(rows)
        high=[(pr,y) for pr,y in rows if pr>=0.60]
        n=len(high);k=sum(y for _,y in high)
        bins={}
        for lower in range(0,100,10):
            subset=[(pr,y) for pr,y in rows if lower/100<=pr<(lower+10)/100 or (lower==90 and pr==1)]
            if subset:
                bins[f'{lower:02d}-{lower+10:02d}%']={
                    'n':len(subset),'observed':round(sum(y for _,y in subset)/len(subset),4),
                    'predicted':round(sum(pr for pr,_ in subset)/len(subset),4)}
        report['groups'][f'{league}:margin_{margin}']={
            'predictions_registered':predicted_counts[f'{league}:margin_{margin}'],
            'calibration_bins_10pct':bins,
            'probability_max':round(max(pr for pr,_ in rows),4),
            'probability_mean':round(sum(pr for pr,_ in rows)/len(rows),4),
            'resolved_n':len(rows),'observed_base_rate':round(sum(y for _,y in rows)/len(rows),4),
            'p60_n':n,'p60_wins':k,
            'p60_observed':round(k/n,4) if n else None,
            'p60_predicted':round(sum(pr for pr,_ in high)/n,4) if n else None,
            'p60_wilson95':wilson(k,n),'p60_insufficient':n<100,
            'brier':round(sum((pr-y)**2 for pr,y in rows)/len(rows),5),
            'log_loss':round(sum(-math.log(max(min(pr if y else 1-pr,1-1e-15),1e-15)) for pr,y in rows)/len(rows),5)}
    report['overall_by_margin']={}
    for margin,rows in sorted(all_margins.items()):
        high=[(p,y) for p,y in rows if p>=0.60]
        report['overall_by_margin'][str(margin)]={
            'resolved_n':len(rows),
            'observed_base_rate':round(sum(y for _,y in rows)/len(rows),4),
            'predicted_mean':round(sum(p for p,_ in rows)/len(rows),4),
            'p60_n':len(high),
            'p60_wins':sum(y for _,y in high),
            'p60_wilson95':wilson(sum(y for _,y in high),len(high))}
    report['model_versions']=dict(sorted(version_counts.items()))
    report['registered_predictions_by_group']=dict(sorted(predicted_counts.items()))
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'groups':len(groups),'exclusions':report['exclusions'],'decision':'NO_GO'}))
if __name__=='__main__':main()
