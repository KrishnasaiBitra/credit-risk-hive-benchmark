"""Compare all four website predictions with the saved native experiment models."""
import argparse
from pathlib import Path
import json
import urllib.error
import urllib.request
import joblib
import numpy as np
import pandas as pd
from .common import read_json, sha, write_json


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--url',required=True)
    p.add_argument('--project',type=Path,required=True)
    p.add_argument('--run',type=Path,required=True)
    a=p.parse_args();checks=[]
    def check(ok,label):
        assert ok,label
        checks.append(label);print('PASS:',label,flush=True)
    def request(path,value=None,expected=200):
        req=urllib.request.Request(a.url+path,data=json.dumps(value).encode() if value is not None else None,headers={'Content-Type':'application/json'} if value is not None else {})
        try:
            with urllib.request.urlopen(req,timeout=120) as r:
                raw=r.read();return json.loads(raw) if r.headers.get('Content-Type','').startswith('application/json') else raw
        except urllib.error.HTTPError as e:
            if e.code==expected:return json.loads(e.read())
            raise AssertionError(f'{path}: {e.code}: {e.read().decode()}')
    html=request('/').decode()
    check('href="#extensions"' in html,'Nine routes include the model extension')
    summary=request('/api/extensions')
    check(len(summary['models'])==5,'Dummy plus four predictive models')
    saved=read_json(a.run/'evaluation/comparison.json')
    check(summary['models']==saved['models'],'Displayed metrics exactly match saved evaluation')
    comparison=request('/api/model-comparison')
    check(comparison['models']==summary['models'],'Unified comparison retains all exact model scores')
    check(len(comparison['curves'])==4 and len({r['model'] for r in comparison['curves']})==4,'Four distinct ROC/PR curves')
    for row in comparison['models']:
        check(sum(row[k] for k in ['true_negatives','false_positives','false_negatives','true_positives'])==90615,'Confusion matrix count: '+row['model'])
    references=comparison['references']
    check(len(references['scores'])==7,'Three published rows plus four project rows')
    paper=[r for r in references['scores'] if r['source']!='Our project']
    check({r['model'] for r in paper}=={'Random Forest','LightGBM','XGBoost'},'Published algorithms correctly attributed')
    check(next(r for r in paper if r['model']=='LightGBM')['roc_auc']==0.8981,'Published LightGBM AUC unchanged')
    check(all(r['threshold'] is None for r in paper),'Unknown paper thresholds remain missing')
    original=read_json(a.project/'results/final_test/evaluation_manifest.json')
    models={name:joblib.load(a.project/'models'/file) for name,file in [('Logistic Regression','logistic_regression.joblib'),('LightGBM','lightgbm.joblib')]}
    models.update({read_json(a.run/k/'selection.json')['model']:joblib.load(a.run/k/'model.joblib') for k in ['catboost','arf']})
    selections={read_json(a.run/k/'selection.json')['model']:read_json(a.run/k/'selection.json')['selected_threshold'] for k in ['catboost','arf']}
    selections.update(original['selected_thresholds'])
    examples=request('/api/demo/examples')
    cases=[(e['id'],e['inputs']) for e in examples]
    missing={**examples[0]['inputs'],'employment_years':None,'revolving_utilization':None}
    cases.append(('missing optional values',missing))
    for label,inputs in cases:
        result=request('/api/predict',inputs)
        check(len(result['results'])==4,'Four predictions: '+label)
        frame=pd.DataFrame([result['features']],columns=original['features'])
        for row in result['results']:
            expected=float(models[row['model']].predict_proba(frame)[0,1])
            check(abs(row['probability']-expected)<1e-10,'Native probability: '+row['model']+' / '+label)
            check(row['threshold']==selections[row['model']] and row['flagged']==(expected>=row['threshold']),'Model-specific threshold: '+row['model'])
    check(selections['Adaptive Random Forest']==0.125,'ARF threshold is 12.5%, not 15%')
    for changes in [{'annual_income':-1},{'fico_range_low':800,'fico_range_high':700},{'purpose':'invalid'}]:
        request('/api/predict',{**examples[0]['inputs'],**changes},expected=422)
    check(True,'Invalid input rejected')
    downloads=request('/api/downloads')
    check(len(downloads)==14 and all(d['available'] for d in downloads),'14 real downloads')
    for d in downloads:
        check(bool(request('/api/download/'+d['id'])),'Download '+d['id'])
    for file,expected in original['file_sha256'].items():
        check(sha(a.project/file)==expected,'Original artifact unchanged: '+file)
    write_json(a.run/'site_verification.json',dict(status='passed',url=a.url,checks=checks))


if __name__=='__main__':main()
