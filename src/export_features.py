from pathlib import Path
import csv
import json
from impala.dbapi import connect

project = Path(__file__).resolve().parents[1]
output = project / "data" / "features"
output.mkdir(parents=True, exist_ok=True)

expected = {
    "train": 143892,
    "validation": 71955,
    "test": 90615,
}

connection = connect(
    host="localhost",
    port=10000,
    user="hive",
    database="credit_risk",
    auth_mechanism="PLAIN",
    timeout=120,
)

summary = {}

try:
    for split, expected_rows in expected.items():
        cursor = connection.cursor()
        temporary = output / f"{split}.csv.partial"
        destination = output / f"{split}.csv"

        try:
            cursor.execute(
                "SELECT * FROM credit_risk.model_features "
                f"WHERE data_split = '{split}'"
            )

            columns = [item[0].rsplit(".", 1)[-1] for item in cursor.description]
            count = 0

            with temporary.open(
                "w", newline="", encoding="utf-8"
            ) as handle:
                writer = csv.writer(handle)
                writer.writerow(columns)

                while True:
                    rows = cursor.fetchmany(10000)
                    if not rows:
                        break
                    writer.writerows(rows)
                    count += len(rows)
                    print(f"{split}: exported {count:,} rows",
                          flush=True)

            if count != expected_rows:
                raise RuntimeError(
                    f"{split}: expected {expected_rows:,} rows, "
                    f"received {count:,}"
                )

            temporary.replace(destination)
            summary[split] = {
                "rows": count,
                "columns": columns,
                "file": str(destination),
            }

        finally:
            cursor.close()

finally:
    connection.close()

(output / "export_manifest.json").write_text(
    json.dumps(summary, indent=2), encoding="utf-8"
)

print("\nEXPORT COMPLETE")
for split, details in summary.items():
    print(f"{split}: {details['rows']:,} rows")
