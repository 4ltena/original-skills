# Web profiling runbook

## 0. Choose a tool

Use Performance/Timeline, Memory, Network of the target browser and its framework profiler. Don't assume that Chrome functionality is in Safari/Firefox. Even if CDP/MCP/Playwright can be used, first list the capabilities, connection destinations, target pages, and tracks that can be recorded. Avoid writing code that calls MCP functions that are not provided. [W08][W23][W24]

Use production build and distinguish between profile build and normal build. Do not confuse extra work due to development inspections such as React with production costs. Even if you find the cause in debug, check whether it is accepted or not in production under the same conditions. [W17][N01]

## 1. Scenario and marker

Fix the reproduction data. For example, ``Edit 10 out of 10,000 lines and confirm,'' ``Search from 100,000 candidates and display 50 results,'' and ``Open/close the same route 20 times.'' For scale, use actual requirements. The result is not complete just because the screen is displayed or the spinner appears.

```js
// For local reproduction. Do not include user input or URLs in the name.
performance.mark('search:start');
//Instrument the UI application completion point of the correct result in the actual app.
performance.mark('search:applied');
performance.measure('search:apply-latency', 'search:start', 'search:applied');
```

This measure is only up to the application of the UI, not the completion of the physical display. The value of waiting one or two rAFs does not guarantee physical present. Performance entries are not accumulated indefinitely, and only the names owned by the app are cleared after export. [W20]

## 2. First, one deep trace

1. Records browser/version, viewport/DPR, CPU/network settings, extensions, foreground, thermal.
2. Record a short record of the operation from before to after the operation, and save the raw trace locally. Start with the minimum necessary categories. Screenshots and detailed allocation will be sent to secondary research.
3. Select slow interval and read the positional relationship of input delay → handler/JS → style/layout → paint/raster/composition. Sections where nothing is running in main are also viewed as candidates for waiting for network/worker/lock/IPC.
4. It goes back and forth between the call tree, bottom-up, event log, and track, and matches the UI application of not only script but also layout, raster, and worker reply. [W08][W07]

Minimum basis to record:

```text
trace: perf/search/baseline/trace.json
range: relative time and unit in trace
process/thread: Observed PID/TID/name
input/marker: anonymous operation ID
critical chain: input queue -> script -> forced layout -> next relevant frame
stack/event: source-mapped symbol or original symbol
unknown: GPU completion not obtained, cross-origin script attribution unknown, etc.
```

The paths and chains described here are examples of report formats, and are not actual measurement results.

## 3. Additional measurements by symptom

| symptoms| Observations to add| Don't rush to conclusions|
|---|---|---|
| Does not respond to input|pending task, event start delay, main queue| Even if the handler itself is short, the input delay will be long|
| handler is short but results are slow| worker/network round-trip, framework commit, layout/paint | The end of DOM update is not the end of display.|
| Only scroll is junk| input, main/compositor, raster/tile, large paint, listener | No LoAF is not proof of smoothness|
| CPU increases gradually| repeated update, timer, subscription, allocation | Just average CPU and don't mix foreground/idle|
| memory keeps increasing| allocation profile, heap diff, retaining paths, detached DOM | process RSS, JS heap and GPU memory are not the same|
| Startup/transition is slow| network waterfall, parse/compile, hydration, font/image, CPU | Reducing bytes alone does not necessarily shorten the critical path.|
|Large screen/high DPR is heavy| layer/raster/texture, paint area, GPU| Even if the number of DOMs is the same, the pixel workload is different|

memory repeats the same scenario and examines the plateau after it is freed. Do not mix stoppage during heap snapshot or reference retention by DevTools into measured values. Forced GC is a separate experiment to investigate the cause, and will not be adopted as a normal behavior of the user environment. [W18]

## 4.field and lab

Field RUM is collected with consent, minimal data, and low overhead. LCP/INP/CLS fixes the official definition implementation and version. The raw event value of the attached runtime probe is not a replacement. Do not compare p95 of a single lab operation and field visit p75 in the same column. [W19][W22]

CPU throttle is a reproducibility aid and is not a complete substitute for memory bandwidth, GPU, thermal, or mobile SoC. Perform final confirmation on the target low-performance actual machine. After turning it into a worker, it records not only the main task but also the total CPU, memory, and result arrival. [W11][N01]

## 5. Before / after

Use deep traces to show the cause, and repeat performance measurements with the same light settings. Check to see if any operations to be sampled are missing due to changes, or if you are not discarding work from the queue and showing only the results faster. Align network/cache states and alternate order.

Agents that receive performance traces do not create hidden capture settings or symbols. Use the included script for gzip/Chrome JSON indexing, and the appropriate tools such as Perfetto for multiple process dependency analysis. Do not forcefully convert unsupported formats and report them as parsed. [C04][C05]


## v1.1.0: Preservation and cross-boundary trace

Assign a correlation ID to each operation and distinguish between queued/start/end, reply, UI apply, local commit, and server ACK. Name only the observed end point without directly subtracting values with different clock domains. [H27]

Add message count/bytes, pool startup, queue age/peak, Outbox pending/retry/conflict, transaction wait and commit, and callback discard counts as necessary. Avoid logging large raw payloads. Associate the observation conditions of [boundary contract](boundaries-and-protocol.md) and the injection points of [fault tests](failure-injection.md) to the same report.

Maintain the old version's metrics and compare separately the faster optimistic display and the faster completion of actual results and saves. If actual machine/fault injection has not been executed, do not set G6 to pass.
