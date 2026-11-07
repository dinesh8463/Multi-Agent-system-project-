# Verification and sanity report

Overall gate: PASS

Scientific sanity exceptions: ['healing_recovery'].

| Check | Category | Result | Evidence / explanation |
|---|---|---|---|
| pytest | gate | PASS | 31 passed in 22.77s |
| decentralization_grep | gate | PASS | forbidden policy imports=[] |
| make_demo | gate | PASS | demo process exit=0 |
| demo_runtime | gate | PASS | 149.05s (budget <300s; matching cached experiment jobs may be reused) |
| figures_results/figures | gate | PASS | missing=[] |
| figure_resolution_results/figures | gate | PASS | 300dpi and width<=6.5in: violations=[] |
| figures_results/demo/figures | gate | PASS | missing=[] |
| figure_resolution_results/demo/figures | gate | PASS | 300dpi and width<=6.5in: violations=[] |
| animation_formats | gate | PASS | GIF frames=115, bytes=2033081; MP4 frames=121, shape=(480, 640, 3) |
| animation_failure_and_recovery | gate | PASS | 2 physical crashes; 2 recovered |
| animation_visible_link_failure | gate | PASS | 20 previously visible radio edges fail while endpoints remain in range before non-vacuous recovery |
| animation_source_equivalence | gate | PASS | all scientific metrics match results/full/jobs/exp2_failure_10_3004.json; illustration is selected, not a distribution summary |
| exp1_seeds | gate | PASS | 60 rows, 3 conditions, expected 20 unique seeds each |
| exp2_seeds | gate | PASS | 80 rows, 4 conditions, expected 20 unique seeds each |
| exp3_seeds | gate | PASS | 60 rows, 3 conditions, expected 20 unique seeds each |
| exp4_seeds | gate | PASS | 40 rows, 2 conditions, expected 20 unique seeds each |
| exp5_seeds | gate | PASS | 80 rows, 4 conditions, expected 20 unique seeds each |
| exp6_seeds | gate | PASS | 80 rows, 4 conditions, expected 20 unique seeds each |
| exp7_seeds | gate | PASS | 180 rows, 9 conditions, expected 20 unique seeds each |
| aggregate_and_summary_integrity | gate | PASS | aggregate matches all seven CSVs; 580 rows; summary covers required metrics and repetitions |
| boundary_fix_provenance | gate | PASS | 580 old/new cases use identical parameters; 1 have changed scientific measurements; see boundary_fix_changes.csv |
| source_fingerprints | gate | PASS | stale jobs=[] |
| current_sweep_configurations | gate | PASS | mismatched job configurations=[] |
| paired_scenarios | gate | PASS | 120 paired scenario groups checked, including batteries/positions; identical intervention schedules across method comparisons |
| transport_optimization_regression | gate | PASS | current-policy seed-41 end-to-end reference-bus regression passed; 0 additional matching archived episodes compared; differences=[] |
| coverage_monotonic | gate | PASS | Checked every saved episode prefix |
| zero_failure_success | gate | PASS | 100.0% (required >=90%) |
| failure_trend_failure_0_failure_10 | scientific | PASS | paired time delta 24.300 +/- 20.482s; success delta 0.000 +/- 0.000; statistical noise allowed |
| failure_trend_failure_10_failure_20 | scientific | PASS | paired time delta 49.650 +/- 44.733s; success delta -0.200 +/- 0.192; statistical noise allowed |
| failure_trend_failure_20_failure_30 | scientific | PASS | paired time delta 12.000 +/- 52.762s; success delta 0.000 +/- 0.263; statistical noise allowed |
| healing_recovery | scientific | FAIL | ON=0.938, OFF=0.963 |
| wmsr_bound | gate | PASS | {'ordinary_bias': 9.49731794529882, 'ordinary_random': 3.2795201141943813, 'wmsr_bias': 0.0435157789672599, 'wmsr_random': 0.016063135728566207} |
| spectral_rate | gate | PASS | relative curve tolerance 1e-5, absolute 1e-10 |
| scaling_communication | scientific | PASS | {10: 22.71828033813595, 20: 80.66863960974288, 50: 503.48802022753944, 100: 1782.318191860791} |
| strong_task_ownership | gate | PASS | 0 duplicate task execution steps; execution requires a majority lease |
| hard_separation | gate | PASS | 0 pair-step violations; all measured live pair distances must exceed d_min |
| scientific_exceptions_explained | gate | PASS | failed scientific checks=['healing_recovery']; completion-gate item 4 requires data-backed investigation in FINDINGS |
| documentation | gate | PASS | README and required scientific documentation |
| report_and_slides_untouched | gate | PASS | Neither report nor slides was created |

All failed checks remain FAIL. Per completion-gate item 4, a scientific trend exception is admissible only with a separate data-backed investigation reproduced in docs/FINDINGS.md. Tests, data integrity, baseline success, decentralization, ownership and safety checks cannot be waived.
