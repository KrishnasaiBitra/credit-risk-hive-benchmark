# Project demonstration and presentation outline

## What to explain first

Our question is which Hive design prepares and exports the same credit-risk
features most efficiently. We compare CSV, raw ORC and features prepared in ORC.
Separately, we compare two predictive models and audit home-ownership group errors.
The pipeline benchmark is the central Big Data Management contribution.

## A 10-minute demonstration

1. Show the problem, architecture and cohort selection (2 minutes).
2. Show Docker services and the three Hive pipeline definitions (1 minute).
3. Show the saved equivalence evidence: zero mismatches and 306,462 rows (1 minute).
4. Show original five-run timing and storage results (1 minute).
5. Optionally run a live single-repeat export smoke check (about 1 minute, varies).
6. Show test metrics, group-rate charts and confidence intervals (2 minutes).
7. Explain preparation costs, retrospective evaluation and limits (2 minutes).

Open Ubuntu and activate the project environment before the demonstration:

```bash
cd /mnt/c/Users/krish/Desktop/big-data-project
source ~/venvs/credit-risk/bin/activate
cd infrastructure
docker compose ps
cd ..
```

Show the original results without changing them:

```bash
cat results/pipeline_benchmark/exports_v2_20261108_124424/summary.csv
cat results/pipeline_benchmark/hdfs_storage_bytes.txt
cat results/final_test/test_metrics.csv
cat results/final_test/test_group_gaps.csv
```

Optional live check, saved separately from the original benchmark:

```bash
python src/benchmark_pipelines.py --repeats 1 --skip-initial
```

Do not retrain, change thresholds or delete volumes during the demonstration.
If live timing changes, explain caching and background load; use the original
five-run range as the recorded experimental evidence. If services are unavailable,
the report, charts, manifests and CSV tables still document the completed work.

## Suggested 10-slide content

1. Title, team/student details, lecturer and course.
2. Problem and research question; why pipeline design matters.
3. Prior work: 2017 Hadoop/Hive study and 2025 fairness/transparency study.
4. Dataset: source audit, cohort filters, target and train/validation/test counts.
5. Architecture: HDFS, Hive/metastore, YARN/Tez, Python models and audit.
6. Three pipelines and equivalence controls.
7. Export timing, storage, preparation cost and repeated-use estimate.
8. Final model comparison; why accuracy alone is misleading.
9. Home-ownership rates and paired confidence intervals.
10. Limits, reproducibility evidence, conclusion and possible future work.

Existing chart files are in `results/report/figures`. This is an outline, not a
finished PowerPoint deck; college branding/template and student details are not assumed.

## Questions you should be able to answer

**Why Hive?** It is the required Big Data Management baseline. Hive centralizes
schema/SQL feature preparation over HDFS and lets us compare physical storage and
materialization choices under the same transformation rules.

**Does ORC improve accuracy?** No accuracy gain is attributed to ORC. All pipeline
feature values were checked for equivalence; model quality is a separate experiment.

**Why prepared ORC is faster?** It reads previously computed features instead of
repeating text parsing, conversions, calculations and the statistics join. The
measured gain also reflects the execution path; no isolated causal attribution
to a single optimization was performed.

**Why only two models?** Logistic Regression provides a simple baseline and
LightGBM provides nonlinear tree boosting. A controlled comparison is more useful
than adding algorithms without a defined research question or tuning budget.

**Why not report 85.87% accuracy as the best result?** The dummy achieves that by
predicting every loan as fully paid and catches no charge-offs. Ranking, recall,
false positives, precision and probabilistic error reveal the actual trade-off.

**Is the best model fair?** It has smaller measured home-ownership disparities,
but large gaps remain. Home ownership is a socioeconomic grouping and an input,
not a complete protected-demographic or causal discrimination analysis.

**Is the split a realistic deployment simulation?** No. It is retrospective by
issue date. Outcomes of all training loans would not have been available at the
start of validation/test issuance. This is an explicit limitation.

**Does a 10.44x speedup generalize to all big data?** No. It applies to repeated
full-feature exports in this single-host experiment on the selected cohort.

**Is cost measured in money?** No. We measured storage, preparation time and
sampled resource usage. There is no cloud-billing or electricity-cost estimate.

**What is new?** The project combines an equivalent-data Hive pipeline comparison,
explicit preparation/repeated-use costs, reproducible predictive baselines and
a quantitative group audit. It does not claim a new learning algorithm or prove
that no previous work has combined these ideas.

## Paper-versus-project comparison

Open the Research comparison page after the model results. Table V of the 2025
paper reports higher predictive scores (LightGBM AUC 0.8981) than our recorded
LightGBM test AUC (0.6644). These are different experiments, not a matched ranking.
The 2017 paper reports descriptive Hive loan analysis, without classifier accuracy
or a comparable timed pipeline baseline. Our added work is the controlled Hive
benchmark, numeric group errors and reproducibility evidence. We do not claim
that we improved the 2025 paper's predictive accuracy or implemented SHAP.
Kaggle is the data source, not a third research paper. The report includes the
comparison under section 2; downloadable score and method tables are available.


## Interactive architecture walkthrough

Open Project architecture from the sidebar. Research workflow shows all 12 stages from the accepted-loan CSV to the saved report and website. Select any stage for its input, processing, output, purpose and implementation evidence. Use Previous / Next stage for a lecturer walkthrough and Back to flow to return to the diagram.

Switch to Website request flow to show the two independent paths: browsing recorded results and submitting a new fixed-model prediction. Expand the 19-input list and explain the technology roles below the flow. This view documents the implemented system; it does not execute cluster jobs or retrain models.
