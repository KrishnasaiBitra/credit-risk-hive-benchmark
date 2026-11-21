# Model comparison and reference-paper results

This comparison records published scores alongside our experiments. It is not a matched replication. Paper scores were transcribed from Table V, PDF p. 6 of the 2025 reference paper. No new model training was performed to build this comparison.

| Study | Model | Accuracy | Recall | F1 | ROC-AUC | Threshold | Evidence |
|---|---|---|---|---|---|---|---|
| Assessing Fairness and Transparency in Credit Scoring Using Explainable AI (2025; DOI: 10.1109/CISCON66933.2025.11337606) | Random Forest | 0.8180 | 0.7318 | 0.8010 | 0.8883 | Not reported | Author-reported; not rerun |
| Assessing Fairness and Transparency in Credit Scoring Using Explainable AI (2025; DOI: 10.1109/CISCON66933.2025.11337606) | LightGBM | 0.8284 | 0.7412 | 0.8111 | 0.8981 | Not reported | Author-reported; not rerun |
| Assessing Fairness and Transparency in Credit Scoring Using Explainable AI (2025; DOI: 10.1109/CISCON66933.2025.11337606) | XGBoost | 0.8285 | 0.7425 | 0.8123 | 0.8988 | Not reported | Author-reported; not rerun |
| Our project | Logistic Regression | 0.6595 | 0.5336 | 0.3068 | 0.6537 | 0.15 | Original frozen experiment; 90,615 test loans |
| Our project | LightGBM | 0.6610 | 0.5434 | 0.3117 | 0.6644 | 0.15 | Original frozen experiment; 90,615 test loans |
| Our project | CatBoost | 0.6629 | 0.5398 | 0.3115 | 0.6647 | 0.15 | Exploratory extension; reused historical holdout |
| Our project | Adaptive Random Forest | 0.5244 | 0.6405 | 0.2756 | 0.5956 | 0.125 | Exploratory extension; reused historical holdout |

## The 2017 reference

Bank loan analysis using customer usage data: A big data approach using Hadoop

DOI: 10.1109/TEL-NET.2017.8343582

The supplied paper reports descriptive Hadoop/Hive loan analysis, not an evaluated predictive classifier. No comparable accuracy, recall, F1 or ROC-AUC is reported for its own analysis. Missing results are not zero.

## Limits of the comparison

- These are side-by-side reported results, not a controlled head-to-head benchmark. We did not reproduce either paper’s full experimental setup.

- Cohort, predictor set, target mapping, sampling and split definitions differ or are insufficiently specified. The 2025 paper states undersampling; our test cohort retains its selected natural imbalance (14.13% charged off).

- Threshold-dependent accuracy, recall and F1 also depend on decision rules. AUC is threshold-independent; its difference cannot be explained by the 0.15 threshold or imbalance alone.

- The 2025 paper’s displayed confusion-matrix totals differ across models: 97,622 for RF/XGBoost and 65,082 for LightGBM (Figures 2–4). Table V is reproduced as author-reported, without silently reconciling those totals or recalculating its metrics.

- No claim is made that our model is more accurate than the 2025 models, that our pipeline is 10.44 times faster than either paper, or that our group audit proves fairness.

- CatBoost and Adaptive Random Forest were proposed after the original test results were known; their historical holdout comparisons are exploratory, not fresh confirmatory tests.

Original paired confidence intervals compare LightGBM with Logistic Regression only. There are no new paired intervals establishing that CatBoost improves over LightGBM. The paper’s Random Forest and XGBoost have not been trained or reproduced in our project. Adaptive Random Forest is a different algorithm from conventional Random Forest.
