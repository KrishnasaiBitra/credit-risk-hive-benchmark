#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ -n "${CREDIT_RISK_PYTHON:-}" ]]; then
    app_python="$CREDIT_RISK_PYTHON"
elif [[ -x "$HOME/venvs/credit-risk/bin/python" ]]; then
    if [[ -f results/model_extensions/inference_manifest.json && -x "$HOME/venvs/credit-risk-extensions/bin/python" ]]; then
        app_python="$HOME/venvs/credit-risk-extensions/bin/python"
    else
        app_python="$HOME/venvs/credit-risk/bin/python"
    fi
else
    app_python="python3"
fi
"$app_python" -c 'import fastapi, uvicorn, joblib, sklearn, lightgbm' || {
    echo 'Install the interface requirements in the existing credit-risk environment; see interface/README.md.' >&2
    exit 1
}
echo "Credit Risk Lab: http://localhost:${PORT:-8000}"
echo 'Stop with Ctrl+C. Hive and Docker are not needed for this interface.'
exec "$app_python" -m uvicorn interface.app:app --host 127.0.0.1 --port "${PORT:-8000}"
