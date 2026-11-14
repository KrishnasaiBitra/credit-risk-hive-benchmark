# Credit Risk Lab interface

Local HTML, CSS and vanilla JavaScript frontend served by Python FastAPI. Plotly.js
is bundled locally. No Streamlit, React, Node build, cloud account or external model
API is required. The dashboard reads existing project files and does not modify
the published models, thresholds, data or benchmark results.

## Start in Ubuntu / WSL

On Windows, you can double-click `interface/start-dashboard.bat`, keep its terminal
open, and then visit http://localhost:8000. It starts the same WSL app as the commands below.

```bash
cd /mnt/c/Users/krish/Desktop/big-data-project
bash interface/start.sh
```

Open **http://localhost:8000** in your Windows browser. Stop the server with Ctrl+C.
The launcher uses `~/venvs/credit-risk/bin/python` if available. To select a different
existing compatible interpreter, set `CREDIT_RISK_PYTHON` to its absolute path.
For another port: `PORT=8001 bash interface/start.sh`.

For first-time installation in the already-compatible model environment:

```bash
source ~/venvs/credit-risk/bin/activate
python -m pip install -c requirements-lock.txt -r interface/requirements.txt
python -m pip check
```

Do not upgrade scikit-learn/LightGBM/numpy/pandas independently of the saved model
environment. UI dependencies have a separate lock, and the original research lock
is unchanged. Model files are loaded only after checking their recorded SHA-256.

## Eight pages

1. Overview: cohort, pipeline speed, model scores and study scope.
2. Project architecture: interactive 12-stage research flow and six-stage website flow, with technology roles and step-by-step explanations.
3. Pipeline benchmark: original five-run timings, storage, preparation, estimated
   break-even and sampled resources. No live cluster task runs from the browser.
4. Model comparison: test metrics, ROC/PR plots, confusion matrices and intervals.
5. Fairness audit: group counts/rates, intervals, gaps, model filter and limitations.
6. Research comparison: published paper outcomes, our scores, scope differences and comparison limits.
7. Loan risk demo: six historical examples; editable inputs; fixed-model predictions.
8. Reports & method: actual file downloads, references, architecture and caveats.

## Prediction correctness

All 19 feature names/order come from the frozen manifest. The demo derives FICO
midpoint, employment/utilization missingness flags and uses the recorded training
fills when those fields are blank. It passes these values through the original
saved preprocessing/model pipelines. Other credit-history values are visible in
an expandable form section. The form uses USD and months, not INR or years for
credit-history months. Historical example FICO bounds reconstruct the recorded
midpoint; they are not a claim that the original bounds were recovered separately.

Both model thresholds remain 0.15. “Meets flag threshold” is a research classification,
not a lending approval decision. Warnings identify values outside observed training
ranges. No causal feature explanation, mitigation or current-borrower calibration
claim is added. Current browser inputs do not alter published test evaluation.

All visible experiment charts use recorded results dated 8 November 2026. A new
demo prediction is explicitly separate. The browser chart curves are decimated
for rendering; original metric values are not recalculated from those display points.

## Files and troubleshooting

- `app.py`: local read-only artifact API, validation and inference.
- `static/index.html`, `styles.css`, `app.js`: browser UI.
- `static/vendor/plotly.min.js`: offline chart library.
- `assets/project_report.pdf`: downloadable report snapshot.
- `verify_interface.py`: API, historical prediction and download checks.

The default project root is the parent of `interface`. If developing from another
directory, set `CREDIT_RISK_PROJECT` to the project path. Data/model artifacts are
not copied into the web-accessible static directory. Only named report/result
downloads are exposed. Missing files produce explicit errors rather than mock data.
Restore a changed model from the frozen experiment if its fingerprint fails.

The API documentation is available locally at `/api/docs` and is optional; the app
itself does not depend on its external Swagger assets. The interface binds to local
loopback, and no public hosting is configured. Default screenshots are not required
to run the app. Stop other apps using port 8000 or choose another port if needed.

## Verify

Start the server, then in another Ubuntu terminal:

```bash
cd /mnt/c/Users/krish/Desktop/big-data-project
source ~/venvs/credit-risk/bin/activate
python interface/verify_interface.py
```

The verification compares historical scores to saved predictions, checks missing
values and invalid inputs, tests result/download routes and confirms frozen artifact
fingerprints. It writes a timestamped report under `results/interface_checks`.
