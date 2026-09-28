# Windows profiling runbook

## 1. Inventory / Secure Recording

Record Windows build, WinAppSDK/.NET/architecture, packaging, Release/symbol, GPU/driver, DPI/refresh, power, RDP/VM. Do not decide whether to accept or reject an application based solely on the debug run within Visual Studio. [N01]

Check available tools such as PowerShell. Below is an example of discovery, which prioritizes output and installed help.

```powershell
Get-Command wpr, wpa, dotnet -ErrorAction SilentlyContinue
wpr -status
wpr -profiles
dotnet --info
dotnet-trace --help
```

If a session of another person/other tool is running in WPR, `-cancel` will not be executed without permission. Only if you can start a new session as your own, select the corresponding profile and perform a short playback operation. [N10]

```powershell
# Example when GeneralProfile is enumerated and it is confirmed that there is no impact on existing sessions
wpr -start GeneralProfile -filemode
# Execute the target scenario once in a separate window
wpr -stop .\perf\baseline.etl
```

Create the output destination in advance and do not overwrite existing ETL. Do not assume that the GeneralProfile includes all required XAML/GPU providers. If the authority is insufficient, use a limited scope/existing trace instead, and do not automatically make the administrator an administrator. [N09][N10]

## 2. Symptom → tool

| symptoms| First candidate| Limit/Additional|
|---|---|---|
| UI CPU occupancy| WPA CPU Usage, Visual Studio CPU profile | symbols and corresponding PID/TID, both managed/native|
| UI waits| WPA thread/scheduling/wait analysis|sample It may not be possible to see the wait destination using just the CPU.|
| WinUI layout/frame | Supported WPA XAML Frame Analysis| Check the prerequisites of ADK/plugin/provider|
| WPF binding/list | WPF compatible CPU/managed/UI measurement| Actual observation of virtualization state and container generation|
| .NET GC/allocations | dotnet-trace / VS memory etc.| Don't confuse EventPipe with ETW/GPU|
| GPU/present/DWM | graphics related ETW/compatible tools| toolkit ownership, display mode, RDP differences|
| startup/I/O | ETW/CPU/I/O for cold/warm startup| Define boundaries from PID generation to operability|

If you need a XAML table, check the ADK and `perf_xaml.dll`/WPA settings using Microsoft's current procedures. When editing global settings such as `perfcore.ini`, propose and approve first, and prepare backup/rollback. Cannot be rewritten automatically. [N11]

## 3. Example of adding only Managed CPUs

```powershell
dotnet-trace ps
dotnet-trace collect --help
# Only if the corresponding profile is in help. Replace with real PID.
dotnet-trace collect --process-id <PID> --profile cpu-sampling --output .\perf\managed.nettrace
```

`<PID>` is a placeholder and will not be executed as is. Check the profile name and duration/stop method of the version you are using, and end only the recording that you started. Since it is not possible to obtain complete allocation/GC details with CPU sampling alone, necessary providers will be added in a separate experiment. [N12]

## 4.Timeline survey

Record the relationship between input reception, worker enqueue/start/end, Dispatcher enqueue/apply, and frame using an anonymous operation ID. Separate the time the queue was placed and the time the callback was executed. Do not block the UI with large amounts of log output.

In WPA, select the operation section and narrow it down to process→thread→stack. Check CPU calculation, lock/I/O wait, GC, layout/binding, UI callback burst, composition/present. Do not add nested duration as total CPU time. [N01][N09]

Do not apply WPF-specific tables or UWP-specific APIs to WinUI. If the stack cannot be read, report the fact that symbol path/build support is insufficient. [N02][N06][N11]

## 5.Before/after and validation

Measure alternately with the same machine, Release, DPI/refresh, power, dataset, cache, and capture settings. Apart from functional tests, check IME, keyboard, UI Automation, selection, multiwindow, resize/DPI change, and task completion while closing the window.

Check whether input-to-result or display latency is worsening even if frame throughput is good. The results reproduced with RDP/VM/software rendering are limited to that range and are not mixed with the results of physical GPU. [N01][N13]


## v1.1.0: Preservation and cross-boundary trace

Assign a correlation ID to each operation and distinguish between queued/start/end, reply, UI apply, local commit, and server ACK. Name only the observed end point without directly subtracting values with different clock domains. [H27]

Add message count/bytes, pool startup, queue age/peak, Outbox pending/retry/conflict, transaction wait and commit, and callback discard counts as necessary. Avoid logging large raw payloads. Associate the observation conditions of [boundary contract](boundaries-and-protocol.md) and the injection points of [fault tests](failure-injection.md) to the same report.

Maintain the old version's metrics and compare separately the faster optimistic display and the faster completion of actual results and saves. If actual machine/fault injection has not been executed, do not set G6 to pass.
