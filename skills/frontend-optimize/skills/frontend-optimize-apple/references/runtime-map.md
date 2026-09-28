# Apple runtime: boundaries between UI, actor, commit, and render

## 1. Check the route by toolkit and OS

The main targets are AppKit/SwiftUI for macOS and UIKit/SwiftUI for iOS/iPadOS. View values, UI objects, layer trees, and GPU resources in SwiftUI have separate lifetimes and update units. The explanation of the render server using UIKit as an example is not a fixed process/thread diagram for all Apple OS. [A01][A05][A06]

| subject| main responsibilities| Waiting/work to observe| wrong interpretation|
|---|---|---|---|
| main thread / main run loop | event, UI lifecycle, UI object operation, layout, etc.| Waiting before processing input, layout, synchronous I/O, long callbacks| Safely touching the UI if you are not the main actor|
| MainActor | Serial isolation domain tied to UI| Job serialized with actor, restart after await, synchronization interval| Actor is a dedicated worker thread, Task is always a separate thread|
| Swift task / cooperative executor |Execute/resume suspendable work| CPU occupancy, waiting for actor, priority/dependency, blocking| Functions with await always release main|
| GCD queues | serial/concurrent scheduling, QoS | queue delay, waiting for sync, excessive parallelism| number of queues = number of threads|
| SwiftUI dependency/update system | Determine necessary view updates based on state dependence| update cause, body/representable cost, identity| Body runs = redraw all pixels|
| AppKit/UIKit layout & drawing | constraint/layout, text/image, layer update| layout pass, measurement, drawing, snapshot | Layout is also free if the layer render is different|
| Core Animation commit | Pass layer-related changes to the render side| commit delay, transaction, serialization|commit completed = screen display completed|
| render side / GPU| compositing, effect, raster, GPU execution | render hitch, offscreen work, bandwidth, queue | The lower the app CPU, the faster the render|
| display | Display with refresh| frame deadline, queue/latency | GPU command completed = photon reached|

There is no one-to-one correspondence between queue/actor and OS thread in this table. Write only the relationships that can be observed with trace to the report. [A03][A05]

## 2. Swift concurrency reads version/configuration first

Detects: Swift compiler, language mode, default actor isolation, enabled upcoming features, function/type isolation annotation, caller actor, capture and sendable boundaries.

Swift 6.2 allows for the option to make main actor isolation the default, as well as changes to caller isolation for nonisolated async. Interpretation changes depending on the adoption status of `NonisolatedNonsendingByDefault` etc. In a new environment, do not unconditionally apply the old explanation that "nonisolated async always leaves to a general-purpose executor." [A04]

- `Task { ... }` may inherit the actor isolation of the creation context. Simply wrapping a large synchronous loop on MainActor does not move the UI's CPU work.
- `await` is an interruption point, and there is no guarantee that it will actually be interrupted or resumed in another OS thread.
- If `@concurrent` is available and meets the applicable conditions, it becomes an option to specify the async processing you want to perform outside the caller actor. However, this is not a contract for securing dedicated threads or unlimited parallelism.
- `Task.detached` not only separates the actor context, but also considers issues that fall outside of structured management. Do not assume that the parent's cancel, priority, TaskLocal, etc. are automatically inherited. [A03][A04]

An example of a safe split design (not a compilation template):

```text
UI/actor: Create a Sendable snapshot of request ID and input
CPU service: Pass calculation to a function/worker that is explicitly isolated in the target toolchain
scheduler: Maximum number of active jobs/bytes, cancel/coalesce unnecessary jobs
CPU service: check cancel with possible granularity, do not capture UI object
UI/actor: If current request ID, apply result as small difference
lifecycle: End work and resources with screen exit/error/shutdown
```

Do not dismiss warnings with `@unchecked Sendable` or unsafe shared mutable state. If you send all large jobs to a dedicated actor, that actor's queue will become the next bottleneck. The cancel flag alone does not stop CPU functions that do not check for interruption.

## 3. Blocking and priority inversion

Avoid designs that clog cooperative executor threads with semaphores, synchronization waits, and long blocking I/O. For I/O that has an async API, use that API, and when you need to isolate a synchronous API, design a bounded execution location that fits that API's contract. If you wait for the background result from MainActor synchronously, input will stop even if you offload. [A03]

Rather than increasing QoS/priority altogether, distinguish between work required for input and look-ahead/index construction. Use trace to check the relationship between high priority jobs waiting for low priority locks/actors and excessive job generation. Don't deny blocking just because of low CPU usage. [A03][A08]

## 4. SwiftUI update cost

Keep the body cheap and place dependent states in the necessary range. If identity is unstable, state/lifecycle, diff, and resource regeneration will change. In List/Table, element identification and row structure are effective. Don't just say "SwiftUI is slow" as a result of including data filter/sort/format or huge image generation in the body. [A01]

The supported version of Instruments uses SwiftUI's Update Groups, long body/representable updates, and cause/effect to track what caused an update and where it spread. Check the Xcode/Instruments version for the measurement UI, threshold, and provided tracks. [A02]

When bridging to AppKit/UIKit, check to see if a representable update causes a full reconfiguration, layout, or model reload on the native side. Declarative value update is not necessarily the same operation as native object regeneration. [A01][A02]

## 5. Hitch location

**Commit side:** Input/state processing, body/layout, text/image preparation, layer update cannot meet the deadline. **render side:** Even if the app has submitted, the effect/raster/composition/GPU side is not in time. Sometimes both occur. [A05]

Shadow shapes, transparent overlap, offscreen rendering, huge layers, image decode/scale, and mask/effect are candidates, but we will conduct comparative experiments while maintaining the appearance and resources. While using raster cache reduces CPU/GPU work, it can have the opposite effect on memory and invalidation. Do not automatically apply Core Animation archive recommendations to all current OSs. [A06]

For apps that own Metal, separate command submission, GPU completion, resource dependence, readback, and wait for present. Do not make changes that bypass the toolkit's own render loop or wait synchronously for GPU completion in the UI thread without checking the API and actual machine trace.


## v1.1.0: Execution context and storage responsibility

Don't finish the list of runtimes by memorizing the number of threads, use [boundary protocol](boundaries-and-protocol.md) to record who owns the state, which queue to enter, and when to apply/commit the result. Shared memory, actors, dispatchers, and DB transactions have different guarantees.

Apply [platform-specific data flow](native-data-flow.md) and [durability and recovery](durability-and-recovery.md). Do not make the lifecycle of the UI and the lifecycle of durable domain operations the same. Parts where the process/thread placement is unknown are clearly marked as estimated.
