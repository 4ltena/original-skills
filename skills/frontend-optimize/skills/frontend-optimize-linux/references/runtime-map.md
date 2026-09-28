# Linux runtime: distinguish toolkit, session, and compositor

## 1. There is no single “Linux frontend thread”

Identify Qt Quick/Widgets, GTK 4/3, WebView, or a custom renderer first. Record Wayland/X11, desktop compositor, renderer/backend, driver, scale, and refresh rate. Do not describe a toolkit concept as a Linux kernel thread layout. [L01][L05][L06][L11]

| Path | UI side | Rendering side | Main observations |
|---|---|---|---|
| Qt Quick | GUI event loop, QML/JS, bindings, models, scene graph synchronization | Basic or threaded render loop, scene graph, GPU backend | QML cost, synchronization blocks, render/submit, present |
| Qt Widgets | GUI event loop, widget/layout/paint events | Backing store and platform drawing path | Layout/paint area and redraw rate; do not reuse the Quick diagram unchanged |
| GTK 4 | Main context/GTK objects, events, layout, snapshot | GSK renderer, GDK surface, GPU/CPU backend | Main-context work, frame clock, snapshot/render, compositor |
| Wayland client | Toolkit surfaces, buffers, commits | Compositor coordinates composition/scanout | Frame callbacks, buffer lifetime, presentation data |
| X11 client | X11 and toolkit events/drawing | Server, compositor, and driver combination | Client/server/compositor dependencies |
| Kernel / DRM/KMS | Scheduling, GPU/driver, display control | Lower paths such as page flip and scanout | System tracing only when needed; the app may not control these directly |

Process and thread names vary by implementation and version. Do not invent a render thread absent from the trace. [L01][L06][L12]

## 2. Qt Quick render loops

Qt Quick has basic and threaded loops; platform and backend affect the choice. In the threaded loop, the GUI thread blocks while synchronizing the scene graph. A render thread does not mean GUI/QML work can run freely in parallel. [L01]

Heavy QML bindings, JavaScript, model updates, or delegate creation on the GUI side delay rendering updates. Scene graph APIs used at the synchronization point have different execution rules from ordinary GUI object operations. Call APIs such as `updatePaintNode` only at the time and on the thread their contract permits. [L01][L02]

A `QThread` object's affinity is not simply the location of code running on that thread. Check QObject parentage, `moveToThread` conditions, queued connections, and event-loop lifetime. Do not mutate a UI-owned model or control directly from a worker. [L03]

Scene graph batching depends on materials, clips, layers, and draw order. Adding a layer or effect does not always speed rendering up. Check batch count, resource size, and invalidation in the trace. [L04]

## 3. GTK 4 main context and rendering

GTK object access generally belongs to the thread handling GTK. Do not mistake exceptions for thread-safe GDK/GSK types or APIs for thread safety of all GTK. Use another thread only for types and operations documented as safe. [L05]

`g_idle_add()` schedules lower-priority work on the main loop; it does not move CPU work to a worker. If using GTask's run-in-thread path, verify delivery of completion to the creating main context and that this context is running. [L08]

GTK 4 performs update/layout/paint work along a frame clock, builds render nodes during snapshot, and hands them to a GSK renderer. Internal renderer parallelism does not make arbitrary GTK UI updates from other threads safe. Do not assume GTK 3 and GTK 4 have the same drawing model. [L06][L14]

ListView/GridView factories reuse widgets for visible items. Separate setup, bind, unbind, and teardown responsibilities; remove old signals and item references on rebind. UI reuse alone does not reduce data memory if the entire model is loaded. [L07]

## 4. Wayland callbacks are not proof of display

A `wl_surface.frame` callback helps schedule the next update; it does not prove that pixels from that frame reached the display. `wl_buffer.release` concerns when a buffer may be reused, not the display time. Treat commit, GPU completion, compositor receipt, and physical display as separate boundaries. [L11]

If presentation feedback is needed, verify the protocol extension, clock, and flags offered by the target compositor and connection against primary documentation and at runtime. Otherwise report only the observed boundary, such as “through submit” or “through frame callback.” Do not derive a fictional input-to-photon value from a frame callback.

Follow the ownership rules of the buffer/device API. Do not modify a surface managed by GTK or Qt behind its back. Reading DRM/KMS documentation does not justify bypassing the compositor in an ordinary desktop app. [L11][L12]

## 5. Scheduling, memory, and energy

Separate CPU-bound GUI work from waiting on workers, locks, I/O, GPU, or compositor. Creating one worker per core can increase GUI contention, cache and memory-bandwidth pressure, and queue growth. Bound worker count and concurrent bytes; observe effects on other desktop processes. [L02][L03]

A perf sample profile estimates the sampled events; it does not automatically capture all waiting, GPU work, or presentation. Combine it with Sysprof, GTK/Qt tracks, and system traces where needed. [L09][L13]

Polling, timers, and continuous frame requests while idle may increase power use and wakeups. An observer can itself create work. Recheck idle and resume behavior without diagnostics. [L06][L14]

## v1.1.0: Execution context and persistence ownership

Go beyond memorizing thread counts. Use the [boundary protocol](boundaries-and-protocol.md) to record state ownership, the target queue, and when results are applied or committed. Shared memory, actors, dispatchers, and database transactions provide different guarantees.

Apply the [platform data-flow contract](native-data-flow.md) and [durability and recovery](durability-and-recovery.md). Do not tie the lifetime of a durable domain operation to that of a UI view. Label unknown process/thread placement as inference.
