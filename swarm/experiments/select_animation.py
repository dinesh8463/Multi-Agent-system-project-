"""Select a disclosed real evaluation replay with a non-vacuous recovery.

Selection is for illustration only. No policy/experiment parameter is changed;
the full seed distribution remains in the statistical CSVs.
"""
from pathlib import Path
import json
import pandas as pd
import yaml


def main() -> None:
    rows, selected = [], None
    for path in sorted(Path('results/full/jobs').glob('exp2*.json')):
        record = json.loads(path.read_text())
        meaningful = any(f['tasks'] and f['recovered'] is not None for f in record['failures'])
        qualifies = meaningful and bool(record['metrics']['success'])
        rows.append(dict(source=str(path).replace('\\', '/'), seed=record['metrics']['seed'],
                         successful=record['metrics']['success'], meaningful_recovery=meaningful,
                         chosen=bool(qualifies and selected is None)))
        if qualifies and selected is None:
            selected = (path, record)
    if selected is None:
        raise RuntimeError('No completed real evaluation episode has a non-vacuous recovery')
    path, record = selected
    settings = record['config'] | {'seed': record['metrics']['seed'], 'frame_stride': 1,
                                   'source_job': str(path).replace('\\', '/')}
    Path('swarm/config/mission_replay.yaml').write_text(yaml.safe_dump(settings, sort_keys=True))
    Path('results/animations').mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv('results/animations/selection_trace.csv', index=False)
    print(f'Selected {path}; only frame sampling differs from the original episode.')


if __name__ == '__main__':
    main()
