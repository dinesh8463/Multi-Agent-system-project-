## healing_recovery

- The primary check remains **FAIL**: mean per-episode strict recovery rate is
  0.9375 with healing and 0.9625 without healing, a difference of -0.025. The
  paired 95% t interval for that difference is [-0.07733, 0.02733], so these 20
  seeds do not establish an improvement on this particular metric. Sources:
  [Experiment 4](../results/full/exp4.csv),
  [event summary](../results/full/recovery_event_summary.csv).
- I checked the denominators rather than replacing the requested metric. Healing
  ON has 66 observed crashes: 60 empty task sets and 6 nonempty sets, of which 2
  strictly recover. Healing OFF has 73 crashes: 68 empty sets and 5 nonempty sets,
  of which 2 strictly recover. Empty sets recover vacuously at the crash time.
  Thus the overall recovery score is dominated by failures with no owned work;
  the few nonempty cases also require simultaneous current activation of every
  original task. Neither the event-weighted nor conditional rate is substituted
  for the primary per-episode result. Sources:
  [recovery events](../results/full/recovery_events.csv),
  [event summary](../results/full/recovery_event_summary.csv).
- A full deterministic replay of ON seed 3012 reproduced every scientific metric
  in its source job. Drone 2 fails at step 31 with task R16; that region is only
  80.56% covered then, so it genuinely remains unfinished. No live controller has
  R16 as its selected task after the failure. Other flight/sensing activity
  nevertheless brings R16 above 95% at step 53, and the mission completes after
  212 steps. The requested strict reactivation predicate therefore stays false
  even though the physical search goal is eventually achieved. This is a
  limitation of the chosen recovery definition relative to opportunistic search,
  not a counting error in this replay. Sources:
  [step-by-step audit](../results/full/recovery_audit_3012.csv),
  [source job](../results/full/jobs/exp4_healing_on_3012.json).
- All four unrecovered nonempty ON events occur in successful missions: seed
  3012 (R16), seed 3014 (R14/R19/R24), and two events in seed 3015
  (R16/R17 and R0/S7). Their source queues and recovery/null flags remain
  unchanged. Multiple queued tasks need not be selected concurrently, and
  completed work is deliberately not substituted for activation under the
  requested formal definition. Source:
  [recovery events](../results/full/recovery_events.csv).
- Mission effectiveness still differs materially: healing ON succeeds in 16/20
  cases and OFF in 4/20; 13 paired seeds succeed only with healing, while one
  succeeds only without it. Mean completion/censoring times are 187.90 and
  259.85 seconds respectively. This supports a benefit for mission operation in
  these scenarios, while leaving the strict recovery-score check failed. No
  policy or objective weights were tuned after inspecting this discrepancy.
  Source: [Experiment 4](../results/full/exp4.csv).
- Per the brief's completion-gate item 4, this is retained as a documented
  scientific exception. It is not relabeled PASS and is not evidence that
  healing improves every metric. Software correctness and data-integrity checks
  remain mandatory and cannot be waived by this note.
