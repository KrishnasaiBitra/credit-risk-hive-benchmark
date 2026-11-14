from pathlib import Path
import json
import time
import warnings

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

project = Path(__file__).resolve().parents[1]
results = project / "results/baseline"
models = project / "models"
results.mkdir(parents=True, exist_ok=True)
models.mkdir(parents=True, exist_ok=True)

train = pd.read_csv(
    project / "data/features/train.csv",
    dtype={"loan_id": "string"},
)
validation = pd.read_csv(
    project / "data/features/validation.csv",
    dtype={"loan_id": "string"},
)

categorical = [
    "home_ownership_group",
    "purpose",
    "verification_status",
]
numeric = [
    "loan_amount", "annual_income", "dti",
    "employment_years", "employment_missing",
    "fico_midpoint", "delinq_2yrs", "inq_last_6mths",
    "open_accounts", "public_records", "revolving_balance",
    "revolving_utilization", "utilization_missing",
    "total_accounts", "bankruptcies", "credit_history_months",
]
features = numeric + categorical

X_train = train[features]
y_train = train["target"].astype(int)
X_validation = validation[features]
y_validation = validation["target"].astype(int)

preprocessing = ColumnTransformer([
    ("numeric", StandardScaler(), numeric),
    (
        "categorical",
        OneHotEncoder(handle_unknown="ignore"),
        categorical,
    ),
])

model = Pipeline([
    ("preprocessing", preprocessing),
    (
        "classifier",
        LogisticRegression(
            C=1.0,
            solver="lbfgs",
            max_iter=2000,
            random_state=42,
        ),
    ),
])

def evaluate(name, probabilities, fit_seconds, prediction_seconds):
    predictions = (probabilities >= 0.5).astype(int)
    tn, fp, fn, tp = confusion_matrix(
        y_validation, predictions, labels=[0, 1]
    ).ravel()

    return {
        "model": name,
        "threshold": 0.5,
        "accuracy": float(accuracy_score(y_validation, predictions)),
        "precision": float(precision_score(
            y_validation, predictions, zero_division=0
        )),
        "default_recall": float(recall_score(
            y_validation, predictions, zero_division=0
        )),
        "f1": float(f1_score(
            y_validation, predictions, zero_division=0
        )),
        "roc_auc": float(roc_auc_score(
            y_validation, probabilities
        )),
        "average_precision": float(average_precision_score(
            y_validation, probabilities
        )),
        "brier_score": float(brier_score_loss(
            y_validation, probabilities
        )),
        "fit_seconds": fit_seconds,
        "validation_prediction_seconds": prediction_seconds,
        "true_negatives": int(tn),
        "false_positives": int(fp),
        "false_negatives": int(fn),
        "true_positives": int(tp),
    }

reports = []

dummy = DummyClassifier(strategy="prior")
dummy_train = np.zeros((len(train), 1))
dummy_validation = np.zeros((len(validation), 1))

start = time.perf_counter()
dummy.fit(dummy_train, y_train)
fit_seconds = time.perf_counter() - start

start = time.perf_counter()
dummy_probabilities = dummy.predict_proba(dummy_validation)[:, 1]
prediction_seconds = time.perf_counter() - start

reports.append(evaluate(
    "Dummy", dummy_probabilities, fit_seconds, prediction_seconds
))

print("Training Logistic Regression...", flush=True)
start = time.perf_counter()

with warnings.catch_warnings(record=True) as captured:
    warnings.simplefilter("always", ConvergenceWarning)
    model.fit(X_train, y_train)

fit_seconds = time.perf_counter() - start

if any(
    issubclass(item.category, ConvergenceWarning)
    for item in captured
):
    raise RuntimeError(
        "Logistic Regression did not converge. "
        "Review the training setup before accepting its results."
    )

start = time.perf_counter()
probabilities = model.predict_proba(X_validation)[:, 1]
prediction_seconds = time.perf_counter() - start

reports.append(evaluate(
    "Logistic Regression",
    probabilities,
    fit_seconds,
    prediction_seconds,
))

joblib.dump(model, models / "logistic_regression.joblib")
joblib.dump(dummy, models / "dummy_classifier.joblib")

predictions = validation[
    ["loan_id", "home_ownership_group", "target"]
].copy()
predictions["probability"] = probabilities
predictions["prediction"] = (probabilities >= 0.5).astype(int)
predictions.to_csv(
    results / "logistic_validation_predictions.csv",
    index=False,
)

report = pd.DataFrame(reports)
report.to_csv(results / "validation_metrics.csv", index=False)

(results / "baseline_config.json").write_text(
    json.dumps({
        "training_rows": len(train),
        "validation_rows": len(validation),
        "numeric_features": numeric,
        "categorical_features": categorical,
        "threshold": 0.5,
        "class_weight": None,
        "test_set_evaluated": False,
        "timing_scope": (
            "One local run; Logistic Regression fit includes "
            "encoding and scaling. Not a repeated pipeline benchmark."
        ),
    }, indent=2),
    encoding="utf-8",
)

print("\nVALIDATION RESULTS")
print(report[[
    "model", "accuracy", "precision", "default_recall",
    "f1", "roc_auc", "average_precision", "brier_score",
    "fit_seconds",
]].round(4).to_string(index=False))
print("\nResults saved to:", results)
print("Test-set performance has not been evaluated.")
