"""Replay a frozen case and independently reconstruct task-completion timing."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
from swarm.src.sim import simulate
from swarm.src.env import Environment


def audit(path: Path, output: Path) -> pd.DataFrame:
    saved = json.loads(path.read_text())
    config = saved['config'] | {'frame_stride': 1}
    seed = saved['metrics']['seed']
    result = simulate(config, seed, capture=True)
    a, b = result['metrics'].copy(), saved['metrics'].copy()
    for values in [a, b]:
        for key in ['runtime_seconds', 'experiment', 'condition']:
            values.pop(key, None)
    assert a == b, 'Replay must reproduce the source case before it can audit metrics'
    env = Environment(seed, config['n'], config)
    geom = env.geometry
    seen = np.zeros(len(geom.free), bool)
    rows = []
    for t, snapshot in enumerate(result['snapshots']):
        positions = env.positions if t == 0 else result['trajectories'][t-1]
        previous_fraction = {r: seen[geom.free & (geom.region == r)].mean()
                             for r in range(config['regions'])}
        for i in np.flatnonzero(snapshot['alive']):
            seen |= geom.free & (np.linalg.norm(geom.centers-positions[i], axis=1) <= config['sense_radius'])
        assert seen[geom.free].mean() == result['history'][t]['coverage']
        for failure in result['failures']:
            if failure['tasks']:
                row = dict(t=t, failed_drone=failure['drone'], failure_t=failure['time'],
                           task_set=';'.join(failure['tasks']),
                           active=';'.join(task for task in snapshot['tasks'] if task),
                           all_active=all(task in snapshot['tasks'] for task in failure['tasks']),
                           global_coverage=float(seen[geom.free].mean()))
                for task in failure['tasks']:
                    if task.startswith('r'):
                        r = int(task[1:])
                        row[f'{task}_coverage_before_step'] = previous_fraction[r]
                        row[f'{task}_coverage_after_sense'] = float(seen[geom.free & (geom.region == r)].mean())
                rows.append(row)
    frame = pd.DataFrame(rows)
    output.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output, index=False)
    return frame


if __name__ == '__main__':
    frame = audit(Path('results/full/jobs/exp4_healing_on_3012.json'),
                  Path('results/full/recovery_audit_3012.csv'))
    print(frame.loc[frame.t == frame.failure_t].to_string(index=False))
