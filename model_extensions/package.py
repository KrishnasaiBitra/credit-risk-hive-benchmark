"""Package the completed extension for the source repo and dashboard."""
from pathlib import Path
import argparse
import shutil
from .common import read_json, sha, write_json


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--run',type=Path,required=True)
    p.add_argument('--target',type=Path,required=True)
    a=p.parse_args();run,target=a.run,a.target
    output=target/'results/model_extensions';output.mkdir(parents=True,exist_ok=True)
    models=target/'models/extensions';models.mkdir(parents=True,exist_ok=True)
    for file in ['model_comparison.csv','group_metrics.csv','group_gaps.csv','comparison.json','manifest.json']:
        shutil.copy2(run/'evaluation'/file,output/file)
    definitions={}
    for key,name,file in [('catboost','CatBoost','catboost_model.py'),('arf','Adaptive Random Forest','adaptive_random_forest.joblib')]:
        selection=read_json(run/key/'selection.json')
        dest=output/key;dest.mkdir(exist_ok=True)
        for f in ['selection.json','validation_metrics.csv','validation_thresholds.csv']:
            shutil.copy2(run/key/f,dest/f)
        original_file=run/key/('portable_model.py' if key=='catboost' else 'model.joblib')
        shutil.copy2(original_file,models/file)
        if key=='catboost':
            shutil.copy2(run/key/'model.joblib',models/'catboost_native.joblib')
            shutil.copy2(run/key/'portable_verification.json',dest/'portable_verification.json')
        definitions[name]=dict(file='models/extensions/'+file,sha256=sha(models/file),threshold=selection['selected_threshold'],
                               format='catboost_python' if key=='catboost' else 'joblib')
    write_json(output/'inference_manifest.json',dict(models=definitions,features=selection['features'],categorical_features=selection['categorical_features']))
    report=read_json(output/'comparison.json')
    text='# CatBoost and Adaptive Random Forest extension\n\nThis is a new exploratory experiment. Original research files and pipeline measurements remain unchanged.\n\n'
    text+='| Model | Threshold | Accuracy | Precision | Recall | F1 | ROC-AUC | Average precision |\n|---|---|---|---|---|---|---|---|\n'
    for r in report['models']:
        text+='| '+r['model']+' | '+' | '.join(f'{r[k]:.4f}' for k in ['threshold','accuracy','precision','chargeoff_recall','f1','roc_auc','average_precision'])+' |\n'
    text+='\n## Method and interpretation\n\n'
    text+='CatBoost uses native categorical features, one preset configuration and validation early stopping. ARF uses River with ten trees, ADWIN detectors, issue-month-ordered training and no learning on validation/test. All models receive the same 19 feature definitions. Their categorical preprocessing and algorithms differ. Thresholds are chosen by the original validation maximum-F1 rule. Training/prediction timings are single local measurements, not repeated benchmarks.\n\n'
    text+='CatBoost has a slightly higher test ROC-AUC point estimate than LightGBM, but slightly lower F1 and average precision. No statistically established improvement is claimed. ARF has higher recall at its chosen threshold but many more false positives and lower ROC-AUC/F1. Adding these algorithms does not itself establish research novelty.\n\n'
    text+='\n'.join('- '+s for s in report['limitations'])+'\n\n'
    text+='## Reproduce\n\nUse a separate environment, keep the original requirements-lock.txt as constraints, and install model_extensions/requirements.txt. Supply the original cohort and split files. From the repository root run:\n\n```bash\npython -m model_extensions.train --project /path/to/full-project --run /path/to/new-run --model catboost\npython -m model_extensions.train --project /path/to/full-project --run /path/to/new-run --model arf\npython -m model_extensions.export_catboost --project /path/to/full-project --run /path/to/new-run\npython -m model_extensions.evaluate --project /path/to/full-project --run /path/to/new-run\n```\n\n'
    text+='## References\n\n- CatBoost: https://catboost.ai/docs/en/concepts/python-reference_catboostclassifier\n- Official standalone export: https://catboost.ai/docs/en/concepts/python-reference_catboost_save_model\n- River ARFClassifier: https://riverml.xyz/latest/api/forest/ARFClassifier/\n'
    (output/'MODEL_EXTENSION_REPORT.md').write_text(text,encoding='utf-8')
    print('Packaged extension:',target)


if __name__=='__main__':main()
