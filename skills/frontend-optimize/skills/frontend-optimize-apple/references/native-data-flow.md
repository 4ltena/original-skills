# Apple: domain / executor / save / scene lifecycle

This section is not a direct copy of the browser design from the lecture to Apple, but an extension of it with the addition of primary Apple/Swift materials. Apply [boundary contract](boundaries-and-protocol.md) and [durability and recovery](durability-and-recovery.md) and check the actual SDK, Swift mode, and framework.

## 1. UI lifetime and domain lifetime

Separate SwiftUI/AppKit/UIKit UI state, domain state, persistent store, and sync owner. Check whether the entire dataset/index/task is recreated every time the view is regenerated. If the design is such that the save disappears when the UI-owned task is destroyed, redesign the save owner and receipt path.

UI reflection returns to the appropriate MainActor/UI context, but domain updates and DB commits do not depend on the existence of the view. For results that arrive after the scene/window is closed, check the lifetime token/entity revision and stop only unnecessary drawing. Don't assume that a business operation that has already been committed is canceled just because the screen has disappeared.

MainActor's task, actor, GCD queue, and OS thread are not synonymous. The syntax `Task {}` or `async` alone does not determine that it has been saved from main. Check whether Swift 6.2's default isolation/nonisolated async settings and `@concurrent` can be adopted in the target toolchain. [A03][A04]

## 2. Separate Actor seriality and transaction

Actor isolation is a boundary to prevent data races, but it does not guarantee that the entire process that spans `await` will not be interrupted by other actor processes. When returning from external I/O, reconfirm entity/baseRevision/account/ permissions. [H29]

```text
read revision r / prepare immutable request on actor side
await external work
Return to actor
  current revision == r ? validate and commit : retry/merge/reject by domain rule
```

This is an example, not a transaction API for any actor. Do not overwrite amounts/inventory etc. based on stale snapshot. Design DB transaction and actor isolation separately, and do not stop UI or cooperative executor with lock/transaction with network wait. [A03][H29]

Adding a cancel flag and a throw does not necessarily undo completed external side effects. Record the state of commit before and after cancel. [H13]

## 3. Core Data / SwiftData / SQLite

Enumerate the stores used first. Instead of passing Core Data's managed object directly to a queue in another context, use the context's perform API, object ID, or immutable DTO. Check the temporary ID and persistent ID, resolve in another context, and merge policy. [H15]

When saving the child context, we distinguish between reflecting it on the parent and writing it to the persistent store. Define which root context/store save completion will be displayed as `locally saved`, and also notify the UI and recovery of parent save failure. Do not call save API success as server ACK. [H15]

When using SwiftData's ModelContext/ModelActor, check the isolation, generation context, autosave, explicit save, and migration API of the target SDK. This skill does not mechanically apply Core Data's API to SwiftData. Prohibit the conclusion that only annotation or autosave is "background and durable."

If you use SQLite directly, check the connection ownership, transaction, busy, WAL/checkpoint, and synchronous/durability policy of driver/wrapper. Do not perform WAL conversion or flush omission as an unconditional speed increase. [H19][H20]

Simply saving the UI's local state and Outbox independently to separate persistent stores is not atomic. If necessary, design it as a record/log within the same transaction, and also match server receipt reflection and pending operation completion. Apply A to E of [Permanent contract](durability-and-recovery.md).

## 4. Cost of returning domain updates to UI

Even if domain computation moves to the background, it may get stuck due to copying all snapshots, notifying MainActor, SwiftUI dependency fan-out, and huge apply to diffable data source. Measure request/reply/apply/commit with the same correlation. [A01][A02]

Consider small results/diffs with revisions, appropriate batches, and visible ranges. However, stable identity, selection, scroll position, undo, and accessibility are maintained. Test that the core data notification merge and UI snapshot revision do not differ.

Put limits on CPU concurrency, prepared images, decoded bytes, and pending UI apply. Do not uniformly increase QoS. Do not increase task/actor generation indefinitely in proportion to the number of inputs, and separate merging policies between queries and durable commands. [A03]

## 5. Scene / app lifecycle / migration

Don't assume that the view task will continue, that the app will run indefinitely in the background, or that you can always flush it with a termination notification. Check the OS lifecycle API used and the behavior of the actual machine, and have a contract that allows you to recover unsynchronized operations after restarting. This section does not cover the specific conditions for background execution that the OS allows.

When multiple scenes/windows, app extensions, or different processes touch the same store, check the simultaneous execution of writer scope, lock, migration, and restart of old processes. A single actor in memory is not called a lock that covers another process. Server synchronization handles account scope, credential expiration, and duplicate receipt.

Migration tests the old model/new model, disk shortage, forced termination, and whether or not rollback is possible according to the migration method of the target store/framework on the test DB. Do not add automatic recovery to clear unsynchronized stores.

## 6. Measurements and required tests

Record `input / queued / domain-start-end / store-commit / sync-send / server-ack / main-apply` separately in Instruments/Signpost. Check each interval of store waiting, MainActor occupied, notification fan-out, and Core Animation commit/render. Distinguish between the word render commit and DB commit in the log. [A02][A05]

Minimum applicable set: late reply + view discard (F01/F03), before and after commit and ACK loss (F04-F07), save failure (F08), multi-scene/migration (F09/F10), backgrounding/returning and resource (F12). Changes that do not touch server/store can be reduced with a reason.

Report simulator, mock DB, static actor analysis, unit test, and actual instrument as additional evidence. It is not treated as if this package executed them.
