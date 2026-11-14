"""Read-only checks of frozen model outputs and optional Hive equivalence queries."""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import json
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score, average_precision_score, brier_score_loss, confusion_matrix


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project',type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument('--hive',action='store_true')
    args=parser.parse_args()
    project=args.project.resolve()
    final=project/'results/final_test'
    checks=[]
    def check(condition,label):
        if not condition:
            raise RuntimeError(label)
        checks.append(label)
        print('PASS:',label,flush=True)
    manifest=json.loads((final/'evaluation_manifest.json').read_text())
    for relative,expected in manifest['file_sha256'].items():
        digest=hashlib.sha256((project/relative).read_bytes()).hexdigest()
        check(digest==expected,'Frozen fingerprint: '+relative)
    split_ids=[]
    for split,count in [('train',143892),('validation',71955),('test',90615)]:
        frame=pd.read_csv(project/f'data/features/{split}.csv',dtype={'loan_id':'string'})
        check(len(frame)==count and frame.loan_id.notna().all() and frame.loan_id.is_unique,split+' IDs and count')
        check(frame.data_split.eq(split).all() and frame.target.isin([0,1]).all(),split+' labels')
        check(frame[manifest['features']].notna().all().all(),split+' nonmissing features')
        split_ids.append(set(frame.loan_id))
    check(all(not split_ids[a]&split_ids[b] for a,b in [(0,1),(0,2),(1,2)]),'No loan-ID overlap between splits')
    saved=pd.read_csv(final/'test_metrics.csv').set_index('model')
    reference=None
    for name,filename in [('Logistic Regression','logistic_regression_predictions.csv'),('LightGBM','lightgbm_predictions.csv')]:
        frame=pd.read_csv(final/filename).sort_values('loan_id').reset_index(drop=True)
        identifiers=frame[['loan_id','target','home_ownership_group']]
        if reference is None:
            reference=identifiers
        else:
            pd.testing.assert_frame_equal(reference,identifiers)
        y=frame.target.to_numpy(); p=frame.probability.to_numpy(); pred=frame.prediction.to_numpy()
        check(np.array_equal(pred,(p>=manifest['selected_thresholds'][name]).astype(int)),name+' threshold')
        values=dict(roc_auc=roc_auc_score(y,p),average_precision=average_precision_score(y,p),brier_score=brier_score_loss(y,p))
        tn,fp,fn,tp=confusion_matrix(y,pred,labels=[0,1]).ravel()
        values.update(chargeoff_recall=tp/(tp+fn),false_positive_rate=fp/(fp+tn),f1=2*tp/(2*tp+fp+fn))
        check(all(np.isclose(value,saved.loc[name,key],atol=1e-12) for key,value in values.items()),name+' saved prediction metrics')
    if args.hive:
        from impala.dbapi import connect
        connection=connect(host='localhost',port=10000,user='hive',database='credit_risk',auth_mechanism='PLAIN',timeout=600)
        try:
            cursor=connection.cursor()
            try:
                cursor.execute('SET hive.query.results.cache.enabled=false')
            finally:
                cursor.close()
            for relative in ['sql/04_verify_raw_orc.sql','sql/06_verify_orc_features.sql','sql/08_verify_prepared_orc.sql']:
                print('Running',relative,flush=True)
                cursor=connection.cursor()
                try:
                    cursor.execute((project/relative).read_text().strip().rstrip(';'))
                    check(cursor.fetchone()[0]==0,'Hive complete-row equivalence: '+relative)
                finally:
                    cursor.close()
        finally:
            connection.close()
    destination=project/'results/reproducibility'/('verification_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S_%fZ')+'.json')
    destination.parent.mkdir(parents=True,exist_ok=True)
    destination.write_text(json.dumps(dict(status='passed',hive_checked=args.hive,checks=checks),indent=2))
    print('Saved:',destination)


if __name__=='__main__':
    main()
