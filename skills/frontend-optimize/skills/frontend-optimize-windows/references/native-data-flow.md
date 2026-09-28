# Windows: Dispatcher / bounded work / save / multi-window

Extend the local-first/boundary design from the lecture to actual contracts for WinUI 3, WPF, and .NET. Do not simply replace Web Worker and Task, DOM and XAML. [boundary contract](boundaries-and-protocol.md) and [durability and recovery](durability-and-recovery.md) are the common parts.

## 1. UI enqueue and business completion

Illustrates the Dispatcher/DispatcherQueue, domain owner, DB writer, and sync owner for each window. Successful enqueue to UI does not mean UI drawing is completed or DB saving is successful. Define another storage destination where domain results and saved receipts will not be lost if the queue does not accept them due to shutdown. [N02][N06]

The late callback checks the window lifetime/entity revision and stops updates to the disposed object. Don't wait synchronously for results from the UI in `.Wait()`/`.Result`. When updating the UI binding/model, follow the framework's thread rules and collect large amounts of per-item notifications into bounded batches. [N03][N06][N08]

Do not capture to Task.Run without checking thread requirements such as COM/apartment, UI object, driver connection, etc. Make CPU work, OS asynchronous I/O, synchronous provider calls, and UI apply separate execution categories.

## 2. Bounded Channels are admission control, not storage.

When using System.Threading.Channels, specify bound capacity and full mode. `Wait` and `DropNewest/DropOldest/DropWrite` have different meanings. Don't silently discard outstanding operations by using drop mode for editing/save. Do not block free waiting on the UI. [H17]

Entering a channel, reading by a consumer, committing a transaction, and receiving server ACK are made into separate states. The in-memory channel is not a durable queue that guarantees recovery in the event of a process crash.

Capacity is determined not only by items but also bytes, inflight, and completed UI notifications for each payload. If you generate an unlimited number of writer tasks for each input and place them in the WriteAsync queue, you can create an endless backlog outside the channel body. Set an upper limit from producer admission.

The candidate for query is latest-wins, and for durable command, use batch or explicit backpressure that preserves the meaning. Distinguish between `CancellationToken` being notified and processing/side effect being stopped.

## 3. Microsoft.Data.Sqlite and other providers

**Microsoft.Data.Sqlite's async ADO.NET methods are executed synchronously**, which is a provider-specific restriction. Don't draw a conclusion unless you stop the UI with just a name like `ExecuteReaderAsync`. Match the description of the target package/version with the trace. [H16]

If the synchronous DB call is a hot path, consider a properly owned bounded DB execution path. Do not share connections/transactions randomly from multiple tasks. Execute the entire transaction in the same ownership/exclusion unit and do not include network await. The DB owner here is a design responsibility and does not mean that all providers necessarily require a dedicated OS thread.

On the other hand, all providers that provide true async I/O are not wrapped in Task.Run. Measure where the ORM/driver, materialization, change tracking, serialization, and binding notifications are occupied. We will also consider the possibility of improving the index/query of SQL itself first.

WAL can change reader/writer waits, but it is not a solution to increasing the number of writers indefinitely. Check checkpoint, long read, SQLITE_BUSY, disk capacity, and durability settings. Do not weaken journal/synchronous etc. arbitrarily. [H19][H20]

## 4.Local-first and ACK

If necessary, make local domain updates and Outbox inserts the same transaction. Decide what should be committed before passing it to a new task/channel, and when should it be marked as saved in the UI. Do not treat WebSocket/TCP send or HTTP reception as authoritative ACK. [H13][H14]

ACK processing checks operationId/intent/account and receipt and updates confirmed revision/Outbox completion to atomic. Test retransmission and deduplication when the server is disconnected after application. Even if notification to the view model fails, the success or failure of the save itself can be tracked independently.

When using file storage instead of DB, check the API contract for temporary write/replace/flush/backup on the target filesystem. Write completion should not be interpreted as rename atomicity, and atomic replace should not be interpreted as power-loss resistance. Do not treat updates of multiple files as the same as one DB transaction. [H20]

## 5. Process lifecycle/migration

Distinguish between the same multi-window process and different processes that open the same store. In-process channel/lock does not exclude other processes. Lists the migration writer, old binary restart, store read/write compatibility, and whether or not rollback is possible.

Don't assume that all pending operations will be flushed in the exit callback, but instead allow saved operations to be retrieved on restart. Separate the upper limit of drain during graceful shutdown and the range guaranteed by interrupt termination. When credentials expire or account is switched, do not send old pending information to another account.

UI callback detects DispatcherQueue shutdown and cancels updating only the closed window. Do not delete the save error as "Successful because there is no window". Next, consider designing a recovery notification to be displayed at a time when there is an appropriate UI. [N02]

## 6. Measurement/falsification/testing

Measure UI, I/O, and thread wait with WPR/WPA/ETW and managed allocation/task with EventPipe/.NET profiler as needed, and map them to the same operation. Check the tool's clock and capture scope, and don't pull irrelevant timestamps directly. [N09][N12]

Disassemble `channel wait -> DB execution -> commit -> sync -> receipt -> dispatcher enqueue -> UI apply` and check whether the binding/layout after exporting the DB is a new bottleneck. XAML Frame Analysis adheres to existing ADK/tool assumptions. [N11]

Applicable tests: saturation/drop (F02), window shutdown/cancel (F03), crash/ACK loss (F04~F07), busy/full/permission (F08), multi-process upgrade (F09/F10), resource/long time (F12). Do not report that durability was confirmed only by mock channel test.
