from pathlib import Path
from collections import Counter
import json
import pandas as pd

project = Path(__file__).resolve().parents[1]
source = (
    project / "archive"
    / "accepted_2007_to_2018q4.csv"
    / "accepted_2007_to_2018Q4.csv"
)
output = project / "results" / "data_audit"
output.mkdir(parents=True, exist_ok=True)

candidate_features = [
    "loan_amnt", "term", "annual_inc", "dti",
    "emp_length", "home_ownership", "purpose",
    "verification_status", "fico_range_low", "fico_range_high",
    "delinq_2yrs", "inq_last_6mths", "open_acc", "pub_rec",
    "revol_bal", "revol_util", "total_acc",
    "pub_rec_bankruptcies", "earliest_cr_line",
]

numeric_features = [
    "loan_amnt", "annual_inc", "dti",
    "fico_range_low", "fico_range_high",
    "delinq_2yrs", "inq_last_6mths", "open_acc",
    "pub_rec", "revol_bal", "revol_util",
    "total_acc", "pub_rec_bankruptcies",
]

# These fields describe subsequent loan performance or later updates.
# This is an initial exclusion list, not a complete leakage assessment.
later_outcome_fields = [
    "out_prncp", "out_prncp_inv",
    "total_pymnt", "total_pymnt_inv",
    "total_rec_prncp", "total_rec_int", "total_rec_late_fee",
    "recoveries", "collection_recovery_fee",
    "last_pymnt_d", "last_pymnt_amnt", "next_pymnt_d",
    "last_credit_pull_d", "last_fico_range_low",
    "last_fico_range_high",
]

header = pd.read_csv(source, nrows=0).columns.tolist()
required = ["id", "loan_status", "issue_d", "term"]

absent = [column for column in required if column not in header]
if absent:
    raise SystemExit(f"Required columns missing: {absent}")

available_features = [
    column for column in candidate_features if column in header
]
read_columns = list(dict.fromkeys(required + available_features))

year_term_status = Counter()
feature_missing = Counter()
invalid_numeric = Counter()
problem_counts = Counter()
problem_samples = []
group_counts = Counter()

total_rows = 0
resolved_rows = 0

for chunk in pd.read_csv(
    source,
    usecols=read_columns,
    dtype="string",
    keep_default_na=False,
    chunksize=25_000,
):
    total_rows += len(chunk)

    status = chunk["loan_status"].str.strip()
    dates = pd.to_datetime(
        chunk["issue_d"].str.strip(),
        format="%b-%Y",
        errors="coerce",
    )
    term = chunk["term"].str.strip().replace("", "(blank)")

    blank_status = status.eq("")
    bad_date = dates.isna()

    problem_counts["blank_status"] += int(blank_status.sum())
    problem_counts["invalid_issue_date"] += int(bad_date.sum())
    problem_counts["both_problems"] += int(
        (blank_status & bad_date).sum()
    )
    problem_counts["either_problem"] += int(
        (blank_status | bad_date).sum()
    )

    bad_rows = chunk.loc[
        blank_status | bad_date,
        ["id", "loan_status", "issue_d", "term"],
    ]
    remaining = max(0, 40 - len(problem_samples))
    problem_samples.extend(
        bad_rows.head(remaining).to_dict(orient="records")
    )

    grouping = pd.DataFrame({
        "issue_year": dates.dt.year.astype("Int64")
            .astype("string").fillna("(invalid)"),
        "term": term,
        "loan_status": status.replace("", "(blank)"),
    })
    counts = grouping.value_counts(sort=False)
    for key, count in counts.items():
        year_term_status[key] += int(count)

    resolved = status.isin(["Fully Paid", "Charged Off"])
    eligible = chunk.loc[resolved]
    resolved_rows += len(eligible)

    for column in available_features:
        values = eligible[column].str.strip()
        feature_missing[column] += int(values.eq("").sum())

        if column in numeric_features:
            invalid = (
                values.ne("")
                & pd.to_numeric(values, errors="coerce").isna()
            )
            invalid_numeric[column] += int(invalid.sum())

    for column in ["home_ownership", "emp_length"]:
        if column in eligible:
            values = eligible[column].str.strip().replace("", "(blank)")
            for value, count in values.value_counts().items():
                group_counts[(column, value)] += int(count)

    if total_rows % 250_000 == 0:
        print(f"Checked {total_rows:,} rows...", flush=True)

summary = {
    "total_rows": total_rows,
    "provisional_resolved_rows": resolved_rows,
    "problem_row_counts": dict(problem_counts),
    "candidate_features_absent": [
        c for c in candidate_features if c not in header
    ],
}

(output / "readiness_summary.json").write_text(
    json.dumps(summary, indent=2), encoding="utf-8"
)

pd.DataFrame(problem_samples).to_csv(
    output / "problem_rows_sample.csv", index=False
)

pd.DataFrame(
    [(*key, count) for key, count in year_term_status.items()],
    columns=["issue_year", "term", "loan_status", "row_count"],
).sort_values(
    ["issue_year", "term", "loan_status"]
).to_csv(output / "status_by_year_term.csv", index=False)

quality = pd.DataFrame([
    {
        "feature": column,
        "blank_count": feature_missing[column],
        "blank_percent": round(
            100 * feature_missing[column] / resolved_rows, 2
        ) if resolved_rows else None,
        "nonblank_invalid_numeric_count": (
            invalid_numeric[column]
            if column in numeric_features else None
        ),
    }
    for column in available_features
])
quality.to_csv(output / "candidate_feature_quality.csv", index=False)

pd.DataFrame(
    [(*key, count) for key, count in group_counts.items()],
    columns=["attribute", "group", "row_count"],
).to_csv(output / "candidate_group_counts.csv", index=False)

flagged = [
    column for column in header
    if column in later_outcome_fields
    or column.startswith(("hardship_", "settlement_"))
    or column.startswith("debt_settlement_")
    or column in [
        "deferral_term", "payment_plan_start_date",
        "orig_projected_additional_accrued_interest",
    ]
]
pd.DataFrame({"field_to_exclude_or_review": flagged}).to_csv(
    output / "later_outcome_fields.csv", index=False
)

print("\nSECOND AUDIT SUMMARY")
print(json.dumps(summary, indent=2))
print("\nCANDIDATE FEATURE QUALITY — RESOLVED LOANS ONLY")
print(quality.to_string(index=False))
print(f"\nReports saved to: {output}")
