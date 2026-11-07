"""Descriptive event-level recovery audit; never replaces the primary metric."""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd


def recovery_events(job_dir: Path, output: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    episodes, events = [], []
    for path in sorted(job_dir.glob('*.json')):
        record = json.loads(path.read_text())
        metrics = record['metrics']
        episodes.append(metrics)
        for number, failure in enumerate(record['failures']):
            recovered = failure['recovered'] is not None
            events.append(dict(experiment=metrics['experiment'], condition=metrics['condition'],
                               seed=metrics['seed'], source_job=path.name, event=number,
                               drone=failure['drone'], failure_t=failure['time'],
                               detection_t=failure['detection'], recovery_t=failure['recovered'],
                               task_count=len(failure['tasks']), tasks=';'.join(failure['tasks']),
                               vacuous=int(not failure['tasks']), recovered=int(recovered),
                               delay=(failure['recovered'] if recovered else record['config']['steps'])-failure['time'],
                               episode_end_t=record['history'][-1]['t'],
                               mission_success=metrics['success']))
    frame = pd.DataFrame(events)
    summaries = []
    for (experiment, condition), data in pd.DataFrame(episodes).groupby(['experiment', 'condition']):
        group = frame[(frame.experiment == experiment) & (frame.condition == condition)]
        nonempty = group[group.task_count > 0]
        summaries.append(dict(experiment=experiment, condition=condition, episodes=len(data),
                              observed_crashes=len(group), vacuous_events=int(group.vacuous.sum()),
                              nonempty_events=len(nonempty), nonempty_recovered=int(nonempty.recovered.sum()),
                              event_recovery_rate=group.recovered.mean() if len(group) else np.nan,
                              nonempty_recovery_rate=nonempty.recovered.mean() if len(nonempty) else np.nan,
                              primary_episode_mean_recovery=data.recovery_rate.mean(),
                              mission_success_rate=data.success.mean()))
    summary = pd.DataFrame(summaries)
    output.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output/'recovery_events.csv', index=False)
    summary.to_csv(output/'recovery_event_summary.csv', index=False)
    return frame, summary


if __name__ == '__main__':
    _, summary = recovery_events(Path('results/full/jobs'), Path('results/full'))
    print(summary[summary.experiment == 4].to_string(index=False))
