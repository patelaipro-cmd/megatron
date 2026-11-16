"""Experimental refit of EXP-009 angles on expanded historical V1 features.

Keeps EXP-009 validation/test windows fixed and compares to frozen results.
This is NOT a standalone 3+ margin model, nor a production promotion.
"""
import argparse,json,shutil
from pathlib import Path
from scripts.exp009_angles import evaluer

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--expanded',type=Path,required=True)
    p.add_argument('--output-dir',type=Path,required=True)
    p.add_argument('--baseline',type=Path,default=Path('docs/experiences/EXP-009/resultats.json'))
    a=p.parse_args()
    a.output_dir.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(a.expanded,a.output_dir/'variables.csv')
    expanded=evaluer(a.output_dir, dev_seasons={f'{y}/{str(y+1)[-2:]}' for y in range(2000,2016)})
    report={'status':'experimental_refit','baseline_path':str(a.baseline),
            'development_period':'2000/01-2015/16','test_period_unchanged':True,'production_modified':False,
            'questions':{}}
    if a.baseline.is_file():
        baseline=json.loads(a.baseline.read_text(encoding='utf-8'))
        for q,new in expanded['questions'].items():
            old=baseline.get('questions',{}).get(q)
            if old:
                report['questions'][q]={
                    'test_log_loss_A_baseline':old['test']['log_loss_A'],
                    'test_log_loss_A_expanded':new['test']['log_loss_A'],
                    'delta_expanded_minus_baseline':round(new['test']['log_loss_A']-old['test']['log_loss_A'],6),
                    'validation_log_loss_A_baseline':old['validation']['log_loss_A'],
                    'validation_log_loss_A_expanded':new['validation']['log_loss_A'],
                    'delta_validation':round(new['validation']['log_loss_A']-old['validation']['log_loss_A'],6),
                    'baseline_coefficients_A':old['A'],
                    'expanded_coefficients_A':new['A'],
                    'coefficients_changed':old['A']!=new['A'],
                    'test_improved':new['test']['log_loss_A']<old['test']['log_loss_A'],
                    'validation_improved':new['validation']['log_loss_A']<old['validation']['log_loss_A']}
    else:
        report['baseline_missing']=True
    (a.output_dir/'comparison.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report))

if __name__=='__main__':main()
