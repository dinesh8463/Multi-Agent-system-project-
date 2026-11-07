# Execution plan

Read AGENTS.md and this file before resuming. The repository began empty.
Do not write report/ or slides. Never manufacture a run or a passing check.

- [x] M0: scaffold, requirements, configs, definitions, test harness.
- [x] M1: seeded environment, isolated agent state, neighbor message bus.
- [x] M2: decentralized search, map merge, stochastic detection.
- [x] M3: allocation interface, auction, centralized optimum, metrics.
- [x] M4: consensus and spectral rate validation.
- [x] M5: heartbeat detection, failure injection, recovery accounting.
- [x] M6: integrated simulation, animation, zero-failure calibration, demo.
- [x] M7: constrained edge-consensus ADMM and optimum tests.
- [x] M8: W-MSR, graph robustness, safety, STL tests.
- [x] M9: seven reproducible experiment suites, figures, tuning/freeze.
- [x] M10: full execution, findings, traceability, verification gate.

Acceptance: all requirements in AGENTS.md; final gate must honestly report
missing evidence. Every completed milestone gets an M<n>: commit.

## M10 current state

The audit corrected startup crash timing, explicit mission Metropolis weights,
shared allocator adapters, and stale ADMM convergence flags. Before final run:
run the expanded tests, freeze the current source fingerprint, then run all 580
holdout episodes (3001-3020). Do not edit simulation/runner source while workers
are alive. Earlier measurements are archived as pilots, not final evaluation.
After completion: generate findings, inspect figures/media, run make verify,
investigate every FAIL, update measured runtimes and traceability, commit M10.

Current boundary-correction execution: previous complete evaluation (fingerprint
4b270c9a37639bdd) is preserved in results/pilot_complete_v1. The new final source
fingerprint is 66f1d9c6e0bac348, and runner session 22318 is freshly executing all
580 jobs. Recovery >= boundary and per-target dwell reset now have regression
tests; all 31 tests pass. Inspect results/full/progress.log and wait for CSV/media
export. Do not edit simulation/runner source during execution. The fresh E4 audit
reproduces the investigated healing_recovery scientific FAIL; preserve it.
After full completion, compare versions, retain the cold manifest, run make verify
(including a cold demo), inspect media, update README runtimes, and commit M10.
M10 completed: all 580 corrected-source episodes finished; all 31 tests pass;
make verify exited 0. Full job wall time is 3523.46 s, cold demo including media
149.05 s, and verification 181.51 s. Every gate check passes. The healing_recovery
scientific check remains FAIL with the reproduced investigation in FINDINGS.
Zero separation violations and duplicate execution steps were recorded. All
580 configurations match the preserved earlier version; the only changed
scientific measurement is OFF seed 3010 recovery time, now correctly zero.
Figure/media review is complete; source and results are ready for the M10 commit.
