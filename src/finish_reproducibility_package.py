"""Assemble a verified status record and update report narrative, preserving experiment numbers."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import shutil

project=Path(__file__).resolve().parents[1]
root=project/'results/reproducibility'
def latest(pattern):
    paths=sorted(root.glob(pattern))
    if not paths:
        raise RuntimeError('Missing evidence: '+pattern)
    return paths[-1]
def load(path):
    return json.loads(path.read_text())

verification=[p for p in sorted(root.glob('verification_*.json')) if load(p).get('hive_checked')][-1]
replay=latest('replay_*/replay_manifest.json')
ordered=latest('ordered_models_*/replay_manifest.json')
harness=latest('harness_checks_*/checks.json')
summary_check=latest('resource_summary_check_*/verification.txt')
assert load(verification)['status']=='passed' and load(verification)['hive_checked']
assert load(replay)['status']=='completed' and load(replay)['feature_replay_passed'] and load(replay)['model_replay_passed']
assert load(ordered)['status']=='completed' and load(ordered)['metrics_match_at_1e_10']
assert load(harness)['status']=='passed'
assert summary_check.read_text().startswith('PASS:')

scripts=['benchmark_pipelines.py','benchmark_preparation.py','summarize_resources.py','capture_environment.py',
         'verify_project.py','replay_project.py','replay_models.py','select_baseline_threshold.py',
         'run_reproducibility_checks.py','bootstrap_test_results.py','build_results_report.py']
record=dict(verified_at_utc=datetime.now(timezone.utc).isoformat(),status='passed',
            original_test_metrics_maximum_replay_difference=load(ordered)['maximum_absolute_metric_difference'],
            evidence={name:str(path.relative_to(project)) for name,path in dict(
                frozen_and_hive_checks=verification,isolated_replay=replay,ordered_models=ordered,
                harness_smoke_checks=harness,resource_summary_recheck=summary_check).items()},
            script_sha256={name:hashlib.sha256((project/'src'/name).read_bytes()).hexdigest() for name in scripts},
            boundaries=['Fresh Windows/WSL installation and fresh-volume initialization were not rerun.',
                        'New benchmark runs are code-path smoke checks; the original five-run comparison is unchanged.',
                        'The full Hive replay starts from the existing audited cohort; raw-source audit/extraction scripts are supplied.',
                        'Lecturer-specific report formatting, student details and finished slides remain submission tasks.'])
(root/'VERIFICATION_STATUS.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
status='''# Reproducibility verification status

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
'''
(root/'VERIFICATION_STATUS.md').write_text(status,encoding='utf-8')

old='The export and resource benchmark harnesses were executed as terminal Python blocks; their logs/configuration were saved, but reusable standalone harness scripts still need to be added for a complete rerun package. Therefore, this report is an evidence-backed draft, not a claim that every experiment can already be reproduced with a single command. The report builder deliberately refuses to overwrite an existing `results/report` directory.'
new='Standalone export, monitored-resource, preparation-timing, environment-capture, verification and isolated-replay scripts are now supplied in `src`. `REPRODUCE.md` gives the exact commands; `DEMO_GUIDE.md` provides a demonstration sequence and slide outline; `references.bib` supplies structured references. The original experiments are preserved and new checks are saved separately under `results/reproducibility`. The report builder deliberately refuses to overwrite an existing `results/report` directory.'
old_next='Before submission, preserve standalone benchmark harnesses, add an exact rerun guide and a structured bibliography, and review the report with the lecturer.'
new_next='The standalone benchmark harnesses, rerun guide, structured bibliography and demonstration outline are supplied and verified as described above. Before submission, review the report with the lecturer and apply the required college template, student details and presentation format.'
extra='''### Verification of the remaining reproducibility package

Frozen file fingerprints and all three complete-row Hive equivalence checks passed. A separate Hive namespace rebuilt the pipelines, recomputed the same training-only statistics, and exported the same feature values for all splits. The copied modelling workflow completed without changing the reported models. Sorting replay rows changed LightGBM slightly (test ROC-AUC 0.6641 versus 0.6644), which demonstrates why row order must be recorded. A second replay aligned reconstructed features to the original frozen export order and reproduced every reported test metric exactly, with maximum absolute metric difference 0.0. It did not select a new model configuration on the test results.

Standalone unmonitored exports, monitored exports, scratch-table preparation jobs, resource aggregation and environment capture passed smoke checks. The reusable resource aggregator also reproduced the original resource summary. These new short checks validate the code paths and do not replace the original repeated-run findings. Evidence is indexed in `results/reproducibility/VERIFICATION_STATUS.json`. Fresh OS installation and fresh-volume bootstrap were documented rather than retested destructively; the Hive replay starts from the existing audited cohort. This verifies the current-environment workflow, not universal cross-machine reproducibility.

'''
for path in [project/'results/report/project_results.md',project/'src/build_results_report.py']:
    text=path.read_text(encoding='utf-8')
    if old not in text or old_next not in text:
        raise RuntimeError('Expected report-draft wording not found: '+str(path))
    text=text.replace(old,new).replace(old_next,new_next)
    text=text.replace('## 10. Limits and next work',extra+'## 10. Limits and next work')
    path.write_text(text,encoding='utf-8')

for name in ['REPRODUCE.md','DEMO_GUIDE.md','references.bib']:
    shutil.copyfile(project/name,project/'results/report'/name)
record['script_sha256']={name:hashlib.sha256((project/'src'/name).read_bytes()).hexdigest() for name in scripts}
(root/'VERIFICATION_STATUS.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
print('Reproducibility status and report updated:',root/'VERIFICATION_STATUS.md')
