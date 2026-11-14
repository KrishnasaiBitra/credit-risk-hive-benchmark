# Reproducibility verification status

The remaining reproducibility package has been implemented and checked in the existing WSL/Docker environment.

| Check | Result |
| --- | --- |
| Frozen model/config/test-file fingerprints | Passed |
| Train/validation/test IDs, row counts and saved metrics | Passed |
| Three full-row Hive equivalence checks | Passed |
| Recomputed training-only imputation statistics | Match original values |
| Isolated Hive rebuild and all exported feature values | Match original values |
| Sorted-row model replay | Completed; small LightGBM ordering sensitivity recorded |
| Original-row-order model replay | All reported test metrics match exactly; maximum difference 0.0 |
| Reusable export benchmark, including initial and measured phases | Smoke check passed |
| Monitored export and resource summary | Smoke check passed |
| Resource summarizer on historical samples | Reproduces the original summary |
| Scratch-table preparation timing and cleanup | Smoke check passed |
| Environment/storage capture | Passed |

The original five-repeat latency study, three-repeat resource experiment, frozen models and final test results were not overwritten. New experiments are under `results/reproducibility`.

This validates the supplied workflow in the current environment, not a fresh OS installation or a cross-machine guarantee. The Hive replay starts from the existing audited cohort. A row-order-preserving replay uses reconstructed values and the original loan-ID order, and selects thresholds using the same validation rule. Timing and model serialization bytes need not match exactly.

For commands see `REPRODUCE.md`; for demonstration and slide content see `DEMO_GUIDE.md`. The structured reference list is `references.bib`. A college-specific template, student details and finished slides are still presentation/submission tasks.

Detailed evidence paths, verification time and script fingerprints are in `VERIFICATION_STATUS.json`.
