"""Persist the agreed validation-only maximum-F1 threshold selection rule."""
from pathlib import Path
import json
import pandas as pd

project=Path(__file__).resolve().parents[1]
folder=project/'results/baseline'
destination=folder/'threshold_selection.json'
if destination.exists():
    raise RuntimeError('Selection already exists; this script is for a fresh replay project.')
comparison=pd.read_csv(folder/'validation_threshold_comparison.csv')
best=comparison.sort_values(['f1','threshold'],ascending=[False,False]).iloc[0]
destination.write_text(json.dumps(dict(
    model='Logistic Regression',selection_dataset='validation',
    selection_rule='Highest F1 on the predefined grid; ties use the higher threshold.',
    threshold_grid=comparison.threshold.tolist(),selected_threshold=float(best.threshold),
    validation_f1=float(best.f1),test_set_evaluated=False,
),indent=2),encoding='utf-8')
print('Selected validation threshold:',best.threshold)
