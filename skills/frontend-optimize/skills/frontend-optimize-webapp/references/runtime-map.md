# Web runtime: what runs where and where it waits

## 1. Don't fix the implementation

This table is a conceptual model of Chromium, not a specification of the number of OS threads. The placement changes depending on the browser version, site isolation, frame, platform, visibility, and GPU settings. Use the 2018 Inside Browser article to understand the concept, and check by PID/TID and thread name of the current trace. [W01][W03][W04]

| Executor| main job| How to read bottlenecks| Range that agent can change|
|---|---|---|---|
| browser process / UI side| window, input routing, navigation, process management| Separate the browser side and the renderer side|app request frequency, IPC/permission. Direct dispatch to internal thread is not possible|
| renderer main | JS, DOM, style, layout, paint record, framework update, input handler| long task, forced layout, concentrated UI application, microtask column| Processing amount/Update range/Split/Move to Worker|
| Dedicated / Shared Worker | Separate global JS, compatible I/O/CPU, message processing| Waiting in queue, clone/transfer, worker's own long task| Bounded job, ownership, cancel, apply result|
| Service Worker | event-driven fetch/cache etc.| activation/startup, I/O, lifetime | fetch route and cache strategy. Do not make it a resident CPU pool|
| Worklet | Specialized processing for audio/paint, etc.| Corresponding pipeline deadline| Limited work on supported APIs. Not a general purpose thread pool|
| renderer compositor / cc |Part of input/scroll, layer tree, commit/activate, frame generation for composition| Waiting for commit from main, waiting for pending tree, waiting for raster| eligible animation, layer/paint amount. scroll in general is not always independent|
| raster workers / GPU raster | rasterize paint records to tile/image| visible tile delay, raster amount, upload| drawing area, image dimensions, invalidation, tile pressure|
| Viz/GPU process side| Surface aggregation, part of GPU command/display composition| GPU side or other surface wait, command queue| Number of surfaces/updates, GPU load. Check the placement on platform|
| OS compositor / GPU / display | command execution, composition, present/display| GPU saturation, queue, missed refresh|App render amount/submission frequency. Do not change the OS without permission|
| V8 background tasks | JIT compilation, concurrent/parallel parts of GC, etc.| Interaction of compilation, allocation, and GC| Measure and reduce JS shape/allocations. Do not treat internal pool as app worker|

V8 isolate is not another name for OS thread. Separate normal JS execution and GC/JIT background work. The GC has work that runs parallel to the mutator and work that requires it to be stopped. “Because there is a background thread, GC and compilation have no main-thread cost” is incorrect. [W05][W06]

## 2. Event loop: Don't think you've yielded

There is a microtask checkpoint after the task, and a separate rendering opportunity exists. Chaining Promise resolution or throwing in lots of `queueMicrotask` does not guarantee returning control to input/draw. `async` allows syntactic interruption, but does not move the first half of the CPU processing to another thread. [W20][W09]

```js
// feature-detect on target browser. timer fallbacks are not of equal priority.
async function yieldToBrowser() {
  if (globalThis.scheduler?.yield) await globalThis.scheduler.yield();
  else await new Promise(resolve => setTimeout(resolve, 0));
}
```

The chunk size is determined by actual measurements based on the frame/input budget, rather than a fixed universal ms value. If one process in the chunk itself is huge, yielding at the end of the loop will not solve the problem. View cancel conditions between chunks. `requestAnimationFrame` is a synchronization point for visual updates, not dedicated extra time for heavy calculations. Idle callbacks are not used to guarantee completion of urgent results. [W09][W20]

## 3. Criteria for selecting workers/worklets

Workers do not directly touch the DOM, so separate pure work such as searching, parsing, aggregation, and codecs from UI application. A transfer transfers ownership of a buffer and also makes it unavailable to the sender. Compare bounded batch to bulk injection of short jobs, including the cost of structured clone and worker startup/initialization. [W11]

A worklet is a mechanism with a dedicated global and constraints, and is not a contract to secure a dedicated OS thread for each `new Worklet`. AudioWorklet participates in audio rendering deadlines; avoid blocking, excessive allocation, and large variable costs. When dealing with audio, evaluate using an underrun index different from UI fps. [W21][W13]

OffscreenCanvas can transfer part of the drawing to the worker, but check the supported context, transfer method, and browser. If DOM/style/layout is the cause, moving the canvas is not the solution. Measure main occupancy reduction and texture/copy/memory/result presentation delay separately. [W12]

Before introducing SharedArrayBuffer or Atomics, check cross-origin isolation, deployment, permissions, and memory ordering in the target environment. Do not change necessary HTTP/security settings "for optimization" without permission. Don't make it a necessary means of regular UI improvement.

## 4. Rendering: Sometimes compositing alone and sometimes not

Style→layout→paint record→raster→composite does not need all of the information in each frame. Use trace to find out what to change and where to start over. Reading geometry immediately after writing the DOM requires the latest layout at that point, which can cause synchronization work. A control experiment will be conducted to organize the read group/write group and reduce the amount of layout targets. [W14][W04]

If transform/opacity follows the compositor path, the main work can be avoided, but there will be a cost depending on layer promotion, paint contents, effects, and memory. Do not attach `will-change` to all elements. Measure not only the number of layers, but also area x DPR, raster, upload, texture pressure, and destruction/recreation. [W01][W04]

`content-visibility` is a means to omit the drawing process of offscreen content, and is not a mechanism to delete DOM or data. Check the effect on scrollbar/placeholder size, anchor, find-in-page, focus, and a11y on the target browser. For large data sets, separate the roles from real virtualization and page loading. [W15]

## 5. Don't mix frameworks/engines

React Profiler is a clue to component work, not a GPU/presentation measurement device. `startTransition` handles the urgency of updates and does not move the heavy synchronization calculations themselves to other threads. Check the enablement conditions and measurement overhead of production profiling. [W16][W17]

Do not describe WebKit process architecture/JSC or Firefox Gecko/WebRender using Chromium/V8 thread names. The commonality of Web APIs and the sameness of implementation are two different things. Measure with the corresponding browser/WebView. [W23][W24]

## 6. Observation boundary

The good boundaries in the field are evaluated for p75 LCP ≤ 2.5 seconds, INP ≤ 200 ms, and CLS ≤ 0.1 for each terminal group. This is not designed to allow 200ms for all operations. Continuous operations such as scroll/drag and specialized editor require separate latency/frame indicators. [W19][W07]

The 50ms boundary for Long Task/Long Animation Frame is not a high refresh frame budget. A 60Hz screen that gets stuck every 20ms isn't smooth even with low LoAF. Instead of averaging the individual durations of EventTiming and calling them INP, use an implementation that follows the official definition. [W10][W22][W19]


## v1.1.0: Execution context and storage responsibility

Don't finish the list of runtimes by memorizing the number of threads, use [boundary protocol](boundaries-and-protocol.md) to record who owns the state, which queue to enter, and when to apply/commit the result. Shared memory, actors, dispatchers, and DB transactions have different guarantees.

Apply [platform-specific data flow](storage-and-lifecycle.md) and [durability and recovery](durability-and-recovery.md). Do not make the lifecycle of the UI and the lifecycle of durable domain operations the same. Parts where the process/thread placement is unknown are clearly marked as estimated.
