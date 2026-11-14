"""Replay model training with reconstructed features aligned to frozen export row order."""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import json
import shutil
import subprocess
import sys
import numpy as np
import pandas as pd

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--features-dir',type=Path,required=True,help='Feature directory produced by the isolated Hive replay')
    parser.add_argument('--project',type=Path,default=Path(__file__).resolve().parents[1])
    args=parser.parse_args()
    project=args.project.resolve()
    output=project/'results/reproducibility'/('ordered_models_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S_%fZ'))
    (output/'data/features').mkdir(parents=True,exist_ok=False)
    (output/'src').mkdir()
    manifest=dict(status='running',features_source=str(args.features_dir.resolve()),row_order='Original frozen export IDs; reconstructed values',models_refitted_in_isolation=True)
    destination=output/'replay_manifest.json'
    def save():
        destination.write_text(json.dumps(manifest,indent=2))
    save()
    try:
        for split in ['train','validation','test']:
            original=pd.read_csv(project/f'data/features/{split}.csv',dtype={'loan_id':'string'})
            rebuilt=pd.read_csv(args.features_dir/f'{split}.csv',dtype={'loan_id':'string'})
            if not rebuilt.loan_id.is_unique:
                raise RuntimeError('Duplicate reconstructed IDs.')
            ordered=rebuilt.set_index('loan_id').loc[original.loan_id].reset_index()[original.columns]
            pd.testing.assert_frame_equal(original,ordered,rtol=1e-12,atol=1e-12)
            ordered.to_csv(output/f'data/features/{split}.csv',index=False)
        scripts=['train_baseline.py','compare_thresholds.py','select_baseline_threshold.py','train_lightgbm.py','audit_validation_groups.py','evaluate_final_test.py']
        for name in scripts:
            shutil.copyfile(project/'src'/name,output/'src'/name)
        for name in scripts:
            print('Ordered replay: '+name,flush=True)
            process=subprocess.run([sys.executable,str(output/'src'/name)],cwd=output,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
            (output/(name+'.log')).write_text(process.stdout,encoding='utf-8')
            process.check_returncode()
        old=pd.read_csv(project/'results/final_test/test_metrics.csv').set_index('model')
        new=pd.read_csv(output/'results/final_test/test_metrics.csv').set_index('model').loc[old.index]
        keys=['threshold','accuracy','precision','chargeoff_recall','false_positive_rate','f1','roc_auc','average_precision','brier_score']
        comparison=old[keys].join(new[keys],lsuffix='_reported',rsuffix='_replay')
        comparison.to_csv(output/'reported_vs_replay.csv')
        manifest['maximum_absolute_metric_difference']=float(np.max(np.abs(old[keys].to_numpy()-new[keys].to_numpy())))
        manifest['metrics_match_at_1e_10']=bool(np.allclose(old[keys],new[keys],atol=1e-10,rtol=0))
        manifest['status']='completed'
        save()
        print(new[keys].round(6).to_string(),flush=True)
        print('Maximum absolute metric difference:',manifest['maximum_absolute_metric_difference'],flush=True)
        print('Saved:',output,flush=True)
    except Exception as exc:
        manifest.update(status='failed',error=str(exc)); save()
        raise

if __name__=='__main__':
    main()
