"""Read-only per-league confidence audit for frozen EXP-012 test results."""
import argparse,json,math
from pathlib import Path

def wilson(k,n):
    if not n:return None
    z=1.959963984540054
    p=k/n
    den=1+z*z/n
    c=(p+z*z/(2*n))/den
    h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return [round(max(0,c-h),4),round(min(1,c+h),4)]

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--input',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args()
    data=json.loads(args.input.read_text())
    report={'decision':'NO_GO','scope':'retrospective_test_only',
            'warning':'Small p60 subsets and repeated historical test do not justify promotion',
            'levels':{}}
    for level in ('victoire_par_2_ou_plus','victoire_par_3_ou_plus'):
        detail=data['niveaux'][level]['ligues_test_detail']
        report['levels'][level]={}
        for league,stats in sorted(detail.items()):
            zone=stats['tranche_p60']
            n=zone['n']
            k=round(zone['frequence']*n) if n else 0
            report['levels'][level][league]={
                'test_n':stats['n'],'test_log_loss':stats['log_loss'],
                'p60_n':n,'p60_successes':k,
                'p60_observed':zone['frequence'],'p60_predicted':zone['p_moyenne'],
                'p60_wilson95':wilson(k,n),
                'insufficient_p60_sample':n<100}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps(report['levels'],ensure_ascii=False))
if __name__=='__main__':main()
