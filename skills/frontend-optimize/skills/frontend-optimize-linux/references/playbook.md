# Linux optimization playbook

## A. Qt GUI/QML is dominant

**Evidence:** Binding/JS/signal/delegate generation occupies the GUI side. **Rebuttal:** If the GUI is short and waits for sync/GPU, simply rewriting the QML style will not solve the problem.

Narrow the recalculation range, handle filter/index/difference in the model, and lighten the delegate. Prepare the minimum data required for display and adjust the required dimensions/time points of the image. Even when moving from QML to C++, heavy C++ running on the same GUI thread stops the UI. [L02]

**Validation:** Input latency, number of delegates created/retained, correctness of visible items, scroll/selection, memory. Do not report that parallelization was achieved simply by changing the language.

## B. Qt worker / affinity / sync

**Evidence:** Massive queued signal to GUI, direct change of model from worker, GUI waits for sync in threaded render loop. **Rebuttal:** Check the sync section of the trace without guessing the cause by changing the thread configuration.

Organize QObject ownership, event loop, queued connection, and termination processing, and return the difference to the UI-owned model with bounded batch. Do not touch render-owned objects except at the point specified in scene graph synchronization. You cannot eliminate the synchronization dependency between GUI↔render by increasing the number of threads. [L01][L03]

**Verification:** Data race on thread termination, window closure, cancel, signal order, device/backend, stress. The mere fact that you used `moveToThread` or `QThread` is not a success.

## C. Qt scene graph / GPU

**Evidence:** QML is cheap, render/submit is heavy, batch breaks, layers/effects/clips and high-resolution resources dominate. **Rebuttal:** If the main update is slow, do not optimize only the GPU.

Make material/clip/layer/invalidation, overdraw, and image dimensions a control experiment. Switching the render loop/backend is for diagnostic purposes, and improvements made only to a specific driver will not be generalized to all Linux. [L01][L04]

**Verification:** Misdrawing, alpha/clip, DPI, resize, resource lifetime, memory and input latency. Measure memory regression due to layer cache increase.

## D. GTK main context is occupied

**Evidence:** Heavy computation in event/idle callback, repeating layout/snapshot. **Rebuttal:** callback If the CPU is short and waits for I/O/compositor, it is not only a calculation offload.

In addition to moving it to `g_idle_add`, it also sends the thread-safely separated CPU work to an appropriate worker path such as GTask. Check the context that created the task and the place where the callback returns. Pass only the results to the UI without operating GtkWidget etc. from the worker. [L05][L08]

**Verification:** cancel, error, window/widget destroyed, old generation, task context lifetime, total CPU/queue. Don't make huge UI application of completion callback a new bottleneck.

## E. GTK lists / snapshot

**Evidence:** Generating all widgets, heavy work every time bind, accumulation of old signal and item references, frequent full snapshots. **Rebuttal:** If factory reuse is normal, proceed to data/model or GPU side.

Use the corresponding ListView/GridView and model, and separate resource responsibilities using setup/bind/unbind/teardown. Differential/bounded filter/sort, paging, image preparation. When dealing with render node cache, check the thread-safety and lifetime of the type/API. [L07][L05][L06]

**Verification:** Item reuse error, focus, scroll, selection, IME, a11y, memory plateau. Measure UI reuse and data virtualization separately.

## F. Wayland / presentation

**Evidence:** The client's UI/render work is short, but delays can be seen in the update schedule and compositor side. **Rebuttal:** If only the client's submit is obtained, the cause of the actual display delay is still unknown.

Review the animation request frequency and surface update amount, and use frame scheduling that is compatible with the toolkit. Do not render in busy-loop without waiting for frame callback. Separate buffer reuse and presentation boundaries. It does not break surface ownership of the toolkit except for its own client. [L11][L14]

**Verification:** Range, refresh/scale, visibility of window, and load of other windows for which the corresponding presentation information was obtained. Do not make unauthorized adjustments to compositor/global driver.

## G. I/O / memory / idle

**Evidence:** UI synchronous DB/file I/O, all dataset copies, event/source remains alive, frame/timer runs even in hidden windows. **Rebuttal:** Do not confuse leak with cache, where resources are released and plateaued.

Isolate I/O properly and reduce work on critical paths with index/paging/caching. Design the cache limit, source/signal release, worker termination, and image/GPU resource owner. Pooling can increase long-lived retention, so we measure both allocation and retained memory. [L02][L03][L08]

**Verification:** Startup/first operation/return, long session, idle CPU/wakeups, memory, error/cancellation. Do not relax perf privileges or make root execution a permanent fix. [L15]


## v1.1.0: Improved storage/protocol/lifecycle branching

| symptoms| necessary evidence| Refusal/alternative cause| Minimum change candidate| Acceptance conditions|
|---|---|---|---|---|
|Light UI but slow results/saving| queue/clone/commit/ACK/UI apply section| Only network and UI apply dominate| batch/index, small result, bounded offload | G2 to G4, improvement of actual end point and resource maintenance|
| Memory increases with input burst| items/bytes/age of producer~completed queue| Other causes of cache retention and GC| Before sending admission, query limited coalesce| G3, F01/F02, no editing drop|
| data returns after displaying saved| local commit/receipt and crash position| server conflict or stale view|Alignment of state display and transaction/outbox| G4, F04–F08 |
| Inconsistency between old and new versions/multiple windows| schema/protocol/leader/writer version| partition/authorization switching, etc.| Compatible protocols / upgrade/lock/recovery| G5, F09/F10 |

Implementations check [platform specific contract](native-data-flow.md). Do not introduce DB/Outbox that is not related to the symptoms you want to improve. The acceptance or rejection will be returned to [stricter contract](hardening-contract.md), and unmeasured improvements will not be determined.
