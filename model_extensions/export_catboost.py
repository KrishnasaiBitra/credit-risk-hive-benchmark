"""Export CatBoost with its categorical processing and verify all validation rows."""
import argparse
from pathlib import Path
import joblib
import numpy as np
from catboost import Pool
from .common import load_split, read_json, sha, write_json
from .portable import PortableCatBoost


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project',type=Path,required=True)
    parser.add_argument('--run',type=Path,required=True)
    args=parser.parse_args()
    output=args.run/'catboost'
    selection=read_json(output/'selection.json')
    features=selection['features']
    train=load_split(args.project,'train',features)
    validation=load_split(args.project,'validation',features)
    native=joblib.load(output/'model.joblib')
    file=output/'portable_model.py'
    native.save_model(str(file),format='python',pool=Pool(train[features],train.target,cat_features=selection['categorical_features']))
    portable=PortableCatBoost(file,features,selection['categorical_features'])
    maximum=0.0
    for offset in range(0,len(validation),5000):
        x=validation[features].iloc[offset:offset+5000]
        expected=native.predict_proba(x)
        actual=portable.predict_proba(x)
        maximum=max(maximum,float(np.max(np.abs(expected-actual))))
        np.testing.assert_allclose(actual,expected,rtol=0,atol=1e-10)
        print(f'Portable CatBoost checked {min(offset+5000,len(validation)):,} validation rows',flush=True)
    write_json(output/'portable_verification.json',dict(rows=len(validation),maximum_absolute_probability_error=maximum,atol=1e-10,
        sha256=sha(file),export='CatBoost official Python export with training Pool; sigmoid applied to raw margin.'))
    print('Export verified:',maximum,flush=True)


if __name__=='__main__':
    main()
