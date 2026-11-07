"""Audit differences between the preserved complete version and corrected runs."""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd


def compare(previous: Path, current: Path, output: Path) -> dict:
    changes, cases, mismatches = [], 0, []
    for path in sorted(current.glob('*.json')):
        old_path = previous/path.name
        if not old_path.exists():
            continue
        before, after = json.loads(old_path.read_text()), json.loads(path.read_text())
        cases += 1
        if before['config'] != after['config']:
            mismatches.append(path.name)
        for metric, value in after['metrics'].items():
            if metric in {'runtime_seconds', 'experiment', 'condition', 'seed'}:
                continue
            old = before['metrics'].get(metric)
            if old is not None and not np.isclose(old, value, rtol=1e-10, atol=1e-8, equal_nan=True):
                changes.append(dict(source_job=path.name, experiment=after['metrics']['experiment'],
                                    condition=after['metrics']['condition'], seed=after['metrics']['seed'],
                                    metric=metric, before=old, after=value, difference=value-old))
    output.mkdir(parents=True, exist_ok=True)
    columns = ['source_job', 'experiment', 'condition', 'seed', 'metric', 'before', 'after', 'difference']
    frame = pd.DataFrame(changes, columns=columns)
    frame.to_csv(output/'boundary_fix_changes.csv', index=False)
    summary = dict(compared_jobs=cases, changed_jobs=frame.source_job.nunique(),
                   changed_measurements=len(frame), configuration_mismatches=mismatches,
                   note='Runtime is excluded. Differences are preserved, not filtered to favor a method.')
    (output/'boundary_fix_comparison.json').write_text(json.dumps(summary, indent=2))
    return summary


if __name__ == '__main__':
    print(compare(Path('results/pilot_complete_v1/jobs'), Path('results/full/jobs'), Path('results/full')))
