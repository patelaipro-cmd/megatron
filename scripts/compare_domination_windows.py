"""Experimental temporal-window sensitivity for V1 margin 2+.

Choose the candidate ONLY by validation loss; report the untouched test
after selection. No model promotion and no optimization on test.
"""
import argparse,json,shutil
from pathlib import Path
from scripts.exp009_angles import evaluer

WINDOW_STARTS=(2004,2008,2010)

def seasons(start):
    return {f'{y}/{str(y+1)[-2:]}' for y in range(start,2016)}

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--expanded',type=Path,required=True)
    p.add_argument('--output-dir',type=Path,required=True)
    a=p.parse_args()
    a.output_dir.mkdir(parents=True,exist_ok=True)
    runs=[]
    for start in WINDOW_STARTS:
        dest=a.output_dir/f'from_{start}'
        dest.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(a.expanded,dest/'variables.csv')
        results=evaluer(dest,dev_seasons=seasons(start))
        margin=results['questions']['ecart']
        runs.append({'train_start':start,'train_end':2015,
                     'validation_log_loss_2plus':margin['validation']['log_loss_A'],
                     'test_log_loss_2plus':margin['test']['log_loss_A'],
                     'coefficients':margin['A']})
    winner=min(runs,key=lambda r:(r['validation_log_loss_2plus'],-r['train_start']))
    report={'status':'experimental','selection_metric':'validation_log_loss_2plus',
            'selected_start':winner['train_start'],
            'test_not_used_for_selection':True,
            'candidates':runs,'production_unchanged':True,
            'warning':'Selection is exploratory; 3+ requires separate target and sufficient sample'}
    (a.output_dir/'window_comparison.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'selected_start':winner['train_start'],
                      'validation':winner['validation_log_loss_2plus'],
                      'test':winner['test_log_loss_2plus'],
                      'candidate_windows':len(runs)}))

if __name__=='__main__':main()
