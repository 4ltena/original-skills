# Apple optimization playbook

## A. CPU remains in MainActor

**Evidence:** Long stack of decode/filter/sort etc. in main after tap/typing. Main occupation continues even within `Task {}`. **Rebuttal:** If the I/O to the await destination is long and main is accepting input, actor offload is not the only solution to the problem.

First, review the amount of data, algorithms, and incremental calculations. Next, pass the Sendable input to the concurrent function/service that complies with the isolation rules of the target Swift. UI objects are not taken out. Provide an upper limit for the number of jobs, cancel/generation, and reduce the UI application of the returned results. [A03][A04]

**Verification:** Measures main occupancy, result arrival, total CPU, memory, error/cancel, and overwriting of old results. The mere fact that you used `Task.detached` does not qualify you as a success.

## B. Waiting for actor/lock/I/O

**Evidence:** Main stops due to semaphore/lock/sync read, etc., and CPU usage is low. **Rebuttal:** If the stack is performing a large number of calculations, it is not just a matter of waiting.

Convert synchronous dependencies to async result delivery. Separate the minimal results required by the UI and subsequent processing. Solve the design of waiting for work on the same actor synchronously, blocking in the collaborative pool, and priority inversion. No hidden waits with unlimited concurrency. [A03]

**Verification:** Is it cancelable? Is it safe to complete when the view ends? Does the UI not freeze due to timeout/error? Reject data races to speed up results.

## C. SwiftUI update fan-out

**Proof:** A single state change propagates to a wide Update Group, causing expensive body/representable updates. **Rebuttal:** If the body is cheap and the render side is in control, don't just continue reconfiguring the state.

Set the scope of state/observation to the required range. Organize derived data, format, and decode outside the body and calculate according to the input version. Maintain stable identity and avoid structures where row IDs change every time they are updated. Make the number of rows and structure for List/Table easy to understand. [A01][A02]

When installing a cache equivalent to memo, first decide on the key/invalidate/bytes upper limit. Even if you use an equatable wrapper etc. to erase the apparent updates, if you miss the display that has changed in meaning, it is incorrect.

## D. Large list/table/diff/native bridge

**Evidence:** Full filter/sort, full snapshot rebuild, heavy measure per row, full reload with representable. **Rebuttal:** If there are few visible rows and data updates are cheap, check the image/render issue first.

Separate paging/indexing on the data side and lazy/reuse on the UI side. Use deltas and stable IDs to avoid reapplying all settings to unchanged native views/models. Reduce UI posts by batch, but avoid exceeding the deadline with one large batch. [A01][A02]

**Verification:** Selection, focus, scroll position, IME, editing while sorting, VoiceOver, Dynamic Type, row content reuse errors. Don't judge based on average scroll FPS alone.

## E. Image/text/layout preprocessing

**Evidence:** Image decode/resize, text shaping/layout, formatter initialization, constraint chaining just before becoming visible. **Rebuttal:** If the GPU on the render side is dominant, moving the CPU preprocessing alone is not enough.

Consider resources that match the display dimensions, bounded cache, removal of duplicate processing, and advance preparation. Check thread-safety/affinity using individual APIs, and do not set "all images as background". Include font/locale/size/scale/content as necessary in the cache key of the layout result. [A01][A06]

**Verification:** Japanese/emoji/RTL, Dynamic Type, DPI/scale, image quality, memory pressure, cache eviction, cancellation. Do not simplify fonts or effects without permission.

## F. commit hitch or render hitch?

**Evidence:** Which stage in the timeline has missed its deadline. **Rebuttal:** The root cause remains even if only GPU optimization is performed even though commits on the app side are delayed.

On the commit side, reduce the amount of UI work/update range. On the render side, check layer/effect, offscreen work, overdraw, and GPU resource dependence. For candidates such as shadowPath and rasterization, check the current API, correctness of shape, invalidation, and memory and perform A/B. Just increasing the cache is not an improvement. [A05][A06]

**Verification:** The screenshot/visual difference compares the tolerance with human requirements and separately measures the actual frame and latency. Check for deterioration in image quality, scroll, resize, animation, and energy.

## G. Startup, recovery, and long-term operation

**Evidence:** Eager initialization unnecessary for UI operation, load all items, startup synchronous I/O, timer/task/subscription that remains even when the screen is closed. **Rebuttal:** Do not separate whether only clean startup is slow or always slow, and do not make it lazy.

Display the minimum required state first and proceed with the rest at a priority/point that does not block the first operation. Be sure to measure the initial usage cost that you postponed. Check cancel, cancel observer, cache limit, and owner of image/layer/resource. [A07][A08]

**Verification:** cold/warm, wake-up, long opening/closing, memory plateau, idle CPU/energy. Do not manipulate the OS to create abnormally advantageous conditions.


## v1.1.0: Improved storage/protocol/lifecycle branching

| symptoms| necessary evidence| Refusal/alternative cause| Minimum change candidate| Acceptance conditions|
|---|---|---|---|---|
|Light UI but slow results/saving| queue/clone/commit/ACK/UI apply section| Only network and UI apply dominate| batch/index, small result, bounded offload | G2 to G4, improvement of actual end point and resource maintenance|
| Memory increases with input burst| items/bytes/age of producer~completed queue| Other causes of cache retention and GC| Before sending admission, query limited coalesce| G3, F01/F02, no editing drop|
| data returns after displaying saved| local commit/receipt and crash position| server conflict or stale view|Alignment of state display and transaction/outbox| G4, F04–F08 |
| Inconsistency between old and new versions/multiple windows| schema/protocol/leader/writer version| partition/authorization switching, etc.| Compatible protocols / upgrade/lock/recovery| G5, F09/F10 |

Implementations check [platform specific contract](native-data-flow.md). Do not introduce DB/Outbox that is not related to the symptoms you want to improve. The acceptance or rejection will be returned to [stricter contract](hardening-contract.md), and unmeasured improvements will not be determined.
