from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import time

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, average_precision_score, brier_score_loss,
    confusion_matrix,
)

project = Path(__file__).resolve().parents[1]
output = project / "results/final_test"

def read_json(relative):
    return json.loads((project / relative).read_text(encoding="utf-8"))

def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

config = read_json("results/baseline/baseline_config.json")
lr_selection = read_json("results/baseline/threshold_selection.json")
lgb_selection = read_json("results/lightgbm/threshold_selection.json")

features = config["numeric_features"] + config["categorical_features"]
thresholds = {
    "Logistic Regression": float(lr_selection["selected_threshold"]),
    "LightGBM": float(lgb_selection["selected_threshold"]),
}

model_files = {
    "Dummy": "models/dummy_classifier.joblib",
    "Logistic Regression": "models/logistic_regression.joblib",
    "LightGBM": "models/lightgbm.joblib",
}

tracked_files = list(model_files.values()) + [
    "data/features/test.csv",
    "results/baseline/baseline_config.json",
    "results/baseline/threshold_selection.json",
    "results/lightgbm/threshold_selection.json",
]

# Read-only validation before creating the evaluation directory.
for relative in tracked_files:
    if not (project / relative).is_file():
        raise FileNotFoundError(relative)

test = pd.read_csv(project / "data/features/test.csv")
required = ["loan_id", "data_split", "target"] + features
if not set(required).issubset(test.columns):
    raise RuntimeError("Required test columns are missing.")
if len(test) != 90615:
    raise RuntimeError("Unexpected test row count.")
if test["loan_id"].isna().any() or test["loan_id"].duplicated().any():
    raise RuntimeError("Invalid or duplicated test loan IDs.")
if not test["data_split"].eq("test").all():
    raise RuntimeError("Unexpected split assignments.")
if not test["target"].isin([0, 1]).all():
    raise RuntimeError("Invalid target values.")
if test[features].isna().any().any():
    raise RuntimeError("Missing feature values.")
if not np.isfinite(
    test[config["numeric_features"]].to_numpy(dtype=float)
).all():
    raise RuntimeError("Non-finite numeric feature values.")

# Existing results are protected against accidental overwriting.
output.mkdir(parents=True, exist_ok=False)

manifest = {
    "frozen_at_utc": datetime.now(timezone.utc).isoformat(),
    "features": features,
    "selected_thresholds": thresholds,
    "threshold_selection_dataset": "validation",
    "lightgbm_best_iteration": lgb_selection["best_iteration"],
    "positive_class": "Charged Off",
    "model_refitting": False,
    "file_sha256": {
        relative: sha256(project / relative)
        for relative in tracked_files
    },
    "evaluation_completed": False,
    "limitation": (
        "Retrospective issue-date split; training outcome availability "
        "at the validation/test issue dates is not established."
    ),
}
manifest_file = output / "evaluation_manifest.json"
manifest_file.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

X = test[features]
y = test["target"].to_numpy(dtype=int)

def classification_metrics(actual, predicted):
    tn, fp, fn, tp = confusion_matrix(
        actual, predicted, labels=[0, 1]
    ).ravel()
    return {
        "accuracy": accuracy_score(actual, predicted),
        "precision": precision_score(actual, predicted, zero_division=0),
        "chargeoff_recall": recall_score(actual, predicted, zero_division=0),
        "false_positive_rate": fp / (fp + tn) if fp + tn else np.nan,
        "f1": f1_score(actual, predicted, zero_division=0),
        "flag_rate": float(np.mean(predicted)),
        "true_positives": int(tp),
        "false_positives": int(fp),
        "false_negatives": int(fn),
        "true_negatives": int(tn),
    }

metrics = []
group_metrics = []

for name, relative in model_files.items():
    print(f"Evaluating {name}...", flush=True)
    model = joblib.load(project / relative)
    positive_index = list(model.classes_).index(1)

    start = time.perf_counter()
    if name == "Dummy":
        probability = model.predict_proba(
            np.zeros((len(test), 1))
        )[:, positive_index]
    else:
        probability = model.predict_proba(X)[:, positive_index]
    prediction_seconds = time.perf_counter() - start

    threshold = 0.5 if name == "Dummy" else thresholds[name]
    predicted = (probability >= threshold).astype(int)

    metrics.append({
        "model": name,
        "threshold": threshold,
        **classification_metrics(y, predicted),
        "roc_auc": roc_auc_score(y, probability),
        "average_precision": average_precision_score(y, probability),
        "brier_score": brier_score_loss(y, probability),
        "prediction_seconds": prediction_seconds,
    })

    predictions = test[
        ["loan_id", "home_ownership_group", "target"]
    ].copy()
    predictions["probability"] = probability
    predictions["prediction"] = predicted
    predictions.to_csv(
        output / f"{Path(relative).stem}_predictions.csv", index=False
    )

    if name != "Dummy":
        for group, frame in predictions.groupby("home_ownership_group"):
            group_metrics.append({
                "model": name,
                "threshold": threshold,
                "group": group,
                "loans": len(frame),
                "charged_off": int(frame["target"].sum()),
                "fully_paid": int((frame["target"] == 0).sum()),
                **classification_metrics(
                    frame["target"], frame["prediction"]
                ),
            })

metrics_frame = pd.DataFrame(metrics)
groups_frame = pd.DataFrame(group_metrics)
metrics_frame.to_csv(output / "test_metrics.csv", index=False)
groups_frame.to_csv(output / "test_group_metrics.csv", index=False)

gaps = []
for name, frame in groups_frame.groupby("model"):
    main = frame[frame["group"].isin(["MORTGAGE", "RENT", "OWN"])]
    fpr_gap = (
        main["false_positive_rate"].max()
        - main["false_positive_rate"].min()
    )
    recall_gap = (
        main["chargeoff_recall"].max()
        - main["chargeoff_recall"].min()
    )
    gaps.append({
        "model": name,
        "false_positive_rate_gap": fpr_gap,
        "chargeoff_recall_gap": recall_gap,
        "equalized_odds_difference": max(fpr_gap, recall_gap),
    })

pd.DataFrame(gaps).to_csv(output / "test_group_gaps.csv", index=False)

manifest["evaluation_completed"] = True
manifest["test_rows"] = len(test)
manifest_file.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

display = [
    "model", "threshold", "accuracy", "precision",
    "chargeoff_recall", "false_positive_rate", "f1",
    "roc_auc", "average_precision", "brier_score",
]
print("\nFINAL TEST RESULTS")
print(metrics_frame[display].round(4).to_string(index=False))
print("\nGROUP GAPS: MORTGAGE, RENT AND OWN")
print(pd.DataFrame(gaps).round(4).to_string(index=False))
print(f"\nSaved: {output}")
print("OTHER_UNKNOWN is reported separately and excluded from group gaps.")
