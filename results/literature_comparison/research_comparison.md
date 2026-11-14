# Reference paper and project comparison

### Comparison of the reference papers and our outcomes

The following is a comparison of published findings and our recorded outcomes, not a matched replication. The 2017 study, the 2025 study and our project address different parts of the problem. Kaggle supplies the dataset and is not a third research paper with its own model scores.

#### What the 2017 paper reports

**Bank loan analysis using customer usage data: A big data approach using Hadoop** (paper ID / DOI: 10.1109/TEL-NET.2017.8343582) uses Hadoop/HDFS/Hive to summarize Lending Club data from January 2012 through December 2016 (approximately 1 GB). Their results include loan issuance, purposes, grade-based summaries and loan statuses. For example, they report debt consolidation at 58.88% of purposes and mean interest rates of 11.21% for 36-month loans, 15.32% for 60-month loans and 12.18% overall (PDF pp. 4 and 7). These are descriptive findings, not predictive accuracy. No accuracy, F1, recall or ROC-AUC is reported for a trained model in their own analysis, and no directly comparable pipeline latency is reported. Our project does not reproduce those descriptive statistics on an identical cohort, so no numeric improvement over those statistics is claimed.

#### What the 2025 paper reports, alongside our model results

**Assessing Fairness and Transparency in Credit Scoring Using Explainable AI** (paper ID / DOI: 10.1109/CISCON66933.2025.11337606) reports the following in Table V (PDF p. 6). Our rows come from the frozen test evaluation. All values in this table are fractions, not percentages.

| Study | Model | Accuracy | Recall | F1 | ROC-AUC |
| --- | --- | --- | --- | --- | --- |
| Assessing Fairness and Transparency in Credit Scoring Using Explainable AI (2025; DOI: 10.1109/CISCON66933.2025.11337606) | Random Forest | 0.8180 | 0.7318 | 0.8010 | 0.8883 |
| Assessing Fairness and Transparency in Credit Scoring Using Explainable AI (2025; DOI: 10.1109/CISCON66933.2025.11337606) | LightGBM | 0.8284 | 0.7412 | 0.8111 | 0.8981 |
| Assessing Fairness and Transparency in Credit Scoring Using Explainable AI (2025; DOI: 10.1109/CISCON66933.2025.11337606) | XGBoost | 0.8285 | 0.7425 | 0.8123 | 0.8988 |
| Our project | Logistic Regression | 0.6595 | 0.5336 | 0.3068 | 0.6537 |
| Our project | LightGBM | 0.6610 | 0.5434 | 0.3117 | 0.6644 |

The published XGBoost row has the highest reported AUC (0.8988); the paper’s LightGBM AUC is 0.8981. Our LightGBM AUC is 0.6644. Therefore, we do not claim a predictive-score improvement over that paper. Our main comparison is between our own pipelines under shared controls, not a claim that our classifier beats the published models.

#### Differences in scope and implemented evidence

| Aspect | Bank loan analysis using customer usage data: A big data approach using Hadoop (2017; DOI: 10.1109/TEL-NET.2017.8343582) | Assessing Fairness and Transparency in Credit Scoring Using Explainable AI (2025; DOI: 10.1109/CISCON66933.2025.11337606) | Our project |
| --- | --- | --- | --- |
| Main outcome | Historical loan/purpose/grade/status summaries. | Predictive model scores and qualitative SHAP interpretation. | Equivalent-data Hive export benchmark, predictive baselines and group error audit. |
| Dataset/cohort | Approximately 1 GB of Lending Club data, Jan 2012–Dec 2016. | Lending Club; exact cohort and split protocol insufficiently specified for a matched rerun. | 306,462 resolved 36-month loans, 2012–2014; 90,615-loan test split. |
| Predictive models | No trained predictive model evaluated in the reported analysis. | Random Forest, LightGBM and XGBoost. | Dummy baseline, Logistic Regression and LightGBM. |
| Class balance / decision rule | Not a predictive classification evaluation. | States undersampling for class balance; discusses NearMiss/Tomek Links. Threshold and split details not fully specified. | Original selected-cohort imbalance retained; validation maximum-F1 rule selects 0.15 for both trained models. |
| Input features | Dataset section reports 74 retained attributes for descriptive analysis. | Table II lists 26 predictors plus target; includes interest rate, grade, subgrade and term. | 19 model inputs; uses FICO midpoint and credit-history months; does not use interest rate or grades. |
| Hive pipeline benchmark | Uses Hive/HiveQL, but no matched CSV/raw-ORC/prepared-ORC timing benchmark is reported. | No Hive storage/materialization benchmark reported. | Five measured exports per pipeline; median 34.96 s (CSV), 30.14 s (raw ORC), 3.35 s (prepared ORC). |
| Storage / preparation cost | Dataset size is described; no comparable pipeline cost breakdown reported. | No comparable pipeline storage/preparation experiment reported. | Raw CSV 50.17 MB; raw ORC 5.99 MB; prepared ORC 7.65 MB. Estimated two-stage preparation 37.39 s. |
| Quantitative group audit | No group error-rate disparity metrics reported. | Fairness/SHAP discussion, but no numeric group FPR/recall gaps in the supplied paper. | MORTGAGE/RENT/OWN audit: LightGBM FPR gap 23.32 pp and recall gap 25.37 pp. Substantial disparities remain. |
| Explainability | Descriptive charts, not individual model explanations. | Describes SHAP-based local/global interpretation and discusses DTI, interest rate and income. | No SHAP or causal feature explanation implemented; this is a limitation relative to the paper’s stated scope. |
| Uncertainty / reproducibility | No paired predictive intervals or comparable frozen-model replay reported. | No paired confidence intervals or matched reproducibility package in the supplied paper. | 1,000 paired row-bootstrap samples; frozen file fingerprints; equivalent-feature replay and exact metric replay with original row order. |
| Execution setting | Cloudera QuickStart 5.8, Hadoop/HDFS and Hive. | Google Colab, 16 GB RAM, Python 3.12. | Single-host WSL2/Docker, Hive 4.2.1, HDFS/YARN/Tez; Python model training outside Hive. |

#### Why these scores cannot establish a fair head-to-head ranking

- These are side-by-side reported results, not a controlled head-to-head benchmark. We did not reproduce either paper’s full experimental setup.

- Cohort, predictor set, target mapping, sampling and split definitions differ or are insufficiently specified. The 2025 paper states undersampling; our test cohort retains its selected natural imbalance (14.13% charged off).

- Threshold-dependent accuracy, recall and F1 also depend on decision rules. AUC is threshold-independent; its difference cannot be explained by the 0.15 threshold or imbalance alone.

- The 2025 paper’s displayed confusion-matrix totals differ across models: 97,622 for RF/XGBoost and 65,082 for LightGBM (Figures 2–4). Table V is reproduced as author-reported, without silently reconciling those totals or recalculating its metrics.

- No claim is made that our model is more accurate than the 2025 models, that our pipeline is 10.44 times faster than either paper, or that our group audit proves fairness.

The 2025 methods section (PDF p. 3) describes undersampling, NearMiss and Tomek Links, but the exact application order, cohort/split details and final decision thresholds are insufficient for a matched reproduction. Table II also includes predictors such as interest rate, grade, subgrade and term that are not in our 19-feature model. These differences are not proof of an error or leakage in that paper. Our own retrospective issue-date split has a label-availability limitation and must also be stated openly.

**What our project adds:** Our added work is the controlled equivalent-feature Hive pipeline benchmark, explicit preparation/storage measurements, quantitative home-ownership error audit and reproducibility evidence. Our reported predictive scores are lower than the 2025 paper’s scores, and SHAP is not implemented here.

Sources: *Bank loan analysis using customer usage data: A big data approach using Hadoop*, DOI 10.1109/TEL-NET.2017.8343582, PDF pp. 3–7; *Assessing Fairness and Transparency in Credit Scoring Using Explainable AI*, DOI 10.1109/CISCON66933.2025.11337606, PDF p. 3 and pp. 5–6/Table V; our `results/final_test/test_metrics.csv` and `results/pipeline_benchmark` files. “Not reported” means no corresponding result was found in the supplied paper; it does not mean a measured value of zero.
