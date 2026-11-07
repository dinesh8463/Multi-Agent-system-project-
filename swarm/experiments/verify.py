"""Strict, reproducible evidence gate. Failures are never suppressed or reclassified."""
from __future__ import annotations
import argparse
import ast
import hashlib
import json
import re
from pathlib import Path
import subprocess
import sys
from time import perf_counter
import numpy as np
import pandas as pd
from PIL import Image
import imageio.v2 as imageio
import yaml
from scipy.stats import t
from .run_all import configuration, fingerprint

ROOT = Path(__file__).resolve().parents[2]


def findings(frame: pd.DataFrame, checks: list[dict]) -> None:
    lines = ['# Findings from recorded evaluation data', '',
             '- These observations are generated from the full-run CSVs. They are not expected outcomes or synthetic values.']
    for experiment, group in frame.groupby('experiment'):
        for condition, data in group.groupby('condition'):
            lines.append(f"- Experiment {experiment}, {condition}: success {data.success.mean():.1%}; "
                         f"mean completion/censoring time {data.completion_time.mean():.2f} s; coverage {data.coverage.mean():.3f}; "
                         f"observed crashes {data.failures.sum():.0f}/{data.scheduled_failures.sum():.0f} scheduled. "
                         f"Source: [exp{experiment}.csv](../results/full/exp{experiment}.csv), "
                         f"[figure](../results/figures/exp{experiment}.png).")
    admm = frame[frame.condition.isin(['admm', 'full'])]
    if len(admm):
        lines.append(f"- ADMM mission configurations logged {admm.admm_fallbacks.sum():.0f} "
                     f"fallbacks over {admm.allocation_rounds.sum():.0f} started local allocation rounds. "
                     "The dynamic mission result cannot be described as a converged ADMM optimum. "
                     "The static connected solver is validated separately against the LP. Sources: "
                     "[all_metrics.csv](../results/full/all_metrics.csv), "
                     "[ADMM residuals](../results/full/diagnostics/admm.csv).")
    lines.append(f"- The robust local barrier recorded {frame.safety_violations.sum():.0f} pair-step "
                 f"separation violations and minimum margin {frame.separation_robustness.min():.3f}. "
                 "This is an empirical check under the explicitly modeled ideal local proximity sensor and bounded-speed assumptions. "
                 "Sources: [all_metrics.csv](../results/full/all_metrics.csv), "
                 "[STL figure](../results/figures/stl_robustness.png).")
    lines.append(f"- Majority task leases recorded {frame.ownership_conflict_steps.sum():.0f} "
                 "duplicate-execution pair-steps. Ballots are one per voter/task/epoch, and "
                 "intersecting majorities prevent conflicting certificates. Minority partitions "
                 "can lose task-claim availability. Source: "
                 "[all_metrics.csv](../results/full/all_metrics.csv).")
    lines.append(f"- Heartbeat false suspicions total {frame.false_positives.sum():.0f}; undetected "
                 f"physical crashes total {frame.false_negatives.sum():.0f}. Link outages and departing "
                 "neighbors explain false suspicions; a timeout is not a perfect crash detector. "
                 "Source: [all_metrics.csv](../results/full/all_metrics.csv), "
                 "[heartbeat curves](../results/animations/heartbeat.csv).")
    if frame.response_robustness.min() < -1000:
        lines.append('- Extreme response-robustness scores denote windows with no eligible '
                     'assigned responder, using the finite categorical penalty defined in '
                     '[DEFINITIONS.md](DEFINITIONS.md). They are not distances across the map. '
                     'Deadline violations count only mature windows. Source: '
                     '[all_metrics.csv](../results/full/all_metrics.csv).')
    exp6 = frame[frame.experiment == 6]
    for condition, data in exp6.groupby('condition'):
        if 'controlled_fault_error' in data:
            lines.append(f"- {condition}: mean controlled honest-reference error "
                         f"{data.controlled_fault_error.mean():.5f}; mission coverage-estimate error "
                         f"{data.consensus_error.mean():.5f}. W-MSR preserves an honest interval, "
                         "not necessarily the initial mean. The mission controller uses maps/bids "
                         "rather than its scalar consensus estimate, so improved estimates do "
                         "not imply faster rescue. Source: [exp6.csv](../results/full/exp6.csv), "
                         "[controlled curves](../results/figures/wmsr_byzantine.png).")
    for check in checks:
        if not check['pass']:
            lines.append(f"- FAILED CHECK `{check['name']}`: {check['detail']}. "
                         "This remains an unmet requirement and is not counted as a pass. "
                         "Source: [sanity report](../results/sanity_report.md).")
    lines += ['- Interpretation limits and development seed overlap are disclosed in '
              '[ASSUMPTIONS.md](ASSUMPTIONS.md). No evaluation result was discarded, '
              'and no favorable outcome was substituted for a measured one.']
    (ROOT/'docs/FINDINGS.md').write_text('\n'.join(lines)+'\n')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--skip-demo', action='store_true', help='Use already generated demo evidence (for development only)')
    args = parser.parse_args()
    start = perf_counter()
    checks = []
    def check(name, passed, detail):
        checks.append(dict(name=name, **{'pass': bool(passed)}, detail=str(detail)))
        print(f"{'PASS' if passed else 'FAIL'} {name}: {detail}", flush=True)
    tests = subprocess.run([sys.executable, '-m', 'pytest', '-q'], cwd=ROOT, text=True,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (ROOT/'results/test_output.txt').write_text(tests.stdout)
    check('pytest', tests.returncode == 0, tests.stdout.strip().splitlines()[-1])
    forbidden_imports = []
    for name in ['drone', 'search', 'selfheal', 'allocation', 'admm', 'consensus']:
        source = (ROOT/f'swarm/src/{name}.py').read_text()
        forbidden_imports.extend(f'{name}: {match.group(0)}' for match in
            re.finditer(r'(?:from\s+\.(?:env|sim|world)\s+import|import\s+(?:world|drones)\b)', source))
    check('decentralization_grep', not forbidden_imports, f'forbidden policy imports={forbidden_imports}')
    if not args.skip_demo:
        demo_start = perf_counter()
        demo = subprocess.run([sys.executable, '-m', 'swarm.experiments.run_all', '--demo'], cwd=ROOT,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        (ROOT/'results/demo_verification.log').write_text(demo.stdout)
        check('make_demo', demo.returncode == 0, f'demo process exit={demo.returncode}')
        check('demo_runtime', perf_counter()-demo_start < 300,
              f'{perf_counter()-demo_start:.2f}s (budget <300s; matching cached experiment jobs may be reused)')
    else:
        check('make_demo', False, 'Demo rerun skipped; strict gate requires the real demo invocation')
    required_figures = ['architecture', 'environment_overview', 'topology_failure', 'task_assignment',
                        'recovery_timeline', 'trajectories', 'consensus_theory', 'consensus_alpha_disconnection',
                        'admm_convergence', 'heartbeat_fp_fn', 'wmsr_byzantine', 'stl_robustness',
                        'summary_comparison'] + [f'exp{i}' for i in range(1, 8)]
    for directory in ['results/figures', 'results/demo/figures']:
        missing = [name for name in required_figures if not (ROOT/directory/f'{name}.png').exists()]
        check(f'figures_{directory}', not missing, f'missing={missing}')
    try:
        gif = ROOT/'results/animations/mission.gif'
        image = Image.open(gif)
        reader = imageio.get_reader(ROOT/'results/animations/mission.mp4')
        first = reader.get_data(0)
        frames = reader.count_frames()
        reader.close()
        check('animation_formats', image.n_frames > 1 and frames > 1 and gif.stat().st_size <= 15*1024**2,
              f'GIF frames={image.n_frames}, bytes={gif.stat().st_size}; MP4 frames={frames}, shape={first.shape}')
        failures = json.loads((ROOT/'results/animations/mission_failures.json').read_text())
        check('animation_failure_and_recovery', any(f['recovered'] is not None and f['tasks'] for f in failures),
              f'{len(failures)} physical crashes; {sum(f["recovered"] is not None for f in failures)} recovered')
    except Exception as exc:
        check('animation_formats', False, repr(exc))
    expected = set(configuration()['evaluation_seeds'])
    frames = []
    for experiment in range(1, 8):
        p = ROOT/f'results/full/exp{experiment}.csv'
        if not p.exists():
            check(f'exp{experiment}_seeds', False, 'Full CSV missing')
            continue
        data = pd.read_csv(p)
        name = f'exp{experiment}' if experiment < 7 else 'ablation_sensitivity'
        conditions = yaml.safe_load((ROOT/f'swarm/config/{name}.yaml').read_text())['conditions']
        check(f'exp{experiment}_seeds', set(data.condition) == set(conditions) and
              all(set(g.seed) == expected and len(g) == len(expected) for _, g in data.groupby('condition')),
              f'{len(data)} rows, {data.condition.nunique()} conditions, expected {len(expected)} unique seeds each')
        frames.append(data)
    if len(frames) == 7:
        frame = pd.concat(frames, ignore_index=True)
        monotonic = True
        stale = []
        for p in (ROOT/'results/full/jobs').glob('*.json'):
            record = json.loads(p.read_text())
            h = record['history']
            monotonic &= all(h[i]['coverage'] <= h[i+1]['coverage'] for i in range(len(h)-1))
            if record['fingerprint'] != fingerprint(record['config']):
                stale.append(p.name)
        check('source_fingerprints', not stale, f'stale jobs={stale[:10]}')
        mismatches = []
        for experiment in range(1, 8):
            name = f'exp{experiment}' if experiment < 7 else 'ablation_sensitivity'
            sweep = yaml.safe_load((ROOT/f'swarm/config/{name}.yaml').read_text())['conditions']
            for condition, override in sweep.items():
                expected_cfg = configuration() | override
                if experiment == 6:
                    expected_cfg.update(attack='random' if condition.endswith('random') else 'bias', fault_count=1)
                for seed in expected:
                    p = ROOT/f'results/full/jobs/exp{experiment}_{condition}_{seed}.json'
                    if not p.exists() or json.loads(p.read_text())['config'] != expected_cfg:
                        mismatches.append(p.name)
        check('current_sweep_configurations', not mismatches, f'mismatched job configurations={mismatches[:10]}')
        from swarm.src.env import Environment
        from swarm.src.selfheal import failure_schedule
        scenarios, schedules = {}, {}
        for p in (ROOT/'results/full/jobs').glob('*.json'):
            record = json.loads(p.read_text())
            local, metrics = record['config'], record['metrics']
            if metrics['experiment'] == 5:
                continue  # N is intentionally the intervention in scalability
            env = Environment(metrics['seed'], local['n'], local)
            digest = hashlib.sha256()
            for value in [env.geometry.free, env.survivors, env.positions, env.batteries]:
                digest.update(value.tobytes())
            key = (metrics['experiment'], metrics['seed'])
            scenarios.setdefault(key, set()).add(digest.hexdigest())
            # Failure percentages intentionally differ in Experiment 2.
            if metrics['experiment'] != 2:
                schedule = failure_schedule(metrics['seed'], local['n'], local['failure_fraction'], local['steps'])
                schedules.setdefault(key, set()).add(json.dumps(schedule, sort_keys=True))
        check('paired_scenarios', all(len(v) == 1 for v in scenarios.values()) and
              all(len(v) == 1 for v in schedules.values()),
              f'{len(scenarios)} paired scenario groups checked, including batteries/positions; identical intervention schedules across method comparisons')
        reference_dir = ROOT/'results/pilot_snapshot_reference/jobs'
        transport_differences = []
        regression_count = 0
        for p in reference_dir.glob('*.json'):
            current = ROOT/'results/full/jobs'/p.name
            if current.exists():
                before, after = json.loads(p.read_text()), json.loads(current.read_text())
                if before['config'] == after['config']:
                    a, b = before['metrics'].copy(), after['metrics'].copy()
                    a.pop('runtime_seconds'); b.pop('runtime_seconds')
                    regression_count += 1
                    if a != b:
                        transport_differences.append(p.name)
        check('transport_optimization_regression', not transport_differences,
              f'{regression_count} independently rerun episodes compared; changed scientific metrics={transport_differences[:10]}')
        check('coverage_monotonic', monotonic, 'Checked every saved episode prefix')
        baseline = frame[(frame.experiment == 1) & (frame.condition == 'auction')]
        check('zero_failure_success', baseline.success.mean() >= .9, f'{baseline.success.mean():.1%} (required >=90%)')
        failure = frame[frame.experiment == 2]
        for a, b in zip(['failure_0', 'failure_10', 'failure_20'], ['failure_10', 'failure_20', 'failure_30']):
            aa, bb = failure[failure.condition == a].set_index('seed'), failure[failure.condition == b].set_index('seed')
            delta = bb.completion_time-aa.completion_time
            half = t.ppf(.975, len(delta)-1)*delta.std(ddof=1)/np.sqrt(len(delta))
            success_delta = bb.success-aa.success
            success_half = t.ppf(.975, len(delta)-1)*success_delta.std(ddof=1)/np.sqrt(len(delta))
            passed = delta.mean()+half >= -1e-9 and success_delta.mean()-success_half <= 1e-9
            check(f'failure_trend_{a}_{b}', passed,
                  f'paired time delta {delta.mean():.3f} +/- {half:.3f}s; success delta {success_delta.mean():.3f} +/- {success_half:.3f}; statistical noise allowed')
        healing = frame[frame.experiment == 4].groupby('condition').recovery_rate.mean()
        check('healing_recovery', healing['healing_on'] >= healing['healing_off']-1e-9,
              f'ON={healing["healing_on"]:.3f}, OFF={healing["healing_off"]:.3f}')
        fault = frame[frame.experiment == 6].groupby('condition').controlled_fault_error.mean()
        check('wmsr_bound', all(fault[f'wmsr_{attack}'] < 1 and fault[f'wmsr_{attack}'] < fault[f'ordinary_{attack}'] for attack in ['bias', 'random']), fault.to_dict())
        theory = pd.read_csv(ROOT/'results/full/diagnostics/consensus.csv')
        check('spectral_rate', np.allclose(theory.measured, theory.theory, rtol=1e-5, atol=1e-10), 'relative curve tolerance 1e-5, absolute 1e-10')
        scale = frame[frame.experiment == 5].groupby('n').messages_per_step.mean()
        check('scaling_communication', bool(np.all(np.diff(scale.values) >= 0)), scale.to_dict())
        # These are explicit strict specification requirements, not silently
        # waived by an eventually-consistent implementation or a passing unit test.
        check('strong_task_ownership', frame.ownership_conflict_steps.sum() == 0,
              f'{frame.ownership_conflict_steps.sum():.0f} duplicate task execution steps; execution requires a majority lease')
        check('hard_separation', frame.safety_violations.sum() == 0,
              f'{frame.safety_violations.sum():.0f} pair-step violations; all measured live pair distances must exceed d_min')
        findings(frame, checks)
    check('documentation', all((ROOT/p).exists() for p in ['README.md', 'docs/DEFINITIONS.md', 'docs/ASSUMPTIONS.md', 'docs/FINDINGS.md', 'docs/TRACEABILITY.md']), 'README and required scientific documentation')
    check('report_and_slides_untouched', not (ROOT/'report').exists() and not (ROOT/'slides').exists(), 'Neither report nor slides was created')
    passed = all(c['pass'] for c in checks)
    record = dict(passed=passed, checks=checks, runtime_seconds=perf_counter()-start)
    (ROOT/'results/verification.json').write_text(json.dumps(record, indent=2))
    text = ['# Verification and sanity report', '', f"Overall gate: {'PASS' if passed else 'FAIL'}", '',
            '| Check | Result | Evidence / explanation |', '|---|---|---|']
    text.extend(f"| {c['name']} | {'PASS' if c['pass'] else 'FAIL'} | {c['detail'].replace('|', '/')} |" for c in checks)
    text += ['', 'All failures remain failures. See docs/FINDINGS.md for limitations and data references.']
    (ROOT/'results/sanity_report.md').write_text('\n'.join(text)+'\n')
    runtime_lines = ['# Measured wall times', '', '| Run | Job wall time (s) | Jobs | Workers |', '|---|---:|---:|---:|']
    for mode in ['demo', 'full']:
        p = ROOT/f'results/{mode}/run_manifest.json'
        if p.exists():
            manifest = json.loads(p.read_text())
            runtime_lines.append(f"| {mode} | {manifest['elapsed_seconds']:.2f} | {manifest['jobs']} | {manifest['workers']} |")
    runtime_lines += ['', f"Verification (tests, cached demo replay and rendering): {record['runtime_seconds']:.2f} s.",
                      'Job times exclude figure and animation rendering. Resumed runs can reuse cached jobs.']
    (ROOT/'results/RUNTIMES.md').write_text('\n'.join(runtime_lines)+'\n')
    sys.exit(0 if passed else 1)


if __name__ == '__main__':
    main()
