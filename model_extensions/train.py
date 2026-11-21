"""Train CatBoost or Adaptive Random Forest without reading test data."""
import argparse
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path
import time
import joblib
import pandas as pd
from .common import load_split, read_json, write_json, metrics, sha
from .models import AdaptiveForestModel


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--model', choices=['catboost', 'arf'], required=True)
    args = parser.parse_args()
    project, run = args.project.resolve(), args.run.resolve()
    output = run / args.model
    output.mkdir(parents=True, exist_ok=False)
    config = read_json(project / 'results/baseline/baseline_config.json')
    features = config['numeric_features'] + config['categorical_features']
    train = load_split(project, 'train', features)
    validation = load_split(project, 'validation', features)
    assert set(train.loan_id).isdisjoint(validation.loan_id)
    before = {f'models/{name}.joblib': sha(project/f'models/{name}.joblib') for name in ['dummy_classifier','logistic_regression','lightgbm']}
    started = time.perf_counter()
    metadata = {}
    if args.model == 'catboost':
        from catboost import CatBoostClassifier
        name = 'CatBoost'
        settings = dict(iterations=1500, depth=6, learning_rate=0.04, l2_leaf_reg=5,
                        loss_function='Logloss', eval_metric='AUC', random_seed=42,
                        thread_count=2, allow_writing_files=False)
        model = CatBoostClassifier(**settings)
        print('Training CatBoost on all training rows...', flush=True)
        model.fit(train[features], train.target, cat_features=config['categorical_features'],
                  eval_set=(validation[features], validation.target), early_stopping_rounds=100,
                  use_best_model=True, verbose=100)
        metadata['best_iteration'] = int(model.get_best_iteration())
        metadata['tree_count'] = int(model.tree_count_)
    else:
        from river import drift, forest
        name = 'Adaptive Random Forest'
        dates = pd.read_csv(project/'data/cohort/credit_cohort.csv', usecols=['id','issue_d'], dtype='string')
        dates['issue_month'] = pd.to_datetime(dates.issue_d, format='%b-%Y')
        assert dates.id.is_unique
        ordered = train.merge(dates[['id','issue_month']], left_on='loan_id', right_on='id', validate='one_to_one', how='left')
        assert ordered.issue_month.notna().all()
        ordered['numeric_loan_id'] = ordered.loan_id.astype('int64')
        ordered = ordered.sort_values(['issue_month','numeric_loan_id'], kind='stable')
        settings = dict(n_models=10, max_features='sqrt', lambda_value=6, grace_period=200,
                        max_depth=12, leaf_prediction='nba', nominal_attributes=config['categorical_features'],
                        max_size=16.0, memory_estimate_period=50000, seed=42)
        adaptive = forest.ARFClassifier(**settings, drift_detector=drift.ADWIN(delta=0.001), warning_detector=drift.ADWIN(delta=0.01))
        for index, (x, y) in enumerate(zip(ordered[features].to_dict(orient='records'), ordered.target), start=1):
            adaptive.learn_one(x, int(y))
            if index % 5000 == 0:
                print(f'ARF trained {index:,}/{len(ordered):,} rows | elapsed {time.perf_counter()-started:.1f}s', flush=True)
        model = AdaptiveForestModel(adaptive, features)
        metadata.update(training_order='Issue month ascending; numeric loan ID breaks within-month ties. Exact within-month event order is unavailable.',
                        training_order_id_sha256=__import__('hashlib').sha256('\n'.join(ordered.loan_id).encode()).hexdigest(),
                        training_drifts=int(adaptive.n_drifts_detected()), training_warnings=int(adaptive.n_warnings_detected()),
                        drift_detector={'type':'ADWIN','delta':0.001}, warning_detector={'type':'ADWIN','delta':0.01})
    fit_seconds = time.perf_counter() - started
    model_path = output / 'model.joblib'
    joblib.dump(model, model_path, compress=3)
    start = time.perf_counter()
    probability = model.predict_proba(validation[features])[:, 1]
    prediction_seconds = time.perf_counter() - start
    selection = read_json(project/'results/baseline/threshold_selection.json')
    threshold_rows = [metrics(name, validation.target, probability, t) for t in selection['threshold_grid']]
    table = pd.DataFrame(threshold_rows)
    table.to_csv(output/'validation_thresholds.csv', index=False)
    best = table.sort_values(['f1','threshold'], ascending=[False,False]).iloc[0].to_dict()
    frame = validation[['loan_id','home_ownership_group','target']].copy()
    frame['probability'] = probability
    frame['prediction'] = (probability >= best['threshold']).astype(int)
    frame.to_csv(output/'validation_predictions.csv', index=False)
    pd.DataFrame([best]).to_csv(output/'validation_metrics.csv', index=False)
    sample = validation[features].iloc[:8]
    import numpy as np
    np.testing.assert_allclose(joblib.load(model_path).predict_proba(sample), model.predict_proba(sample), rtol=0, atol=1e-12)
    assert before == {p:sha(project/p) for p in before}
    write_json(output/'selection.json', dict(model=name, model_key=args.model, features=features, categorical_features=config['categorical_features'],
               training_rows=len(train), validation_rows=len(validation), selected_threshold=best['threshold'],
               threshold_grid=selection['threshold_grid'], threshold_selection_rule=selection['selection_rule'],
               hyperparameters=settings, validation_metrics=best, fit_seconds=fit_seconds,
               validation_prediction_seconds=prediction_seconds, model_sha256=sha(model_path), original_models_sha256=before,
               data_sha256={s:sha(project/f'data/features/{s}.csv') for s in ['train','validation']},
               packages={p:version(p) for p in ['catboost','river','numpy','pandas','scikit-learn','joblib']},
               evaluation_mode='Fit on training; select threshold on validation; freeze for holdout prediction.',
               test_set_evaluated=False, completed_at_utc=datetime.now(timezone.utc).isoformat(), **metadata))
    print('\nVALIDATION RESULTS', name, '\n', pd.DataFrame([best]).round(4).to_string(index=False), flush=True)
    print(f'Fit: {fit_seconds:.2f}s; validation prediction: {prediction_seconds:.2f}s; model bytes: {model_path.stat().st_size:,}', flush=True)
    print('Test set has not been evaluated. Output:', output, flush=True)


if __name__ == '__main__':
    main()
