# Persistence/Outbox/Sync/Disaster Recovery

For G4/G5. Apply local-first and outbox as mentioned in the lecture **only when necessary** for preservation guarantees. There is no obligation to add DB/Outbox to read-only apps or previews that do not require restoration. The state machine and gate below are the design rules for this package, and are not a verbatim transcript of the lecture.

## 1. Breaking down “done”

```text
input accepted -> optimistic/pending UI
               -> local transaction committed
               -> retryable sync pending -> sending
               -> authoritative server ACK -> synchronized UI
                                      \-> conflict / rejected / uncertain
```

Design at least a distinction between `pending / locally saved / synchronized / failed-or-conflict`. You can use the display word to match the product, but do not change server undetermined to "server saved." If only server persistence is required, a local store is optional; still handle network failures and unknown outcomes.

Specify what `local commit` can withstand: view destruction, worker termination, app/process crash, OS crash/power loss, storage eviction, user deletion. These are not the same. Even with transaction commit, strict durability hint, and flush API, there is no guarantee that backup will survive all device failures and browser deletions. [H03][H06][H20]

Separately measure input-to-feedback, input-to-local-commit, input-to-server-ack, and input-to-result/present. Changes that speed up only the spinner or optimistic display but slow down the save completion will make the trade-off clear.

## 2. Authoritative state and transaction unit

In the local-first example, we put the local state that appears saved to the user and the sending intent in the same atomic transaction.

```text
transaction begin
  validate expected revision / mutation intent
  update local domain data (or append authoritative operation log)
  append outbox {operationId, accountScope, entityId, baseVersion, payloadVersion,
                 immutableIntent, createdAt, retryMetadata}
transaction commit
publish "locally saved" and committed revision
```

This is designed pseudocode rather than an implemented generic DB API. If the existing design derives the state from the operation log, the log may be authoritative and the snapshot reconstructable. An implementation that writes twice to separate DB/files is not called atomicity as above. If multiple stores cannot have the same transaction, journal/recovery or consistency level needs to be changed.

External I/O such as network and image downloads are issued before and after the transaction. Re-validate base revision and permissions when committing prepared results. The state does not necessarily remain unchanged until the await returns. Check the active/inactive, actor reentrancy, and connection/transaction ranges of IndexedDB and native DB. [H03][H29]

## 3. Contract for each failure position

| boundary| observable state| Rules for recovery and display|
|---|---|---|
| A: After UI reflection, before local commit| Screen has been changed but not saved| Displayed as pending. If commit fails, rollback/re-edit/explicitly unsave. Do not mark unsaved items as saved. |
| B: After local commit, before send| local state and outbox remain| Restore by restarting, check authentication/account and resend. Don't delete it arbitrarily. |
| C: After send, before and after server commit is unknown| timeout, disconnection, ACK loss|unknown outcome. Query/resend with the same operationId to prevent duplicate application on the server. |
| D: After receiving ACK, but before reflecting local receipt| server has been applied, Outbox may remain| A server contract that allows retransmission. Recovers from the next ACK and does not apply twice. |
| E: local receipt processing| Requires consistency between local state and Outbox completion| Update authoritative revision/receipt and acknowledged marking or deletion in the same transaction. |

Don't end C and later with "Not related to client". The client is in charge of stable ID, retransmission, unconfirmed display, and receipt processing, and the server is in charge of authorization, deduplication, and response of confirmed contents. However, it is not possible to create server guarantees with just the client. [H13][H14]

## 4.Idempotency / ACK

For retransmission of the same operation, use the same `operationId` and payload with the same meaning. Do not assign a new ID on every retry. Request or confirm the following in your server agreement:

- ID scope: Avoid conflicting IDs with others and confusing authorizations, including tenant/account/operation types, etc.
- Correspondence between ID and intent: Reject/conflict processing if another payload is received with the same ID. Do not change the meaning by regenerating the current time, etc.
- Atomicity of deduplication record and business update: Just "dedup record after update" can be applied twice by crash.
- receipt: Return operationId, confirmed result/revision, and authorized target. WebSocket `send`, HTTP reception, and writing to queue are not substitutes for this receipt.
- retention: Match the dedup retention period with the client's maximum retry/offline period. Expired operations are not blindly retransmitted as new operations, but are verified or manually restored.

This does not declare unconditional end-to-end exactly-once delivery. We will separately explain resendable delivery and suppression of duplicate effects within the range determined by the server. If there is infinite offline, lack of quota, deletion, or expired credentials, even event delivery cannot be guaranteed unconditionally. [H13]

Partial ACK allows only operations that are confirmed to be successful to complete. Do not delete the entire batch. The order of dependent operations, conflicts, and undo/compensation follow domain rules. Do not divert the search optimization of "drop from old" to the save command.

## 5. Retry/Capacity/Authority

Retry uses existing policies such as concurrency with an upper limit and exponential backoff+jitter to distinguish between permanent errors and temporary errors. Don't accept a fixed value as the correct answer when the exponent or number of seconds is unknown to the environment. Do not silently discard unsynchronized operations even if retry is exhausted, leaving a failed/blocked message and a means of recovery.

Observe the number of queue/outbox items, bytes, oldest pending age, number of retries, number of conflicts, and disk capacity. Design log retention, compact, and snapshot, and define deletion conditions while receipt/dedup is required. Do not send operations from another account when logging out or switching accounts. Separate cache and unsynchronized originals, and deletion follows existing authorization and data retention policies.

## 6. Multiple clients and version skew

Manage versions of apps, UI, workers, storage schema, message protocols, server APIs, and service workers/cache separately. Table the read/write compatibility and upgrade order for each combination. Build hash matching alone does not guarantee data compatibility.

local leader/lock is a way to reduce duplicate syncs, not a replacement for server-side idempotency. Consider a case where the old leader returns after the leader stops/suspends and is replaced. The lease method requires a design in which the fencing token is verified by the write recipient, and the client's clock and a boolean indicating "I am the leader" are not enough. Even when employing appropriate local locks, do not assume that the scope covers the entire device or all users. [H07]

Migration is designed as the responsibility of the application, and tests the behavior of old connections and processes, blocked status, crash recovery, disk shortage, and whether rollback is possible. Changes that completely delete unsynchronized DBs are prohibited due to schema mismatch. Destructive migrations satisfy existing rules such as backup/export, phased migrations, user approvals, etc. Do not treat service workers as resident sync daemons. [H03][H08][H24]

## 7. Required fault testing

At a minimum, stop and restart at the boundary between A and E to be applied, and check the operation set, local/server revision, duplicate effects, and pending display. Details in [Fault injection procedure](failure-injection.md). Passing with fixtures or mock servers validates only the modeled server contract. It does not establish resilience to every real failure mode.
