from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.metrics import (
    confusion_matrix,
    precision_score,
    recall_score,
    f1_score,
)

project = Path(__file__).resolve().parents[1]
folder = project / "results/baseline"
data = pd.read_csv(
    folder / "logistic_validation_predictions.csv",
    dtype={"loan_id": "string"},
)

y = data["target"].to_numpy()
probabilities = data["probability"].to_numpy()

assert np.isin(y, [0, 1]).all(), "Invalid target values"
assert np.isfinite(probabilities).all(), "Invalid probabilities"
assert ((probabilities >= 0) & (probabilities <= 1)).all()

print("\nVALIDATION PROBABILITY DISTRIBUTION")
print(data["probability"].describe(
    percentiles=[0.10, 0.50, 0.75, 0.90, 0.95, 0.99]
).round(4).to_string())

print("\nPROBABILITIES BY ACTUAL OUTCOME")
print(data.groupby("target")["probability"].agg(
    ["count", "mean", "median", "min", "max"]
).round(4).to_string())

rows = []
thresholds = [
    0.05, 0.075, 0.10, 0.125, 0.15,
    0.175, 0.20, 0.25, 0.30, 0.40, 0.50,
]

for threshold in thresholds:
    predictions = (probabilities >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(
        y, predictions, labels=[0, 1]
    ).ravel()

    rows.append({
        "threshold": threshold,
        "precision": precision_score(y, predictions, zero_division=0),
        "chargeoff_recall": recall_score(y, predictions, zero_division=0),
        "false_positive_rate": fp / (fp + tn),
        "f1": f1_score(y, predictions, zero_division=0),
        "flagged_percent": 100 * predictions.mean(),
        "true_positives": int(tp),
        "false_positives": int(fp),
        "false_negatives": int(fn),
        "true_negatives": int(tn),
    })

report = pd.DataFrame(rows)
report.to_csv(folder / "validation_threshold_comparison.csv", index=False)

print("\nTHRESHOLD COMPARISON")
print(report.round(4).to_string(index=False))
print("\nComparison saved. No threshold has been selected.")
print("Test-set performance remains unevaluated.")
