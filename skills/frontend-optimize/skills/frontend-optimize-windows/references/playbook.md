# Windows optimization playbook

## A. UI handler hogs CPU

**Evidence:** The CPU stack for parse/sort/format is concentrated in the Dispatcher thread after input. **Rebuttal:** If you mainly focus on wait, simply adding Task.Run is not your first choice.

Reduce the amount of calculation/number of outputs and make CPU work independent of UI objects. Pass it to the appropriate worker task and return the result to the Dispatcher with a small diff. I/O uses the corresponding async API. Make the number of tasks, bytes, and concurrency bounded. [N03][N06]

**Verification:** Total CPU, UI thread occupancy, result reached, cancel/error, view exit, stale generation. Even if it becomes a worker, if the last huge collection application remains, it is unresolved.

## B. Sync wait / ThreadPool starvation / queue flood

**Evidence:** `.Wait/.Result`, sync Dispatcher, lock, stack where worker tasks wait for UI/interdependencies. Or tons of short UI callbacks. **Rebuttal:** If the Dispatcher queue is empty and waiting for GPU, queue control is not the primary cause.

Solve the synchronous wait from the UI and connect it to asynchronous completion. Find an API that just makes blocking look like async. Specify UI ownership for continuation processing. The producer→UI boundary is controlled using bounded channel/queue, batch, coalesce, etc., but the order and persistence are maintained for business events that cannot be discarded. [N02][N03][N06]

**Verification:** The queue depth/bytes is bounded by the producer with a faster load than the UI. The number of jobs will be returned when canceling. Changes that simply raise all priorities or move all processing to ThreadPool are not adopted.

## C. Binding / notification fan-out

**Proof:** One edit causes all item updates, binding re-resolution, all collection replacements, and multiple layout passes. **Rebuttal:** If the binding cost is small, micro-optimizations such as reflection will not continue.

Use proper property-based notifications and incremental updates. Reduce calculation/convert of unnecessary values for display. Preserve object identity and collection lifetime and confirm the need for full rebuild. The binding methods available for WPF and WinUI are different, so follow the contract of the target version. [N08][N11]

**Validation:** Stale UI with content not updated, order reversal, edit rewind, validation display, a11y notification. If you just want to remove notifications and make it faster, use reject.

## D. Virtualization is not working

**Evidence:** A large amount of container generation/measure/retention compared to the number of visible items. In WPF, check the conditions for panel/scroll/container to disable virtualization. **Rebuttal:** If the number of containers is appropriate, proceed to a different route such as loading all data or image processing. [N07]

Choose appropriate virtualizing control/panels, recycling, and bounded data paging. Do not transfer WPF setting names to WinUI. Handle recycled item selection/editing/validation/resource correctly when binding/unbind. [N07]

**Verification:** Variable row height, scroll restore, focus, keyboard, screen reader, DPI, row state leaks. I don't claim that data memory is reduced just by UI virtualization.

## E. Layout / template / image

**Evidence:** Measure/arrange reruns, complex templates, huge image decodes, full updates on every resize. **Rebuttal:** If present/GPU domination, layout flattening alone is not enough.

Perform a control experiment to reduce unnecessary visuals/templates to maintain an acceptable appearance. Sort out layout invalidations and adjust image dimensions and decode time. Use individual optimizations such as WPF's Freezable after re-checking the applicable conditions, thread affinity, and immutable contracts with the official API. [N06][N07][N08]

**Verification:** Text/image quality, IME, enlargement, DPI, theme, a11y. Do not arbitrarily simplify the appearance of production.

## F. Composition / present

**Evidence:** UI CPU is short but render/present delay, GPU queue and effects dominate. **Rebuttal:** If the main commit is slow, business latency cannot be saved just by introducing compositor-only animation.

Isolate effect, surface size, overdraw, and invalidation. If you use your own swapchain, check the current DXGI's flip model/latency control and resource ownership. Do not modify toolkit-owned swapchain. [N04][N05][N13]

**Verification:** Check not only throughput/missed frame but also latency from input to display, multiwindow, resize, and device recovery on the target scope. Do not use numbers obtained by changing security/driver/global power without permission.

## G. GC / memory / startup

**Evidence:** Event subscriptions and timers keep closed windows, full data duplication, allocation bursts and GC, unnecessary initializations on startup critical path. **Rebuttal:** If managed heap returns but process increases, also check native/GPU/I/O cache.

Clarify the cache limit/eviction, event cancellation, CancellationToken/lifetime, and the owner of disposable resources. Array/object pools are measured including retention, return, confidential data, and thread safety, and are not adopted unconditionally. Measure whether the delayed initialization of startup is transferred to the initial usage latency. [N01][N12]

**Verification:** cold/warm, opening/closing multiple windows, long session, heap plateau, idle CPU, first operation. Do not add forced GC as part of normal product operation.


## v1.1.0: Improved storage/protocol/lifecycle branching

| symptoms| necessary evidence| Refusal/alternative cause| Minimum change candidate| Acceptance conditions|
|---|---|---|---|---|
|Light UI but slow results/saving| queue/clone/commit/ACK/UI apply section| Only network and UI apply dominate| batch/index, small result, bounded offload | G2 to G4, improvement of actual end point and resource maintenance|
| Memory increases with input burst| items/bytes/age of producer~completed queue| Other causes of cache retention and GC| Before sending admission, query limited coalesce| G3, F01/F02, no editing drop|
| data returns after displaying saved| local commit/receipt and crash position| server conflict or stale view|Alignment of state display and transaction/outbox| G4, F04–F08 |
| Inconsistency between old and new versions/multiple windows| schema/protocol/leader/writer version| partition/authorization switching, etc.| Compatible protocols / upgrade/lock/recovery| G5, F09/F10 |

Implementations check [platform specific contract](native-data-flow.md). Do not introduce DB/Outbox that is not related to the symptoms you want to improve. The acceptance or rejection will be returned to [stricter contract](hardening-contract.md), and unmeasured improvements will not be determined.
