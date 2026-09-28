# Execution, state, and communication boundary contract

For G1/G3. The tables and message shape below aid design; they do not require a new communication mechanism. Do not add a transport for a purely synchronous calculation.

## 1. Separate responsibilities first

| Responsibility | Owns | Generally avoid mixing in |
|---|---|---|
| UI adapter | Input, focus/IME, view state, visible range, result display | Full scans of a huge dataset on every input; guesses about save success |
| Domain | Business rules, indexes, validation, applying changes, queries, revisions | Direct UI-object references; deleting data for display convenience |
| Local persistence | Transactions, schema, saved revisions, Outbox if needed | Indefinite transactions while waiting for network |
| Sync/transport | Protocol, retry, ACK, conflicts, backpressure | Silently skipping domain decisions; replacing server authorization |
| OS/browser/framework | Scheduling, I/O, rendering, compositor | Dedicated threads or guarantees assumed by the agent without evidence |

These responsibilities may coexist in one module or executor in a small app. Separation of responsibility and parallelism are different decisions. When extracting large state from UI Effects or notification chains, preserve existing lifecycle, undo, and transactions. [H22]

For every state, record `name / authoritative scope / writer / replicas / lifetime / revision / invalidation / recovery`. UI selection, local drafts, server-confirmed balances, and shared documents may have different authority rules. Avoid circular claims that both replicas are always right. Client validation does not replace server authorization or balance guarantees.

## 2. Fill in the boundary table

Use the [boundary template](../assets/boundary-contract-template.md) and check both ends:

- Process/thread/actor/dispatcher/context and actual version; separate observation from inference.
- Messages per second, payload bytes, serialize/clone/transfer/FFI costs, fixed costs, and cold/warm pool state.
- Mutable-object owner, allowed use after transfer, and publication synchronization for shared memory.
- Limits on inflight **items and bytes**, pending work, completed results, and UI application backlog, plus overflow behavior.
- Owner of normal shutdown, crash, timeout, revoked permission, cancellation, and view/window destruction.

A bounded receiving queue does not bound the system if the sender creates unlimited posts, sends, or tasks. Apply admission control, credits, or a bounded channel **before enqueue**. An I/O return or queue acceptance is not a durable commit. [H14][H17]

## 3. Messages and versions

Example when introducing a new asynchronous protocol; do not add it if the existing protocol suffices:

```json
{
  "protocolVersion": 1,
  "sessionEpoch": "worker-restart-id",
  "requestId": "query-42",
  "kind": "search",
  "baseRevision": 103,
  "generation": 9,
  "payload": {"query": "..."}
}
```

`requestId` correlates a request and reply. A durable `operationId` identifies the same operation across retries; `sessionEpoch` marks worker restarts; `generation` implements latest-result search. Do not overload one sequence number for all roles. IDs do not prove authorization. Validate type, size, range, and protocol compatibility at the boundary.

Rely on ordering only within the scope guaranteed by the transport. Do not assume one total order across ports, connections, workers, or reconnections. Define handling for duplicates, delays, unknown requests, old epochs, and incompatible schemas.

## 4. When to move from full snapshots to patches

Consider keeping indexes and state with their owner and sending only queries/commands and necessary results, instead of round-tripping a whole dataset on every input. A patch must still preserve consistency.

```text
patch: { baseRevision, nextRevision, operations }
receiver:
  baseRevision == currentRevision -> validate, apply atomically, advance revision
  already-applied patch          -> documented duplicate handling
  gap / incompatible version     -> bounded resync; do not partially guess-apply
```

This is an example for a single ordered revision protocol. If the product already has a proven CRDT/OT merge model, use its rules. Align patch application, indexes, and view snapshots to the same revision. Hashes help diagnosis but do not prove equivalence absolutely. Bound the size of resync snapshots and define a consistent capture point and restart behavior.

React memoization differs from structured cloning. `useMemo` caches a calculation by comparing dependencies with Object.is; it is neither durable authority nor a deep copy of all state. An external store must preserve snapshot identity while unchanged, immutable snapshots, unsubscribe behavior, and consistent SSR initial values. `useState` and `useReducer` are legitimate choices. [H04][H21]

## 5. Queues, cancellation, and priority

| Operation | Permitted coalescing/drop | Required condition |
|---|---|---|
| Search suggestions, hover preview | Latest-wins for pending work and ignoring old results may fit | Apply only the latest generation; stopping in-progress computation is a separate contract. |
| Rendering snapshot | Intermediate revisions may be skipped | Resync on gaps when deltas depend on them; preserve final state and selection. |
| Edit, save, payment-like command | Never drop silently | Use a semantics-preserving combination rule or durable queue; explicitly reject when full. |
| Audio/real-time stream | Dedicated underrun/overflow policy | Meet deadlines; do not block a callback for retries. |

Distinguish cancellation `requested / acknowledged / computation-stopped / result-discarded / side-effect-compensated`. A timeout does not prove non-delivery. Client cancellation of a sent command may not undo a server commit. [H13]

Cooperative scheduling needs points where work yields control. Priority is not an ordering guarantee for essential business operations or transaction isolation. Measure starvation, queue age, maximum wait, and unfinished shutdown work. [H01]

## 6. Trace correlation

Attach the same operation/request correlation ID across stages. Distinguish `queued/start/end/reply/apply/local-commit/server-ack`. Bound event retention and record sampling and drop counts rather than logging everything.

When contexts have different `performance.now()` origins, do not subtract the readings directly. For applicable contexts in one browser, `timeOrigin + now` can align origins subject to rounding; for native profilers, verify the clock domain. Do not assume server clocks, other devices, or restarted processes share a clock. If clock alignment is unknown, report causal relationships and durations within each domain only. [H27]

Do not sum concurrent intervals into end-to-end latency. Report critical path, CPU time, queue wait, and memory retention separately. Check that final UI application did not create a new bottleneck. [C04][C05]
