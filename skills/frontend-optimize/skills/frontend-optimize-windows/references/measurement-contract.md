# Measurement contract and acceptance decisions

The repetition counts, example thresholds, and decision procedure here are operating rules for this skill, not OS or browser standards. Fix measurement conditions before optimizing; do not change them afterward to favor a result. The sequence of measurement, cause isolation, and remeasurement also follows primary guidance. [N01][C07]

## 1. Record at the start

Use a location consistent with the repository, such as `perf/<scenario>/<baseline-or-candidate>/`.

- `environment.json`: OS/build, toolchain, runtime, framework, device class, CPU/GPU, RAM, DPI/DPR, refresh rate, power/thermal state, backend, and build configuration. Distinguish physical devices, VMs, simulators, remote sessions, and headless runs.
- `scenario.md`: Reproduction input, data seed/version/size, start and end points, successful outcome, foreground/background, cold/warm/cache, network conditions, repetitions, and rest conditions.
- `hypotheses.md`: Symptom, candidate causes, falsification conditions, planned change, primary metric, guardrails, and acceptance criteria. Write it before optimizing.
- `raw/`: Profiles, traces, logs, schema/tool versions, and commit ID. `report.md`: Supporting PID/TID/track, timestamps, symbols, diff, statistics, and limitations.

Exclude hostnames, actual user input, credentials, and customer data. Traces may contain URLs, paths, strings, and screen content. Permission to use a profiler is separate from permission to transmit its output. Do not upload traces externally.

## 2. Evaluate a user operation

Measure when the needed data appears and the operation completes, not just when a window opens. Track spinner display separately from completion of the actual result. Candidate scenarios include input response, search, scrolling, dragging, large datasets, navigation, resumption, idle behavior, and repeated opening and closing.

- Latency: Distinguish input-to-acknowledgement from input-to-result. Do not speed up the former at the expense of the latter.
- Smoothness: Track missed frame deadlines, hitch duration and proportion, and frame-time distributions. Average FPS alone does not justify adoption.
- Resources: Track CPU time, wall time, allocations, retained memory, GPU/texture use, I/O bytes, IPC count/bytes, idle wakeups, and energy where possible.
- Correctness: Check display, interaction, data integrity, cancellation, ordering, IME, focus, keyboard navigation, accessibility, reduced motion, and localization.

`1000 / refresh_hz` gives milliseconds per refresh cycle, not the CPU budget available to the whole app: about 16.67 ms at 60 Hz and 8.33 ms at 120 Hz. Measure variable refresh and pipeline delay separately. GPU completion, present submission, and appearance on screen are distinct events.

## 3. Measurement quality

For exploration, begin with roughly five runs of each case to assess reproducibility. Base a final decision on a predefined number of independent trials, for example ten or more, and their variation. These convenience counts do not guarantee statistical power; use more trials for small effects or tail metrics.

Record warmup separately and define exclusion reasons in advance. Do not mix cold and warm startup. Use ABBA or randomized alternating order to reduce thermal, battery, cache, and background-load bias. Keep the operation and dataset constant; isolate runtime upgrades from other changes.

Do not treat consecutive frames from one run as thousands of independent experiments. A comparison of each run's p95 is a distribution of within-run p95 values, not the p95 of all users. State the sample count and quantile method. Do not claim a precise p99 from dozens of samples. The helper produces descriptive statistics, not a significance test.

Use comparable measurement settings in Release/production builds. Heavy profiling and debug settings may help diagnosis, but recheck adoption with comparable profiling overhead. Forced GC, extensive DevTools logging, screenshots, heap snapshots, and sanitizers change measurements. Also check behavior without instrumentation.

## 4. Demonstrate the cause

Place input acceptance, queue wait, CPU compute, I/O or lock wait, UI application, layout/render, and presentation on the same timeline. Distinguish parallel intervals from serial dependencies; do not simply sum every interval. The critical path is the dependency chain to completion, not a ranking of the longest functions.

Record this for each candidate cause:

```text
Observation: operation interval, PID/TID, stack, wait target, raw trace path
Hypothesis: which dependency or queue worsens which metric
Falsification: what would be observed if the hypothesis were wrong
Change: smallest change addressing one cause
Result: comparable before/after plus functional, memory, and energy guardrails
Decision: accepted / rejected / inconclusive / unverified
```

Do not confuse self time with inclusive time. Do not sum nested slices, parallel thread wall durations, or GPU submission time as total CPU time. Sampling estimates may miss short work. Label missing stacks, events, and symbols as unknown, not zero. [C04][C05]

## 5. Order of improvement

First remove unnecessary work, then reduce data volume, search scope, or update scope. Next consider caching, diffs, batching, and virtualization. If CPU remains dominant, split work or move it to another executor or worker. Consider GPU or lower-level backends last. This is an exploration order, not a fixed ranking; evidence about the cause can change it.

Break offload cost into `enqueue + clone/encode + transfer + queue wait + compute + reply + UI apply`. Lower main/UI occupancy can still increase time to result, total CPU, or memory. Bound queues. Coalesce or use latest-wins only when only the latest state matters. Preserve ordering and durability for non-discardable edits, accounting, and saves.

For a cache, design keys, invalidation, maximum bytes/items, eviction, and responsibility for release. For parallel work, design ownership, thread affinity, cancellation, errors, shutdown, and backpressure.

## 6. Decision and stopping

Accept only when the primary metric improves or the predefined SLO is met, guardrails and functions remain intact, and the cause and result agree. A small difference within noise is inconclusive. Revert failed changes individually and safely; preserve other people's changes.

A full rewrite, framework migration, broader access, disabled sandbox, or global OS setting change falls outside routine optimization and needs separate justification and approval. Follow existing permission rules for commits and pushes.

Without a device, profiler, permissions, or reproduction steps, continue through static review and an instrumentation change, then report `unverified`. Never invent measured values or remove appearance or features to conceal an agent limitation.

## 7. Bundled script

`compare_metrics.py` checks context, unit, direction, and sample unit in both datasets, then returns a descriptive decision for policy-defined median and p95 metrics. It does not run benchmarks. See the schema and examples in `assets/`. Synthetic examples cannot justify adoption without explicit authorization.

```sh
python3 <this-skill>/scripts/compare_metrics.py baseline.json candidate.json --policy policy.json --out comparison.json
```

Exit codes: 0 = numeric gate passes; 1 = numeric gate fails; 2 = invalid input or incomparable conditions; 3 = insufficient samples. Code 0 is not `accepted` without functional, trace, and representative-device checks.

## v1.1.0: acceptance across durability and boundaries

Apply G0–G7 of the [acceptance contract](hardening-contract.md) as well. The helper's numeric gate and the design/correctness gates are separate. The meaning of the helper and schema is unchanged.

Do not combine optimistic feedback, result arrival, local commit, and server ACK under one latency label. Apply the [boundary contract](boundaries-and-protocol.md) when adding an async boundary and [durability and recovery](durability-and-recovery.md) when edits or saves are affected. If applicable [fault tests](failure-injection.md) have not run, do not mark that scope `accepted` even if numbers improve.
