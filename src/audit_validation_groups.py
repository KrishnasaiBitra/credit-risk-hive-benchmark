from pathlib import Path
import json
import pandas as pd
from fairlearn.metrics import (
    MetricFrame,
    false_positive_rate,
    selection_rate,
)
from sklearn.metrics import precision_score, recall_score

project = Path(__file__).resolve().parents[1]
output = project / "results/group_audit"
output.mkdir(parents=True, exist_ok=True)

models = [
    (
        "Logistic Regression",
        "results/baseline/logistic_validation_predictions.csv",
        "results/baseline/threshold_selection.json",
    ),
    (
        "LightGBM",
        "results/lightgbm/lightgbm_validation_predictions.csv",
        "results/lightgbm/threshold_selection.json",
    ),
]

all_results = []
summaries = []
reference = None

for name, predictions_path, settings_path in models:
    data = pd.read_csv(
        project / predictions_path,
        dtype={"loan_id": "string"},
    ).sort_values("loan_id").reset_index(drop=True)

    assert len(data) == 71955
    assert data["loan_id"].is_unique

    tracking = data[
        ["loan_id", "target", "home_ownership_group"]
    ]
    if reference is None:
        reference = tracking.copy()
    else:
        pd.testing.assert_frame_equal(reference, tracking)

    settings = json.loads((project / settings_path).read_text())
    threshold = settings["selected_threshold"]

    # Recalculate predictions: the LR file originally used threshold 0.5.
    predicted = (data["probability"] >= threshold).astype(int)

    frame = MetricFrame(
        metrics={
            "precision": lambda y, p: precision_score(
                y, p, zero_division=0
            ),
            "chargeoff_recall": recall_score,
            "false_positive_rate": false_positive_rate,
            "flag_rate": selection_rate,
        },
        y_true=data["target"],
        y_pred=predicted,
        sensitive_features=data["home_ownership_group"],
    )

    counts = data.groupby("home_ownership_group")["target"].agg(
        loans="size",
        charged_off="sum",
    )
    counts["fully_paid"] = counts["loans"] - counts["charged_off"]

    report = counts.join(frame.by_group)
    report.index.name = "group"
    report = report.reset_index()
    report.insert(0, "model", name)
    report.insert(1, "threshold", threshold)
    all_results.append(report)

    main = report[
        report["group"].isin(["MORTGAGE", "RENT", "OWN"])
    ]
    fpr_gap = (
        main["false_positive_rate"].max()
        - main["false_positive_rate"].min()
    )
    recall_gap = (
        main["chargeoff_recall"].max()
        - main["chargeoff_recall"].min()
    )

    summaries.append({
        "model": name,
        "false_positive_rate_gap": fpr_gap,
        "chargeoff_recall_gap": recall_gap,
        "equalized_odds_difference": max(fpr_gap, recall_gap),
    })

combined = pd.concat(all_results, ignore_index=True)
summary = pd.DataFrame(summaries)

combined.to_csv(
    output / "validation_group_metrics.csv", index=False
)
summary.to_csv(
    output / "validation_group_gaps.csv", index=False
)

print("\nVALIDATION GROUP METRICS")
print(combined.round(4).to_string(index=False))
print("\nGAPS ACROSS MORTGAGE, RENT AND OWN")
print(summary.round(4).to_string(index=False))
print("\nTest-set performance remains unevaluated.")
