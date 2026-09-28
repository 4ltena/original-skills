# Web auxiliary script: features and limitations

## runtime-probe.js

Check the file contents using the local DevTools snippet of the target page, and then load it. Observation does not start just by loading the script. Measure the running page in a permitted verification environment to ensure that there are no conflicts with existing global names.

```js
const probe = createFrontendRuntimeProbe({maxEntries: 300, autoStopMs: 15000});
// Perform the reproduction operation.
const observation = probe.stop(); // Safe to call twice. snapshot() continues measurement.
console.log(observation); // Only once after the operation is completed. Avoid large amounts of logs during measurement.
```

Observe only the corresponding longtask/long-animation-frame/event with PerformanceObserver. EventTiming has durationThreshold≥16ms, implementation has rounding/suppression/missing. Distinguish unsupported/privileges/implementation restrictions from empty observations and check `unsupportedTypes` and `errors`. [W10][W22]

It is a fixed length ring buffer, and when the upper limit is exceeded, the old value is discarded and recorded in `dropped`. Do not collect URL, DOM, target, key value, or script source. No communication. It will stop after 15 seconds by default, and clear observer/timeout/rAF/listener with stop. `autoStopMs: 0` explicitly disables automatic stop.

rAF observation is OFF by default. Specify `sampleAnimationFrames: true` only for the required reproduction interval. Reset the criteria by changing visibility, excluding intervals that span the background. However, the rAF callback interval is not the displayed frame time/FPS, and the observation loop itself disturbs idle. Not used to measure idle power. [W20]

This script does not calculate INP/LCP/CLS. The average value of raw EventTiming is not called INP. Even if LoAF is low, it does not necessarily mean that there is no high refresh jank. [W19][W10]

## trace_summary.py

```sh
python3 scripts/trace_summary.py trace.json --out slice-index.json
python3 scripts/trace_summary.py trace.json.gz --pid 123 --tid 456 --start-us 1000000 --end-us 2000000
```

Compatible with Chrome Trace Event JSON (traceEvents array or top-level array) and gzip. Handle microsecond `ts/dur` and index stack-paired B/E with the same PID/TID as X. B/E pairs in the order of input and reports invalid/unmatched. Not a complete trace validator.

`covered_slice_wall_ms` of each thread is the union of the observed slice interval, not the CPU usage time/usage rate. `inclusive_slice_sum_ms` can double-count nested slices. Do not reconfigure async/flow/counter/GPU dependence. The causal proof of the critical path is performed using the relevant trace tool. [C04][C05]

Perfetto protobuf/binary and other profiler formats are not supported. Default upper limit is decoded 128MiB and 1 million events, and narrow down to shorter captures if necessary. `--max-mib` is an explicit range of 1 to 1024. Exit code 0=index exists, 2=input error, 3=no corresponding slice. `--out` is only a new file and will not be overwritten.

Metadata and event names output short labels included in the input trace, so they may contain confidential information. Review before sharing externally. Do not upload the entire trace to an external service just for numerical aggregation.
