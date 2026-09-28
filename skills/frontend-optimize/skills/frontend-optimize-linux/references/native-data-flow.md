# Linux: Qt/GTK domain/storage/process boundaries

A section that expands the browser-centered principles of the lecture to suit the conventions of the target toolkit/driver. Identify Qt Quick/Widgets, GTK, and Wayland/X11 first. [boundary contract](boundaries-and-protocol.md) and [durability and recovery](durability-and-recovery.md) are the common parts.

## 1. UI callback and domain owner

Distinguish between Qt's QObject affinity, model mutation, and queued signal and GTK's UI thread/GMainContext/GTask completion. Even if you put heavy computation into the idle callback, it will not become a background worker. Do not change the UI model directly from the worker. [L03][L05][L08]

Determine whether the owner of the database/index/operation log needs to be kept alive longer than the view, and use safe lifetime references and revisions for replies after the window is destroyed. Ignoring callbacks, stopping calculations, and canceling saves are separate contracts.

Do not generate unlimited Qt signals or GTasks for each item. Bound the producer side admission control, inflight count/bytes, and the amount of difference applied to the UI. Avoid structures in which both sides wait with GUI↔worker synchronous calls or blocking queued connections, and check the actual queue/lock with trace. [L03][L08]

## 2. Thread belonging to Qt SQL connection

Specify the thread/context that uses QSqlDatabase. Even if you create a value copy pointing to the same connection, it will not become an independent connection for another thread. The thread-safe setting of the SQLite engine itself does not eliminate the affinity rules on the Qt side. [H18]

As a general rule, configure the connection with the thread to be used, and handle queries, transactions, and closes with appropriate owners. When using `moveToThread` of Qt 6.8 or later, check that there is no bound QSqlQuery, QObject movement restrictions, and return values. Don't move a running connection to an arbitrary pool thread because there is a new API. [H18]

Check the return value of `transaction/commit/rollback` and driver error. Depending on the driver, active SELECT may prevent commit. Observe the intended DB commit success, not the sent saved notification to the UI. When deleting a connection, check the query/reference and QCoreApplication termination order. [H18]

## 3. GTK/GIO and file saving

Use GTask's worker/completion, cancelable, and main context according to the contract of the target API. Rather than assuming that the callback received a cancel as ``the worker will never touch the buffer again,'' check the reference lifespan and termination. Only necessary results and limited updates are returned to the GUI side. [L08]

When using GIO `replace_contents_async`, keep the input buffer valid until the callback is called and check for finish/error. Deals with the meaning of etag and flags, conflicts, and permission/disk failure. The async API changes the way the UI waits, and does not automatically generate business transactions for multiple files. [H26]

Qt's QSaveFile provides a path to commit using a temporary file, but the atomicity is different when direct write fallback is enabled. Don't always assume it's atomic, check target directory/permissions and return values. [H25]

Atomic replacement of a single file, DB transaction, flushing the filesystem, and power failure tolerance are different. Specify the range that can be guaranteed with the selected API, filesystem, and mount/device conditions. Do not use direct overwriting of the final file or omitting sync as "speeding up" without permission. [H20]

## 4. SQLite / Outbox / Multiple processes

Identify native SQLite, Qt SQL, another database, or plain file. If you use SQLite WAL, observe writer contention, long readers and checkpoints, WAL size, and busy handling. Do not retry to SQLITE_BUSY with infinite spin and occupy GUI/CPU. [H19]

The necessary local-first guarantee is established by ensuring that domain data and Outbox are in the same transaction or original log. ACK loss, partial ACK, retransmission, and operationId/receipt follow the common agreement. A mutex within a process alone does not control sync or migration of another instance.

Check scope and owner of lock/lease and prevent stale write when old instance resumes. Test how to stop the old writer during migration, compatibility read/write, rollback/restart in case of disk shortage and forced termination. Do not delete unsynchronized data because it is in the same directory as cache.

## 5. Separation of domain improvement and drawing improvement

Even if you speed up database queries and indexes, full model resets, QML binding reevaluations, and GTK list/snapshot updates may remain. Apply stable IDs and differences with revisions in the UI thread to shorten the scope of model update notifications. Keep focus, selection, scroll position, accessibility, IME. [L02][L07]

Do not confuse the period where GUI stops due to sync in Qt Quick threaded render loop with DB lock wait. The work of GTK snapshot/GSK, Wayland compositor, and GPU will not disappear with the conversion to DB workers. Do not report frame callback or buffer release as physical presentation time. [L01][L06][L11]

## 6. Measurement and failure testing

Place correlation in `input / producer admission / worker start-end / DB commit / receipt / model apply / render`. Check the clock scope of perf/Sysprof/Qt profiler and application log. Record ID/revision/size without sending record contents or credentials to trace. [L09][L13]

Select queue/lifetime for F01 to F03, save/ACK/disk/busy for F04 to F08, old/new version/multi-process for F09/F10, and long time/high DPI/backend for F12. Separate kill and graceful close, and check oracle by actually reading from the restarted test DB. If you want to change the read-only display, you can change the save type to N/A with a reason.

Simply passing the Python helper on a Linux container is not called a Qt/GTK/Wayland application integration test. Unverified if the toolkit and session/backend to be implemented are not measured.
