from pathlib import Path
import json
import pandas as pd

project = Path(__file__).resolve().parents[1]
source = (
    project / "archive"
    / "accepted_2007_to_2018q4.csv"
    / "accepted_2007_to_2018Q4.csv"
)
destination = project / "data/cohort/credit_cohort.csv"
destination.parent.mkdir(parents=True, exist_ok=True)
temporary = destination.with_suffix(".csv.partial")

columns = [
    "id", "issue_d", "loan_status", "loan_amnt", "term",
    "annual_inc", "dti", "emp_length", "home_ownership",
    "purpose", "verification_status",
    "fico_range_low", "fico_range_high",
    "delinq_2yrs", "inq_last_6mths", "open_acc", "pub_rec",
    "revol_bal", "revol_util", "total_acc",
    "pub_rec_bankruptcies", "earliest_cr_line",
]

total = 0
first_chunk = True

for chunk in pd.read_csv(
    source,
    usecols=columns,
    dtype="string",
    keep_default_na=False,
    chunksize=25_000,
):
    issued = pd.to_datetime(
        chunk["issue_d"], format="%b-%Y", errors="coerce"
    )

    selected = (
        issued.dt.year.between(2012, 2014)
        & chunk["term"].str.strip().eq("36 months")
        & chunk["loan_status"].isin(["Fully Paid", "Charged Off"])
        & chunk["id"].str.fullmatch(r"\d+", na=False)
    )

    cohort = chunk.loc[selected, columns].copy()
    if cohort.empty:
        continue

    cohort.to_csv(
        temporary,
        mode="w" if first_chunk else "a",
        header=first_chunk,
        index=False,
    )
    first_chunk = False
    total += len(cohort)

if total != 306_462:
    raise SystemExit(
        f"Unexpected count: {total:,}. "
        "The partial file was retained for investigation."
    )

temporary.replace(destination)

manifest = {
    "source": str(source),
    "cohort": str(destination),
    "records": total,
    "columns": columns,
    "eligibility": {
        "issue_years": [2012, 2013, 2014],
        "term": "36 months",
        "statuses": ["Fully Paid", "Charged Off"],
        "id": "nonblank numeric",
    },
    "changes": "Row and column selection only; no imputation or clipping.",
    "evaluation": "Retrospective split by issuance date, not deployment simulation.",
}
(destination.parent / "cohort_manifest.json").write_text(
    json.dumps(manifest, indent=2), encoding="utf-8"
)

print(f"Cohort saved: {destination}")
print(f"Records: {total:,}")
print(f"Columns: {len(columns)}")
print(f"File size: {destination.stat().st_size / 1_000_000:.2f} MB")
