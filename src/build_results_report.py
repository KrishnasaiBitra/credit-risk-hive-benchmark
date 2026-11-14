"""Assemble the credit-risk results report and figures from saved experiment files."""
from pathlib import Path
import argparse
import hashlib
import json
import math
import shutil

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sklearn.metrics import roc_curve, precision_recall_curve


def md_table(frame, digits=4):
    def cell(value):
        return f'{value:.{digits}f}' if isinstance(value, (float, np.floating)) else str(value)
    return '\n'.join([
        '| ' + ' | '.join(map(str, frame.columns)) + ' |',
        '| ' + ' | '.join(['---']*len(frame.columns)) + ' |',
        *['| ' + ' | '.join(cell(v) for v in row) + ' |' for row in frame.itertuples(index=False, name=None)],
    ])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True)
    project = parser.parse_args().project.resolve()
    benchmark = project / 'results/pipeline_benchmark'
    final = project / 'results/final_test'
    uncertainty = final / 'uncertainty'
    output = project / 'results/report'
    output.mkdir(exist_ok=False)
    figures = output / 'figures'
    figures.mkdir()
    latency_folder = benchmark / 'exports_v2_20261108_124424'
    resources_folder = benchmark / 'resources_20261108_130043'
    latency = pd.read_csv(latency_folder / 'summary.csv').set_index('pipeline').loc[['CSV', 'Raw_ORC', 'Prepared_ORC']].reset_index()
    runs = pd.read_csv(latency_folder / 'runs.csv')
    resource = pd.read_csv(resources_folder / 'resource_summary.csv')
    metrics = pd.read_csv(final / 'test_metrics.csv')
    groups = pd.read_csv(final / 'test_group_metrics.csv')
    gaps = pd.read_csv(final / 'test_group_gaps.csv')
    paired = pd.read_csv(uncertainty / 'paired_model_differences.csv')
    intervals = pd.read_csv(uncertainty / 'metric_confidence_intervals.csv')
    conversion_file = benchmark / 'raw_orc_conversion_20261108_125602.json'
    conversion = json.loads(conversion_file.read_text())['conversion_seconds']
    preparation = json.loads((benchmark / 'prepared_orc_creation.json').read_text())['insert_seconds']
    environment = json.loads((benchmark / 'environment/python_versions.json').read_text())
    manifest = json.loads((final / 'evaluation_manifest.json').read_text())
    for relative, expected in manifest['file_sha256'].items():
        actual = hashlib.sha256((project / relative).read_bytes()).hexdigest()
        assert actual == expected, f'Frozen input changed: {relative}'
    assert runs[runs.phase=='measured'].groupby('pipeline').size().eq(5).all()
    assert runs.row_count.eq(306462).all()
    for name in ['raw_orc_equivalence.json', 'orc_feature_equivalence.json', 'prepared_orc_equivalence.json']:
        assert json.loads((benchmark / name).read_text())['passed']

    storage = [line.split() for line in (benchmark / 'hdfs_storage_bytes.txt').read_text().splitlines() if line.strip()]
    sizes = {parts[2]: int(parts[0]) for parts in storage}
    paths = ['/credit-risk/raw/cohort', '/warehouse/external/raw_credit_orc', '/warehouse/external/model_features_prepared_orc']
    latency['logical_bytes'] = [sizes[path] for path in paths]
    latency['size_MB_decimal'] = latency.logical_bytes / 1e6
    latency['additional_preparation_seconds'] = [0., conversion, conversion+preparation]
    csv_time = latency.iloc[0].median_seconds
    latency['speedup_vs_csv'] = csv_time / latency.median_seconds
    latency['estimated_exports_to_recover_preparation'] = [0] + [
        math.ceil(row.additional_preparation_seconds/(csv_time-row.median_seconds))
        for row in latency.iloc[1:].itertuples()
    ]
    latency.to_csv(output / 'pipeline_comparison.csv', index=False)
    for name, frame in [('model_test_results', metrics), ('group_test_results', groups), ('group_gaps', gaps),
                        ('metric_confidence_intervals', intervals), ('paired_model_differences', paired),
                        ('resource_summary', resource)]:
        frame.to_csv(output / f'{name}.csv', index=False)

    plt.rcParams.update({'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False})
    colors = ['#60758b', '#397eb8', '#14836e']
    labels = ['CSV', 'Raw ORC', 'Prepared ORC']
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.5), layout='constrained')
    times = latency.median_seconds.to_numpy()
    errors = np.array([times-latency.minimum_seconds.to_numpy(), latency.maximum_seconds.to_numpy()-times])
    bars = axes[0].bar(labels, times, color=colors, yerr=errors, capsize=5)
    axes[0].bar_label(bars, labels=[f'{v:.2f}s' for v in times], padding=8)
    axes[0].set_ylim(0, 43)
    axes[0].set_ylabel('Full export time (seconds)')
    axes[0].set_title('Median and observed range: five runs')
    bars = axes[1].bar(labels, latency.size_MB_decimal, color=colors)
    axes[1].bar_label(bars, fmt='%.2f', padding=4)
    axes[1].set_ylim(0, 60)
    axes[1].set_ylabel('HDFS logical storage (decimal MB)')
    axes[1].set_title('Stored representation; replication factor 1')
    fig.suptitle('Same 306,462 loans and equivalent feature values')
    fig.savefig(figures / 'pipeline_performance.png', dpi=180)
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(10, 4.5), layout='constrained')
    for name, filename, color in [('Logistic Regression', 'logistic_regression_predictions.csv', '#3969ac'),
                                  ('LightGBM', 'lightgbm_predictions.csv', '#13866c')]:
        frame = pd.read_csv(final / filename)
        actual, probability = frame.target, frame.probability
        fpr, tpr, _ = roc_curve(actual, probability)
        precision, recall, _ = precision_recall_curve(actual, probability)
        result = metrics[metrics.model==name].iloc[0]
        axes[0].plot(fpr, tpr, color=color, label=f'{name} (AUC {result.roc_auc:.3f})')
        axes[1].plot(recall, precision, color=color, label=f'{name} (AP {result.average_precision:.3f})')
    axes[0].plot([0,1], [0,1], '--', color='gray', label='Random ranking')
    axes[1].axhline(actual.mean(), color='gray', ls='--', label=f'Charge-off rate ({actual.mean():.3f})')
    for ax in axes:
        ax.set_xlim(0,1)
        ax.set_ylim(0,1)
        ax.legend(fontsize=8)
        ax.grid(alpha=.2)
    axes[0].set(xlabel='False-positive rate', ylabel='Charge-off recall', title='Test ROC curves')
    axes[1].set(xlabel='Charge-off recall', ylabel='Precision', title='Test precision–recall curves')
    fig.savefig(figures / 'test_discrimination.png', dpi=180)
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5), layout='constrained')
    group_order = ['MORTGAGE', 'RENT', 'OWN']
    for ax, metric, title in zip(axes, ['false_positive_rate', 'chargeoff_recall'], ['False-positive rate', 'Charge-off recall']):
        for j, (name, color) in enumerate([('Logistic Regression','#3969ac'), ('LightGBM','#13866c')]):
            data = groups[groups.model==name].set_index('group').loc[group_order]
            centers = np.arange(3)+(j-.5)*.34
            ci = intervals[intervals.model==name].set_index('metric')
            lower = np.array([ci.loc[f'{g}_{metric}', 'lower_95'] for g in group_order])
            upper = np.array([ci.loc[f'{g}_{metric}', 'upper_95'] for g in group_order])
            values = data[metric].to_numpy()
            ax.bar(centers, values*100, width=.32, color=color, label=name,
                   yerr=np.array([values-lower, upper-values])*100, capsize=3)
        ax.set_xticks(np.arange(3), group_order)
        ax.set_ylim(0, 80)
        ax.set_ylabel('Percent')
        ax.set_title(title)
        ax.legend(fontsize=8)
    fig.suptitle('Home-ownership audit at threshold 0.15; 95% row-bootstrap intervals')
    fig.savefig(figures / 'test_group_audit.png', dpi=180)
    plt.close(fig)
    shutil.copyfile(uncertainty / 'test_confidence_intervals.png', figures / 'test_confidence_intervals.png')

    model_table = metrics[['model', 'threshold', 'accuracy', 'precision', 'chargeoff_recall', 'false_positive_rate', 'f1', 'roc_auc', 'average_precision', 'brier_score']]
    group_table = groups[groups.group.isin(group_order)][['model','group','loans','charged_off','precision','chargeoff_recall','false_positive_rate','flag_rate']]
    differences = paired[paired.metric.isin(['roc_auc','average_precision','f1','brier_score','chargeoff_recall_gap','false_positive_rate_gap'])]
    resource_table = resource.groupby('pipeline').agg(
        median_of_run_cpu_medians=('median_sampled_total_cpu_percent','median'),
        highest_sampled_memory_MiB=('maximum_sampled_total_memory_mib','max'),
        minimum_snapshots_per_run=('complete_snapshots_during_export','min'),
        maximum_snapshots_per_run=('complete_snapshots_during_export','max'),
    ).reset_index()
    resource_table.to_csv(output / 'resource_comparison.csv', index=False)
    feature_text = ', '.join(f'`{f}`' for f in manifest['features'])
    package_text = ', '.join(f'{k} {v}' for k,v in environment['packages'].items())
    report = f'''# A Reproducible Benchmark of Credit Risk Pipelines: A Hive Study

Results report draft — assembled from saved experiment outputs on 8 November 2026.

## Abstract

This project studies how Hive pipeline design affects the preparation and export of credit-risk features. It uses a public Lending Club dataset to construct a cohort of 306,462 resolved, 36-month loans issued during 2012–2014. Three pipelines are compared: CSV with features calculated during queries, raw ORC with the same calculations, and prepared ORC with features stored in advance. Data-equivalence checks confirm matching feature values. Median complete-export times over five measured runs are 34.96, 30.14 and 3.35 seconds, respectively. Separately, Logistic Regression and LightGBM predict charged-off versus fully paid loans using the same 19 inputs. Their held-out test ROC-AUC scores are 0.6537 and 0.6644. A home-ownership audit finds smaller disparities for LightGBM, although substantial gaps remain. The results support prepared ORC for repeated feature exports in this single-machine experiment, with preparation cost reported separately. They do not establish large-cluster scalability, deployment-ready risk prediction, or absence of discrimination.

## 1. Problem and research questions

The lecturer's brief is to predict borrower risk, audit differences across groups, and benchmark Hive-based pipeline designs on accuracy, latency and cost. The main question is: which of the tested Hive designs exports equivalent credit-risk features most efficiently on this dataset and machine, and why?

The supporting questions are whether LightGBM improves on a simple Logistic Regression baseline and how their error rates differ across home-ownership groups. Pipeline speed and prediction quality are separate comparisons: changing storage format is not claimed to improve model accuracy.

## 2. References and relationship to prior work

1. *Bank loan analysis using customer usage data: A big data approach using Hadoop*, IEEE TEL-NET, 2017. Paper ID / DOI: [10.1109/TEL-NET.2017.8343582](https://doi.org/10.1109/TEL-NET.2017.8343582). This is the architectural background for Hadoop/HDFS/Hive loan analysis. Our project adds a controlled storage-and-feature-pipeline comparison, predictive baselines and a quantitative group audit.
2. *Assessing Fairness and Transparency in Credit Scoring Using Explainable AI*, IEEE CISCON, 2025. Paper ID / DOI: [10.1109/CISCON66933.2025.11337606](https://doi.org/10.1109/CISCON66933.2025.11337606). This motivates modern Lending Club modelling and fairness/transparency analysis. It compares tree-based models and discusses explainability; our implemented contribution is an explicit group-error audit combined with the Hive benchmark. SHAP and fairness mitigation have not been implemented here.

This is a related-work extension, not an exact reproduction of either paper. Their reported scores are not directly comparable because cohorts, features, class distributions and evaluation procedures differ. No claim is made that using LightGBM for lending is new, or that this is the first Hive fairness benchmark.

## 3. Dataset, target and cohort

Source: the accepted-loan file from the public [Lending Club dataset on Kaggle](https://www.kaggle.com/datasets/wordsforthewise/lending-club). The dataset audit found 2,260,701 source rows and 151 columns. Thirty-three summary/footer rows had missing loan status and invalid issue dates. The modelling cohort retains numeric loan IDs, issue years 2012–2014, 36-month terms, and statuses Fully Paid or Charged Off.

The final cohort has 306,462 loans: 40,596 charged off and 265,866 fully paid. Target 1 means Charged Off; target 0 means Fully Paid. This is a charge-off classification task, not a universal definition of default or a prediction over all loan applicants. Rejected applications are not included.

| Split | Issue dates | Loans |
| --- | --- | ---: |
| Train | January 2012–December 2013 | 143,892 |
| Validation | January–June 2014 | 71,955 |
| Test | July–December 2014 | 90,615 |

The mature 36-month cohort reduces the outcome-censoring problem visible in later issue years. However, the split is **retrospective**: outcomes of loans issued in 2013 would not all have been available when loans were issued in early 2014. This is not a demonstrated prospective deployment simulation. Unique loan IDs also do not establish unique borrowers.

## 4. Architecture and feature preparation

Accepted CSV → chunked audit and cohort extraction in Python → HDFS → Hive raw tables → typed/feature views → exported features → saved Python model pipelines → prediction and group evaluation.

HDFS stores data. Hive defines tables and transformations, the PostgreSQL-backed metastore stores metadata, and Tez runs processing through YARN. Python/scikit-learn/LightGBM train and evaluate the models outside Hive. Fairlearn was used for the validation audit; final group rates and bootstrap intervals are calculated from saved predictions.

There are 19 model inputs: {feature_text}.

Loan ID, split and target are tracking columns, not model inputs. The constant 36-month term is excluded. FICO ranges become a midpoint; earliest credit and issue dates become credit-history months; employment text becomes years; rare ownership categories become OTHER_UNKNOWN. Employment and utilization are filled using training-only medians, with missingness indicators retained. The same saved statistics are used in every pipeline. Numeric scaling and categorical one-hot encoding are fitted on training data only. Values of utilization above 100 are retained rather than silently capped.

## 5. Controlled Hive pipeline benchmark

| Pipeline | Hive source | Feature work during export |
| --- | --- | --- |
| CSV | `model_features` over raw CSV | Parsing, type conversion and feature calculations |
| Raw ORC | `model_features_orc` over raw ORC | Same feature calculations |
| Prepared ORC | `model_features_prepared_orc` | Reads already calculated features |

ORC uses ZLIB compression. Raw CSV and raw ORC contain identical complete-row values and multiplicities. Both calculated feature views match, and the prepared ORC table matches the ORC feature view. Schema and full-row comparisons all passed with zero mismatched row patterns. Data row order is not assumed to match.

Each pipeline had one initial export followed by five measured exports. Measured order was shuffled using seed 42. Every export returned 306,462 records. Query-result caching was disabled. OS/JVM caches were not cleared, so initial runs are not controlled cold-cache tests. Exports used fresh cursors, 10,000-row fetch batches and the same CSV-writing procedure. Timing includes query execution, transfer to Python, serialization and file close; it excludes forced filesystem synchronization. It is not isolated engine latency.

{md_table(latency[['pipeline','runs','median_seconds','minimum_seconds','maximum_seconds','size_MB_decimal','speedup_vs_csv']], 3)}

![Pipeline export time and storage](figures/pipeline_performance.png)

Prepared ORC is approximately {latency.iloc[2].speedup_vs_csv:.2f} times faster than CSV for this full-export workload. Raw ORC is approximately {latency.iloc[1].speedup_vs_csv:.2f} times faster. The first improvement combines ORC's representation/compression with the observed execution path; the larger prepared-ORC gain also avoids repeated parsing, calculations and the statistics join. An execution-plan study would be needed to isolate each cause.

Raw CSV occupies 50.165 MB, raw ORC 5.986 MB, and prepared ORC 7.653 MB (decimal units). Raw ORC is 88.1% smaller than the equivalent raw CSV. Prepared ORC stores a different, transformed representation. Keeping all three uses approximately 63.804 MB. HDFS logical bytes and replication-adjusted bytes match at replication factor 1; system metadata and temporary working files are not included in these directory totals.

### Preparation cost and repeated use

The repeat CSV-to-ORC conversion took {conversion:.2f} seconds. Feature calculation and ORC materialization then took {preparation:.2f} seconds in a separate measurement. Their sum, {conversion+preparation:.2f} seconds, estimates the two-stage preparation cost starting from the existing cohort CSV. It excludes initial dataset extraction, cluster startup, table creation and model training. These are single warm-system measurements, not distributions or controlled cold-start timings.

Estimated repeated-use totals are `CSV = n × 34.96 s`, `raw ORC = 13.56 + n × 30.14 s`, and `prepared ORC = 37.39 + n × 3.35 s`. Using the unrounded measurements, raw ORC recovers its additional preparation cost after about 3 exports and prepared ORC after about 2, relative to CSV. This is an arithmetic estimate, not a directly measured end-to-end break-even experiment. Prepared features must also be refreshed if source data or transformation rules change.

### Resource observations

Resource monitoring was conducted separately, over three exports per pipeline, because monitoring adds overhead. All seven project containers were sampled; Python-client usage was excluded. Boundary samples ending after export completion were excluded from the summary.

{md_table(resource_table, 2)}

CPU is the sum of container percentages and may exceed 100% when multiple cores are used. The aggregate shown is the median of per-run sampled CPU medians. Memory is the highest observed sum of container memory, including resident services. It is not an incremental-query measurement or a true peak. Prepared ORC has only 1–2 usable snapshots per run, so its CPU figures are exploratory. No electricity, cloud bill or total CPU-seconds estimate was measured. Here, cost is described using preparation time, storage and sampled resources.

## 6. Models and evaluation rules

The Dummy baseline uses the training class prior. Logistic Regression uses a training-fitted scaling/encoding pipeline and no class weighting. LightGBM uses the same input feature definitions and cloned, training-fitted preprocessing: learning rate 0.03, at most 1,000 estimators, 15 leaves, minimum 100 samples per leaf, L2 regularization 5, row/column sampling 0.8, seed 42 and two worker threads. Early stopping on validation AUC selects iteration 522. Training budgets differ; this is not an equal-budget hyperparameter search.

Each predictive model uses threshold 0.15, selected on validation F1 from the saved grid, breaking ties toward the higher threshold. The original 0.5-threshold baseline is retained in earlier outputs. F1 is an academic decision rule here, not an established lending-profit objective. The same validation set informed stopping and threshold choice, making those validation results selection-dependent.

Saved model/data/configuration SHA-256 fingerprints were recorded before final predictions. The test set was evaluated with fixed trained models and thresholds; no test-driven fitting or threshold changes were performed.

{md_table(model_table)}

![Test discrimination curves](figures/test_discrimination.png)

LightGBM improves modestly over Logistic Regression on AUC, average precision, F1 and Brier score. At threshold 0.15, it detects 54.34% of charged-off loans but flags 31.97% of fully paid loans. Only 21.85% of its flagged loans are actually charged off. The Dummy's higher accuracy is caused by majority-class predictions with zero charge-off recall. ROC-AUC and average precision describe ranking; Brier score measures probabilistic error and alone does not prove calibration.

## 7. Group audit

Home ownership is an available socioeconomic grouping and is also an input feature. MORTGAGE, RENT and OWN are compared. OTHER_UNKNOWN contains one test loan and is retained in the saved detailed results, but excluded from disparity gaps and confidence intervals for group rates. These are descriptive home-ownership disparities, not a protected-demographic audit or causal finding.

{md_table(group_table)}

{md_table(gaps)}

![Test group error rates](figures/test_group_audit.png)

The false-positive-rate gap is the maximum minus minimum group FPR; the recall gap is the maximum minus minimum group charge-off recall. Equalized-odds difference is the larger of these two gaps. Smaller values mean smaller observed disparities, not a guarantee of fairness. LightGBM reduces both gaps compared with Logistic Regression, but a roughly 23-percentage-point FPR gap and 25-percentage-point recall gap remain. Group base rates, feature distributions and use of home ownership itself may contribute; no causal attribution is established. No mitigation or group-specific thresholds were applied.

## 8. Uncertainty

One thousand paired ordinary row-bootstrap samples, seed 42, were drawn from the 90,615 test loans. Both models were evaluated on identical sampled rows in each replicate. Model parameters and thresholds stayed fixed. The following differences are LightGBM minus Logistic Regression; lower is better for Brier score and disparity gaps.

{md_table(differences[['metric','lightgbm_minus_logistic','lower_95','upper_95']], 6)}

![Model confidence intervals](figures/test_confidence_intervals.png)

The paired intervals exclude zero for these differences, supporting a modest model improvement conditional on this cohort and the independence assumption. Intervals are pointwise percentile intervals without multiple-comparison correction. Repeated borrowers and temporal dependence are not modeled. Training uncertainty, selection uncertainty and label-availability problems are not covered. The AUC/AP implementation was checked against scikit-learn, and point metrics were checked against the frozen final evaluation outputs.

## 9. Environment and reproducibility

The experiment runs in Ubuntu under WSL2 on a Windows host, using Docker Compose with one NameNode, one DataNode, HiveServer2, Hive metastore, PostgreSQL, YARN ResourceManager and NodeManager. This is a single-host setup. The observed WSL environment has approximately 7.6 GiB RAM and 16 logical CPUs; configured container limits are recorded in the infrastructure files.

Python {environment['python']}; {package_text}. Service images are Hadoop 3.5.0 for HDFS, Hive 4.2.1 for Hive/YARN, and PostgreSQL 17-bookworm. The Hive image bundles Hadoop 3.4.1 clients; the server and client Hadoop versions are not identical. Environment/service outputs and image identifiers are stored under `results/pipeline_benchmark/environment`.

Key evidence locations, relative to the project root:

- `src/audit_dataset.py`, `src/audit_model_readiness.py`, `src/build_cohort.py`: audit and cohort extraction.
- `results/hive_snapshot/20261108_110652`: original Hive definitions and training statistics.
- `sql/03_raw_credit_orc.sql` through `sql/08_verify_prepared_orc.sql`: pipeline construction and equivalence checks.
- `results/pipeline_benchmark/exports_v2_20261108_124424`: original valid latency runs/configuration.
- `results/pipeline_benchmark/resources_20261108_130043`: monitored runs and resource samples.
- `src/train_baseline.py`, `src/train_lightgbm.py`, `src/evaluate_final_test.py`: modelling and final evaluation.
- `results/final_test/evaluation_manifest.json`: frozen configuration and fingerprints.
- `src/bootstrap_test_results.py`, `results/final_test/uncertainty`: bootstrap method, draws and intervals.
- `src/build_results_report.py`: this report/figure assembly script.

Standalone export, monitored-resource, preparation-timing, environment-capture, verification and isolated-replay scripts are now supplied in `src`. `REPRODUCE.md` gives the exact commands; `DEMO_GUIDE.md` provides a demonstration sequence and slide outline; `references.bib` supplies structured references. The original experiments are preserved and new checks are saved separately under `results/reproducibility`. The report builder deliberately refuses to overwrite an existing `results/report` directory.

### Verification of the remaining reproducibility package

Frozen file fingerprints and all three complete-row Hive equivalence checks passed. A separate Hive namespace rebuilt the pipelines, recomputed the same training-only statistics, and exported the same feature values for all splits. The copied modelling workflow completed without changing the reported models. Sorting replay rows changed LightGBM slightly (test ROC-AUC 0.6641 versus 0.6644), which demonstrates why row order must be recorded. A second replay aligned reconstructed features to the original frozen export order and reproduced every reported test metric exactly, with maximum absolute metric difference 0.0. It did not select a new model configuration on the test results.

Standalone unmonitored exports, monitored exports, scratch-table preparation jobs, resource aggregation and environment capture passed smoke checks. The reusable resource aggregator also reproduced the original resource summary. These new short checks validate the code paths and do not replace the original repeated-run findings. Evidence is indexed in `results/reproducibility/VERIFICATION_STATUS.json`. Fresh OS installation and fresh-volume bootstrap were documented rather than retested destructively; the Hive replay starts from the existing audited cohort. This verifies the current-environment workflow, not universal cross-machine reproducibility.

## 10. Limits and next work

The main limits are retrospective outcome availability; accepted-loan and resolved-status selection; a restricted older 36-month cohort; absence of borrower-level grouping; one host, one dataset size and a roughly 50 MB cohort CSV; five latency repetitions; limited resource coverage for short queries; no controlled cold-cache study; single preparation-cost measurements; and no monetary-cost measurement. The benchmark compares complete exports, not all analytical SQL workloads or large-cluster scalability. Storage equivalence does not independently demonstrate bit-identical retraining across differently ordered inputs. The models have only moderate predictive performance and substantial false positives and group disparities.

The standalone benchmark harnesses, rerun guide, structured bibliography and demonstration outline are supplied and verified as described above. Before submission, review the report with the lecturer and apply the required college template, student details and presentation format. Optional follow-up experiments include multiple dataset sizes, repeated preparation measurements and execution-plan analysis. A realistic prospective validation would require outcome timestamps and label-maturity rules and must be treated as a separate experiment, not silently substituted into the completed test evaluation. SHAP, mitigation and a user interface are optional extensions, not completed features.

## 11. Conclusion

Prepared ORC wins the measured repeated full-feature-export workload: its median export time is 3.35 seconds versus 34.96 seconds for CSV, with equivalent feature values and explicit preparation cost. Raw ORC offers a large storage reduction and a smaller export-time improvement. Separately, LightGBM improves modestly on Logistic Regression and shows smaller home-ownership error gaps, while leaving significant prediction errors and disparities. The project demonstrates a controlled Hive pipeline comparison and a transparent model audit within the stated single-machine, retrospective scope.
'''
    # Include the source-attributed literature comparison when it is available.
    literature = project / 'results/literature_comparison/research_comparison.md'
    if literature.exists():
        comparison_section = literature.read_text(encoding='utf-8').split('\n', 2)[-1]
        report = report.replace('## 3. Dataset, target and cohort', comparison_section + '\n\n## 3. Dataset, target and cohort', 1)
    (output / 'project_results.md').write_text(report, encoding='utf-8')
    (output / 'README.md').write_text('# Results package\n\nRead [project_results.md](project_results.md) for the report. CSV tables and four PNG figures are included. All charts use saved results; models were not retrained.\n', encoding='utf-8')
    destination = project / 'src/build_results_report.py'
    if Path(__file__).resolve() != destination.resolve():
        shutil.copyfile(Path(__file__), destination)
    print(f'Report: {output / "project_results.md"}')
    print(f'Figures: {len(list(figures.glob("*.png")))}')
    print(f'Tables: {len(list(output.glob("*.csv")))}')


if __name__ == '__main__':
    main()
