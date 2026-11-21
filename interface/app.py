"""Local lecturer demo. Read-only research artifacts and fixed-model inference."""
from functools import lru_cache
from pathlib import Path
from typing import Literal
import hashlib
import json
import logging
import math
import os
import threading
import time

import joblib
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sklearn.metrics import roc_curve, precision_recall_curve

HERE = Path(__file__).resolve().parent
PROJECT = Path(os.environ.get('CREDIT_RISK_PROJECT', HERE.parent)).resolve()
FINAL = PROJECT / 'results/final_test'
BENCH = PROJECT / 'results/pipeline_benchmark'
LATENCY = BENCH / 'exports_v2_20261108_124424'
MODEL_FILES = {'Logistic Regression': 'logistic_regression.joblib', 'LightGBM': 'lightgbm.joblib'}
GROUPS = ['MORTGAGE', 'RENT', 'OWN']
predict_lock = threading.Lock()
app = FastAPI(title='Credit Risk Lab', version='1.0.0', docs_url='/api/docs', openapi_url='/api/openapi.json', redoc_url=None)


def require(path):
    if not path.is_file():
        raise HTTPException(503, f'Required research file is missing: {path.relative_to(PROJECT) if path.is_relative_to(PROJECT) else path.name}. Restore it and restart the app.')
    return path


@lru_cache(maxsize=32)
def read_json(relative):
    return json.loads(require(PROJECT / relative).read_text(encoding='utf-8'))


def records(frame):
    return json.loads(frame.to_json(orient='records'))


@lru_cache(maxsize=24)
def csv_data(relative):
    return pd.read_csv(require(PROJECT / relative))


def manifest():
    return read_json('results/final_test/evaluation_manifest.json')


@lru_cache(maxsize=1)
def training():
    return pd.read_csv(require(PROJECT / 'data/features/train.csv'), dtype={'loan_id': 'string'})


@lru_cache(maxsize=1)
def test_features():
    return pd.read_csv(require(PROJECT / 'data/features/test.csv'), dtype={'loan_id': 'string'})


@lru_cache(maxsize=1)
def training_fills():
    # Same frozen statistics file used to build all original feature pipelines.
    return read_json('results/hive_snapshot/20261108_110652/preprocessing_stats_values.json')[0]


@lru_cache(maxsize=1)
def demo_schema():
    compact = HERE / 'runtime/schema.json'
    if compact.is_file():
        return json.loads(compact.read_text(encoding='utf-8'))
    train = training()
    numeric = read_json('results/baseline/baseline_config.json')['numeric_features']
    return {
        'purposes': sorted(train.purpose.unique().tolist()),
        'verification_statuses': sorted(train.verification_status.unique().tolist()),
        'home_ownership_groups': ['MORTGAGE', 'RENT', 'OWN', 'OTHER_UNKNOWN'],
        'numeric_ranges': {name: {'min': float(train[name].min()), 'max': float(train[name].max())} for name in numeric},
        'training_fills': training_fills(),
        'thresholds': manifest()['selected_thresholds'],
    }


def extension_manifest():
    path = PROJECT / 'results/model_extensions/inference_manifest.json'
    return read_json('results/model_extensions/inference_manifest.json') if path.is_file() else {'models': {}}


@lru_cache(maxsize=4)
def load_model(name):
    if name not in MODEL_FILES:
        from model_extensions.portable import PortableCatBoost
        config = extension_manifest()
        spec = config['models'][name]
        path = require(PROJECT / spec['file'])
        if hashlib.sha256(path.read_bytes()).hexdigest() != spec['sha256']:
            raise HTTPException(503, 'Extension model fingerprint differs from its recorded experiment.')
        if spec['format'] == 'catboost_python':
            return PortableCatBoost(path, config['features'], config['categorical_features'])
        return joblib.load(path)
    relative = 'models/' + MODEL_FILES[name]
    path = require(PROJECT / relative)
    expected = manifest()['file_sha256'][relative]
    if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise HTTPException(503, 'Saved model fingerprint differs from the frozen experiment. Restore the recorded model before prediction.')
    return joblib.load(path)


@app.exception_handler(Exception)
async def artifact_error(request: Request, exc: Exception):
    logging.exception('Interface request failed: %s (%s: %s)', request.url.path, type(exc).__name__, exc)
    return JSONResponse(status_code=503, content={'detail': 'The research data or model could not be loaded. Check the local server log and restore the project artifacts. No result has been substituted.'})


@app.get('/api/health')
def health():
    require(FINAL / 'test_metrics.csv')
    require(LATENCY / 'summary.csv')
    return {'status': 'ok', 'mode': 'Local saved-artifact demonstration', 'hive_required': False}


@app.get('/api/research')
@lru_cache(maxsize=1)
def research():
    compact = HERE / 'runtime/research.json'
    if compact.is_file():
        return json.loads(compact.read_text(encoding='utf-8'))
    export = read_json('data/features/export_manifest.json')
    metrics = csv_data('results/final_test/test_metrics.csv')
    summary = csv_data('results/pipeline_benchmark/exports_v2_20261108_124424/summary.csv').copy()
    summary = summary.set_index('pipeline').loc[['CSV', 'Raw_ORC', 'Prepared_ORC']].reset_index()
    sizes = {}
    for line in require(BENCH / 'hdfs_storage_bytes.txt').read_text().splitlines():
        parts = line.split()
        if len(parts) == 3:
            sizes[parts[2]] = int(parts[0])
    paths = ['/credit-risk/raw/cohort', '/warehouse/external/raw_credit_orc', '/warehouse/external/model_features_prepared_orc']
    summary['logical_bytes'] = [sizes[path] for path in paths]
    conversion = read_json('results/pipeline_benchmark/raw_orc_conversion_20261108_125602.json')['conversion_seconds']
    preparation = read_json('results/pipeline_benchmark/prepared_orc_creation.json')['insert_seconds']
    summary['preparation_seconds'] = [0., conversion, conversion + preparation]
    baseline = float(summary.iloc[0].median_seconds)
    summary['speedup'] = baseline / summary.median_seconds
    summary['estimated_break_even_exports'] = [0] + [math.ceil(row.preparation_seconds / (baseline - row.median_seconds)) for row in summary.iloc[1:].itertuples()]
    groups = csv_data('results/final_test/test_group_metrics.csv')
    resources = csv_data('results/pipeline_benchmark/resources_20261108_130043/resource_summary.csv')
    resource_summary = resources.groupby('pipeline').agg(
        sampled_cpu_median=('median_sampled_total_cpu_percent', 'median'),
        sampled_memory_max_mib=('maximum_sampled_total_memory_mib', 'max'),
        min_snapshots=('complete_snapshots_during_export', 'min'),
        max_snapshots=('complete_snapshots_during_export', 'max')).reset_index()
    checks = read_json('results/reproducibility/VERIFICATION_STATUS.json')
    return {
        'cohort': {'rows': sum(item['rows'] for item in export.values()),
                   'splits': {key: value['rows'] for key, value in export.items()},
                   'test_positive': int(groups[groups.model == 'LightGBM'].charged_off.sum()),
                   'features': manifest()['features'], 'years': '2012–2014', 'term_months': 36},
        'experiment_date': manifest()['frozen_at_utc'][:10],
        'pipelines': records(summary), 'runs': records(csv_data('results/pipeline_benchmark/exports_v2_20261108_124424/runs.csv')),
        'models': records(metrics), 'groups': records(groups),
        'gaps': records(csv_data('results/final_test/test_group_gaps.csv')),
        'intervals': records(csv_data('results/final_test/uncertainty/metric_confidence_intervals.csv')),
        'paired_differences': records(csv_data('results/final_test/uncertainty/paired_model_differences.csv')),
        'resources': records(resource_summary), 'conversion_seconds': conversion, 'feature_preparation_seconds': preparation,
        'verification': {'status': checks['status'], 'replay_metric_difference': checks['original_test_metrics_maximum_replay_difference']},
        'sources': ['results/pipeline_benchmark/exports_v2_20261108_124424', 'results/final_test', 'results/final_test/uncertainty'],
    }


@app.get('/api/curves')
@lru_cache(maxsize=1)
def curves():
    compact = HERE / 'runtime/curves.json'
    if compact.is_file():
        return json.loads(compact.read_text(encoding='utf-8'))
    output = []
    for name, filename in MODEL_FILES.items():
        frame = csv_data('results/final_test/' + filename.replace('.joblib', '_predictions.csv'))
        fpr, tpr, _ = roc_curve(frame.target, frame.probability)
        precision, recall, _ = precision_recall_curve(frame.target, frame.probability)
        # Display-only decimation; exact scores are read from the original metrics CSV.
        def sampled(x, y):
            indices = np.unique(np.linspace(0, len(x) - 1, min(1000, len(x)), dtype=int))
            return {'x': x[indices].tolist(), 'y': y[indices].tolist()}
        output.append({'model': name, 'roc': sampled(fpr, tpr), 'pr': sampled(recall, precision), 'prevalence': float(frame.target.mean())})
    return output


@app.get('/api/literature')
def literature():
    return read_json('results/literature_comparison/comparison.json')


@app.get('/api/extensions')
def extensions():
    return read_json('results/model_extensions/comparison.json')


class LoanInput(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)
    loan_amount: float = Field(gt=0, le=1e9)
    annual_income: float = Field(gt=0, le=1e10)
    dti: float = Field(ge=0, le=10000)
    employment_years: float | None = Field(default=None, ge=0, le=80)
    home_ownership_group: Literal['MORTGAGE', 'RENT', 'OWN', 'OTHER_UNKNOWN']
    purpose: str = Field(min_length=1, max_length=80)
    verification_status: str = Field(min_length=1, max_length=50)
    fico_range_low: float = Field(ge=300, le=850)
    fico_range_high: float = Field(ge=300, le=850)
    delinq_2yrs: int = Field(ge=0, le=100000)
    inq_last_6mths: int = Field(ge=0, le=100000)
    open_accounts: int = Field(ge=0, le=100000)
    public_records: int = Field(ge=0, le=100000)
    revolving_balance: float = Field(ge=0, le=1e10)
    revolving_utilization: float | None = Field(default=None, ge=0, le=10000)
    total_accounts: int = Field(ge=0, le=100000)
    bankruptcies: int = Field(ge=0, le=100000)
    credit_history_months: int = Field(ge=0, le=1500)

    @model_validator(mode='after')
    def valid_fico(self):
        if self.fico_range_high < self.fico_range_low:
            raise ValueError('FICO upper bound must be at least the lower bound.')
        return self


def make_features(loan):
    schema = demo_schema()
    if loan.purpose not in schema['purposes'] or loan.verification_status not in schema['verification_statuses']:
        raise HTTPException(422, 'Choose a purpose and verification status from the provided options.')
    values = loan.model_dump()
    low, high = values.pop('fico_range_low'), values.pop('fico_range_high')
    values['fico_midpoint'] = (low + high) / 2
    values['employment_missing'] = int(values['employment_years'] is None)
    values['utilization_missing'] = int(values['revolving_utilization'] is None)
    if values['employment_missing']:
        values['employment_years'] = training_fills()['employment_fill']
    if values['utilization_missing']:
        values['revolving_utilization'] = training_fills()['utilization_fill']
    columns = manifest()['features']
    return pd.DataFrame([values], columns=columns)


@app.get('/api/demo/schema')
def get_demo_schema():
    schema = demo_schema()
    return {**schema, 'thresholds': {**schema['thresholds'], **{name: spec['threshold'] for name, spec in extension_manifest()['models'].items()}}}


@app.get('/api/demo/examples')
@lru_cache(maxsize=1)
def examples():
    compact = HERE / 'runtime/examples.json'
    if compact.is_file():
        return json.loads(compact.read_text(encoding='utf-8'))
    frame = test_features()
    chosen = []
    for group in GROUPS:
        for target in (0, 1):
            matches = frame[(frame.home_ownership_group == group) & (frame.target == target)]
            if not matches.empty:
                row = matches.iloc[0]
                inputs = {key: row[key] for key in manifest()['features'] if key not in ['fico_midpoint', 'employment_missing', 'utilization_missing']}
                for key in ['delinq_2yrs', 'inq_last_6mths', 'open_accounts', 'public_records', 'total_accounts', 'bankruptcies', 'credit_history_months']:
                    inputs[key] = int(inputs[key])
                if int(row.employment_missing):
                    inputs['employment_years'] = None
                if int(row.utilization_missing):
                    inputs['revolving_utilization'] = None
                midpoint = float(row.fico_midpoint)
                inputs['fico_range_low'] = 845. if midpoint == 847.5 else midpoint - 2
                inputs['fico_range_high'] = 850. if midpoint == 847.5 else midpoint + 2
                chosen.append({'id': str(row.loan_id), 'label': f'{group.title()} · historical example {len(chosen)+1}',
                               'recorded_outcome': 'Charged Off' if target else 'Fully Paid', 'inputs': inputs,
                               'note': 'FICO bounds reconstruct the saved midpoint; all other inputs come from the exported historical record.'})
    return json.loads(json.dumps(chosen, default=lambda value: value.item() if isinstance(value, np.generic) else value))


@app.post('/api/predict')
def predict(loan: LoanInput):
    features = make_features(loan)
    warnings = []
    for key, limits in demo_schema()['numeric_ranges'].items():
        value = float(features.iloc[0][key])
        if value < limits['min'] or value > limits['max']:
            warnings.append(f'{key.replace("_", " ").capitalize()} is outside the observed training range ({limits["min"]:g}–{limits["max"]:g}).')
    results = []
    with predict_lock:
        for name in [*MODEL_FILES, *extension_manifest()['models']]:
            model = load_model(name)
            start = time.perf_counter()
            probability = float(model.predict_proba(features)[0, list(model.classes_).index(1)])
            threshold = float(manifest()['selected_thresholds'][name] if name in MODEL_FILES else extension_manifest()['models'][name]['threshold'])
            results.append({'model': name, 'probability': probability, 'threshold': threshold,
                            'flagged': probability >= threshold, 'prediction_seconds': time.perf_counter() - start})
    return {'results': results, 'features': features.iloc[0].to_dict(), 'warnings': warnings,
            'scope': 'Estimated historical charge-off risk. The fixed threshold is a research comparison rule, not a loan approval decision.'}


DOWNLOADS = {
    'extension-models': (PROJECT / 'results/model_extensions/model_comparison.csv', 'extended_model_comparison.csv'),
    'extension-groups': (PROJECT / 'results/model_extensions/group_metrics.csv', 'extended_group_metrics.csv'),
    'extension-method': (PROJECT / 'results/model_extensions/MODEL_EXTENSION_REPORT.md', 'MODEL_EXTENSION_REPORT.md'),
    'report': (HERE / 'assets/project_report.pdf', 'Credit_Risk_Hive_Project_Report.pdf'),
    'model-results': (FINAL / 'test_metrics.csv', 'model_test_results.csv'),
    'pipeline-results': (LATENCY / 'summary.csv', 'pipeline_export_results.csv'),
    'group-results': (FINAL / 'test_group_metrics.csv', 'home_ownership_audit.csv'),
    'confidence-intervals': (FINAL / 'uncertainty/metric_confidence_intervals.csv', 'confidence_intervals.csv'),
    'method': (PROJECT / 'results/report/project_results.md', 'project_results.md'),
    'references': (PROJECT / 'references.bib', 'references.bib'),
    'rerun-guide': (PROJECT / 'REPRODUCE.md', 'REPRODUCE.md'),
    'paper-scores': (PROJECT / 'results/literature_comparison/reported_model_scores.csv', 'reported_paper_and_project_scores.csv'),
    'study-comparison': (PROJECT / 'results/literature_comparison/study_comparison.csv', 'research_scope_comparison.csv'),
}


@app.get('/api/downloads')
def downloads():
    return [{'id': key, 'filename': filename, 'available': path.is_file()} for key, (path, filename) in DOWNLOADS.items()]


@app.get('/api/download/{key}')
def download(key: str):
    if key not in DOWNLOADS:
        raise HTTPException(404, 'Unknown download.')
    path, filename = DOWNLOADS[key]
    require(path)
    return FileResponse(path, filename=filename, media_type='application/pdf' if key == 'report' else None)


@app.get('/')
def home():
    return FileResponse(HERE / 'static/index.html', headers={'Cache-Control': 'no-cache'})


app.mount('/static', StaticFiles(directory=HERE / 'static'), name='static')
