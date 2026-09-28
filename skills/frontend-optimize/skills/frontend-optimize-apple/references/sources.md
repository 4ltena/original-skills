# Sources for frontend-optimize-apple

This skill can resolve references by itself. The H series was confirmed with v1.1.0 for lecture corrections and additional contracts, and the rest was inherited from v1.0.0. Check the citation range and source type, and reconfirm the current implementation with the target version.

## C04 — Perfetto: Trace Processor

https://perfetto.dev/docs/analysis/trace-processor

- Relevant scope: Offline trace analysis. Information beyond recorded events cannot be restored.
- Verification record: 2026-09-23 / inherited-v1.0.0; this revision does not claim a complete re-verification

## C05 — Perfetto: Trace analysis quickstart

https://perfetto.dev/docs/quickstart/trace-analysis

- Related scope: SQL, process/thread/slice investigation.
- Verification record: 2026-09-23 / inherited-v1.0.0; this revision does not claim a complete re-verification

## C06 — Electron: Process Model

https://www.electronjs.org/docs/latest/tutorial/process-model

- Relevant scope: Distinction between main process and renderer process.
- Verification record: 2026-09-23 / inherited-v1.0.0; this revision does not claim a complete re-verification

## C07 — Electron: Performance

https://www.electronjs.org/docs/latest/tutorial/performance

- Related scope: main/renderer blocking, instrumentation, and lazy initialization. Individual old recommendations are not applied across the board.
- Verification record: 2026-09-23 / inherited-v1.0.0; this revision does not claim a complete re-verification

## C08 — Tauri: Process Model

https://v2.tauri.app/concept/process-model/

- Related scope: Rust core and WebView, IPC boundaries.
- Verification record: 2026-09-23 / inherited-v1.0.0; this revision does not claim a complete re-verification

## C09 — Tauri: Webview Versions

https://v2.tauri.app/reference/webview-versions/

- Related scope: Windows WebView2, Apple WKWebView, Linux WebKitGTK.
- Verification record: 2026-09-23 / inherited-v1.0.0; this revision does not claim a complete re-verification

## C10 — Flutter: Performance profiling

https://docs.flutter.dev/perf/ui-performance

- Related scope: UI/raster side instrumentation, profile mode. Thread configuration is version dependent.
- Verification record: 2026-09-23 / inherited-v1.0.0; this revision does not claim a complete re-verification

## C11 — Flutter: Concurrency and isolates

https://docs.flutter.dev/perf/isolates

- Relevant scope: isolate usage and message costs. Distinguish between compute and native in the web.
- Verification record: 2026-09-23 / inherited-v1.0.0; this revision does not claim a complete re-verification

## W01 — Chrome: Inside look at modern web browser, part 3

https://developer.chrome.com/blog/inside-browser-part3

- Relevant scope: 2018 concept description. This is not the basis for fixing the current arrangement.
- Verification record: 2026-09-23 / inherited-v1.0.0; this revision does not claim a complete re-verification

## W03 — Chromium: Threading and Tasks

https://chromium.googlesource.com/chromium/src/+/main/docs/threading_and_tasks.md

- Related scope: thread and sequence, ThreadPool. Since it is the main branch, double check at runtime.
- Verification record: 2026-09-23 / inherited-v1.0.0; this revision does not claim a complete re-verification

## W04 — Chromium: How cc Works

https://chromium.googlesource.com/chromium/src/+/main/docs/how_cc_works.md

- Affected scope: Compositor, commit, raster, activation internal model.
- Verification record: 2026-09-23 / inherited-v1.0.0; this revision does not claim a complete re-verification

## W08 — Chrome DevTools: Performance reference

https://developer.chrome.com/docs/devtools/performance/reference

- Related scope: trace acquisition, flame chart, execution and drawing investigation.
- Verification record: 2026-09-23 / inherited-v1.0.0; this revision does not claim a complete re-verification

## W11 — web.dev: Off-main-thread architecture

https://web.dev/articles/off-main-thread

- Related scope: CPU processing movement by Worker, trade-off with communication.
- Verification record: 2026-09-23 / inherited-v1.0.0; this revision does not claim a complete re-verification

## W14 — web.dev: Avoid layout thrashing

https://web.dev/articles/avoid-large-complex-layouts-and-layout-thrashing

- Relevant scope: forced layout synchronization and read/write.
- Verification record: 2026-09-23 / inherited-v1.0.0; this revision does not claim a complete re-verification

## A01 — Apple: Demystify SwiftUI performance (WWDC23)

https://developer.apple.com/videos/play/wwdc2023/10160/

- Related scope: Dependency, identity, List/Table.
- Verification record: 2026-09-23 / inherited-v1.0.0; this revision does not claim a complete re-verification

## A02 — Apple: Optimize SwiftUI performance with Instruments (WWDC25)

https://developer.apple.com/videos/play/wwdc2025/306/

- Related scope: Update Groups, long body/representable updates, cause/effect.
- Verification record: 2026-09-23 / inherited-v1.0.0; this revision does not claim a complete re-verification

## A03 — Apple: Swift concurrency behind the scenes (WWDC21)

https://developer.apple.com/videos/play/wwdc2021/10254/

- Related scope: cooperative execution, actors, thread pools. Also check A04 for new isolation settings.
- Verification record: 2026-09-23 / inherited-v1.0.0; this revision does not claim a complete re-verification

## A04 — Swift.org: Swift 6.2 Released

https://www.swift.org/blog/swift-6.2-released/

- Related scopes: default isolation, NonisolatedNonsendingByDefault, @concurrent. Check your recruitment settings.
- Verification record: 2026-09-23 / inherited-v1.0.0; this revision does not claim a complete re-verification

## A05 — Apple: UI animation hitches and render loop

https://developer.apple.com/videos/play/tech-talks/10855/

- Related scope: iOS-based commit/render hitches and render servers. Do not generalize to a fixed configuration for all OSs.
- Verification record: 2026-09-23 / inherited-v1.0.0; this revision does not claim a complete re-verification

## A06 — Apple: Improving Animation Performance

https://developer.apple.com/library/archive/documentation/Cocoa/Conceptual/CoreAnimation_guide/ImprovingAnimationPerformance/ImprovingAnimationPerformance.html

- Related scope: Core Animation archive materials. Concepts of layer, shadow, and drawing cache.
- Verification record: 2026-09-23 / inherited-v1.0.0; this revision does not claim a complete re-verification

## A07 — Apple: Track down hangs with Xcode and on-device detection (WWDC22)

https://developer.apple.com/videos/play/wwdc2022/10082/

- Related scope: Hang detection, sample and actual observation.
- Verification record: 2026-09-23 / inherited-v1.0.0; this revision does not claim a complete re-verification

## A08 — Apple: Optimize CPU performance with Instruments (WWDC25)

https://developer.apple.com/videos/play/wwdc2025/308/

- Related scope: CPU profiling, examining execution costs.
- Verification record: 2026-09-23 / inherited-v1.0.0; this revision does not claim a complete re-verification

## N01 — Microsoft: Windows app performance overview

https://learn.microsoft.com/en-us/windows/apps/develop/performance/

- Related scope: Release, representative terminal, cold/warm, and re-measurement of actual operation.
- Verification record: 2026-09-23 / inherited-v1.0.0; this revision does not claim a complete re-verification

## H01 — Prioritized Task Scheduling — WICG draft

https://wicg.github.io/scheduling-apis/

- Related scope: collaborative task scheduling, priority, TaskController, yield. This is a Community Group draft and is not guaranteed to be compatible with all browsers.
- Confirmation record: 2026-09-23 / v1.1.0: relevant sections opened and checked

## H02 — HTML — Safe passing of structured data

https://html.spec.whatwg.org/multipage/structured-data.html

- Relevant scope: Structured clone, transfer steps, distinction between ArrayBuffer detach and shared memory.
- Confirmation record: 2026-09-23 / v1.1.0: relevant sections opened and checked

## H03 — Indexed Database API — living editor draft

https://w3c.github.io/IndexedDB/

- Relevant scope: transaction lifecycle, active/inactive, commit/durability hints, versionchange/blocked/upgrade.
- Confirmation record: 2026-09-23 / v1.1.0: relevant sections opened and checked

## H04 — React — useMemo

https://react.dev/reference/react/useMemo

- Related scope: Dependent comparison Object.is, cache of calculation results. It is not a structured clone or state persistence.
- Confirmation record: 2026-09-23 / v1.1.0: relevant sections opened and checked

## H05 — WHATWG File System standard

https://fs.spec.whatwg.org/

- Related scope: OPFS, FileSystemSyncAccessHandle and DedicatedWorker exposure, close/flush.
- Confirmation record: 2026-09-23 / v1.1.0: relevant sections opened and checked

## H06 — WHATWG Storage standard

https://storage.spec.whatwg.org/

- Related scopes: storage key, quota/estimate, persistence and eviction. It is not a fixed capacity or backup guarantee.
- Confirmation record: 2026-09-23 / v1.1.0: relevant sections opened and checked

## H07 — Web Locks API — editor draft

https://w3c.github.io/web-locks/

- Associated scope: lock manager corresponding to storage bucket, exclusive within the same scope, request lifetime. Not server authorization.
- Confirmation record: 2026-09-23 / v1.1.0: relevant sections opened and checked

## H08 — Service Workers — editor draft

https://w3c.github.io/ServiceWorker/

- Related scopes: event-driven lifetime, termination, registration/scope, update. It is not a resident daemon.
- Confirmation record: 2026-09-23 / v1.1.0: relevant sections opened and checked

## H09 — ECMAScript — Memory model

https://tc39.es/ecma262/multipage/memory-model.html

- Related scope: shared data, atomic ordering, data race. Distinguish between specification draft and target engine implementation.
- Confirmation record: 2026-09-23 / v1.1.0: relevant sections opened and checked

## H10 — ECMAScript — Structured data and Atomics

https://tc39.es/ecma262/multipage/structured-data.html

- Related scope: Atomics, wait/notify and AgentCanSuspend. Notifications are not a substitute for state predicates.
- Confirmation record: 2026-09-23 / v1.1.0: relevant sections opened and checked

## H11 — web.dev — Making your website cross-origin isolated using COOP and COEP

https://web.dev/articles/coop-coep

- Related scope: Deployment conditions for cross-origin isolation and its impact on other origin resources and window relationships.
- Confirmation record: 2026-09-23 / v1.1.0: relevant sections opened and checked

## H12 — HTML — Web workers

https://html.spec.whatwg.org/multipage/workers.html

- Related scope: Dedicated/Shared Worker, lifetime, context, message routing. There is no one-to-one guarantee for tab/process.
- Confirmation record: 2026-09-23 / v1.1.0: relevant sections opened and checked

## H13 — AWS Builders Library — Making retries safe with idempotent APIs

https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/

- Related scope: caller request ID, timeout ambiguity, semantic equivalence, dedup record and mutation atomicity.
- Confirmation record: 2026-09-23 / v1.1.0: relevant sections opened and checked

## H14 — WHATWG WebSockets standard

https://websockets.spec.whatwg.org/

- Relevant scope: send/readyState/bufferedAmount, distinction between send queue and application-level ACK.
- Confirmation record: 2026-09-23 / v1.1.0: relevant sections opened and checked

## H15 — Apple Core Data Programming Guide — Concurrency (archived)

https://developer.apple.com/library/archive/documentation/Cocoa/Conceptual/CoreData/Concurrency.html

- Relevant scope: context queue confinement, perform, object ID, child and parent save. Check the current API with the target SDK as it is an archive.
- Confirmation record: 2026-09-23 / v1.1.0: relevant sections opened and checked

## H16 — Microsoft.Data.Sqlite — Async limitations

https://learn.microsoft.com/en-us/dotnet/standard/data/sqlite/async

- Related scope: SQLite's ADO.NET async methods perform synchronous execution. Reflect provider-specific constraints in UI design.
- Confirmation record: 2026-09-23 / v1.1.0: relevant sections opened and checked

## H17 — System.Threading.Channels library

https://learn.microsoft.com/en-us/dotnet/core/extensions/channels

- Related scope: Wait/DropNewest/DropOldest/DropWrite and producer backpressure for bound channels.
- Confirmation record: 2026-09-23 / v1.1.0: relevant sections opened and checked

## H18 — Qt 6 — QSqlDatabase

https://doc.qt.io/qt-6/qsqldatabase.html

- Relevant scope: database connection thread membership, transaction, moveToThread constraints since Qt 6.8.
- Confirmation record: 2026-09-23 / v1.1.0: relevant sections opened and checked

## H19 — SQLite — Write-Ahead Logging

https://www.sqlite.org/wal.html

- Related scope: concurrent reader/single writer, checkpoint, busy, WAL lifetime and operational assumptions.
- Confirmation record: 2026-09-23 / v1.1.0: relevant sections opened and checked

## H20 — SQLite — Atomic Commit In SQLite

https://www.sqlite.org/atomiccommit.html

- Relevant scope: transaction atomicity and filesystem/hardware/flush assumptions. OS process kill and power loss are not the same.
- Confirmation record: 2026-09-23 / v1.1.0: relevant sections opened and checked

## H21 — React — useSyncExternalStore

https://react.dev/reference/react/useSyncExternalStore

- Related scope: external store subscription, cached immutable snapshot, Object.is and SSR snapshot consistency.
- Confirmation record: 2026-09-23 / v1.1.0: relevant sections opened and checked

## H22 — React — You Might Not Need an Effect

https://react.dev/learn/you-might-not-need-an-effect

- Related scope: States and event processing that can be derived by render, reduction of unnecessary Effect chains.
- Confirmation record: 2026-09-23 / v1.1.0: relevant sections opened and checked

## H23 — SQLite Wasm — Persistent Storage

https://sqlite.org/wasm/doc/trunk/persistence.md

- Related scope: VFS types, locking, worker/backend constraints for OPFS. OPFS itself is not called a SQL engine.
- Confirmation record: 2026-09-23 / v1.1.0: relevant sections opened and checked

## H24 — web.dev — The service worker lifecycle

https://web.dev/articles/service-worker-lifecycle

- Related scope: install/waiting/activate, coexistence with old clients, and cautions about skipWaiting.
- Confirmation record: 2026-09-23 / v1.1.0: relevant sections opened and checked

## H27 — High Resolution Time Level 3 — Working Draft

https://www.w3.org/TR/hr-time-3/

- Relevant ranges: timeOrigin and performance.now, time reference between context, coarsening. Direct connection with server clock is not possible.
- Confirmation record: 2026-09-23 / v1.1.0: relevant sections opened and checked

## H29 — Swift evolution SE-0306 — Actors

https://raw.githubusercontent.com/swiftlang/swift-evolution/main/proposals/0306-actors.md

- Relevant scope: reentrancy across actor isolation and await. A separate contract from thread affinity and transaction isolation.
- Confirmation record: 2026-09-23 / v1.1.0: relevant sections opened and checked
