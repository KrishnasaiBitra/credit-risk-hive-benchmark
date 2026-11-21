# CatBoost and Adaptive Random Forest extension

This is a new exploratory experiment. Original research files and pipeline measurements remain unchanged.

| Model | Threshold | Accuracy | Precision | Recall | F1 | ROC-AUC | Average precision |
|---|---|---|---|---|---|---|---|
| Dummy | 0.5000 | 0.8587 | 0.0000 | 0.0000 | 0.0000 | 0.5000 | 0.1413 |
| Logistic Regression | 0.1500 | 0.6595 | 0.2153 | 0.5336 | 0.3068 | 0.6537 | 0.2231 |
| LightGBM | 0.1500 | 0.6610 | 0.2185 | 0.5434 | 0.3117 | 0.6644 | 0.2306 |
| CatBoost | 0.1500 | 0.6629 | 0.2189 | 0.5398 | 0.3115 | 0.6647 | 0.2295 |
| Adaptive Random Forest | 0.1250 | 0.5244 | 0.1756 | 0.6405 | 0.2756 | 0.5956 | 0.1790 |

## Method and interpretation

CatBoost uses native categorical features, one preset configuration and validation early stopping. ARF uses River with ten trees, ADWIN detectors, issue-month-ordered training and no learning on validation/test. All models receive the same 19 feature definitions. Their categorical preprocessing and algorithms differ. Thresholds are chosen by the original validation maximum-F1 rule. Training/prediction timings are single local measurements, not repeated benchmarks.

CatBoost has a slightly higher test ROC-AUC point estimate than LightGBM, but slightly lower F1 and average precision. No statistically established improvement is claimed. ARF has higher recall at its chosen threshold but many more false positives and lower ROC-AUC/F1. Adding these algorithms does not itself establish research novelty.

- Extension experiment: the original test results were already known before these models were proposed. This reused historical holdout is not a fresh confirmatory test.
- No model tuning or learning uses test outcomes. Thresholds use the original validation-only maximum-F1 grid.
- ARF learns only the training partition, ordered by issue month and loan ID; it is frozen for validation/test. These results do not demonstrate live drift adaptation.
- Loan outcomes are delayed. The retrospective issue-date split is not a valid prospective label-arrival simulation.
- One fixed configuration and seed per new model; no new significance claim, fairness mitigation or new algorithm is established.
- Home ownership is a predictor and an audit grouping; protected-group or causal fairness is not established.

## Reproduce

Use a separate environment, keep the original requirements-lock.txt as constraints, and install model_extensions/requirements.txt. Supply the original cohort and split files. From the repository root run:

```bash
python -m model_extensions.train --project /path/to/full-project --run /path/to/new-run --model catboost
python -m model_extensions.train --project /path/to/full-project --run /path/to/new-run --model arf
python -m model_extensions.export_catboost --project /path/to/full-project --run /path/to/new-run
python -m model_extensions.evaluate --project /path/to/full-project --run /path/to/new-run
```

## References

- CatBoost: https://catboost.ai/docs/en/concepts/python-reference_catboostclassifier
- Official standalone export: https://catboost.ai/docs/en/concepts/python-reference_catboost_save_model
- River ARFClassifier: https://riverml.xyz/latest/api/forest/ARFClassifier/
