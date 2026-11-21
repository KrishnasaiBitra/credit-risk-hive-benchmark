# Credit-risk Hive benchmark

The project predicts charged-off versus fully paid Lending Club loans, benchmarks
three equivalent Hive pipelines and audits home-ownership group disparities.

**Live demonstration:** [Credit Risk Lab](https://credit-risk-hive-benchmark.vercel.app/)

The **Model comparison** page contains all four predictive models, a Dummy
baseline, four ROC/PR curves, selectable confusion matrices and a **Reference
papers** view. The paper view attributes the 2025 Random Forest, LightGBM and
XGBoost scores by title and DOI; it does not claim a matched replication. Download
the [full comparison report](results/model_extensions/MODEL_REFERENCE_COMPARISON.md)
for source locations, decision thresholds and evaluation limits.

## New model extension

CatBoost and Adaptive Random Forest are implemented in a separate experiment.
See [method and results](results/model_extensions/MODEL_EXTENSION_REPORT.md),
the **New model experiments** page and the four-model loan demo. CatBoost uses
its official standalone export for hosted inference; River is pinned at 0.27.0.
Original experiment files remain unchanged. The reused historical holdout does
not establish a new confirmatory performance improvement or live drift adaptation.

- [Reproduce and verify the work](REPRODUCE.md)
- [Report](results/report/project_results.md)
- [Demo guide and presentation outline](DEMO_GUIDE.md)
- [References](references.bib)
- [Infrastructure details](infrastructure/SETUP_GUIDE.md)

## Reported findings

On 306,462 loans, median full-export times were 34.96 s for CSV, 30.14 s for raw ORC
and 3.35 s for prepared ORC, over five measured runs per pipeline. Logical storage
was 50.17 MB, 5.99 MB and 7.65 MB, respectively. Preparation costs were recorded
separately. Every pipeline produced equivalent feature values.

On 90,615 held-out test loans, Logistic Regression ROC-AUC was 0.6537 and LightGBM
ROC-AUC was 0.6644 at the frozen model configurations. Both use validation-selected
threshold 0.15. LightGBM had smaller observed home-ownership gaps, but substantial
disparities and false positives remain. Row-bootstrap intervals are conditional
on the fixed models and assume independent loan rows.

## Status and boundaries

Core experiments, test evaluation and report draft are complete. Standalone
verification, benchmark and isolated replay scripts are now supplied. New runs
go to `results/reproducibility` and do not replace reported findings. Read the
verification status document in that directory for executed checks.

The cohort is retrospective and not a prospective label-availability simulation.
The roughly 50 MB CSV/single-host benchmark does not establish large-cluster
scalability. The dashboard is a presentation of saved research results; SHAP analysis and fairness mitigation are not implemented.
Lecturer-specific cover details, formatting and a finished slide deck still
depend on the submission requirements.

## Quick start in Ubuntu

```bash
cd /mnt/c/Users/krish/Desktop/big-data-project
source ~/venvs/credit-risk/bin/activate
python src/verify_project.py
```

Use `REPRODUCE.md` to start services, run Hive verification and rerun experiments.
No model retraining is needed to review the original results.

## Lecturer demonstration interface

The local HTML/CSS/JavaScript + FastAPI interface is in `interface/`. It includes eight
pages: overview, project architecture, pipeline benchmark, model comparison, fairness audit, research comparison, loan risk demo
and report downloads. It uses saved results and the frozen models without requiring
Hive or Docker. See [interface/README.md](interface/README.md).

In Ubuntu, run `bash interface/start.sh` from the project root, then open
http://localhost:8000. On Windows, double-click `interface/start-dashboard.bat`.
The interface is a research demonstration, not a loan approval system.

## GitHub release and hosted demonstration

The release includes the research source, Hive SQL, Docker Compose topology,
original model binaries, aggregate results, comparison tables and report.
The full Kaggle download, row-level feature exports/predictions, credentials,
Docker volumes, JDBC/Tez downloads and repeated replay directories are excluded.
Download the accepted-loan dataset from the linked Kaggle source to reproduce
the data pipeline. See [DEPLOYMENT.md](DEPLOYMENT.md) for deployment and data scope.

The hosted interface reads compact payloads exported from the original result
files. These are the same chart values, schema and six public historical examples,
not newly invented or recomputed research scores. The saved-model predictions
are evaluated on the server; form inputs are not stored by this application.
