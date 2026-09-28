# Metrics JSON and comparison helper

`compare_metrics.py` computes descriptive statistics over independent runs and evaluates numeric gates from a policy fixed in advance. It is not a benchmark runner, trace analyzer, INP calculator, or statistical test. Better numbers do not establish `accepted` without checks of function, cause, and representative devices.

## Input

Copy `assets/metrics-template.json` for baseline and candidate, replacing placeholders with measured conditions and values. Empty samples are intentionally invalid. See `assets/measurement.schema.json` too.

- `schema_version`: Integer 1.
- `synthetic`: Explicit boolean; false for measurements, true for synthetic data. The helper cannot verify authenticity.
- `context`: Nonempty strings for environment_id, scenario_id, dataset_id, cache_state, instrumentation_id, and measurement_kind. Other fixed conditions may be added. The entire context must match between baseline and candidate.
- `build`: Revision and configuration. Revisions may differ; configurations must match. Record intentionally changed runtimes or dependencies in the build and manually verify environmental comparability. Do not move arbitrary differences into `build` to make an unfair comparison pass.
- `metrics.<name>`: Unit, direction (`lower` or `higher`), sample_unit (`run`), and samples. Optional run_ids must match the sample count and be unique. Values must be finite and nonnegative.

One sample represents one independent run. Do not enter consecutive frames as independent runs. If each sample is a run's frame-time p95, say so in the metric name and definition. The resulting p95 is the p95 of the distribution of within-run p95 samples, not the p95 of all field events.

## Policy

`assets/policy-example.json` is illustrative, not a product SLO. Set the primary metric, guardrails, and thresholds before optimizing.

`min_samples` must be at least 2. Every metric needs a `statistic` (`median` or `p95`) and at least one gate. All gates are combined with AND.

| Gate | Meaning |
|---|---|
| max_regression_percent | Upper limit on regression percentage, respecting direction |
| max_regression_absolute | Upper limit on regression in the metric's unit |
| min_improvement_percent | Minimum improvement percentage, respecting direction |
| min_improvement_absolute | Minimum absolute improvement |
| target | Candidate must be at or below the target for `lower`, or at or above it for `higher` |

A percentage gate is incomparable when the baseline is zero and produces an error; use an absolute gate or target instead. Do not infer or convert metric names, units, direction, or sample_unit. Metrics absent from the policy produce a warning and are excluded. Unknown policy keys are errors to catch typos.

The p95 uses nearest rank, `ceil(0.95*n)`. Small n is unstable. The helper warns when p95 is evaluated with fewer than 100 samples, but 100 does not guarantee adequacy. More samples alone do not remove bias or differing measurement conditions.

## Run

```sh
python3 scripts/compare_metrics.py baseline.json candidate.json --policy policy.json --out comparison.json
# Check only the behavior of the synthetic example:
python3 scripts/compare_metrics.py assets/synthetic-baseline.json assets/synthetic-candidate.json --policy assets/policy-example.json --allow-synthetic
```

`--out` creates a new file only and does not overwrite an existing file. Input JSON is limited to 8 MiB. Duplicate keys, NaN/Infinity, booleans used as numbers, and empty samples are rejected. The helper makes no network calls.

Exit codes: 0 = numeric gates pass; 1 = a gate fails; 2 = input or comparability error; 3 = too few samples. When samples are insufficient, even computable gates do not justify a decision. `acceptance` is always `not-determined-by-this-tool`.
