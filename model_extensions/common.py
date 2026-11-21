from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, average_precision_score, brier_score_loss, confusion_matrix, f1_score, precision_score, recall_score, roc_auc_score

SIZES = {'train': 143892, 'validation': 71955, 'test': 90615}
GROUPS = ['MORTGAGE', 'RENT', 'OWN']


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False, default=str) + '\n', encoding='utf-8')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_split(project, split, features):
    frame = pd.read_csv(project / f'data/features/{split}.csv', dtype={'loan_id': 'string'})
    assert len(frame) == SIZES[split] and frame.loan_id.is_unique
    assert frame.data_split.eq(split).all() and set(frame.target.unique()) == {0, 1}
    assert frame[features].notna().all().all()
    return frame


def metrics(name, y, probability, threshold):
    probability = np.asarray(probability, dtype=float)
    assert np.isfinite(probability).all() and ((probability >= 0) & (probability <= 1)).all()
    prediction = probability >= threshold
    tn, fp, fn, tp = confusion_matrix(y, prediction, labels=[0, 1]).ravel()
    return dict(model=name, threshold=float(threshold), accuracy=float(accuracy_score(y, prediction)),
                precision=float(precision_score(y, prediction, zero_division=0)),
                chargeoff_recall=float(recall_score(y, prediction, zero_division=0)),
                false_positive_rate=float(fp / (fp + tn)) if fp + tn else None,
                f1=float(f1_score(y, prediction, zero_division=0)), roc_auc=float(roc_auc_score(y, probability)) if len(set(y)) == 2 else None,
                average_precision=float(average_precision_score(y, probability)) if np.sum(y) else None,
                brier_score=float(brier_score_loss(y, probability)), loans=len(y),
                true_positives=int(tp), false_positives=int(fp), false_negatives=int(fn), true_negatives=int(tn))


def group_metrics(name, frame, probability, threshold):
    output = []
    for group in sorted(frame.home_ownership_group.unique()):
        mask = frame.home_ownership_group.eq(group).to_numpy()
        row = metrics(name, frame.loc[mask, 'target'], probability[mask], threshold)
        row.update(group=group, charged_off=int(frame.loc[mask, 'target'].sum()),
                   fully_paid=int(mask.sum()-frame.loc[mask, 'target'].sum()))
        output.append(row)
    return output
