"""Real-run figures and compact headless mission GIF/MP4 generation."""
from __future__ import annotations
from pathlib import Path
import json
import yaml
import textwrap
import numpy as np
import pandas as pd
import networkx as nx
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from PIL import Image
import imageio.v2 as imageio
from .consensus import metropolis, spectral_rate, faulty_trial
from .admm import solve, centralized
from .sim import simulate

plt.rcParams.update({'font.size': 9, 'axes.labelsize': 9, 'legend.fontsize': 8,
                     'axes.spines.top': False, 'axes.spines.right': False,
                     'savefig.dpi': 300, 'figure.constrained_layout.use': True})


def save(fig, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=300)
    plt.close(fig)


def experiment_figures(frame: pd.DataFrame, summary: pd.DataFrame, folder: Path) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    for experiment, data in frame.groupby('experiment'):
        labels = list(data.condition.unique())
        fig, axes = (plt.subplots(4, 1, figsize=(6.5, 8.5)) if len(labels) > 6
                     else plt.subplots(2, 2, figsize=(6.5, 5.2)))
        metrics = [('completion_time', 'Completion / censoring time (s)'),
                   ('success', 'Mission success fraction'),
                   ('messages_per_step', 'Attempted transmissions / step'),
                   ('recovery_time' if experiment == 4 else 'coverage',
                    'Recovery / censoring time (s)' if experiment == 4 else 'Free-cell coverage fraction')]
        if experiment == 6:
            metrics[2:] = [('controlled_fault_error', 'Controlled honest-reference error'),
                            ('consensus_error', 'Mission coverage-estimate error')]
        if experiment == 5:
            metrics[3] = ('runtime_seconds', 'Simulation runtime (s)')
        for ax, (metric, ylabel) in zip(axes.flat, metrics):
            s = summary[(summary.experiment == experiment) & (summary.metric == metric)].set_index('condition').loc[labels]
            x = np.arange(len(labels))
            ax.errorbar(x, s['mean'], yerr=np.vstack([s['mean']-s.ci_low, s.ci_high-s['mean']]),
                        fmt='o-', capsize=3, color='#16657b', label='Mean and 95% t CI')
            ax.fill_between(x, s.ci_low, s.ci_high, alpha=.12, color='#16657b')
            display = [label.replace('_', '\n') if len(labels) <= 4 else label.replace('_', ' ') for label in labels]
            ax.set_xticks(x, display, rotation=40, ha='right', fontsize=8)
            ax.set_ylabel(textwrap.fill(ylabel, 20))
            ax.grid(alpha=.2)
        axes.flat[0].legend()
        count = data.seed.nunique()
        fig.suptitle(f'Experiment {experiment} | {count} scenario {"seed" if count == 1 else "seeds"}')
        save(fig, folder/f'exp{experiment}.png')
    fig, ax = plt.subplots(figsize=(6.5, 3))
    data = summary[summary.metric == 'success']
    for experiment, group in data.groupby('experiment'):
        ax.plot(np.full(len(group), experiment), group['mean'], 'o', label=f'Experiment {experiment}')
    ax.set(xlabel='Experiment', ylabel='Mission success fraction', ylim=(-.05, 1.05))
    ax.legend(ncol=4, fontsize=8, loc='lower center')
    ax.grid(alpha=.2)
    save(fig, folder/'summary_comparison.png')


def diagnostics(cfg: dict, figures: Path, data_folder: Path) -> None:
    """Controlled analytic validation runs, saved alongside episode measurements."""
    diag = data_folder/'diagnostics'
    diag.mkdir(parents=True, exist_ok=True)
    # Theory: initialize exactly in the subdominant eigenspace; no fitted theory.
    g = nx.cycle_graph(9)
    w = metropolis(g)
    vals, vectors = np.linalg.eigh(w)
    k = np.argsort(abs(vals))[-2]
    x = vectors[:, k]
    errors = []
    for step in range(60):
        errors.append(np.linalg.norm(x-x.mean()))
        x = w@x
    lambda2 = float(np.linalg.eigvalsh(nx.laplacian_matrix(g).toarray())[1])
    rate = 1-lambda2/3  # 2-regular cycle: Metropolis W = I - L/3
    predicted = errors[0]*rate**np.arange(60)
    pd.DataFrame({'step': range(60), 'measured': errors, 'theory': predicted,
                  'lambda2': lambda2, 'predicted_rate': rate}).to_csv(diag/'consensus.csv', index=False)
    fig, ax = plt.subplots(figsize=(6.2, 3.4))
    ax.semilogy(errors, label='Measured norm')
    ax.semilogy(predicted, '--', label='Prediction from Fiedler eigenvalue')
    ax.set(xlabel='Neighbor rounds', ylabel='Disagreement norm')
    ax.legend()
    save(fig, figures/'consensus_theory.png')
    fig, axes = plt.subplots(1, 2, figsize=(6.5, 3))
    rng = np.random.default_rng(77)
    initial = rng.uniform(0, 1, 9)
    rows = []
    lap = nx.laplacian_matrix(g).toarray()
    for alpha in [.05, .2, .4]:
        x = initial.copy()
        curve = []
        for t in range(100):
            curve.append(np.linalg.norm(x-x.mean()))
            x -= alpha*lap@x
            rows.append(dict(step=t, alpha=alpha, error=curve[-1]))
        axes[0].semilogy(curve, label=f'alpha={alpha}')
    x = initial.copy()
    curve = []
    broken = g.copy(); broken.remove_edges_from([(0, 1), (4, 5)])
    for t in range(100):
        x = metropolis(broken if 15 <= t < 55 else g)@x
        curve.append(np.linalg.norm(x-x.mean()))
    axes[1].semilogy(curve)
    axes[1].axvspan(15, 55, alpha=.15, color='orange', label='Disconnected')
    for ax in axes:
        ax.set(xlabel='Neighbor rounds', ylabel='Disagreement norm')
        ax.legend()
    pd.DataFrame(rows).to_csv(diag/'alpha.csv', index=False)
    pd.DataFrame({'step': range(100), 'error': curve}).to_csv(diag/'disconnection.csv', index=False)
    save(fig, figures/'consensus_alpha_disconnection.png')
    # ADMM objective / residual evidence versus independent centralized LP.
    cost = np.random.default_rng(81).uniform(0, 6, (4, 6))
    cap = np.full(4, 2.)
    result = solve(cost, cap, nx.cycle_graph(4), iterations=2000, tol=1e-4)
    optimum = centralized(cost, cap)[1]
    h = result['history']
    pd.DataFrame(h, columns=['primal', 'dual', 'objective']).assign(optimum=optimum).to_csv(diag/'admm.csv', index=False)
    fig, axes = plt.subplots(1, 2, figsize=(6.5, 3))
    axes[0].semilogy(np.maximum(h[:, 0], 1e-12), label='Primal')
    axes[0].semilogy(np.maximum(h[:, 1], 1e-12), label='Dual')
    axes[0].set(xlabel='ADMM neighbor round', ylabel='Residual norm'); axes[0].legend()
    axes[1].semilogy(np.maximum(abs(h[:, 2]-optimum), 1e-12), label='Absolute objective gap')
    axes[1].set(xlabel='ADMM neighbor round', ylabel='Gap to centralized LP'); axes[1].legend()
    save(fig, figures/'admm_convergence.png')
    fig, axes = plt.subplots(1, 2, figsize=(6.5, 3))
    records = []
    for panel, attack in zip(axes, ['bias', 'random']):
        for method in ['ordinary', 'wmsr']:
            trial = faulty_trial(82, method, attack=attack)
            error = np.max(abs(trial['history'][:, 1:]-trial['reference']), axis=1)
            panel.plot(error, label=method.upper())
            records.extend(dict(attack=attack, method=method, step=t, error=e) for t, e in enumerate(error))
        panel.set(title=attack, xlabel='Neighbor rounds', ylabel='Honest error to initial mean')
        panel.legend()
    pd.DataFrame(records).to_csv(diag/'wmrs.csv', index=False)
    save(fig, figures/'wmsr_byzantine.png')
    # Architecture is explanatory; all other diagrams use sampled traces.
    fig, ax = plt.subplots(figsize=(6.5, 3))
    ax.set_axis_off()
    boxes = [(0.12, .7, 'Local sensing'), (.5, .7, 'Neighbor bus'), (.88, .7, 'Consensus / ADMM'),
             (.88, .2, 'Execute safely'), (.5, .2, 'Heartbeat suspicion'), (.12, .2, 'Reallocate / resume')]
    for x, y, label in boxes:
        ax.text(x, y, label, ha='center', va='center', fontsize=8,
                bbox=dict(boxstyle='round,pad=.5', fc='#e7f0f3', ec='#16657b'))
    for a, b in zip(boxes, boxes[1:]+boxes[:1]):
        ax.annotate('', xy=b[:2], xytext=a[:2], arrowprops=dict(arrowstyle='->', color='#447'))
    save(fig, figures/'architecture.png')


def draw_world(ax, geom, survivors, snapshot, battery_labels: bool = True):
    ax.set(xlim=(0, geom.size), ylim=(0, geom.size), xlabel='x (world units)', ylabel='y (world units)')
    ax.set_aspect('equal')
    for x, y, w, h in geom.obstacles:
        ax.add_patch(Rectangle((x, y), w, h, color='#666b73', alpha=.8))
    positions, alive = snapshot['positions'], snapshot['alive']
    for i, j in snapshot['edges']:
        ax.plot(positions[[i, j], 0], positions[[i, j], 1], color='#7396a7', alpha=.3, lw=.5)
    for i in snapshot['detected']:
        ax.scatter(*survivors[i], marker='*', s=85, c='#2d9e63' if i in snapshot['rescued'] else '#ed9830', zorder=4)
    colors = [('#2d9e63' if task.startswith('s') else matplotlib.colors.to_hex(plt.cm.tab20(int(task[1:]) % 20)))
              if task else '#2269aa' for task in snapshot['tasks']]
    ax.scatter(positions[alive, 0], positions[alive, 1], c=np.array(colors)[alive], s=20, zorder=5)
    if (~alive).any():
        ax.scatter(positions[~alive, 0], positions[~alive, 1], c='#d52d39', marker='x', s=50, zorder=6)
    for i, p in enumerate(positions):
        if alive[i] and battery_labels:
            ax.text(p[0]+.6, p[1]+.6, f'{snapshot["battery"][i]:.0f}', fontsize=8)


def mission_media(cfg: dict, output: Path, figures: Path, live: bool = False) -> None:
    output.mkdir(parents=True, exist_ok=True)
    settings = yaml.safe_load((Path(__file__).resolve().parents[1]/'config/mission_replay.yaml').read_text())
    seed = settings.pop('seed')
    local = cfg | settings
    result = simulate(local, seed, capture=True)
    if not any(f['tasks'] and f['recovered'] is not None for f in result['failures']):
        raise RuntimeError('Illustration has no real non-vacuous recovery; rerun select_animation')
    (output/'mission_config.json').write_text(json.dumps(local | {'seed': seed}, indent=2))
    (output/'mission_metrics.json').write_text(json.dumps(result['metrics'], indent=2))
    pd.DataFrame(result['history']).to_csv(output/'mission_trace.csv', index=False)
    (output/'mission_failures.json').write_text(json.dumps(result['failures'], indent=2))
    geom, survivors = result['geometry'], result['survivors']
    snapshots = result['snapshots']
    if not snapshots:
        raise RuntimeError('No animation frames')
    images = []
    writer = imageio.get_writer(str(output/'mission.mp4'), fps=8, codec='libx264', quality=7)
    for snapshot in snapshots:
        fig, (ax, panel) = plt.subplots(1, 2, figsize=(6.4, 4.8), dpi=100, gridspec_kw={'width_ratios': [3, 1]})
        draw_world(ax, geom, survivors, snapshot)
        panel.set_axis_off()
        text = (f"t = {snapshot['t']} s\n\nCoverage\n{snapshot['coverage']:.1%}\n\nMessages / step\n{snapshot['messages']}"
                f"\n\nConsensus error\n{snapshot['consensus_error']:.3f}\n\nAlive\n{int(snapshot['alive'].sum())}/{len(snapshot['alive'])}"
                f"\n\nRescued\n{len(snapshot['rescued'])}/{len(survivors)}")
        panel.text(0, .97, text, va='top', fontsize=9)
        fig.suptitle('Distributed response | task colors; numbers: battery; red X: crash', fontsize=9)
        fig.canvas.draw()
        rgb = np.asarray(fig.canvas.buffer_rgba())[:, :, :3].copy()
        writer.append_data(rgb)
        images.append(Image.fromarray(rgb).quantize(colors=128))
        plt.close(fig)
    writer.close()
    images[0].save(output/'mission.gif', save_all=True, append_images=images[1:], duration=125, loop=0, optimize=True)
    assert (output/'mission.gif').stat().st_size <= 15*1024*1024
    for filename, snapshot in [('environment_overview', snapshots[0]), ('task_assignment', snapshots[len(snapshots)//2])]:
        fig, ax = plt.subplots(figsize=(5.8, 5.2))
        draw_world(ax, geom, survivors, snapshot, battery_labels=False)
        if filename == 'environment_overview':
            ax.scatter(survivors[:, 0], survivors[:, 1], marker='*', s=65, color='#ed9830', label='Ground-truth survivors')
            ax.set_title(f"Environment at t={snapshot['t']} s (observer view)")
            ax.legend(fontsize=8)
        else:
            blocks = int(np.sqrt(cfg['regions']))
            for line in np.linspace(0, geom.size, blocks+1)[1:-1]:
                ax.axvline(line, color='gray', lw=.5, ls='--', alpha=.4)
                ax.axhline(line, color='gray', lw=.5, ls='--', alpha=.4)
            for i, task in enumerate(snapshot['tasks']):
                if task and snapshot['alive'][i]:
                    ax.text(*snapshot['positions'][i]+1, task.upper(), fontsize=8)
            ax.set_title(f"Current task labels at t={snapshot['t']} s")
        save(fig, figures/f'{filename}.png')
    event = next((f['time'] for f in result['failures'] if f['tasks']), snapshots[len(snapshots)//2]['t'])
    fig, axes = plt.subplots(1, 3, figsize=(6.5, 2.8))
    for ax, when, label in zip(axes, [max(0, event-4), event, event+12], ['Before', 'During', 'After']):
        snapshot = min(snapshots, key=lambda s: abs(s['t']-when))
        draw_world(ax, geom, survivors, snapshot, battery_labels=False)
        ax.set_title(f"{label}: t={snapshot['t']}\nFiedler={snapshot['fiedler']:.2f}", fontsize=9)
        ax.set_xlabel('x'); ax.set_ylabel('y')
    save(fig, figures/'topology_failure.png')
    fig, ax = plt.subplots(figsize=(6.2, 3.4))
    for index, failure in enumerate(result['failures']):
        for key, marker, color in [('time', 'x', '#d52d39'), ('detection', 'o', '#ed9830'), ('recovered', 's', '#2d9e63')]:
            if failure[key] is not None:
                ax.scatter(failure[key], index, marker=marker, color=color, label=key if index == 0 else None)
    ax.set(xlabel='Mission time (s)', ylabel='Observed failure event')
    ax.set_yticks(range(len(result['failures'])),
                  [f"Drone {f['drone']} ({len(f['tasks'])} {'task' if len(f['tasks']) == 1 else 'tasks'})" for f in result['failures']], fontsize=8)
    handles, labels = ax.get_legend_handles_labels()
    if handles:
        ax.legend()
    save(fig, figures/'recovery_timeline.png')
    fig, ax = plt.subplots(figsize=(5.8, 5.2))
    draw_world(ax, geom, survivors, snapshots[-1], battery_labels=False)
    trajectory = result['trajectories']
    for i in range(trajectory.shape[1]):
        ax.plot(trajectory[:, i, 0], trajectory[:, i, 1], lw=.7, alpha=.5)
    save(fig, figures/'trajectories.png')
    trace = pd.DataFrame(result['history'])
    fig, axes = plt.subplots(2, 1, figsize=(6.2, 4.5))
    axes[0].plot(trace.t, np.minimum.accumulate(trace.separation_robustness), label='Always separation prefix robustness')
    axes[0].axhline(0, color='red', ls='--'); axes[0].set(ylabel='Distance margin'); axes[0].legend()
    axes[1].axhline(result['metrics']['response_robustness'], label='Minimum finite-window response robustness')
    axes[1].axhline(0, color='red', ls='--')
    axes[1].set(xlabel='Mission time (s)', ylabel='Response robustness score'); axes[1].legend()
    save(fig, figures/'stl_robustness.png')
    # FP/FN evaluated from actual local suspicion events across timeout settings.
    rows = []
    for timeout in [3, 5, 10, 20]:
        metrics = result['metrics'] if timeout == local['h_timeout'] else simulate(local | {'h_timeout': timeout}, seed)['metrics']
        rows.append(dict(timeout=timeout, false_positives=metrics['false_positives'], false_negatives=metrics['false_negatives']))
    pd.DataFrame(rows).to_csv(output/'heartbeat.csv', index=False)
    fig, ax = plt.subplots(figsize=(6.2, 3.4))
    for key in ['false_positives', 'false_negatives']:
        ax.plot([r['timeout'] for r in rows], [r[key] for r in rows], 'o-', label=key.replace('_', ' '))
    ax.set(xlabel='Heartbeat timeout (steps)', ylabel='Observed count'); ax.legend()
    save(fig, figures/'heartbeat_fp_fn.png')
    if live:
        import subprocess, sys
        subprocess.run([sys.executable, '-m', 'swarm.experiments.live', str(output/'mission.gif')], check=True)


if __name__ == '__main__':
    import argparse
    import yaml
    parser = argparse.ArgumentParser()
    parser.add_argument('--live', action='store_true')
    args = parser.parse_args()
    cfg = yaml.safe_load(Path('swarm/config/default.yaml').read_text())
    mission_media(cfg, Path('results/animations'), Path('results/figures'), args.live)
