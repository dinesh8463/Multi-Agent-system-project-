# Proposal and specification traceability

Paths are relative to the repository root. Figures come from real CSV/JSON traces
except the explanatory architecture diagram. The table maps evidence, including
limitations; it does not claim that a plot is a correctness proof.

| Requirement | Implementation / configuration | Test / data evidence | Figure |
|---|---|---|---|
| Disaster-response pipeline, decentralized coordination | src/sim.py, src/drone.py under swarm/ | test_decentralization_ast_and_object_isolation; results/full/all_metrics.csv | architecture.png |
| 100x100, obstacles, batteries, 20 drones, 9 survivors | swarm/src/env.py; swarm/config/default.yaml | test_connected_free_map_and_spawns | environment_overview.png |
| Private position, velocity, battery, task, neighbors, map, detections | swarm/src/drone.py | test_decentralization_ast_and_object_isolation | task_assignment.png |
| Dynamic range graph, links, message delays/drops, counters | swarm/src/comms.py | test_graph_and_fiedler; test_bus_delivers_only_existing_edges_and_counts | topology_failure.png |
| Search and local map merge, probabilistic detection | swarm/src/search.py, drone.py, env.py | test_determinism_and_step_invariants; results/animations/mission_trace.csv | trajectories.png |
| Coverage threshold and rescue dwell, timeout flags | swarm/src/sim.py, drone.py | test_capture_contains_actual_failures_and_serializable_trace; exp1.csv | exp1.png |
| Consensus, shared coverage/survivor estimates, lambda2, alpha, disconnection | swarm/src/consensus.py, drone.py | test_consensus_rate_matches_spectral_prediction; results/full/diagnostics/consensus.csv, alpha.csv, disconnection.csv | consensus_theory.png; consensus_alpha_disconnection.png |
| Distance/battery/workload/connectivity/priority costs | swarm/src/allocation.py | test_auction_capacity_and_optimal_bound; docs/ASSUMPTIONS.md | admm_convergence.png |
| Edge-consensus ADMM, row-local objective, residuals, rounding, fallback | swarm/src/admm.py, drone.py | test_edge_admm_matches_independent_lp; results/full/diagnostics/admm.csv; admm_fallbacks in exp1.csv | admm_convergence.png |
| Centralized optimum and distributed greedy comparator | swarm/src/allocation.py | test_infeasible_capacity_rejected; test_auction_capacity_and_optimal_bound | exp1.png |
| Heartbeat crash detection, FP/FN, topology update | swarm/src/selfheal.py, comms.py, drone.py | test_heartbeat_timeout_and_revival; results/animations/heartbeat.csv | heartbeat_fp_fn.png |
| Seeded 10/20/30% crashes | swarm/src/selfheal.py; swarm/config/exp2.yaml | test_failure_seed_varies_identity_and_schedule; results/full/exp2.csv | exp2.png |
| Flooded release, majority leases, local task redistribution | swarm/src/drone.py | test_local_redistribution_after_suspicion; test_settled_assignment_unique_on_common_neighbor_information; test_majority_leases_reject_partition_split_brain | recovery_timeline.png |
| Relay repositioning and recovery time | swarm/src/drone.py, sim.py | relay_steps and recovery_rate in results/full/exp4.csv; mission_failures.json | recovery_timeline.png |
| Resilient consensus, F-local faults, robust graph | swarm/src/consensus.py; swarm/config/exp6.yaml | test_wmsr_validity_and_byzantine_counterexample; results/full/diagnostics/wmrs.csv | wmsr_byzantine.png |
| Minimum separation barrier and response deadline, STL | swarm/src/safety.py, drone.py, sim.py | test_stl_known_signs_and_local_repulsion; test_reciprocal_barrier_prevents_fresh_pair_crossing; test_barrier_covers_delayed_peer_reachable_ball; safety_violations and response_violations columns | stl_robustness.png |
| Exp1 centralized/distributed, Welch tests | swarm/config/exp1.yaml; swarm/experiments/run_all.py | results/full/exp1.csv; welch_tests.csv | exp1.png |
| Exp2 failure robustness | swarm/config/exp2.yaml | results/full/exp2.csv | exp2.png |
| Exp3 degraded links/range/drops | swarm/config/exp3.yaml | results/full/exp3.csv | exp3.png |
| Exp4 self-healing ON/OFF | swarm/config/exp4.yaml | results/full/exp4.csv | exp4.png |
| Exp5 10/20/50/100 scalability | swarm/config/exp5.yaml | results/full/exp5.csv | exp5.png |
| Exp6 ordinary/W-MSR mission effect plus controlled theory | swarm/config/exp6.yaml | results/full/exp6.csv; diagnostics/wmrs.csv | exp6.png; wmsr_byzantine.png |
| Exp7 ablations and sensitivities | swarm/config/ablation_sensitivity.yaml | results/full/exp7.csv | exp7.png |
| Completion, success, coverage/detection, energy | swarm/src/metrics.py, sim.py | exp1-exp7.csv; summary.csv | exp1-exp7.png |
| Allocation efficiency and Jain work fairness | swarm/src/metrics.py | fairness column; test_auction_capacity_and_optimal_bound | summary_comparison.png |
| Communication, consensus error, recovery, safety, scalability | swarm/src/sim.py | results/full/all_metrics.csv | exp3-exp6.png; stl_robustness.png |
| Paired seeds, 20 repetitions, means/std/95% CIs, resumability | swarm/experiments/run_all.py | job fingerprints; run_manifest.json; summary.csv | exp1-exp7.png |
| Fixed tuning, frozen configuration, honest findings | swarm/config/frozen.json; docs/ASSUMPTIONS.md | results/tuning/metrics.json; docs/FINDINGS.md | summary_comparison.png |
| Step invariants, deterministic execution, common-view unique owner | swarm/src/sim.py; swarm/tests/test_core.py | test_determinism_and_step_invariants; test_settled_assignment_unique_on_common_neighbor_information | trajectories.png |
| Immutable neighbor-message snapshots and transport regression | swarm/src/comms.py | test_bus_broadcast_snapshot_is_immutable_and_isolated; results/tuning/message_snapshot_regression.json | topology_failure.png |
| GIF/MP4, task colors, battery labels, faults and reallocation | swarm/src/viz.py | results/animations/mission_trace.csv; mission_failures.json | mission.gif; mission.mp4 |
| Optional live playback, default Agg | swarm/experiments/live.py; swarm/src/viz.py | CLI --live; headless media decoding in verify | mission.gif |
| Installation, Make targets, actual runtimes and output locations | README.md; Makefile; make.cmd | results/verification.json; run_manifest.json | results/figures/ |
| Complete gate and documented failures | swarm/experiments/verify.py | results/sanity_report.md; docs/FINDINGS.md | summary_comparison.png |

All figure names above refer to results/figures/ unless another directory is
given. Report and slides are deliberately outside this project's deliverables.
