# Operational definitions

The complete requested definitions are preserved in ../AGENTS.md. Simulation
time is in seconds (dt=1), position in world units. The map uses 2-unit cells,
100 by 100 world, 25 regions. Coverage counts free cell centers within radius 6
of any visit, accumulated monotonically. Region completion threshold is 95%.
Survivors are sampled only from free cells; independent per-step detection is
0.9 within radius 6. Response completion needs distance <=1.5 for three steps.
The default mission requires all survivors rescued AND >=95% free-cell coverage.
Timeout completion times are right-censored at T; success is reported separately.

Failure selection is seeded, uniformly timed in the first 60% of the horizon.
Heartbeats are sent each step; timeout is five missed steps by default. Receiver
suspicions may be false positives; they are not omniscient crash notifications.
Recovery is the first step all unfinished tasks owned at failure have live owners
actively executing them. Unrecovered observations are censored at T-t_failure.

Costs are distance + inverse-battery distance + workload + connectivity penalty
minus priority, with weights in YAML. Fractional assignment columns sum to one;
rows have capacity limits. See admm.py for the edge splitting and projection.
Centralized optimization is an allocation-cost bound, not a mission-time bound.

Energy is initial battery minus remaining battery; per-step drain includes
distance moved, attempted edge transmissions, and sensing. Bus overhead counts
each directed edge transmission attempt, including drops. Jain fairness is
(sum work)^2 / (N sum work^2), including failed drones in the initial population.
Consensus error uses a declared initial-honest-mean reference in controlled
tests; mission consensus error uses the actual observer coverage fraction.
Separation robustness is minimum observed distance minus d_min. Response STL
robustness is max over the allowed window of 1.5-distance, per detection.
Negative values denote violations; unfinished windows are marked pending.
Evaluation uses identical scenario seeds across methods and independent RNG
streams for environment, failures, links, bus and sensing.
