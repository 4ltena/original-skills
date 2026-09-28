# Apple profiling runbook

## 1. Check feasibility and build

Check macOS host, appropriate Xcode, target device/simulator, and required signatures/permissions. Separate the Release/Profile configuration of the actual machine and the debug investigation. If there is no symbol, check the available dSYM and build ID, and mark the stack that cannot be restored as "unknown". [A07][A08][N01]

Examples of secure tool discovery:

```sh
xcodebuild -version
xcrun swift --version
xcrun xctrace list templates
xcrun xctrace list devices
xcrun xctrace help record
xcrun xctrace help export
```

Use only the options that exist in the help of installed tools. Resolve the device name, PID, and template from the output, and do not use the example values for production. In Linux/Windows environments where there are no settings or tools, actual Apple machine measurements have not been performed.

## 2. Select instrument based on symptoms

| symptoms| First observation| What to check next|
|---|---|---|
| Input stops / hang| Hangs / Time Profiler / main thread| Is it CPU-bound, wait/lock/I/O, or who is waiting for it?|
| One SwiftUI operation is heavy| Compatible version of SwiftUI instrument| Update Groups, long body/representable, cause/effect |
| scroll/animation hitch | Hitches / animation related tracks| Dependency on the same frame, whether on commit side or render side|
|High CPU/power| Time Profiler / CPU related instruments| hot path, timer, idle work, excessive parallelism|
| memory increase| Available tools such as Allocations / Leaks / memory graph etc.| Allocation or retention, image/layer/native resource?|
| GPU processing is slow| Target version of Metal/GPU tool| GPU execution, resource dependence, excessive effects, synchronous readback|
| Startup/return is slow| CPU/I/O + operation marker during launch section| eager initialization, serial dependence, until first input|

Check the instrument name and availability using `list templates` and Xcode UI. The above name does not necessarily exist as the same template name on all OS/versions. [A02][A05][A07][A08]

## 3. Create operation sections

Reuse any existing signpost/metrics infrastructure. When adopting `os_signpost`/`OSSignposter`, etc., check the deployment target, import, and availability using the official API, make sure that begin/end are paired with the same ID, and end with error/cancel. Do not include input strings or personal information in the name.

Divide the section into at least "UI reception", "background calculation/obtainment", and "UI application". Do not name an interval that does not measure up to the actual display as input-to-display. When using XCTest's performance metrics, specify measurement boundaries, repetition, warmup, and app state reset.

This package does not automatically insert signpost/XCTest code for unknown deployment targets. The types and functions of the target API are type-checked using the actual toolchain before being added.

## 4. How to read trace

1. First, select the operation section. Separate the wall time of the entire hang and the running time of main.
2. If it is CPU-bound, check the self/inclusive stack of main and identify which of body/formatting/parse/layout etc. dominates.
3. If it is a wait, look at the lock/actor/semaphore/I/O and other party's work. Check if there is a synchronous wait after moving from main to background.
4. Follow SwiftUI update causes → dependencies → update groups, and separate the simple number of body calls and its CPU cost.
5. Hitch separates the commit delay on the app side and the delay on the render side, and records the corresponding frame/time in the report. [A02][A03][A05][A08]

The execution location of the job on the main actor is not determined only by the source annotation, but by checking the toolchain settings and trace. Even if a large number of tasks are generated, serial queues of the same actor will not result in parallel processing. [A03][A04]

## 5. Single-cause control experiment

Choose one change, such as precomputing filters, narrowing the scope of update state, or moving image decode to the appropriate location. Temporary disabling of effect is limited to diagnostic A/B and does not constitute approval for removal from the product. Leave the measurement flag in the report and do not mix it with the adopted value. [A01][A06]

## 6. Remeasurement matrix

Select the actual device class, refresh, battery/power, thermal, data scale, cold/warm, Dynamic Type, VoiceOver, IME, reduce motion, background return, and low memory state depending on your needs. If all combinations are not possible, write the scope of implementation.

Even if you can see the cause of the CPU stack in the simulator, check whether GPU/thermal/energy is adopted or not on a representative actual machine. Verify the cause using light measurements multiple times before/after and heavy tracing. Do not extend archived OS generalizations or results from a single device to all Apple products. [N01][A05]


## v1.1.0: Preservation and cross-boundary trace

Assign a correlation ID to each operation and distinguish between queued/start/end, reply, UI apply, local commit, and server ACK. Name only the observed end point without directly subtracting values with different clock domains. [H27]

Add message count/bytes, pool startup, queue age/peak, Outbox pending/retry/conflict, transaction wait and commit, and callback discard counts as necessary. Avoid logging large raw payloads. Associate the observation conditions of [boundary contract](boundaries-and-protocol.md) and the injection points of [fault tests](failure-injection.md) to the same report.

Maintain the old version's metrics and compare separately the faster optimistic display and the faster completion of actual results and saves. If actual machine/fault injection has not been executed, do not set G6 to pass.
