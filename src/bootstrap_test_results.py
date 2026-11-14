"""Paired row bootstrap of frozen credit-risk test predictions; no model fitting."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score, average_precision_score


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--replicates', type=int, default=1000)
    parser.add_argument('--reuse-results', action='store_true', help='Render already saved bootstrap draws without resampling')
    args = parser.parse_args()
    project = args.project.resolve()
    base = project / 'results/final_test'
    manifest = json.loads((base / 'evaluation_manifest.json').read_text())
    assert manifest['evaluation_completed'], 'Final evaluation is incomplete.'
    for relative, expected in manifest['file_sha256'].items():
        assert digest(project / relative) == expected, f'Frozen file changed: {relative}'

    names = ['Logistic Regression', 'LightGBM']
    files = ['logistic_regression_predictions.csv', 'lightgbm_predictions.csv']
    frames = [pd.read_csv(base / f).sort_values('loan_id').reset_index(drop=True) for f in files]
    for frame in frames:
        assert len(frame) == 90615 and frame.loan_id.is_unique
    pd.testing.assert_frame_equal(frames[0][['loan_id', 'target', 'home_ownership_group']],
                                  frames[1][['loan_id', 'target', 'home_ownership_group']])
    y = frames[0].target.to_numpy(dtype=int)
    assert set(y) == {0, 1}
    groups = ['MORTGAGE', 'RENT', 'OWN']
    group_code = frames[0].home_ownership_group.map(dict(zip(groups, range(3)))).fillna(3).to_numpy(dtype=int)
    prepared = []
    for name, frame in zip(names, frames):
        p = frame.probability.to_numpy()
        prediction = frame.prediction.to_numpy(dtype=int)
        assert np.isfinite(p).all() and ((p >= 0) & (p <= 1)).all()
        assert np.array_equal(prediction, (p >= manifest['selected_thresholds'][name]).astype(int))
        # Group equal scores in descending order so weighted AUC/AP handle ties exactly.
        _, score_group = np.unique(-p, return_inverse=True)
        prepared.append((p, prediction, score_group))

    def metrics(weights, model):
        p, prediction, score_group = model
        tn, fp, fn, tp = np.bincount(2*y + prediction, weights=weights, minlength=4)
        n = weights.sum()
        pos = np.bincount(score_group, weights=weights*y, minlength=score_group.max()+1)
        neg = np.bincount(score_group, weights=weights*(1-y), minlength=len(pos))
        cumulative_pos, cumulative_neg = pos.cumsum(), neg.cumsum()
        tpr = np.r_[0., cumulative_pos/cumulative_pos[-1]]
        fpr = np.r_[0., cumulative_neg/cumulative_neg[-1]]
        precision = np.divide(cumulative_pos, cumulative_pos+cumulative_neg,
                              out=np.zeros_like(cumulative_pos), where=(cumulative_pos+cumulative_neg)>0)
        result = {
            'accuracy': (tp+tn)/n,
            'precision': tp/(tp+fp) if tp+fp else 0.,
            'chargeoff_recall': tp/(tp+fn),
            'false_positive_rate': fp/(fp+tn),
            'f1': 2*tp/(2*tp+fp+fn),
            'roc_auc': np.trapezoid(tpr, fpr),
            'average_precision': np.sum(pos/cumulative_pos[-1]*precision),
            'brier_score': np.sum(weights*(p-y)**2)/n,
        }
        group_rates = []
        counts = np.bincount(group_code*4 + y*2 + prediction, weights=weights, minlength=16).reshape(4,4)
        for group, (gtn, gfp, gfn, gtp) in zip(groups, counts[:3]):
            recall, fpr_group = gtp/(gtp+gfn), gfp/(gfp+gtn)
            result[f'{group}_chargeoff_recall'] = recall
            result[f'{group}_false_positive_rate'] = fpr_group
            group_rates.append((recall, fpr_group))
        rates = np.array(group_rates)
        result['chargeoff_recall_gap'] = np.ptp(rates[:, 0])
        result['false_positive_rate_gap'] = np.ptp(rates[:, 1])
        result['equalized_odds_difference'] = max(result['chargeoff_recall_gap'], result['false_positive_rate_gap'])
        return result

    ones = np.ones(len(y))
    point = [metrics(ones, model) for model in prepared]
    # Validate the bootstrap metric implementation against sklearn and saved results.
    saved = pd.read_csv(base / 'test_metrics.csv').set_index('model')
    for name, model, result in zip(names, prepared, point):
        assert np.isclose(result['roc_auc'], roc_auc_score(y, model[0]), atol=1e-12)
        assert np.isclose(result['average_precision'], average_precision_score(y, model[0]), atol=1e-12)
        for key in saved.columns.intersection(result):
            assert np.isclose(result[key], saved.loc[name, key], atol=1e-10), (name, key)

    output = base / 'uncertainty'
    output.mkdir(exist_ok=args.reuse_results)
    keys = list(point[0])
    draws = (np.load(output / 'bootstrap_draws.npz')['draws'] if args.reuse_results
             else np.empty((args.replicates, 2, len(keys))))
    if args.reuse_results:
        assert draws.shape == (args.replicates, 2, len(keys))
    rng = np.random.default_rng(42)
    print(f'Paired bootstrap: {len(y):,} loans, {args.replicates:,} replicates', flush=True)
    for replicate in range(0 if args.reuse_results else args.replicates):
        weights = np.bincount(rng.integers(0, len(y), size=len(y)), minlength=len(y))
        for j, model in enumerate(prepared):
            result = metrics(weights, model)
            draws[replicate, j] = [result[key] for key in keys]
        if (replicate+1) % 100 == 0:
            print(f'Completed {replicate+1:,} replicates', flush=True)

    rows, differences = [], []
    for k, key in enumerate(keys):
        for j, name in enumerate(names):
            lower, upper = np.quantile(draws[:, j, k], [.025, .975])
            rows.append(dict(model=name, metric=key, estimate=point[j][key], lower_95=lower, upper_95=upper))
        lower, upper = np.quantile(draws[:, 1, k]-draws[:, 0, k], [.025, .975])
        differences.append(dict(metric=key, lightgbm_minus_logistic=point[1][key]-point[0][key],
                                lower_95=lower, upper_95=upper, excludes_zero=bool(lower>0 or upper<0)))
    intervals = pd.DataFrame(rows)
    paired = pd.DataFrame(differences)
    intervals.to_csv(output / 'metric_confidence_intervals.csv', index=False)
    paired.to_csv(output / 'paired_model_differences.csv', index=False)
    np.savez_compressed(output / 'bootstrap_draws.npz', draws=draws, metrics=np.array(keys), models=np.array(names))
    method = {
        'method': 'Ordinary paired loan-row bootstrap; percentile 95% intervals',
        'replicates': args.replicates, 'seed': 42, 'rows': len(y),
        'paired_difference': 'LightGBM minus Logistic Regression; same sampled rows for both models',
        'thresholds': manifest['selected_thresholds'],
        'gap_groups': groups, 'excluded_from_gaps': 'OTHER_UNKNOWN (one test loan)',
        'prediction_sha256': {f: digest(base / f) for f in files},
        'limitations': [
            'Assumes independent loan rows; repeated borrowers and time dependence are not modeled.',
            'Conditional on fixed trained models, preprocessing, thresholds and this test cohort.',
            'Does not include training or model-selection uncertainty, or correct retrospective label availability.',
            'Intervals are pointwise, without multiple-comparison correction.',
            'Home-ownership gaps are descriptive disparities, not causal evidence of discrimination.'
        ],
    }
    (output / 'methodology.json').write_text(json.dumps(method, indent=2))
    destination = project / 'src/bootstrap_test_results.py'
    if Path(__file__).resolve() != destination.resolve():
        shutil.copyfile(Path(__file__), destination)

    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plot_keys = ['roc_auc', 'average_precision', 'false_positive_rate_gap', 'chargeoff_recall_gap']
    labels = ['ROC-AUC', 'Average precision', 'False-positive-rate gap', 'Charge-off recall gap']
    fig, axes = plt.subplots(2, 2, figsize=(10, 7), layout='constrained')
    for ax, key, label in zip(axes.flat, plot_keys, labels):
        for j, name in enumerate(names):
            row = intervals[(intervals.model==name) & (intervals.metric==key)].iloc[0]
            ax.errorbar(row.estimate, j, xerr=[[row.estimate-row.lower_95], [row.upper_95-row.estimate]],
                        fmt='o', capsize=5, color=['#3969ac', '#13866c'][j])
        ax.set_yticks([0, 1], names)
        ax.set_ylim(-.6, 1.6)
        ax.set_xlabel(label + ' (95% interval)')
        ax.grid(axis='x', alpha=.25)
    fig.suptitle('Frozen test models: paired row-bootstrap uncertainty')
    fig.savefig(output / 'test_confidence_intervals.png', dpi=180)
    plt.close(fig)
    print('\nPAIRED DIFFERENCES (LightGBM minus Logistic Regression)')
    print(paired[paired.metric.isin(plot_keys + ['f1', 'brier_score'])].round(6).to_string(index=False))
    print('\nMODEL CONFIDENCE INTERVALS')
    print(intervals[intervals.metric.isin(plot_keys)].round(6).to_string(index=False))
    print(f'\nSaved: {output}', flush=True)


if __name__ == '__main__':
    main()
