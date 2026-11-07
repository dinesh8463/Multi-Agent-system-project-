"""Resumable process-pool experiments; per-job JSON commits are atomic.

Run from the repository root. A content hash prevents stale cache reuse after
code or configuration changes. No metrics are imputed for crashed jobs.
"""
from __future__ import annotations
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import hashlib
import json
import logging
import os
from pathlib import Path
from time import perf_counter
# Each worker uses one numerical thread: avoid 4 processes each launching a full
# BLAS thread team. These settings change runtime, not algorithms or RNG streams.
for variable in ['OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS']:
    os.environ[variable] = '1'
import numpy as np
import pandas as pd
import yaml
from scipy.stats import ttest_ind
from swarm.src.sim import simulate
from swarm.src.metrics import summarize
from swarm.src.consensus import faulty_trial

ROOT = Path(__file__).resolve().parents[2]


def configuration() -> dict:
    return yaml.safe_load((ROOT/'swarm/config/default.yaml').read_text())


def fingerprint(cfg: dict) -> str:
    h = hashlib.sha256(json.dumps(cfg, sort_keys=True).encode())
    for p in sorted((ROOT/'swarm/src').glob('*.py')):
        if p.name != 'viz.py':  # rendering changes cannot alter simulation measurements
            h.update(p.read_bytes())
    h.update(Path(__file__).read_bytes())
    return h.hexdigest()[:16]


def execute(job: tuple) -> dict:
    experiment, condition, seed, cfg, folder = job
    cache = Path(folder)/'jobs'/f'exp{experiment}_{condition}_{seed}.json'
    key = fingerprint(cfg)
    if cache.exists():
        old = json.loads(cache.read_text())
        if old.get('fingerprint') == key:
            return old['metrics']
    result = simulate(cfg, seed)
    metrics = result['metrics']
    metrics.update(experiment=experiment, condition=condition)
    if experiment == 6:
        attack = 'random' if condition.endswith('random') else 'bias'
        trial = faulty_trial(seed, 'wmsr' if cfg['resilient'] else 'ordinary', attack=attack)
        metrics['controlled_fault_error'] = trial['error']
        metrics['controlled_honest_spread'] = trial['spread']
    record = dict(fingerprint=key, config=cfg, metrics=metrics,
                  history=result['history'], failures=result['failures'])
    cache.parent.mkdir(parents=True, exist_ok=True)
    temp = cache.with_suffix('.tmp')
    temp.write_text(json.dumps(record, indent=2, allow_nan=True))
    temp.replace(cache)
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--demo', action='store_true')
    parser.add_argument('--workers', type=int, default=min(4, os.cpu_count() or 1))
    parser.add_argument('--only', type=int, choices=range(1, 8))
    parser.add_argument('--no-media', action='store_true')
    args = parser.parse_args()
    folder = ROOT/'results'/('demo' if args.demo else 'full')
    folder.mkdir(parents=True, exist_ok=True)
    (ROOT/'results/logs').mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s',
                        handlers=[logging.StreamHandler(), logging.FileHandler(folder/'progress.log')])
    cfg = configuration()
    if args.demo:
        cfg.update(yaml.safe_load((ROOT/'swarm/config/demo.yaml').read_text()))
    jobs = []
    for experiment in range(1, 8):
        if args.only and args.only != experiment:
            continue
        name = f'exp{experiment}' if experiment < 7 else 'ablation_sensitivity'
        sweep = yaml.safe_load((ROOT/f'swarm/config/{name}.yaml').read_text())
        for condition, override in sweep['conditions'].items():
            local = cfg | override
            if args.demo:
                local['steps'] = min(local['steps'], cfg['steps'])
            if experiment == 6:
                local['attack'] = 'random' if condition.endswith('random') else 'bias'
                local['fault_count'] = 1
            for seed in cfg['evaluation_seeds']:
                jobs.append((experiment, condition, seed, local, str(folder)))
    start = perf_counter()
    records = []
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(execute, j): j[:3] for j in jobs}
        for number, future in enumerate(as_completed(futures), 1):
            record = future.result()  # fail loudly; completed jobs remain resumable
            records.append(record)
            logging.info('%s/%s exp%s %s seed=%s success=%s time=%s runtime=%.2fs',
                         number, len(jobs), record['experiment'], record['condition'], record['seed'],
                         record['success'], record['completion_time'], record['runtime_seconds'])
    frame = pd.DataFrame(records).sort_values(['experiment', 'condition', 'seed'])
    for experiment, data in frame.groupby('experiment'):
        data.to_csv(folder/f'exp{experiment}.csv', index=False)
    frame.to_csv(folder/'all_metrics.csv', index=False)
    summary = summarize(frame)
    summary.to_csv(folder/'summary.csv', index=False)
    if 1 in frame['experiment'].values:
        data = frame[frame.experiment == 1]
        tests = []
        for metric in ['completion_time', 'energy', 'messages', 'fairness']:
            a = data[data.condition == 'centralized'][metric]
            for method in ['auction', 'admm']:
                b = data[data.condition == method][metric]
                if len(a) > 1 and len(b) > 1:
                    result = ttest_ind(a, b, equal_var=False)
                    tests.append(dict(metric=metric, comparison=f'centralized vs {method}',
                                      statistic=result.statistic, p_value=result.pvalue))
        pd.DataFrame(tests).to_csv(folder/'welch_tests.csv', index=False)
    elapsed = perf_counter()-start
    (folder/'run_manifest.json').write_text(json.dumps(dict(
        mode='demo' if args.demo else 'full', jobs=len(jobs), elapsed_seconds=elapsed,
        workers=args.workers, configuration=cfg, fingerprint=fingerprint(cfg)), indent=2))
    logging.info('Experiment jobs finished in %.2fs. Generating figures.', elapsed)
    from swarm.src.viz import experiment_figures, diagnostics, mission_media
    figure_dir = ROOT/'results'/('demo/figures' if args.demo else 'figures')
    experiment_figures(frame, summary, figure_dir)
    if not args.no_media:
        diagnostics(cfg, figure_dir, folder)
        mission_media(configuration(), ROOT/'results/animations', figure_dir)
    logging.info('Finished. Data: %s', folder)


if __name__ == '__main__':
    main()
