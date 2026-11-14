"""Rebuild Hive features in a new namespace; optionally replay models in an isolated folder."""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import csv
import hashlib
import json
import re
import shutil
import subprocess
import sys
import time

import numpy as np
import pandas as pd
from impala.dbapi import connect


def split_sql(text):
    # The saved project SQL has quoted delimiters but no procedural blocks.
    parts=[]; current=[]; quote=None; i=0
    while i<len(text):
        char=text[i]
        if quote:
            current.append(char)
            if char=='\\' and i+1<len(text):
                i+=1; current.append(text[i])
            elif char==quote:
                if i+1<len(text) and text[i+1]==quote:
                    i+=1; current.append(text[i])
                else:
                    quote=None
        elif char in "'\"`":
            quote=char; current.append(char)
        elif char==';':
            if ''.join(current).strip():
                parts.append(''.join(current).strip())
            current=[]
        else:
            current.append(char)
        i+=1
    if quote:
        raise ValueError('Unclosed SQL quote.')
    if ''.join(current).strip():
        parts.append(''.join(current).strip())
    return parts


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project',type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument('--train',action='store_true',help='Replay modelling and final evaluation in the new replay folder')
    args=parser.parse_args()
    project=args.project.resolve()
    stamp=datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f')
    database='credit_risk_replay_'+stamp
    root='/credit-risk/replays/'+stamp
    output=project/'results/reproducibility'/('replay_'+stamp)
    output.mkdir(parents=True,exist_ok=False)
    (output/'sql').mkdir()
    (output/'data/features').mkdir(parents=True)
    record=dict(database=database,hdfs_root=root,status='running',steps=[],source_project=str(project),
                note='Isolated replay; published models/results are not replaced. Training order may affect fitted models.')
    def save():
        (output/'replay_manifest.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
    save()
    def compose(*arguments,**kwargs):
        return subprocess.run(['docker','compose','exec','-T','namenode','hdfs',*arguments],
                              cwd=project/'infrastructure',check=True,**kwargs)
    source=project/'data/cohort/credit_cohort.csv'
    if not source.is_file():
        raise FileNotFoundError('Run src/build_cohort.py first.')
    record['cohort_sha256']=hashlib.sha256(source.read_bytes()).hexdigest()
    # Unique directories only. Existing HDFS tables are never overwritten.
    compose('dfs','-mkdir','-p',root+'/raw',root+'/warehouse')
    with source.open('rb') as stream:
        compose('dfs','-put','-',root+'/raw/credit_cohort.csv',stdin=stream)
    compose('dfs','-chown','-R','hive',root)

    connection=connect(host='localhost',port=10000,user='hive',database='default',auth_mechanism='PLAIN',timeout=600)
    def execute(sql,label,fetch=False):
        cursor=connection.cursor()
        try:
            print(label,flush=True)
            start=time.perf_counter()
            cursor.execute(sql)
            rows=cursor.fetchall() if fetch else None
            record['steps'].append(dict(label=label,seconds=time.perf_counter()-start))
            save()
            return rows
        finally:
            cursor.close()
    def adapt(sql):
        sql=sql.replace('`credit_risk`',f'`{database}`')
        sql=re.sub(r'\bcredit_risk\.',database+'.',sql)
        sql=sql.replace('hdfs://namenode:8020/credit-risk/raw/cohort',root+'/raw')
        sql=sql.replace('hdfs://namenode:8020/warehouse/external/',root+'/warehouse/')
        sql=sql.replace("'/warehouse/external/","'"+root+'/warehouse/')
        return sql
    def run_file(path):
        sql=adapt(path.read_text(encoding='utf-8'))
        (output/'sql'/path.name).write_text(sql,encoding='utf-8')
        for i,statement in enumerate(split_sql(sql),1):
            execute(statement,f'{path.name}: statement {i}')
    try:
        execute(f"CREATE DATABASE {database} LOCATION '{root}/warehouse'",'Create isolated replay database')
        execute('SET hive.query.results.cache.enabled=false','Disable result cache')
        snapshot=project/'results/hive_snapshot/20261108_110652'
        run_file(snapshot/'raw_credit.sql')
        run_file(project/'sql/02_typed_credit.sql')
        run_file(snapshot/'preprocessing_stats.sql')
        stats_sql=f'''INSERT OVERWRITE TABLE {database}.preprocessing_stats
SELECT COUNT(*) AS training_rows,
       PERCENTILE_APPROX(CAST(employment_years AS DOUBLE), 0.5, 10000) AS employment_fill,
       PERCENTILE_APPROX(revolving_utilization, 0.5, 10000) AS utilization_fill
FROM {database}.typed_credit WHERE data_split='train' '''
        (output/'sql/recompute_training_stats.sql').write_text(stats_sql+';')
        execute(stats_sql,'Recompute imputation statistics using training rows only')
        observed=execute(f'SELECT * FROM {database}.preprocessing_stats','Read replay training statistics',True)[0]
        expected=json.loads((snapshot/'preprocessing_stats_values.json').read_text())[0]
        record['training_statistics']=dict(zip(['training_rows','employment_fill','utilization_fill'],observed))
        if not np.allclose(np.array(observed,dtype=float),[expected['training_rows'],expected['employment_fill'],expected['utilization_fill']],rtol=0,atol=1e-10):
            raise RuntimeError(f'Recomputed training statistics differ: {observed}. Replay stopped; originals unchanged.')
        run_file(snapshot/'model_features.sql')
        for filename in ['03_raw_credit_orc.sql','05_orc_feature_views.sql','07_prepared_orc_features.sql']:
            run_file(project/'sql'/filename)
        for filename in ['04_verify_raw_orc.sql','06_verify_orc_features.sql','08_verify_prepared_orc.sql']:
            sql=adapt((project/'sql'/filename).read_text()).strip().rstrip(';')
            if execute(sql,'Replay equivalence: '+filename,True)[0][0]!=0:
                raise RuntimeError('Replay pipeline equivalence failed.')
        # Export in a stable order for the new replay; original experiments are unchanged.
        for split,expected_count in [('train',143892),('validation',71955),('test',90615)]:
            cursor=connection.cursor()
            try:
                print('Exporting replay '+split,flush=True)
                cursor.execute(f"SELECT * FROM {database}.model_features WHERE data_split='{split}' ORDER BY loan_id")
                columns=[item[0].rsplit('.',1)[-1] for item in cursor.description]
                destination=output/f'data/features/{split}.csv'
                count=0
                with destination.open('w',newline='',encoding='utf-8') as handle:
                    writer=csv.writer(handle); writer.writerow(columns)
                    while True:
                        batch=cursor.fetchmany(10000)
                        if not batch:
                            break
                        writer.writerows(batch); count+=len(batch)
                if count!=expected_count:
                    raise RuntimeError('Unexpected replay split count.')
            finally:
                cursor.close()
            original=pd.read_csv(project/f'data/features/{split}.csv',dtype={'loan_id':'string'}).sort_values('loan_id').reset_index(drop=True)
            replay=pd.read_csv(destination,dtype={'loan_id':'string'}).sort_values('loan_id').reset_index(drop=True)
            pd.testing.assert_frame_equal(original,replay,check_exact=False,rtol=1e-12,atol=1e-12)
            print(f'{split}: {count:,} rows; every exported value matches original.',flush=True)
        record['feature_replay_passed']=True
    except Exception as exc:
        record.update(status='failed',error=str(exc)); save()
        raise
    finally:
        connection.close()

    if args.train:
        (output/'src').mkdir()
        scripts=['train_baseline.py','compare_thresholds.py','select_baseline_threshold.py','train_lightgbm.py',
                 'audit_validation_groups.py','evaluate_final_test.py','bootstrap_test_results.py']
        for name in scripts:
            shutil.copyfile(project/'src'/name,output/'src'/name)
        try:
            for name in scripts[:-1]:
                print('Replaying modelling step: '+name,flush=True)
                result=subprocess.run([sys.executable,str(output/'src'/name)],cwd=output,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
                (output/(name+'.log')).write_text(result.stdout,encoding='utf-8')
                print(result.stdout,flush=True)
                result.check_returncode()
            original=pd.read_csv(project/'results/final_test/test_metrics.csv')
            replay=pd.read_csv(output/'results/final_test/test_metrics.csv')
            comparison=original.merge(replay,on='model',suffixes=('_reported','_replay'))
            comparison.to_csv(output/'reported_vs_replay_models.csv',index=False)
            record['model_replay_passed']=True
            record['model_note']='Rerun completed with fixed algorithm/threshold-selection rules; bit-identical fitted predictions are not required.'
        except Exception as exc:
            record.update(status='failed',error=str(exc)); save()
            raise
    record['status']='completed'; save()
    print(f'REPLAY COMPLETE: {output}',flush=True)
    print('Isolated Hive database:',database,flush=True)
    print('Published results and models were not replaced.',flush=True)


if __name__=='__main__':
    main()
