# Self-healing distributed drone swarm

AI3403 Multi-Agent Systems, IIT Hyderabad. A seeded 2D simulator with private
agent state, neighbor-only delayed/lossy communication, local search and map
exchange, capacitated auctions, edge-consensus ADMM with logged fallback,
heartbeat recovery, majority task leases, robust local safety barriers, W-MSR,
and observer-based STL monitoring.

Read [the verification report](results/sanity_report.md) before interpreting
results. A successful Python process is not evidence that every scientific or
safety requirement passed. [Findings](docs/FINDINGS.md) and
[assumptions](docs/ASSUMPTIONS.md) explicitly describe remaining limitations.
No report or presentation is included.

## Install and run

Python 3.10+ is required. Run from the repository root. A fresh virtual
environment avoids the host Anaconda installation's NumPy/Matplotlib ABI issue.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
.\make.cmd test
.\make.cmd demo
.\make.cmd all
.\make.cmd verify
```

On this host Anaconda's ensurepip failed. The environment was bootstrapped with
the host pip's explicit target-interpreter support:

```powershell
python -m venv --without-pip .venv
python -m pip --python .venv\Scripts\python.exe install -r requirements.txt
```

`make.cmd` is an explicit Windows task adapter, not an installation of GNU Make.
On Linux/macOS, activate a venv, install requirements, and use the supplied
`Makefile`:

```sh
make test
make demo
make all
make verify
```

Equivalent portable entry points:

```sh
python -m pytest -q
python -m swarm.experiments.run_all --demo
python -m swarm.experiments.run_all --workers 4
python -m swarm.experiments.verify
python -m swarm.src.viz --live
```

`--live` generates the mission artifacts and opens a Tk playback window. All
ordinary rendering uses Agg and works headlessly. Live GUI playback is optional;
it has not been interactively verified on this host.

## Outputs and reproducibility

- `results/full/exp1.csv` through `exp7.csv`: one row per seed per condition,
  20 fixed evaluation seeds (3001-3020). All seven suites total 580 episodes.
- `results/full/summary.csv`: per-condition mean, sample standard deviation,
  and two-sided 95% Student t confidence interval, with seed as sample unit.
- `results/full/welch_tests.csv`: required Welch comparisons for Experiment 1.
  The paired scenario design is retained; Welch is not a paired analysis.
- `results/full/jobs/`: atomic per-episode JSON, full histories and failure
  records, complete configuration and source/config fingerprint. Restarting
  `all` reuses matching completed jobs. Changed algorithms invalidate caches;
  rendering-only changes do not. Failed jobs are never replaced by invented rows.
- `results/figures/`: 300-dpi labeled PNGs, maximum width 6.5 inches.
- `results/animations/mission.gif`, `mission.mp4`: actual captured demonstration
  (selected evaluation episode, Experiment 2 seed 3004), including agent and link failures and recovery. The JSON and trace
  next to these files disclose the precise scenario and physical failures.
- `results/demo/`: reduced run of every condition, separate seed 71. The demo
  inherits the same algorithms; only seeds and simulation size/horizon differ.
- `results/tuning/metrics.json` and `swarm/config/frozen.json`: tuning seeds
  41-43 and the fixed parameters. Earlier 1001/2001-series seeds are pilot/development
  data, kept separate from the final frozen-source evaluation. Some pre-audit
  smoke checks also used 3001-series scenarios; this is disclosed in assumptions.
- `results/sanity_report.md`, `verification.json`, `test_output.txt`: gate status,
  checks and test evidence. Verification reruns the demo and tests.
- `docs/DEFINITIONS.md`, `ASSUMPTIONS.md`, `FINDINGS.md`, `TRACEABILITY.md`:
  metric definitions, limitations, data-backed findings and proposal mapping.

All random streams are independent for scenario, failures, sensing, radio links,
bus and fault injection. Compared methods receive identical seeded obstacles,
survivor positions, initial batteries and failure schedules. Executed trajectories
and packet counts can legitimately diverge after policies diverge. The centralized
LP is a lower bound on assignment **cost**, not on mission completion time.

For an individual episode in Python:

```python
from swarm.experiments.run_all import configuration
from swarm.src.sim import simulate
result = simulate(configuration() | {"debug": True}, seed=3001)
print(result["metrics"])
```

Debug mode checks physical map validity, monotonic battery and coverage, dead
agent immobility/silence, and bus counters at every step. Tests independently
check optimum agreement, spectral convergence, exact small-graph robustness,
known STL signs, local redistribution, object isolation and deterministic output.

## Scientific limits

The mission's changing local ADMM membership often forces fallback; static
solver convergence must not be substituted for mission optimality. Local
bid views are eventually consistent; majority leases protect actual execution
while sacrificing availability in minority partitions. The local reachable-ball
barrier uses an ideal onboard proximity observation (6.05-unit default radius),
independent of radio loss. Its safety guarantee depends on accurate proximity
measurements and bounded speeds; it does not require globally shared positions.
Violations are recorded in CSVs and the gate. Mission completion can precede a
scheduled crash: observed and scheduled
failure counts are reported separately. See the findings before claiming
resilience at a requested injected percentage.

The full run is not deliberately slowed to match an estimated 2-3-hour budget.
Actual experiment wall times are recorded in each `run_manifest.json` and job
runtime fields. Rendering and verification time are separate from job wall time.

## Measured runtimes

The final measured values are written to `results/RUNTIMES.md` from run manifests.
An initial complete reduced smoke run took 47.14 seconds for its 29 experiment
jobs and about 27 seconds for diagnostic figures and animation. The final
31-test suite took 22.77 seconds (see `results/test_output.txt`).
Cold dependency installation and first Matplotlib font-cache creation are excluded.

The corrected 580-job evaluation took **3523.46 seconds (58.72 minutes)** for the
jobs plus about 81 seconds for final rendering. The cold 120-step demo took
**149.05 seconds** including its figures and media, below the five-minute budget.
Its 29 experiment jobs took 100.33 seconds. Final verification, including the
tests and cold demo, took **181.51 seconds**. These are measured host timings,
not the original 2-3-hour planning estimate. Cold manifests are retained as
`results/full/cold_run_manifest.json` and `results/demo/cold_run_manifest.json`.
The previous complete version and its timings remain in `results/pilot_complete_v1/`.

The recorded dependency environment is Python 3.12.7; use
`requirements-lock.txt` for those exact package versions. The minimum-version
`requirements.txt` supports compatible installations on Python 3.10+.

## Source layout

`swarm/src/` implements environment, agent, comms, search, allocation, ADMM,
consensus, healing, safety, metrics, simulation and rendering. `swarm/config/`
contains YAML defaults and each experiment sweep. `swarm/experiments/` contains
the resumable process-pool runner, verifier and optional playback. `swarm/tests/`
contains independent numerical and invariant tests. The unchanged proposal is
preserved as `inputs/proposal.pdf`; the complete brief is in `AGENTS.md`.
