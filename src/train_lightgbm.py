from pathlib import Path
import json
import time

import joblib
import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier, early_stopping
from sklearn.base import clone
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

project = Path(__file__).resolve().parents[1]
output = project / "results/lightgbm"
output.mkdir(parents=True, exist_ok=True)

train = pd.read_csv(
    project / "data/features/train.csv",
    dtype={"loan_id": "string"},
)
validation = pd.read_csv(
    project / "data/features/validation.csv",
    dtype={"loan_id": "string"},
)

config = json.loads(
    (project / "results/baseline/baseline_config.json").read_text()
)
features = config["numeric_features"] + config["categorical_features"]

X_train = train[features]
y_train = train["target"].astype(int)
X_validation = validation[features]
y_validation = validation["target"].astype(int)

baseline = joblib.load(
    project / "models/logistic_regression.joblib"
)

# Clone makes an unfitted copy. Fit it on training data only.
preprocessing = clone(baseline.named_steps["preprocessing"])

start = time.perf_counter()
train_matrix = preprocessing.fit_transform(X_train)
validation_matrix = preprocessing.transform(X_validation)
preprocessing_seconds = time.perf_counter() - start

classifier = LGBMClassifier(
    objective="binary",
    metric="auc",
    n_estimators=1000,
    learning_rate=0.03,
    num_leaves=15,
    min_child_samples=100,
    reg_lambda=5.0,
    colsample_bytree=0.8,
    subsample=0.8,
    subsample_freq=1,
    class_weight=None,
    random_state=42,
    n_jobs=2,
    verbosity=-1,
)

print("Training LightGBM...", flush=True)
start = time.perf_counter()

classifier.fit(
    train_matrix,
    y_train,
    eval_X=validation_matrix,
    eval_y=y_validation,
    callbacks=[
        early_stopping(
            stopping_rounds=50,
            first_metric_only=True,
            verbose=False,
        )
    ],
)

fit_seconds = time.perf_counter() - start

# Both components are already fitted.
model = Pipeline([
    ("preprocessing", preprocessing),
    ("classifier", classifier),
])

start = time.perf_counter()
probabilities = model.predict_proba(X_validation)[:, 1]
prediction_seconds = time.perf_counter() - start

assert np.isfinite(probabilities).all()

baseline_selection = json.loads(
    (project / "results/baseline/threshold_selection.json").read_text()
)
thresholds = baseline_selection["threshold_grid"]

rows = []
for threshold in thresholds:
    predicted = (probabilities >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(
        y_validation, predicted, labels=[0, 1]
    ).ravel()

    rows.append({
        "threshold": float(threshold),
        "precision": precision_score(
            y_validation, predicted, zero_division=0
        ),
        "chargeoff_recall": recall_score(
            y_validation, predicted, zero_division=0
        ),
        "false_positive_rate": fp / (fp + tn),
        "f1": f1_score(y_validation, predicted, zero_division=0),
        "flagged_percent": 100 * predicted.mean(),
    })

threshold_table = pd.DataFrame(rows)
threshold_table.to_csv(
    output / "validation_threshold_comparison.csv", index=False
)

best = threshold_table.sort_values(
    ["f1", "threshold"], ascending=[False, False]
).iloc[0]
selected_threshold = float(best["threshold"])

selection = {
    "model": "LightGBM",
    "selection_dataset": "validation",
    "selection_rule": baseline_selection["selection_rule"],
    "threshold_grid": thresholds,
    "selected_threshold": selected_threshold,
    "best_iteration": int(classifier.best_iteration_),
    "preprocessing_seconds": preprocessing_seconds,
    "classifier_fit_seconds": fit_seconds,
    "validation_prediction_seconds": prediction_seconds,
    "test_set_evaluated": False,
}

(output / "threshold_selection.json").write_text(
    json.dumps(selection, indent=2), encoding="utf-8"
)
joblib.dump(model, project / "models/lightgbm.joblib")

predictions = validation[
    ["loan_id", "home_ownership_group", "target"]
].copy()
predictions["probability"] = probabilities
predictions["prediction"] = (
    probabilities >= selected_threshold
).astype(int)
predictions.to_csv(
    output / "lightgbm_validation_predictions.csv", index=False
)

def metrics(name, probability, threshold):
    predicted = (probability >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(
        y_validation, predicted, labels=[0, 1]
    ).ravel()
    return {
        "model": name,
        "threshold": threshold,
        "accuracy": accuracy_score(y_validation, predicted),
        "precision": precision_score(
            y_validation, predicted, zero_division=0
        ),
        "chargeoff_recall": recall_score(
            y_validation, predicted, zero_division=0
        ),
        "false_positive_rate": fp / (fp + tn),
        "f1": f1_score(y_validation, predicted, zero_division=0),
        "roc_auc": roc_auc_score(y_validation, probability),
        "average_precision": average_precision_score(
            y_validation, probability
        ),
        "brier_score": brier_score_loss(y_validation, probability),
    }

baseline_probabilities = baseline.predict_proba(X_validation)[:, 1]

comparison = pd.DataFrame([
    metrics(
        "Logistic Regression",
        baseline_probabilities,
        baseline_selection["selected_threshold"],
    ),
    metrics("LightGBM", probabilities, selected_threshold),
])
comparison.to_csv(
    output / "validation_model_comparison.csv", index=False
)

print("\nVALIDATION MODEL COMPARISON")
print(comparison.round(4).to_string(index=False))
print("\nLightGBM best iteration:", classifier.best_iteration_)
print("Preprocessing seconds:", round(preprocessing_seconds, 2))
print("Classifier fit seconds:", round(fit_seconds, 2))
print("Prediction seconds:", round(prediction_seconds, 2))
print("\nTest-set performance remains unevaluated.")
