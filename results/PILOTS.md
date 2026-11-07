# Development records

Final statistical evidence is in `results/full/`: 580 freshly executed frozen-source
episodes, with source/configuration fingerprints validated by `make verify`.

The `pilot*` directories preserve earlier development measurements and stopped
runs. They are not additional evaluation seeds and are not pooled into final
means, confidence intervals, or hypothesis tests. Their development snapshots
are not a guarantee of reproducibility with the final source version.

The animation is a disclosed replay of `exp2_failure_10_3004.json`. Its scientific
metrics match that source exactly. Earlier illustration-selection attempts and
repeated cold-demo timings are retained under `pilot/`; they are not selected
performance evidence. `animations/selection_trace.csv` records the final replay
selection across the complete Experiment 2 cases.
