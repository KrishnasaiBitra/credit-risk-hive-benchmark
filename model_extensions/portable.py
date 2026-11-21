"""Inference-only adapter for CatBoost's official standalone Python export."""
import importlib.util
from pathlib import Path
import math
import numpy as np


class PortableCatBoost:
    def __init__(self,path,features,categorical):
        self.features=list(features)
        self.categorical=list(categorical)
        self.numeric=[f for f in features if f not in categorical]
        self.classes_=np.array([0,1])
        spec=importlib.util.spec_from_file_location('_credit_catboost_export',Path(path))
        self.module=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)

    def predict_proba(self,frame):
        values=[]
        for row in frame[self.features].to_dict(orient='records'):
            # Native CatBoost quantizes numeric inputs from float32 values.
            raw=self.module.apply_catboost_model([float(np.float32(row[f])) for f in self.numeric],[str(row[f]) for f in self.categorical])
            p=1/(1+math.exp(-raw)) if raw>=0 else math.exp(raw)/(1+math.exp(raw))
            values.append([1-p,p])
        return np.array(values)
