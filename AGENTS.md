=====================================================
MISSION
You are working inside my repository. Deliver the COMPLETE PROJECT (code, tests, full experiment runs, all figures, animation) for the course project below. The report and slides are NOT part of this task: do not create or edit report/ or slides. They come in a later task that will use your real outputs. Do not stop after a milestone. Keep going until the COMPLETION GATE at the bottom passes. The result must be correct, make sense scientifically, and work properly when I run it. Never fabricate results.

Input: inputs/proposal.pdf (the proposal; its content is reproduced below). If it is missing, work from the text below.

RESUME PROTOCOL
At the start of every run read AGENTS.md and PLAN.md and continue from the first unticked milestone. Commit after every milestone with prefix "M<n>:" and tick PLAN.md. If you are about to run out of time or credits, commit everything and write exactly what is next into PLAN.md.

STEP 0
Write this whole specification into AGENTS.md (condensed but lossless). Create PLAN.md with milestones M0-M10 and acceptance criteria.

=====================================================
THE PROPOSAL (authoritative; implement all of it)
Course: AI3403 Multi-Agent Systems, IIT Hyderabad.
Title: "Self-Healing Distributed Multi-Agent Drone Swarm for Disaster Response: Resilient Task Allocation and Coordination under Dynamic Agent and Communication Failures."
Roles: Puli Dinesh - ADMM, formulation, task allocation; Sai Dhanush - consensus, resilient consensus, convergence; Ajay - failure detection, redistribution, recovery; Nenavath Kalyan - dynamic graph, links, coordination; Kalyan - simulation, environment, visualization, experiments.

A swarm of drones collaboratively searches a disaster region, detects survivors, shares local information and dynamically reallocates tasks WITHOUT a centralized controller. The swarm is a dynamic communication graph G(t)=(V,E(t)). Distributed consensus lets agents agree using only neighbor information; distributed optimization (ADMM) drives task allocation based on distance, battery, workload, connectivity and region priority. On drone or link failure, remaining agents detect the change, update the topology, redistribute unfinished tasks and continue the mission, with no central recovery controller.
Central question: can a drone swarm maintain coordinated disaster-response operations and autonomously reorganize when drones or links dynamically fail?

System model: 100x100 region, ~20 drones, 8-10 survivors, obstacles, heterogeneous batteries, dynamic graph. Each drone keeps position, velocity, battery, current task, neighbor set, local map, detected-survivor info.
Pipeline: Environment -> distributed search and survivor detection -> neighbor information sharing over G(t) -> {consensus, distributed optimization} -> coordinated execution -> on failure: detect -> redistribute -> reorganize topology -> resume.
Consensus: x_i(k+1)=x_i(k)+alpha*sum_{j in N_i(k)} a_ij (x_j(k)-x_i(k)); agree on search coverage and shared mission estimates.
ADMM: when survivors are found or regions become unassigned, drones jointly pick responders optimizing distance, battery, workload, connectivity, region priority; each agent solves a local problem and exchanges coordination variables with neighbors.
Self-healing: drone failures via lost heartbeats; link failures remove graph edges; remaining agents redistribute unfinished work.
Extension: resilient consensus against faulty agents; minimum inter-drone separation and response-time constraints; STL-based verification.
Experiments: (1) centralized vs distributed allocation; (2) agent failure 10/20/30%; (3) communication robustness under degraded connectivity; (4) self-healing recovery time; (5) scalability at 10/20/50/100 drones; (6) resilient vs ordinary consensus under inconsistent information.
Metrics: mission completion time; search coverage / detection rate; task allocation efficiency (workload distribution); energy consumption; communication overhead; consensus error; failure recovery time; scalability; safety violations.

=====================================================
CONCRETE DEFINITIONS (so the project makes sense; implement exactly, record in docs/DEFINITIONS.md)
- Time: discrete steps of dt=1 s; drone speed v_max=2 units/step (configurable); episode max T steps (configurable, default 600).
- Grid: world discretized into 1x1 cells (or 2x2). Obstacles are axis-aligned rectangles or discs covering about 8-12% of the area; drones and survivors never spawn inside obstacles; every free cell must be reachable.
- Regions: the free area is partitioned into R search regions (default R = 25, a 5x5 block grid). Each region has a priority weight in [1,3] (higher near a randomly placed "hotspot"). A region is "searched" when its fraction of seen cells >= 0.95 (seen = within sensing radius of some drone visit).
- Search task = a region to cover. Response task = a detected survivor. A survivor is "rescued" when a drone assigned to it reaches within 1.5 units and stays 3 steps. Survivors are detected only when inside a drone's sensing radius (6) with probability 0.9 per step.
- MISSION COMPLETE = all survivors rescued AND (coverage >= 0.95 of free cells OR all survivors rescued, as stated per experiment config). Mission completion time = first step where complete; if not complete by T, record T and flag "timeout" (also report success rate).
- Battery: heterogeneous initial capacity (uniform 60-100 units). Cost per step = c_move*speed + c_comm*messages_sent + c_sense. A drone with battery <= 0 FAILS (crash, stops sending heartbeats). Battery-aware behaviour: a drone with low battery reduces willingness to take new tasks (through the ADMM battery cost term).
- Failure injection: "agent failure x%" = x% of the initial drones (rounded) crash at random times uniformly within the first 60% of the episode, chosen with the experiment seed (never the same drone set for every seed). Link failure: each edge independently drops each step with probability p_link.
- Heartbeats: each drone broadcasts a heartbeat every step; a neighbor is declared failed after h_timeout consecutive missed steps (default 5). Message drops cause false positives; measure them against ground truth.
- Task redistribution: when a drone is declared failed by its neighbors, tasks it owned become unassigned, and that information propagates via neighbor messages (flooding with sequence numbers); each drone that learns of it joins the next distributed allocation round for those tasks.
- Recovery time (formal): for a failure event at step t_f, recovery time = (first step t_r >= t_f at which every task owned by the failed drone is owned by a live drone that is actively executing it) minus t_f. If never, record T - t_f and flag unrecovered.
- Allocation is invoked event-driven: when new survivors are detected, tasks freed, or a periodic timer fires (default every 20 steps). Distributed methods only use neighbor messages; multi-hop information spreads hop by hop.
- ADMM formulation (use this unless you can justify a better one, then document it): tasks j=1..M (current unassigned search regions and survivors), drones i=1..N (alive, in the connected component). Assignment variable x_ij in [0,1]. Cost c_ij = w1*dist_ij + w2*(1/battery_i)*dist_ij + w3*load_i + w4*conn_penalty_ij - w5*priority_j. Constraints: sum_i x_ij = 1 for each task (each task assigned once), sum_j x_ij <= cap_i. Decentralized consensus-form ADMM: drone i holds a local copy X^i of the full assignment matrix, only the row i enters its own cost, and consensus constraints X^i = Z force agreement between neighbors via edge-wise dual variables. Standard x-update (local QP or closed-form/projected step), z/neighbor-average update, dual update, stopping on primal and dual residuals; then round to a 0/1 assignment with deterministic conflict resolution using neighbor messages. Must reproduce the centralized optimum on small instances within the tested tolerance, and fall back to greedy auction if not converged in K iterations (log how often).
- Resilient consensus experiment: choose F-local faulty agents (default F=1 or 2, respecting an (F+1,F+1)-robust graph, checked numerically) that send inconsistent values (Byzantine random, or constant bias) while honest agents run (a) ordinary consensus and (b) W-MSR on the shared survivor-count / coverage estimate. Report consensus error among honest agents and the effect on mission metrics.
- Metrics formulas, documented: Jain's fairness index J=(sum w_i)^2/(N sum w_i^2) over per-drone work (tasks completed or distance travelled); messages per step counted at the bus; consensus error = max_i |x_i - mean of honest initial values| (or true global quantity).

DECENTRALIZATION RULE (enforced by design, tested): a drone may read only (a) its own state and (b) messages delivered by the message bus from its CURRENT neighbors (delay 0-2 steps, drop probability default 0.05, configurable). Drones hold no references to other drones or global state. Only the clearly labeled centralized baseline (class name contains "Centralized") may access global state. A test fails if drone-side code touches global world state.

=====================================================
ENGINEERING SPECIFICATION (all REQUIRED)
Python 3.10+; numpy, scipy, networkx, matplotlib, pandas, pyyaml, pytest, pillow, imageio, imageio-ffmpeg. Type hints, docstrings, logging, no global state, YAML configs, fixed seeds. Layout: swarm/ config/ (default, demo, exp1..exp6, ablation_sensitivity yaml) | src/ env.py drone.py comms.py search.py consensus.py admm.py allocation.py selfheal.py safety.py metrics.py sim.py viz.py | experiments/ | tests/ | results/ | docs/ | inputs/ | README.md requirements.txt Makefile (demo | test | all | verify).
Modules:
1 env/drone/comms: range graph (comm_range 25), random link failure, degraded settings, message bus with delay/drop/counters, neighbor discovery, Fiedler-value tracking, battery model.
2 search: frontier- or Voronoi-based decentralized region search, potential-field obstacle avoidance, local maps merged only with neighbors.
3 consensus: alpha<1/d_max or Metropolis weights on time-varying graphs; coverage and survivor-count estimates; measured rate vs theory from lambda_2; temporary disconnection; effect of alpha.
4 allocation: shared interface; distributed auction/greedy; ADMM (above); CentralizedAllocator (global optimal, used only in Experiment 1).
5 selfheal: heartbeat detection with false-positive/negative analysis; edge removal; local redistribution; relay repositioning to restore connectivity (a drone with spare capacity moves to bridge a disconnected component, decided locally); failure injection.
6 safety: minimum separation d_min (default 2) via CBF or potential field; response-time constraint (a detected survivor must be reached within T_resp steps; violations counted); STL robustness monitor for always(min pairwise distance > d_min) and eventually-within-T each detected survivor reached; robustness values recorded per episode.
7 metrics: all nine metrics plus Jain's index.
Experiments (>=20 seeds from a fixed seed list; each seed changes obstacles, survivor positions, batteries, failure times):
 1 Centralized vs distributed allocation (Welch t-test)
 2 Agent failure 10/20/30%
 3 Degraded connectivity (vary range, p_link, drop prob)
 4 Self-healing recovery time (with vs without self-healing)
 5 Scalability at 10, 20, 50, 100 drones (region count and T scale sensibly)
 6 W-MSR vs ordinary consensus under inconsistent information
 7 Ablations (no ADMM / no self-healing / no resilient consensus) and sensitivity (alpha, heartbeat timeout, comm range)
Each: YAML config, CSV in results/ (one row per seed per condition, all metrics), summary CSV with mean/std/95% CI, 300-dpi figures with labeled axes, legends and CI bands, width <= 6.5 in, fonts >= 8 pt. run_all.py uses multiprocessing, logs progress, is RESUMABLE. demo.yaml finishes `make demo` in under 5 minutes and includes a reduced version of every experiment. Calibrate the full config so `make all` finishes in about 2-3 hours; record measured runtimes in README.
Figures (code-generated from real runs): architecture/pipeline diagram, environment overview, topology before/during/after failure, task assignment map, recovery timeline (failure -> detection -> reallocation -> resume), trajectories, consensus (theory vs measured, alpha effect, temporary disconnection), ADMM convergence (residuals, optimality gap vs centralized), heartbeat FP/FN curves, W-MSR vs ordinary under Byzantine/bias, STL robustness, one figure set per experiment, and a summary comparison figure.
Animation: results/animations/mission.gif (Pillow, <=15 MB) AND mission.mp4 (imageio-ffmpeg). `--live` opens an interactive window; default backend Agg. Shows obstacles, survivors (hidden until detected), drones colored by task, communication links (removed edges vanish), battery labels, failed drones red with X, timestep, side panel with coverage %, messages/step, consensus error, and at least one drone failure and one link failure followed visibly by reallocation.
YOU MUST ACTUALLY RUN `make all` (background with nohup, poll sparingly) and keep its real outputs. If a run crashes, fix and resume.

=====================================================
CORRECTNESS AND SANITY REQUIREMENTS (the project must make sense, not just run)
1. Unit tests for: graph connectivity, consensus convergence and rate vs lambda_2, ADMM vs centralized optimum (optimality gap within stated tolerance), heartbeat detection, task redistribution, separation constraint, decentralization rule, W-MSR (including a case showing ordinary consensus is pulled away by a Byzantine agent while W-MSR is not, on an (F+1,F+1)-robust graph), STL monitor on hand-built trajectories with known robustness signs, determinism (same seed gives identical results).
2. Invariants checked every step in a debug mode and in tests: no drone inside an obstacle; battery never increases; a dead drone never sends or moves; every task has at most one owner among live drones after allocation settles; the message bus delivers only along existing edges; message counters equal the number of sends.
3. Sanity checks on experiment outcomes, automated in `make verify` and logged to results/sanity_report.md (report PASS/FAIL, do not hide failures):
   - coverage is non-decreasing over an episode;
   - with 0% failures the mission success rate is high (>= 90% in the default setting); if not, the simulation parameters are wrong: fix the simulator, not the check;
   - more failures should not make the swarm better: success rate non-increasing and completion time non-decreasing in failure % (allow statistical noise; if violated, investigate for a bug and explain in docs/FINDINGS.md);
   - self-healing ON recovers (recovery rate) at least as well as OFF in Experiment 4;
   - centralized baseline is an upper bound on allocation optimality, not necessarily on mission time (state which);
   - W-MSR error stays bounded under F-local faults while ordinary consensus error is larger, consistent with theory; if results disagree with theory, investigate for a bug first, then report honestly;
   - consensus measured rate within a stated tolerance of theory;
   - scalability: communication overhead grows with N as expected.
4. Fairness of comparisons: every compared method runs on identical seeded scenarios (same obstacles, survivors, batteries, failure times).
5. DO NOT tune parameters to make the proposed method look better. Tune once on a separate set of tuning seeds (not the evaluation seeds), freeze the config, and then run evaluation seeds. If the proposed method does not win somewhere, keep that result and write it in docs/FINDINGS.md.
6. docs/FINDINGS.md: after the full run, write a plain list of what the real data shows, including surprises, failures of the method, and anything unexplained. No fabrication; every statement cites a CSV/figure.
7. docs/ASSUMPTIONS.md: every simplification (2D, point drones, perfect localization, ideal sensing within radius, etc.).
8. Review pass before finishing: re-read the proposal line by line and fix any gap; check that no drone code reads non-local state; check that demo and full configs differ only in size (seeds, steps, N sweeps), not in algorithms.

MILESTONES
M0 AGENTS.md, PLAN.md, scaffold, requirements, Makefile, configs, test harness, docs/DEFINITIONS.md
M1 env + drone + comms
M2 search, local map merge, survivor detection
M3 allocation interface + auction/greedy + CentralizedAllocator + metrics.py
M4 consensus + theory-vs-measured test
M5 self-healing + failure injection + recovery time
M6 sim.py core pipeline + viz.py (GIF and MP4) + working `make demo`; sanity-check the zero-failure success rate here and fix the simulator if low
M7 ADMM + test vs centralized
M8 W-MSR + robustness; safety; STL monitor
M9 experiments 1-7 + run_all + demo versions + all figure scripts; tune on tuning seeds, freeze config
M10 run the FULL `make all`; produce all CSVs and figures; write docs/FINDINGS.md; run `make verify`; write docs/TRACEABILITY.md

=====================================================
COMPLETION GATE (do not declare done until ALL pass)
`make verify` must succeed and check:
1. `pytest` passes fully.
2. `make demo` produces mission.gif, mission.mp4 and all figures listed above.
3. results/ has full-run CSVs, summary CSVs and figures for experiments 1-7, each with >=20 evaluation seeds (verify row counts).
4. results/sanity_report.md exists; every FAIL is explained in docs/FINDINGS.md (or fixed).
5. The decentralization test passes, and a grep confirms drone-side code never imports the world or other drones.
6. Determinism test passes.
7. docs/TRACEABILITY.md maps EVERY requirement in the proposal (each module, experiment, metric, extension) to file, test and figure; no row without evidence.
8. README.md explains install, `make demo`, `make test`, `make all`, `make verify`, where each output appears, and measured runtimes.

FINAL MESSAGE FORMAT
Reply with: (a) the gate result, (b) honestly, anything that does not work as intended and any surprising results, (c) exact reproduce commands, (d) paths to open: results/animations/mission.gif, mission.mp4, results/figures/, results/sanity_report.md, docs/FINDINGS.md.