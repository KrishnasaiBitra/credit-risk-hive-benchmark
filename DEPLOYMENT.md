# Deployment

Python 3.14; FastAPI entrypoint `app.py`. Vercel uses the repository root.
Install runtime packages with `pip install -r requirements.txt` and run locally:

```bash
python -m uvicorn app:app --host 127.0.0.1 --port 8000
```

The full experimental environment remains documented in `requirements-lock.txt`.
No Hive/Hadoop services run on Vercel. It hosts the dashboard and fixed-model
inference only; all cluster measurements were recorded in the local experiment.

## Included data

`interface/runtime/` contains source-derived research/schema/curve payloads and
six historical examples from the public dataset. Original model binaries and
their recorded SHA-256 fingerprints are preserved. Original bulk data and
row-level prediction CSVs are not uploaded. To rerun the research, supply the
Kaggle accepted-loan file and follow REPRODUCE.md; not every data-dependent
verification script can run from a data-free clone alone.

The website displays borrower-risk estimates for a research demonstration.
It is not a production lending decision system. Its test scores and threshold
were not changed for hosting.

## Local infrastructure

Copy `infrastructure/.env.example` to `infrastructure/.env`, set a local database
password, and download the official PostgreSQL JDBC driver into the path used
by Compose. See infrastructure/SETUP_GUIDE.md for the original lab setup and
REPRODUCE.md for the Tez runtime preparation. Local binary dependencies and
data volumes are deliberately excluded from Git.
