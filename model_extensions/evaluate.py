"""Score frozen extension models on the historical holdout; no training or tuning."""
import argparse
from datetime import datetime, timezone
from pathlib import Path
import time
import joblib
import numpy as np
import pandas as pd
from .common import GROUPS, group_metrics, load_split, metrics, read_json, sha, write_json


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project',type=Path,required=True)
    parser.add_argument('--run',type=Path,required=True)
    args=parser.parse_args()
    project,run=args.project.resolve(),args.run.resolve()
    output=run/'evaluation'
    output.mkdir(exist_ok=False)
    original=read_json(project/'results/final_test/evaluation_manifest.json')
    for relative,expected in original['file_sha256'].items():
        assert sha(project/relative)==expected, relative
    selections={key:read_json(run/key/'selection.json') for key in ['catboost','arf']}
    features=selections['catboost']['features']
    assert features==original['features']==selections['arf']['features']
    test=load_split(project,'test',features)
    train_ids=set(pd.read_csv(project/'data/features/train.csv',usecols=['loan_id'],dtype='string').loan_id)
    val_ids=set(pd.read_csv(project/'data/features/validation.csv',usecols=['loan_id'],dtype='string').loan_id)
    assert train_ids.isdisjoint(test.loan_id) and val_ids.isdisjoint(test.loan_id)
    baseline=pd.read_csv(project/'results/final_test/test_metrics.csv')
    score_rows=baseline.to_dict(orient='records')
    group_rows=pd.read_csv(project/'results/final_test/test_group_metrics.csv').to_dict(orient='records')
    gaps=pd.read_csv(project/'results/final_test/test_group_gaps.csv').to_dict(orient='records')
    validation=[]
    timings={}
    for key,selection in selections.items():
        model_file=run/key/'model.joblib'
        assert sha(model_file)==selection['model_sha256']
        for split,expected in selection['data_sha256'].items():
            assert sha(project/f'data/features/{split}.csv')==expected
        model=joblib.load(model_file)
        start=time.perf_counter()
        probability=model.predict_proba(test[features])[:,1]
        timings[selection['model']]=time.perf_counter()-start
        threshold=selection['selected_threshold']
        result=metrics(selection['model'],test.target,probability,threshold)
        score_rows.append(result)
        validation.append(selection['validation_metrics'])
        groups=group_metrics(selection['model'],test,probability,threshold)
        group_rows.extend(groups)
        main=pd.DataFrame(groups).set_index('group').loc[GROUPS]
        fpr_gap=float(main.false_positive_rate.max()-main.false_positive_rate.min())
        recall_gap=float(main.chargeoff_recall.max()-main.chargeoff_recall.min())
        gaps.append(dict(model=selection['model'],false_positive_rate_gap=fpr_gap,chargeoff_recall_gap=recall_gap,
                         equalized_odds_difference=max(fpr_gap,recall_gap)))
        saved=test[['loan_id','home_ownership_group','target']].copy()
        saved['probability']=probability;saved['prediction']=(probability>=threshold).astype(int)
        saved.to_csv(output/f'{key}_predictions.csv',index=False)
        print('TEST RESULTS',selection['model'],'\n',pd.DataFrame([result]).round(4).to_string(index=False),flush=True)
    scores=pd.DataFrame(score_rows)
    scores.to_csv(output/'model_comparison.csv',index=False)
    pd.DataFrame(group_rows).to_csv(output/'group_metrics.csv',index=False)
    pd.DataFrame(gaps).to_csv(output/'group_gaps.csv',index=False)
    limitations=[
        'Extension experiment: the original test results were already known before these models were proposed. This reused historical holdout is not a fresh confirmatory test.',
        'No model tuning or learning uses test outcomes. Thresholds use the original validation-only maximum-F1 grid.',
        'ARF learns only the training partition, ordered by issue month and loan ID; it is frozen for validation/test. These results do not demonstrate live drift adaptation.',
        'Loan outcomes are delayed. The retrospective issue-date split is not a valid prospective label-arrival simulation.',
        'One fixed configuration and seed per new model; no new significance claim, fairness mitigation or new algorithm is established.',
        'Home ownership is a predictor and an audit grouping; protected-group or causal fairness is not established.',
    ]
    payload=dict(run=run.name,completed_at_utc=datetime.now(timezone.utc).isoformat(),test_rows=len(test),features=features,
                 models=__import__('json').loads(scores.to_json(orient='records')),groups=__import__('json').loads(pd.DataFrame(group_rows).to_json(orient='records')),
                 gaps=gaps,validation=validation,settings=[dict(model=s['model'],threshold=s['selected_threshold'],fit_seconds=s['fit_seconds'],validation_prediction_seconds=s['validation_prediction_seconds'],
                 hyperparameters=s['hyperparameters'],best_iteration=s.get('best_iteration'),tree_count=s.get('tree_count'),training_drifts=s.get('training_drifts'),training_warnings=s.get('training_warnings')) for s in selections.values()],
                 prediction_seconds=timings,limitations=limitations,original_artifacts_unchanged=True)
    write_json(output/'comparison.json',payload)
    write_json(output/'manifest.json',dict(test_sha256=sha(project/'data/features/test.csv'),model_sha256={k:s['model_sha256'] for k,s in selections.items()},
                    selected_thresholds={s['model']:s['selected_threshold'] for s in selections.values()},test_labels_used_for_learning=False,
                    completed_at_utc=payload['completed_at_utc'],limitations=limitations))
    for relative,expected in original['file_sha256'].items():
        assert sha(project/relative)==expected
    print('Original models, input files and configurations remain unchanged. Saved:',output,flush=True)


if __name__=='__main__':
    main()
