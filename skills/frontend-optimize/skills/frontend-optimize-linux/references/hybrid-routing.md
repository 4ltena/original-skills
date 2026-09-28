# Hybrid / cross-platform routing

This is not an additional fifth skill. Combine host OS skills and actual drawing runtime skills to the extent necessary. Don't decide the route based only on the product name or language name. [C06][C08][C09][C10]

## first determination

| configuration| Boundary to be observed| material to read|
|---|---|---|
| Electron | renderer web work, main Node/I/O, IPC, Chromium/GPU, OS compositor| webapp + host OS profiling|
| Tauri | WebView DOM/JS, IPC encode/decode, Rust side task/lock/I/O, host WebView/GPU| webapp + host OS|
|Embed WKWebView/WebView2/WebKitGTK| host↔web message, web side drawing, host UI, engine process| web tools + host profiler that matches the engine|
| Qt Quick / Qt Widgets | QML/model/GUI/scene graph or Widgets paint, OS compositor| Qt runtime documentation + host OS|
| Flutter | framework build/layout/paint, raster, isolate, platform channel, embedder | Flutter DevTools + host OS|
| Avalonia etc. unspecified toolkit| managed runtime, dispatcher, renderer, platform backend | Additional investigation of official runtime materials for target version + host OS|

Tauri uses WebView2 for Windows, WKWebView for Apple, and WebKitGTK for Linux. Don't judge the completion of the entire OS just by opening the Tauri screen in Chrome. Also record the conditions under which the WebView runtime changes due to OS updates or separate distribution. [C08][C09]

In Electron, the main process can be responsible for all windows. Don't move heavy processing from the renderer to main and stop all windows. Distinguish between main/renderer/worker and measure copy, serialization, and callback delivery between processes. Don't remove sandbox, context isolation, and IPC verification for performance. [C06][C07]

## Boundary-spanning measurement contracts

1. Assign an anonymous operation ID to the scenario and use the same ID for web reception, host reception, host completion, web application, and drawing. Do not input user input string to trace.
2. Do not assume that clocks of different processes/runtimes have the same epoch/precision. If a common tracing clock cannot be used, measure the within-boundary duration and round-trip, and do not call the uncalibrated time difference one-way latency.
3. Separate bytes, number of messages, queue depth, processing time, and result application time. The design of repeatedly sending a huge full-state snapshot of JSON makes differences, typed buffers, and batch a control experiment.
4. Provide request ID/generation, cancel, finite queue, error, and shutdown for concurrent requests. Even if the calculation is sent to a separate process, the huge UI application of the result remains.
5. Rust's async tasks and Node's async functions are also not places where you can process unlimited CPU-bound processing. Check the rules for the executor and blocking pool in the target runtime official documentation and make it bounded.

Clock alignment and IPC expansion for testing are measurement designs of this skill, and are not guaranteed to be provided automatically by each runtime.

## Exceptions in Flutter and other toolkits

Flutter does not assume DOM. First determine which of the build/layout/raster is losing budget in profile mode and on the actual machine. The arrangement of platform/UI threading can change depending on the version/embedder, so it is not fixed as "always 4 independent threads". Isolate movement has message/copy, and native and web `compute` are not treated as the same offload guarantee. [C10][C11]

Qt Quick's scene graph and Qt Widgets are separate routes. WinUI/SwiftUI-specific optimizations are not applied even if Qt is running on Windows/macOS. When using a skill alone that does not come with Qt materials, obtain Qt official runtime materials to supplement the hypothesis.

## Scope / escalation

This package does not exhaustively cover all toolkits for each OS. The main routes are Web, SwiftUI/AppKit/UIKit, WinUI3/WPF, Qt6/GTK4. For the game engine, WebGPU dedicated renderer, XR, real-time audio, and original window system, we even perform boundary diagnosis, and create additional procedures using the primary materials of the render loop, device, and audio API we own. Don't fill unknown routes with similar toolkit specifications.
