"""Verify the live local interface against frozen research outputs (no retraining)."""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import json
import urllib.error
import urllib.request

import numpy as np
import pandas as pd


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url',default='http://127.0.0.1:8000')
    args=parser.parse_args()
    project=Path(__file__).resolve().parents[1]
    checks=[]
    def check(condition,label):
        if not condition:
            raise AssertionError(label)
        checks.append(label);print('PASS:',label,flush=True)
    def request(path,payload=None,expected=200):
        req=urllib.request.Request(args.url+path,data=json.dumps(payload).encode() if payload is not None else None,
                                   headers={'Content-Type':'application/json'} if payload is not None else {})
        try:
            response=urllib.request.urlopen(req,timeout=90)
        except urllib.error.HTTPError as error:
            if error.code==expected:
                return json.loads(error.read())
            raise AssertionError(f'{path}: HTTP {error.code}: {error.read().decode()}')
        with response:
            check(response.status==expected,'HTTP '+path)
            raw=response.read()
            return json.loads(raw) if response.headers.get('Content-Type','').startswith('application/json') else raw
    check(request('/api/health')['status']=='ok','Local artifact health')
    html=request('/').decode()
    check(all(f'href="#{page}"' in html for page in ['overview','architecture','pipelines','models','extensions','fairness','literature','demo','reports']),'Nine navigation routes')
    for path in ['/static/styles.css','/static/app.js','/static/architecture.js','/static/architecture.css','/static/vendor/plotly.min.js']:
        check(len(request(path))>100,'Local frontend asset '+path)
    research=request('/api/research')
    check(research['cohort']['rows']==306462 and research['cohort']['splits']['test']==90615,'Research cohort counts')
    check(len(research['pipelines'])==3 and all(row['runs']==5 for row in research['pipelines']),'Original five-run pipeline results')
    original=pd.read_csv(project/'results/final_test/test_metrics.csv').set_index('model')
    for model in research['models']:
        check(abs(model['roc_auc']-original.loc[model['model'],'roc_auc'])<1e-9,'Displayed ROC-AUC '+model['model'])
    curves=request('/api/curves')
    check(len(curves)==2 and all(2<=len(r['roc']['x'])<=1000 for r in curves),'Saved prediction curves')
    literature=request('/api/literature')
    check(len(literature['papers'])==2 and len(literature['scores'])==7,'Two papers and seven attributed model results')
    check(all(p['id']==p['doi'] and p['title'] for p in literature['papers']), 'Paper titles and DOI identifiers')
    check(all('DOI:' in r['source'] for r in literature['scores'] if r['source']!='Our project'), 'Published score labels use paper title and DOI')
    published=[r for r in literature['scores'] if r['source']!='Our project' and r['model']=='LightGBM'][0]
    check(published['roc_auc']==.8981 and published['f1']==.8111,'2025 Table V LightGBM transcription')
    for row in literature['scores']:
        if row['source']=='Our project' and row['model'] in original.index:
            check(abs(row['roc_auc']-original.loc[row['model'],'roc_auc'])<1e-12,'Literature comparison uses frozen score '+row['model'])
    schema=request('/api/demo/schema')
    examples=request('/api/demo/examples')
    check(len(examples)==6,'Six historical examples')
    predictions={name:pd.read_csv(project/'results/final_test'/filename,dtype={'loan_id':'string'}).set_index('loan_id')
                 for name,filename in [('LightGBM','lightgbm_predictions.csv'),('Logistic Regression','logistic_regression_predictions.csv')]}
    for example in examples:
        result=request('/api/predict',example['inputs'])
        check(len(result['features'])==19,'Exact feature count '+example['id'])
        for row in result['results']:
            if row['model'] not in predictions: continue  # New models are covered by model_extensions.verify_site.
            expected=predictions[row['model']].loc[example['id']]
            check(np.isclose(row['probability'],expected.probability,atol=1e-12,rtol=0),f'Historical probability: {row["model"]}, {example["id"]}')
            check(row['threshold']==.15 and int(row['flagged'])==int(expected.prediction),'Frozen flag: '+row['model'])
    payload={**examples[0]['inputs'],'employment_years':None,'revolving_utilization':None}
    result=request('/api/predict',payload)
    check(result['features']['employment_missing']==1 and result['features']['utilization_missing']==1,'Missingness flags')
    check(result['features']['employment_years']==schema['training_fills']['employment_fill'],'Frozen employment fill')
    check(result['features']['revolving_utilization']==schema['training_fills']['utilization_fill'],'Frozen utilization fill')
    for label,changes in [('negative income',{'annual_income':-1}),('reversed FICO',{'fico_range_low':800,'fico_range_high':700}),
                           ('unknown purpose',{'purpose':'not_a_real_purpose'}),('fractional count',{'open_accounts':1.5}),
                           ('unknown field',{'not_a_feature':42})]:
        request('/api/predict',{**examples[0]['inputs'],**changes},expected=422)
        checks.append('Rejected '+label);print('PASS: Rejected '+label,flush=True)
    downloads=request('/api/downloads')
    check(len(downloads)==14 and all(item['available'] for item in downloads),'Fourteen real downloads available')
    for item in downloads:
        content=request('/api/download/'+item['id'])
        check(bool(content),'Download '+item['id'])
        if item['id']=='report':
            check(content.startswith(b'%PDF'),'Actual PDF report')
    request('/api/download/not-a-file',expected=404)
    checks.append('Unknown file access rejected')
    manifest=json.loads((project/'results/final_test/evaluation_manifest.json').read_text())
    for relative,expected in manifest['file_sha256'].items():
        check(hashlib.sha256((project/relative).read_bytes()).hexdigest()==expected,'Unchanged artifact '+relative)
    output=project/'results/interface_checks'
    output.mkdir(parents=True,exist_ok=True)
    destination=output/(datetime.now(timezone.utc).strftime('api_%Y%m%dT%H%M%S_%fZ')+'.json')
    destination.write_text(json.dumps({'status':'passed','checks':checks,'url':args.url,'models_retrained':False},indent=2))
    print('Verification saved:',destination,flush=True)


if __name__=='__main__':
    main()
