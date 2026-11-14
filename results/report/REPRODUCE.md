# Reproduce the credit-risk project

This guide distinguishes the reported experiment from later verification runs.
Run commands in **Ubuntu/WSL Bash**, not PowerShell, unless explicitly indicated.
Copy complete shell code blocks. Python snippets must be run through Python.

## 1. Resume the existing project

```bash
cd /mnt/c/Users/krish/Desktop/big-data-project
source ~/venvs/credit-risk/bin/activate
python -m pip check
cd infrastructure
docker compose up -d
docker compose ps
cd ..
```

The `.env` file selects the five Compose files. Scripts that call Compose set their
working directory to `infrastructure`; this avoids the earlier COMPOSE_FILE path error.
Allow Hive to finish starting before a query. If a connection is refused, inspect
`docker compose logs --tail=100 hiveserver2` from `infrastructure`, then retry.
If a restarted cluster retains a broken Tez session, restart HiveServer2 and reconnect.
Do not remove persistent volumes to fix a connection error.

## 2. Verify the reported work without retraining

```bash
python src/verify_project.py --hive
```

This checks frozen model/config/test-file hashes, row counts, unique IDs, split
disjointness, selected thresholds and metrics recomputed from saved predictions.
It also re-executes all three complete-row Hive equivalence checks. Reports are
saved in a new `results/reproducibility/verification_*.json` file. A successful
check confirms internal consistency; it does not prove realistic label availability.

## 3. Rerun the export benchmark

```bash
python src/benchmark_pipelines.py --repeats 5
```

The default matches the reported procedure: fixed initial order Raw ORC, CSV,
prepared ORC; one initial export per pipeline excluded from summaries; five
measured exports per pipeline; shuffled measured order with seed 42; 10,000-row
batches; fresh cursor for every export; query-result caching disabled. Full export
time includes Hive work, transfer, CSV serialization and file close. There is no
forced disk sync or OS/JVM cache reset. Do not call this cold-cache or isolated
engine latency. Temporary CSVs are deleted after valid runs; failed CSVs are retained.

For a shorter **verification only**, use `--repeats 1 --skip-initial`. A single run
is a smoke check and must not replace the original five-run findings.

Every run prints its unique results directory under `results/reproducibility/exports`.
It contains `configuration.json`, per-export `runs.csv` and `summary.csv`. Failure
sets status `failed`; incomplete runs must not be used for comparisons. Run one
benchmark at a time and avoid unrelated heavy work. Expect timings to vary with
cache state, background load, warm-up and the machine.

## 4. Rerun the monitored resource experiment separately

```bash
python src/benchmark_pipelines.py --monitor --repeats 3 --skip-initial
```

Use the exact new directory printed by the command in place of RUN_DIRECTORY:

```bash
python src/summarize_resources.py RUN_DIRECTORY
```

The monitor covers the seven project containers, including YARN workers, but
excludes Python-client resources. Only complete snapshots ending within an export
are summarized. Percent CPU can exceed 100% across cores. Maximum sampled memory
is not a true peak or incremental query memory. Prepared ORC's short runtime may
produce very few snapshots; do not infer strong CPU-efficiency claims from this.
Monitoring adds overhead, so use the unmonitored run for the main latency results.

## 5. Preparation time, storage and environment

```bash
python src/benchmark_preparation.py
python src/capture_environment.py
```

Preparation jobs use uniquely named managed scratch tables and drop only those
tables afterward. Neither original raw ORC nor prepared ORC is overwritten. Jobs
time CSV-to-raw-ORC and existing-raw-ORC-to-prepared-features separately, excluding
DDL and training. Their sum is an estimate, not a directly timed cold full chain.
The environment capture saves service/image/version information, HDFS directory
sizes and a post-workload resource snapshot; it is not a workload resource trace.
Repeated measurements are new evidence and never overwrite the historical values.

## 6. Isolated feature and model replay

```bash
python src/replay_project.py --train
```

This creates a new `credit_risk_replay_TIMESTAMP` Hive database and
`/credit-risk/replays/TIMESTAMP` HDFS directories. It uploads the existing cohort,
rebuilds tables/views using saved SQL, recomputes the training-only approximate
medians, verifies them against recorded training statistics, and checks complete
pipeline equivalence. Each exported split is compared by loan ID with the original
export using a tight numeric tolerance.

The replay then copies the modelling scripts into its own output directory,
trains there, selects thresholds using the same validation-only rule and evaluates
the replay models there. Original `models`, `results/final_test` and published
benchmarks remain untouched. New exports use stable loan-ID ordering, whereas the
original exports were unordered; fitted models need not be bit-identical. The saved
`reported_vs_replay_models.csv` makes any differences visible. Do not choose a new
model configuration based on the already-seen test results.

Use `python src/replay_project.py` without `--train` for a features-only replay.
The manifest records a failure without deleting the isolated namespace. Successful
replays remain available for inspection and consume additional storage. No broad
cleanup or volume deletion is required.

### Preserve original model input order

The sorted-row replay is also an ordering-sensitivity experiment. For an exact
metric replay, align the reconstructed features to the original frozen export IDs:

```bash
python src/replay_models.py --features-dir REPLAY_DIRECTORY/data/features
```

Replace REPLAY_DIRECTORY with the directory printed by the feature replay. This
checks all reconstructed values, preserves original row order, trains only in a
new folder, and records the maximum absolute difference from reported test metrics.
Neither experiment changes the original selected models. Timing values and model
serialization bytes need not be identical even when evaluation metrics match.

## 7. Rebuild from the public source file

The replay intentionally starts from the existing audited cohort. To repeat the
earlier raw-file stage, run the following in a separate copy of the project before
the replay. Keep the original experiment evidence intact.

```bash
python src/audit_dataset.py
python src/audit_model_readiness.py
python src/build_cohort.py
```

Expected source path:
`archive/accepted_2007_to_2018q4.csv/accepted_2007_to_2018Q4.csv`.
The audit reports 2,260,701 rows, including 33 footer/summary records. The cohort
contains 306,462 resolved 36-month loans issued in 2012-2014, with 22 raw columns.
The cohort builder requires that count and preserves the original source file.

## 8. Fresh machine or fresh Docker volumes

Use the supplied infrastructure directory, including XML configuration,
`jdbc/postgresql-42.7.5.jar`, `runtime/tez-0.10.5.tar.gz`, Compose files and `.env`.
Use Docker Desktop with Ubuntu WSL integration and the recorded Python 3.14.4
environment. The locked packages are in `requirements-lock.txt`:

```bash
python3.14 -m venv ~/venvs/credit-risk
source ~/venvs/credit-risk/bin/activate
python -m pip install -r requirements-lock.txt
python -m pip check
```

The exact interpreter and tagged images may not remain obtainable indefinitely;
recorded versions/image identifiers describe the tested environment. Avoid replacing
versions silently. Image tags alone are not immutable. Installation of WSL/Docker
depends on the Windows machine and is outside this data-replay command.

For **new volumes only**, initialize storage before starting all services:

```bash
cd infrastructure
docker compose up -d namenode datanode postgres
docker compose exec -T namenode hdfs dfsadmin -safemode wait
docker compose exec -T namenode hdfs dfs -mkdir -p /apps/tez /user/hive/tez-staging /warehouse/managed /warehouse/external /tmp
docker compose exec -T namenode hdfs dfs -chown -R hive /user/hive /warehouse
docker compose exec -T namenode hdfs dfs -chmod 1777 /tmp
docker compose exec -T namenode hdfs dfs -put - /apps/tez/tez-0.10.5.tar.gz < runtime/tez-0.10.5.tar.gz
docker compose run --rm --no-deps --user 0 --entrypoint /bin/bash nodemanager -c 'mkdir -p /tmp/yarn-logs && chown 1000:1000 /tmp/yarn-logs'
docker compose up -d
docker compose ps
cd ..
```

Wait for HiveServer2 and the metastore to initialize, then run the raw-file stage
and isolated replay above. Fresh-volume initialization is documented but has not
been retested by destroying the existing project. If HDFS is still starting, wait
and retry its readiness check. Never run `docker compose down -v` on the original
experiment; that removes HDFS and metastore data.

The replay SQL namespace is self-contained. To benchmark an isolated replay,
pass its printed database name through `benchmark_pipelines.py --database NAME`.
Recreating the historical `credit_risk` namespace is unnecessary.

## 9. Recreate uncertainty and the report

For the original fixed predictions, the existing uncertainty directory is protected.
To rerender saved bootstrap draws without resampling:

```bash
python src/bootstrap_test_results.py --project "$PWD" --reuse-results
```

For a new modelling replay, run its copied bootstrap script with that replay folder
as `--project` (no `--reuse-results` on its first run). Report assembly is available
as `src/build_results_report.py --project PROJECT_ROOT`; it reads the original
experiment directories recorded in the script and refuses to replace an existing
`results/report` directory. The report is an assembly of known original experiments,
not a general report builder for arbitrary replay directories. The PDF was rendered
separately; `results/report/project_results.md` is the editable report source.

## 10. Interpretation and submission boundaries

The main result is a pipeline comparison on one roughly 50 MB cohort CSV, not a
large-cluster scalability claim. Prediction is retrospective Charged Off versus
Fully Paid classification. The issue-date split does not establish that all training
outcomes were known at validation/test origination. Home ownership is both an input
and an audit grouping; group gaps do not prove protected-demographic fairness or
discrimination. Independent-row bootstrap intervals exclude training/selection and
time-dependence uncertainty. SHAP, mitigation, a dashboard and cloud-money costing
are not implemented requirements. A college-specific report template and slides
can be prepared after the lecturer confirms their format.
