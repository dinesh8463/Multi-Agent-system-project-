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

Task execution uses pipelined majority leases: ballots cast in epoch k authorize
only epoch k+1 (20-second epochs). Each initial identity signs one candidate per
task per epoch. Certificates require more than N_initial/2 distinct identities;
old certificates expire at the common boundary. This resolves conflicting local
auction/ADMM rounding views while exposing minority-partition availability costs.
Unassigned drones may explore frontiers without claiming a region task.

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
The response monitor restricts eligible responders to the assigned task owner
or an agent that already reached that survivor while assigned. A window with
no eligible responder uses an explicitly defined finite penalty distance of
1,000,000 (robustness -999,998.5), rather than an infinite CSV value. This is a
categorical unassigned-response penalty, never a measured physical distance;
its magnitude must not be interpreted as geometric error. Deadline violation
counts exclude immature windows. The three-step rescue requirement is separate.
Evaluation uses identical scenario seeds across methods and independent RNG
streams for environment, failures, links, bus and sensing.

An onboard proximity observation is part of own sensor state: only live positions
within max(r_sense,d_min+2*v_max+0.05) are exposed (6.05 units by default), without
task, battery or remote-map data. It is independent of radio drops. Feasible local
motion lies outside every nearby peer's next-step reachable ball; infeasible
motion holds. This hardware assumption is recorded separately from the lossy
neighbor-message model for shared mission information.
