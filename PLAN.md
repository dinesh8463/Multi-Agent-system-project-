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
- [ ] M10: full execution, findings, traceability, verification gate.

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

Current execution: all 580 holdout jobs are running with source fingerprint 4b270c9a37639bdd. Do not restart from M0. Full runner session is 12372; inspect results/full/progress.log and wait for all 580 job JSONs and full CSV export. Cold 120-step demo passed in 215.21 seconds; 28 tests passed. Animation replays exp2_failure_10_3004, and every scientific metric matched the source. The healing_recovery point check is an investigated scientific FAIL (docs/INVESTIGATIONS.md); do not change policy or overwrite this negative result. Next run verification after the full runner finishes, review any other failures, then commit M10.
