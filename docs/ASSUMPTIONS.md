# Model assumptions and limits

- Simulation is planar, discrete time (one second), point drones, perfect own
  localization, and an immutable public obstacle map. Local coverage maps and
  survivor discoveries are private until communicated. Cell centers approximate
  visible area; sensing has no occlusion model, within-radius detection is 0.9.
- Obstacles are four separated random rectangles, about 8-12% of cell area;
  boundary corridors make every free cell reachable. A* handles local obstacle
  detours after the direct motion attempt is blocked. No vertical dynamics,
  aerodynamic drag, wind, charging, or survivor movement are modeled.
- The simulator observes all states for physics, seeded sensor observations,
  recording and verification. Distributed agents receive only local sensor
  observations, immutable geography, and current-neighbor messages. They hold
  no Environment or other Drone references. The centralized baseline alone
  receives ideal map/detection fusion for its allocation decision.
- Local bid views are eventually consistent; execution is gated by majority
  leases. Each initial member signs one candidate per task per epoch. Epoch k
  ballots authorize epoch k+1, expire synchronously, and are flooded hop by hop.
  Two valid majorities intersect, preventing split-brain task execution. This
  assumes authenticated identities, honest lease voting and a shared discrete
  clock. Minority partitions sacrifice task-claim availability until connectivity
  returns; autonomous exploration and local relay motion can continue. Scalar
  Byzantine consensus attacks do not corrupt the lease-voting protocol.
- Local ADMM iterates exchange full matrices only when their epoch/task/identity
  signatures match. Dynamic graph/membership or short deadlines frequently
  force the explicitly counted greedy fallback. The static connected reference
  solver has residual and independent LP-gap tests; those tests do not establish
  optimal mission allocation in the lossy dynamic setting.
- Safety has an ideal bounded onboard proximity sensor as part of each drone's
  own observation state. Its radius is max(r_sense,d_min+2*v_max+0.05), 6.05 units
  by default; it exposes only nearby live identities/positions, never batteries,
  tasks, maps, or nonlocal agents. It is independent of radio loss. This added
  hardware assumption is essential for hard separation during total radio
  outages; the radio-only pilot model could not provide that guarantee.
  The barrier projects velocity onto supporting halfspaces outside each peer's
  reachable ball, with radius d_min+0.05+v_max for fresh observations. Infeasible
  envelopes and blocked motion cause a hold. A moving agent's feasible velocity
  protects against any bounded-speed motion of the other agent; two held agents
  preserve their existing separation. Unseen peers cannot close the gap in one
  step because the sensor radius exceeds d_min+2*v_max. Thus the guarantee is
  conditional on ideal proximity sensing, correct localization, and bounded speed.
  Recent-radio data are a fallback only when no proximity observation has been
  supplied. The modeled sensing cost includes the proximity sensor.
  Observer truth records violations, including any model-limit counterexamples.
  Negative response margins count as deadline violations only for mature windows;
  immature windows remain pending. Arrival and three-step rescue differ.
  The response robustness score has a finite no-assigned-responder penalty,
  defined in DEFINITIONS.md; extreme negative values represent unavailable
  response service and do not represent physical distances in the 100x100 map.
- Heartbeat suspicions are local, reversible and may reflect a broken link,
  movement out of range, packet loss, or a crash. They are not an oracle. FP
  counts are per local suspicion event; FN counts are physical crashes never
  detected by any agent before episode end. Thus FP and FN have different
  denominators and are shown as counts, not commensurate rates.
- Recovery includes completed tasks, since already finished work needs no new
  execution. Tasks waiting in an owner's queue do not count as actively resumed.
  A failure with no unfinished owned tasks is vacuously recovered at the next
  observer step. Censored recovery times and unrecovered flags remain in JSON.
- A relay heuristic uses only last heard missing-neighbor positions. Sparse
  nodes and locally elected minimum-ID spare agents try recent lost peers,
  rotating targets by epoch. It does not know component geometry or guarantee
  restoration. Motion is counted; there is no central recovery controller.
- Controlled W-MSR trials use a seven-node complete graph, checked numerically
  for (2,2)-robustness, and one Byzantine sender (F-local=1). Per-recipient random
  equivocation is used in the controlled random attack. Mission experiment 6
  uses the same complete seven-drone radio graph, zero delay/loss, and broadcast
  bias/random misinformation. Faulty agents still fly and perform tasks.
- W-MSR preserves the honest initial interval and reaches agreement under the
  controlled assumptions; it need not preserve the honest initial average.
  Mission estimates also have local innovations, so static average-consensus
  convergence theory is validated in controlled runs rather than claimed for
  the changing physical coverage signal. Consensus is informational; allocation
  uses communicated maps/bids, so estimate robustness need not improve mission
  time in this model.
- Priority-only terms constant across drones do not change the LP optimum when
  every task must be allocated; priority matters to task selection/execution.
  Workload and connectivity penalties as written are row constants. This is a
  limitation of the requested linear objective, not evidence of a priority gain.
- Failure injection is uniform in the first 60% of the configured horizon.
  Successful episodes stop immediately; later scheduled crashes never occur.
  Both scheduled_failures and failures are retained. Experiments 2 and 4 use a
  300-second horizon, selected after separate-seed calibration of the corrected
  safety/lease policy (about 130-second missions).
- Final evaluation seeds are 3001-3020; tuning seeds are 41-43 and demo seed 71.
  Earlier 1001/2001-series measurements are development pilots, preserved under
  results/pilot*/. Pilot correctness defects motivated
  majority leases and the reachable-ball safety controller. The objective weights
  were not changed to favor a method. Final holdout measurements use the frozen
  corrected policy and are not mixed with pilot rows.
- The animation is an explicitly illustrative scenario, not an evaluation sample:
  range 45, random link drops 0.12, six scheduled crashes and a 240-second cap.
  The first tuning seed (41-43) with a real nonempty-task recovery is selected;
  the chosen seed/configuration and all failure records are saved beside the media.
- No waiting is added to force a two-hour runtime. The measured runtime is
  reported honestly; the requested wall-time estimate is not an artificial goal.
