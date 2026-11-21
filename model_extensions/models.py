import numpy as np


class AdaptiveForestModel:
    """DataFrame prediction adapter. Prediction never calls learn_one."""
    def __init__(self, forest, features):
        self.forest = forest
        self.features = list(features)
        self.classes_ = np.array([0, 1])

    def predict_proba(self, frame):
        probabilities = np.array([
            self.forest.predict_proba_one(row).get(1, 0.0)
            for row in frame[self.features].to_dict(orient='records')
        ], dtype=float)
        if not np.isfinite(probabilities).all():
            raise ValueError('Adaptive Random Forest produced non-finite probabilities.')
        return np.column_stack([1 - probabilities, probabilities])
