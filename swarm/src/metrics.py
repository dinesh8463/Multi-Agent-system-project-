"""Mission metrics and uncertainty summaries (seed is the sampling unit)."""
from __future__ import annotations
import numpy as np
import pandas as pd
from scipy.stats import t


def jain(work: np.ndarray) -> float:
    work = np.asarray(work)
    return float(work.sum()**2/(len(work)*(work@work))) if work@work > 0 else 1.0


def summarize(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (experiment, condition), data in frame.groupby(['experiment', 'condition']):
        for metric in data.select_dtypes(include='number').columns.difference(['seed', 'experiment']):
            values = data[metric].dropna().to_numpy()
            if len(values) == 0:
                continue
            std = float(np.std(values, ddof=1)) if len(values) > 1 else 0.
            half = float(t.ppf(.975, len(values)-1)*std/np.sqrt(len(values))) if len(values) > 1 else 0.
            mean = float(values.mean())
            rows.append(dict(experiment=experiment, condition=condition, metric=metric,
                             n=len(values), mean=mean, std=std, ci_low=mean-half, ci_high=mean+half))
    return pd.DataFrame(rows)
