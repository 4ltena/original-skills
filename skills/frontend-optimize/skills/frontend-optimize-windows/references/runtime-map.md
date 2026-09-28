# Windows runtime: from Dispatcher to display

## 1. Differentiate between toolkits

WinUI3, WPF, WinForms, Win32, Qt, Electron are not the same runtime. Check the following main routes using the actual application. WinUI3's DispatcherQueue is `Microsoft.UI.Dispatching`, and UWP-derived CoreDispatcher etc. are different APIs. [N02][N03][N06]

| Executor| main job| Bottleneck candidate|
|---|---|---|
| UI thread / message loop / Dispatcher | input, UI state, XAML/WPF layout, binding, managed/native callbacks | long handler, sync wait, queue flooding, layout invalidation |
| .NET tasks / ThreadPool | Jobs related to CPU jobs, async continuation, and I/O completion| starvation, excess tasks, lock, GC allocation, blocking|
| app worker / I/O | parse/index/database/file/network |queue/serialization, blocking API, lock, completion notification burst|
| WPF render thread | Another stage of prepared rendering| Waiting for update from UI, render resource|
| Windows composition / DirectComposition | Visual tree composition and asynchronous animation path| commit, surface update, effect, dependence|
| DWM / GPU scheduling / display | desktop synthesis, GPU execution, present| GPU queue, composition, refresh, latency to actual display|

The execution context and the number of OS threads are not 1:1. Even if WPF has a render thread, the layout, binding, and input on the Dispatcher can get clogged. Even if the animation using composition is smooth, it does not necessarily mean that the business input is responsive. [N06][N04][N05]

## 2. async / Task / Dispatcher

I/O-bound uses available async I/O. CPU-bound synchronous computations are candidates for appropriate worker designs such as `Task.Run`. However, check the processing amount, copy, concurrency, and cancel. The `async` qualification alone does not move the CPU calculation to another thread. [N03]

If you perform synchronous waits such as `.Result`/`.Wait()` on the UI, you can create mutual waits with work waiting for continuation delivery to the UI. Also check the dependencies of synchronous waits such as `Dispatcher.Invoke`. Just adding `ConfigureAwait(false)` does not eliminate thread affinity for UI operations. [N06][N03]

Do not change UI-owned collection/control directly from workers. Returns to the appropriate Dispatcher upon completion, and handles cancel, error, and old request results after the window closes. A design that posts 10,000 results to a queue 10,000 times creates a new queue delay after moving the UI calculations. [N02][N03]

## 3. Binding / layout / virtualization

Binding resolution, property notification, collection notification, template generation, and measure/arrange have different costs. Separate whether changing a single value leads to regenerating the entire list or requires multiple passes of layout. [N07][N08]

WPF's UI virtualization is to narrow down the generation of display containers, and is different from data virtualization, which avoids loading/parsing the entire data. UI virtualization can be invalidated by panel, scroll settings, how to specify containers, etc. Recycling involves resetting the state. [N07]

WinUI's binding/virtualized control checks the contract of the target WinAppSDK version. Do not port WPF's `VirtualizingStackPanel` countermeasures to WinUI as is. For mass notifications, design differences, batches, and upper limits so that the UI does not stop with a single huge batch. [N03][N11]

## 4. Composition / GPU / present

DirectComposition can execute visual composition asynchronously. The UI side layout/CPU work does not move automatically. Separately record the owners of WPF rendering, WinUI composition tree, and original DXGI swapchain. [N04][N05][N06]

DXGI's flip model and queue control can be considered if the application manages the swapchain legitimately. Do not arbitrarily replace present inside the toolkit. If you maximize only throughput and increase the frame queue, you will lose the evaluation of latency from input to display. Specify whether submitted, rendered, or displayed is being measured. [N13]

## 5. .NET observation and OS observation are different

dotnet-trace by EventPipe is a tool to check CPU/GC etc. of managed runtime, and it does not check all system-wide thread scheduling and DWM/GPU of ETW in the same way. Check the providers/events actually included in both captures. [N09][N12]

Long intervals with few CPU samples are not "costless", but are candidates for wait/lock/I/O, another process, or missing symbols. Separate the UI wall time and CPU running time. [N01][N09]

## 6. Version boundaries

Microsoft's explanation of WinUI performance profiling requires ADK 10.1.26100.1 or later for WPA's XAML Frame Analysis. Check the installation version and plugin settings. Agents should not claim to have viewed tables that do not exist in older ADKs. [N11]

The number of UI threads and the lifespan of the Dispatcher for each window also depend on the application design. Verify ownership during multiwindow without easily sharing objects belonging to different Dispatchers. [N02]


## v1.1.0: Execution context and storage responsibility

Don't finish the list of runtimes by memorizing the number of threads, use [boundary protocol](boundaries-and-protocol.md) to record who owns the state, which queue to enter, and when to apply/commit the result. Shared memory, actors, dispatchers, and DB transactions have different guarantees.

Apply [platform-specific data flow](native-data-flow.md) and [durability and recovery](durability-and-recovery.md). Do not make the lifecycle of the UI and the lifecycle of durable domain operations the same. Parts where the process/thread placement is unknown are clearly marked as estimated.
