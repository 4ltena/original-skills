# Web optimization playbook

The following are suggestions and are not automatically applied rules. Without evidence for each node, the optimization remains a hypothesis.

## A. Search, conversion, and analysis occupy the main area

**Symptoms:** The CPU stack following the input occupies the majority and increases relative to the amount of data. **Rebuttal:** If the CPU time is short and most of the time is waiting for I/O/queue, converting the calculation to a worker is not the primary cause.

First, reduce the need for recalculation, indexes, incremental parses, differences, and the number of outputs. When sending pure calculations whose order has little meaning to the worker, use separate markers for input encode/clone, startup, queue, processing, response, and UI application. Don't reciprocate the entire document with every keystroke. [W11]

Example design contract:

```text
Search request = {generation, query, datasetVersion}
Worker side: Upper limit on concurrent active number and pending bytes/items
Pending searches that only require the latest can be replaced
Stop running calculation: cancel check for each chunk or cooperative stop
Main side: If generation != latest, it will not be applied to the UI
dispose: listener release, task cancel, worker/transfer resource lifespan processing
```

Discarding results with generation does not necessarily stop old calculations from consuming CPU. This latest-wins method is not applied to write/edit transactions that cannot be discarded. The main indicators are input-to-result and UI occupancy, and guardrail is total CPU, memory, and correctness. [W11]

## B. Intended to be divided into microtasks/heavy processing for each frame

**Symptoms:** Long stacks in consecutive microtasks or rAFs. **Rebuttal:** If there is space between frames and the raster is clogged, yield alone will not solve the problem.

Use yield to return to the next task and make the processing unit bounded. Look for multiple rAF loops, observer re-firing, and cycles of state change → effect → state change. While visual updates coalesce within one frame, business events are saved and the order is not lost. If nothing changes every frame, don't schedule. [W09][W20]

## C. Large component tree / invalidation fan-out

**Symptoms:** Huge commit, updating most unrelated components with a single character input. **Rebuttal:** If profiler's component cost is small and DOM/layout is large, do not increase memoization.

Narrow the state ownership location and subscription scope. derived data only calculates from changed inputs. Use stable identities and appropriate keys to reduce unnecessary context/global store distribution. Memo and selector implementation also measures compare/cache cost. Transitions are used for non-urgent display updates and do not magically offload input values or heavy synchronous functions. [W16][W17]

**Verification:** Edit cursor, IME composition, focus, screen reader, controlled input alignment. Even if the number of updates decreases, if stale is displayed, reject.

## D. layout thrashing / mass DOM / list

**Symptoms:** JS and layout alternating, lots of geometry reads, full line measurements per scroll. **Rebuttal:** If there is no synchronized layout and paint/GPU is dominant, layout cannot be the only culprit.

Coalesce reads and writes and coalesce resize/scroll. Design corrections for fixed/estimated row size, measurement cache, overscan, and variable height. In virtualization, not only the number of DOM/nodes but also data acquisition is bounded. Distinguish between content-visibility, which leaves the entire DOM, and virtualization, which manages the lifespan of rows. [W14][W15]

**Verification:** keyboard navigation, selection, a11y semantics, anchor, find, scroll restore, line height change, font load, Japanese IME. Virtualization that does not maintain the necessary meaning will not be adopted.

## E. Bottlenecks moved to paint/raster/GPU

**Symptoms:** Main is short but increases with raster/tile/paint, blur/overdraw, and high DPR. **Rebuttal:** If there is no basis for GPU/paint, do not conclude that "GPU is slow".

Control experiments on invalidated area, large box-shadow/blur/backdrop, duplicate transparent layers, canvas resolution, and image decode dimensions. Also measure cache/layer memory when changing to compositor-eligible animation. When introducing OffscreenCanvas, check the target context and browser and design resource sharing/release. [W04][W12][W14]

**Verification:** Appearance tolerances, text clarity, zoom, resize, color, DPR, low memory devices. Do not "speed up" by deleting effects without permission.

## F. startup / network / hydration

**Symptoms:** Unnecessary modules, parse/compile, multiple serial fetches, and double processing of the same data are visible in the critical route. **Rebuttal:** If server/network control or CPU control is unseparated, only bundle size is not tracked.

Initialize critical resources first and functions that are not required for operation lazily. However, the latency will be measured separately during the first use. Parallelization of fetch protects API/order/rate/resource and avoids excessive prefetch. Check the duplicate data processing and huge serialized state of SSR/hydration with the target framework official documentation. [W08][W06][W19]

When changing font/image, check text metrics, layout stability, and LCP at the same time. The method of forcing everything to idle after startup and blocking the first input will not be successful. [W07][W19]

## G. memory / GC / background energy

**Symptoms:** Increased retained heap after repeated operations, proliferation of listeners/timers/observers, increased frequency of GC and allocation. **Rebuttal:** If heap plateaus and only RSS increases, check other areas such as native/texture/cache.

Add an upper limit/invalidation to the cache and release closed view subscriptions, callbacks, and workers. Reduce continuous generation of large temporary objects, but do not blindly introduce object pooling. Long-lived pool increases retention. Enable to stop hidden screen timer/animation/polling. [W18][W05]

**Verification:** Return to acceptable range after repeating the same operation. Check not only heap snapshot but also normal execution GC pause/CPU, return of tab background/foreground, stale cache, and resource lifespan.

## H. Final low-level optimization

Monomorphic access, typed arrays, WASM, SIMD, WebGPU, etc. are checked only on hot paths that dominate even after reducing the algorithm/data/update amount. V8 tiering internal names, thresholds, and optimization conditions are not treated as fixed APIs. Verifying the victory of microbenchmark by returning to real user operation. [W06]

Special GPU/compute routes are not covered by this playbook. We will additionally investigate the device loss, resource barriers, readback, security, and browser compatibility of the target API, and show the critical path for both main and GPU.


## v1.1.0: Improved storage/protocol/lifecycle branching

| symptoms| necessary evidence| Refusal/alternative cause| Minimum change candidate| Acceptance conditions|
|---|---|---|---|---|
|Light UI but slow results/saving| queue/clone/commit/ACK/UI apply section| Only network and UI apply dominate| batch/index, small result, bounded offload | G2 to G4, improvement of actual end point and resource maintenance|
| Memory increases with input burst| items/bytes/age of producer~completed queue| Other causes of cache retention and GC| Before sending admission, query limited coalesce| G3, F01/F02, no editing drop|
| data returns after displaying saved| local commit/receipt and crash position| server conflict or stale view|Alignment of state display and transaction/outbox| G4, F04–F08 |
| Inconsistency between old and new versions/multiple windows| schema/protocol/leader/writer version| partition/authorization switching, etc.| Compatible protocols / upgrade/lock/recovery| G5, F09/F10 |

Implementations check [platform specific contract](storage-and-lifecycle.md). Do not introduce DB/Outbox that is not related to the symptoms you want to improve. The acceptance or rejection will be returned to [stricter contract](hardening-contract.md), and unmeasured improvements will not be determined.
