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

if not source.is_file():
    raise SystemExit(f"Dataset not found: {source}")

total_rows = 0
statuses = Counter()
years = Counter()
missing = Counter()
seen_ids = set()
duplicate_ids = 0
blank_ids = 0
invalid_dates = 0
earliest = None
latest = None
columns = None

print("Reading the dataset in chunks of 25,000 rows...", flush=True)

for chunk_number, chunk in enumerate(
    pd.read_csv(
        source,
        chunksize=25_000,
        dtype="string",
        keep_default_na=False,
    ),
    start=1,
):
    if columns is None:
        columns = chunk.columns.tolist()
        required = {"id", "loan_status", "issue_d"}
        absent = required.difference(columns)
        if absent:
            raise SystemExit(f"Required columns missing: {sorted(absent)}")

    total_rows += len(chunk)

    for column in columns:
        missing[column] += int(chunk[column].str.strip().eq("").sum())

    status = chunk["loan_status"].str.strip().replace("", "(blank)")
    statuses.update(status.tolist())

    dates = pd.to_datetime(
        chunk["issue_d"].str.strip(),
        format="%b-%Y",
        errors="coerce",
    )
    invalid_dates += int(dates.isna().sum())
    valid_dates = dates.dropna()

    if not valid_dates.empty:
        first = valid_dates.min()
        last = valid_dates.max()
        earliest = first if earliest is None else min(earliest, first)
        latest = last if latest is None else max(latest, last)
        years.update(valid_dates.dt.year.astype(int).tolist())

    for loan_id in chunk["id"].str.strip():
        if loan_id == "":
            blank_ids += 1
        elif loan_id in seen_ids:
            duplicate_ids += 1
        else:
            seen_ids.add(loan_id)

    if chunk_number % 10 == 0:
        print(f"Checked {total_rows:,} rows...", flush=True)

summary = {
    "source_file": str(source),
    "total_rows": total_rows,
    "total_columns": len(columns or []),
    "unique_nonblank_loan_ids": len(seen_ids),
    "repeated_nonblank_loan_id_rows": duplicate_ids,
    "blank_loan_id_rows": blank_ids,
    "earliest_issue_month": (
        earliest.strftime("%Y-%m") if earliest is not None else None
    ),
    "latest_issue_month": (
        latest.strftime("%Y-%m") if latest is not None else None
    ),
    "blank_or_unparseable_issue_dates": invalid_dates,
}

(output / "summary.json").write_text(
    json.dumps(summary, indent=2), encoding="utf-8"
)

pd.DataFrame(
    statuses.most_common(), columns=["loan_status", "row_count"]
).to_csv(output / "loan_status_counts.csv", index=False)

pd.DataFrame(
    sorted(years.items()), columns=["issue_year", "row_count"]
).to_csv(output / "issue_year_counts.csv", index=False)

missing_report = pd.DataFrame({
    "column": columns,
    "missing_count": [missing[column] for column in columns],
})
missing_report["missing_percent"] = (
    missing_report["missing_count"] / total_rows * 100
).round(2)
missing_report.sort_values(
    "missing_count", ascending=False
).to_csv(output / "missing_values.csv", index=False)

pd.DataFrame({"column": columns}).to_csv(
    output / "columns.csv", index=False
)

print("\nAUDIT SUMMARY")
print(json.dumps(summary, indent=2))
print("\nLOAN STATUSES")
for status, count in statuses.most_common():
    print(f"{status}: {count:,}")

print(f"\nReports saved to: {output}")
