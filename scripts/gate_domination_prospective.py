"""Fail-closed experimental V1 promotion gate.

Retrospective evidence alone never permits production promotion.
"""
import argparse,json
from pathlib import Path

LEVELS=('victoire_par_2_ou_plus','victoire_par_3_ou_plus')

def evaluate(audit,prospective=None):
    result={'decision':'NO_GO','reasons':[],'levels':{}}
    if audit.get('scope')!='retrospective_test_only':
        result['reasons'].append('unexpected_historical_audit_scope')
    result['reasons'].append('historical_replay_is_not_prospective_validation')
    for level in LEVELS:
        leagues=audit.get('levels',{}).get(level,{})
        insufficient=[name for name,d in leagues.items() if d.get('insufficient_p60_sample',True)]
        result['levels'][level]={'league_count':len(leagues),
                                 'insufficient_p60_leagues':insufficient,
                                 'historical_p60_n':sum(d.get('p60_n',0) for d in leagues.values())}
        if insufficient:result['reasons'].append(level+':insufficient_per_league_p60')
    if prospective is None:
        result['reasons'].append('no_immutable_pre_kickoff_prospective_registry')
    else:
        result['reasons'].append('prospective_data_not_yet_independently_audited')
    return result

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--audit',required=True,type=Path)
    p.add_argument('--output',required=True,type=Path)
    a=p.parse_args()
    report=evaluate(json.loads(a.audit.read_text()))
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
    assert report['decision']=='NO_GO'
    print(json.dumps(report,ensure_ascii=False))
if __name__=='__main__':main()
