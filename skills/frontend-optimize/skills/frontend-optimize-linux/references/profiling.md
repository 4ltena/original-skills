# Linux profiling runbook

## 1. Detect the environment

Record `uname`, OS release, toolkit build information, session type, desktop/compositor, GPU/driver, backend, scale/refresh, and Release build and symbols. Environment-variable dumps can include tokens or secrets; read only the fields needed.

```sh
uname -sr
printf 'session=%s\n' "$XDG_SESSION_TYPE"
command -v perf
command -v sysprof-cli
perf version
sysprof-cli --help
```

Treat a missing command as uninstalled. Do not automatically install packages, escalate to root, or change global settings. XDG variables alone do not prove the backend used by every window; check the target app for mixed XWayland and native windows. [L11][L15]

## 2. Investigate Qt

Use a compatible QML Profiler in Qt Creator or another suitable tool to align QML/JS, bindings, signals, and delegate/object creation with the user action. Combine render-loop/backend information with render and synchronization tracks to separate GUI and rendering costs. [L01][L02]

Use process-scoped diagnostics such as `QSG_INFO=1` only after checking their meaning and availability in the running Qt version's documentation. Forcing `QSG_RENDER_LOOP` or another backend is a diagnostic A/B experiment, not an automatic permanent fix. Confirm the variable and value exist in the version in use. [L01][L04]

QML profiling settings or debugging services may add overhead even in Release builds. Do not ship unnecessary debug features; decide performance with measurements under matched conditions. [L02]

## 3. Investigate GTK

Align Sysprof's GTK/GDK/GSK frame information with CPU activity. Available marks depend on GTK and Sysprof versions, build options, and capture features; an empty track does not mean zero cost. Separate main-context dispatch, layout, snapshot, and rendering. [L09][L06][L14]

Check GTK Inspector, `GSK_RENDERER`, and other debugging features against the running GTK version's documentation. Available backends depend on build and driver. Keep comparisons process-scoped; do not assume Vulkan, OpenGL, or CPU rendering is always fastest. [L10]

## 4. Example CPU sampling

Example for a short action in a process you start:

```sh
# Confirm support with perf record --help. Do not overwrite an existing output file.
perf record -F 99 --call-graph dwarf -o ./perf/baseline.perf.data -- ./your-app
perf report --stdio -i ./perf/baseline.perf.data
```

Replace `./your-app` with the target executable. End the foreground app or only the capture you started. 99 Hz is an exploratory example, not a standard. Account for missed short functions, unwind cost, symbols/inlining, and sampling overhead. [L13]

If DWARF unwinding costs too much, compare frame pointers or another method suitable for the build and architecture. Check ownership and permission before attaching to an existing PID. Do not lower `perf_event_paranoid` or run the app as root merely to make profiling work. If access is missing, use the toolkit profiler, lightweight app markers, or existing traces and state the observation gap. [L15]

## 5. Waiting, compositor, and GPU

When input is slow but a CPU flame graph shows little cost, investigate queues, locks, I/O, GUI–render synchronization, GPU, and compositor. Capture off-CPU, scheduling, or GPU events separately with tools and permissions that support them; do not invent wait targets from a CPU profile. [L01][L09][L13]

State whether evidence reaches the Wayland frame callback, client submission, GPU completion, or actual presentation. Measurements across processes with different clocks need calibration or a shared clock. Headless/Xvfb may test some functional and CPU regressions, but cannot replace a real desktop for presentation or energy decisions. [L11][L12]

## 6. Remeasure and check the release path

Compare before and after with the same backend, compositor, scale/refresh, driver, power state, dataset, symbols, and instrumentation. If representative Wayland/X11 or GPU configurations differ, measure them in separate columns. Separate comparisons if a global backend change mixed baseline and candidate conditions.

Check IME, keyboard, accessibility, selection, window moves/resizes, scaling, background/resume, long-session memory, and idle wakeups. Verify the gain remains during normal launch without Qt/GTK diagnostic flags. [L02][L07][L10]

## v1.1.0: Trace across persistence and execution boundaries

Assign a correlation ID to each operation. Distinguish queued/start/end, reply, UI apply, local commit, and server ACK. Do not subtract timestamps from different clock domains directly; name only observed endpoints. [H27]

As needed, add message counts/bytes, pool startup, queue age and peak, pending/retry/conflict Outbox counts, transaction wait and commit, and discarded callbacks. Avoid logging large raw payloads. Match the [boundary contract](boundaries-and-protocol.md) observations and [fault tests](failure-injection.md) injection points in the same report.

Preserve earlier measurement metrics. Compare faster optimistic feedback separately from completion of the real result or save. Do not mark G6 `pass` if representative-device or fault tests are unrun.
