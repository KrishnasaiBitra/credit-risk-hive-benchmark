"""Build a read-only comparison dashboard from recorded results; no model fitting."""
import argparse
import csv
import json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.metrics import roc_curve, precision_recall_curve
from .common import read_json, write_json


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--project',type=Path,required=True)
    p.add_argument('--run',type=Path,required=True)
    a=p.parse_args();project=a.project
    extension=read_json(project/'results/model_extensions/comparison.json')
    references=read_json(project/'results/literature_comparison/comparison.json')
    if (project/'interface/runtime/research.json').is_file():
        original=read_json(project/'interface/runtime/research.json')
        curves=read_json(project/'interface/runtime/curves.json')
    else:
        import importlib.util, sys
        spec=importlib.util.spec_from_file_location('_comparison_source',project/'interface/app.py')
        module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
        original=module.research();curves=module.curves()
    for key,name in [('catboost','CatBoost'),('arf','Adaptive Random Forest')]:
        frame=pd.read_csv(a.run/'evaluation'/f'{key}_predictions.csv')
        fpr,tpr,_=roc_curve(frame.target,frame.probability)
        precision,recall,_=precision_recall_curve(frame.target,frame.probability)
        def sample(x,y):
            indices=np.unique(np.linspace(0,len(x)-1,min(1000,len(x)),dtype=int))
            return dict(x=x[indices].tolist(),y=y[indices].tolist())
        curves.append(dict(model=name,roc=sample(fpr,tpr),pr=sample(recall,precision),prevalence=float(frame.target.mean())))
    paper_scores=[r for r in references['scores'] if r['source']!='Our project']
    own_scores=[]
    for row in extension['models']:
        if row['model']=='Dummy':continue
        own_scores.append(dict(source='Our project',model=row['model'],accuracy=row['accuracy'],recall=row['chargeoff_recall'],f1=row['f1'],roc_auc=row['roc_auc'],threshold=row['threshold'],
            evidence='results/model_extensions/model_comparison.csv' if row['model'] in {'CatBoost','Adaptive Random Forest'} else 'results/final_test/test_metrics.csv',
            provenance='Exploratory extension; reused historical holdout' if row['model'] in {'CatBoost','Adaptive Random Forest'} else 'Original frozen experiment; 90,615 test loans'))
    references['scores']=paper_scores+own_scores
    references['comparison_scope']='Original models plus CatBoost and Adaptive Random Forest extension; published results were not rerun.'
    for row in references['capabilities']:
        if row['aspect']=='Predictive models':row['ours']='Dummy baseline, Logistic Regression, LightGBM, CatBoost and Adaptive Random Forest; the last two are a separate exploratory extension.'
        if row['aspect']=='Class balance / decision rule':row['ours']='Original selected-cohort imbalance retained. Validation-selected thresholds: 0.15 (LR/LightGBM/CatBoost), 0.125 (Adaptive Random Forest).'
        if row['aspect']=='Quantitative group audit':row['ours']='MORTGAGE/RENT/OWN audits for all four predictive models; full metrics and gaps in results/model_extensions.'
    note='CatBoost and Adaptive Random Forest were proposed after the original test results were known; their historical holdout comparisons are exploratory, not fresh confirmatory tests.'
    if note not in references['cautions']:references['cautions'].append(note)
    write_json(project/'results/literature_comparison/comparison.json',references)
    with (project/'results/literature_comparison/reported_model_scores.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=list(references['scores'][0]),lineterminator='\n');writer.writeheader();writer.writerows(references['scores'])
    with (project/'results/literature_comparison/study_comparison.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=list(references['capabilities'][0]),lineterminator='\n');writer.writeheader();writer.writerows(references['capabilities'])
    payload=dict(models=extension['models'],curves=curves,test_rows=90615,positive_class='Charged Off',references=references,
                 paired_differences=original['paired_differences'],limitations=extension['limitations'],
                 phases={r['model']:('Exploratory extension' if r['model'] in {'CatBoost','Adaptive Random Forest'} else 'Original experiment') for r in extension['models']})
    write_json(project/'results/model_extensions/model_comparison_dashboard.json',payload)
    text='# Model comparison and reference-paper results\n\n'
    text+='This comparison records published scores alongside our experiments. It is not a matched replication. Paper scores were transcribed from Table V, PDF p. 6 of the 2025 reference paper. No new model training was performed to build this comparison.\n\n'
    text+='| Study | Model | Accuracy | Recall | F1 | ROC-AUC | Threshold | Evidence |\n|---|---|---|---|---|---|---|---|\n'
    for row in references['scores']:
        text+='| '+row['source']+' | '+row['model']+' | '+' | '.join(f'{row[k]:.4f}' for k in ['accuracy','recall','f1','roc_auc'])+' | '+('Not reported' if row['threshold'] is None else str(row['threshold']))+' | '+row['provenance']+' |\n'
    text+='\n## The 2017 reference\n\n'+references['papers'][0]['title']+'\n\nDOI: '+references['papers'][0]['doi']+'\n\nThe supplied paper reports descriptive Hadoop/Hive loan analysis, not an evaluated predictive classifier. No comparable accuracy, recall, F1 or ROC-AUC is reported for its own analysis. Missing results are not zero.\n\n'
    text+='## Limits of the comparison\n\n'+'\n\n'.join('- '+s for s in references['cautions'])+'\n\n'
    text+='Original paired confidence intervals compare LightGBM with Logistic Regression only. There are no new paired intervals establishing that CatBoost improves over LightGBM. The paper’s Random Forest and XGBoost have not been trained or reproduced in our project. Adaptive Random Forest is a different algorithm from conventional Random Forest.\n'
    (project/'results/model_extensions/MODEL_REFERENCE_COMPARISON.md').write_text(text,encoding='utf-8')
    print('Built comparison: 5 local model rows, 4 ROC/PR curves, 7 published/project score rows.')


if __name__=='__main__':main()
