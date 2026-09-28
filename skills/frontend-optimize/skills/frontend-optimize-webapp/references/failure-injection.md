# Fault injection and acceptance tests

For G6. These are **specifications for tests to run**, not completed results. Mark untouched paths N/A with a reason. Prefer the target repository's existing test harness and protect real data, production APIs, and other people's work.

## Procedure

1. Prepare a disposable profile, test account, temporary database, and mock server; allowlist any external destinations. Fix the seed, schema, API version, expected operation set, and tolerances.
2. Stop at the fault point with an operationId-linked hook or barrier. An arbitrary sleep does not prove that a fault happened immediately after commit. Record the injection point and preceding event in a trace.
3. Distinguish graceful close/cancel, worker termination, abrupt process exit, and network loss. A test that runs shutdown handlers is not an abrupt-crash test. A process kill does not validate power loss or filesystem failure.
4. Reopen the same profile and database; compare UI, domain state, saved revision, Outbox, server receipts, queues, and resources. Absence of an exception alone is insufficient.
5. Record `pass / fail / not-run / not-applicable` and raw evidence for each case. Do not omit flaky failures by trial; investigate their causes. Unreproducible targets remain `unverified`.

## Cases and oracles

| ID | Applicable fault | State required to pass |
|---|---|---|
| F01 | Deliver query/worker replies out of order or twice | Apply the latest-result rule; an old epoch or generation must not overwrite the UI. |
| F02 | Keep the producer faster than the consumer | Bound pending, inflight, and result items/bytes; apply input backpressure; converge after recovery. Never silently drop edits. |
| F03 | Cancel during execution, destroy the view/window, or crash a worker | No callback use-after-free. Record the actual cancellation point and remaining work. Recover durable operations through another owner. |
| F04 | Fail or exit after optimistic application and before local commit | Do not label unsaved work as saved. State after restart matches the defined commit point. |
| F05 | Exit abruptly after local commit and before send | Restore both state and Outbox and send using the same operationId. |
| F06 | Drop the ACK after the server applies an operation | Retry or reconciliation does not duplicate the effect. The UI does not falsely resolve an unknown outcome. |
| F07 | Exit after receiving ACK but before committing receipt/Outbox processing | Resend is safe; completed and pending sets remain consistent. A partial ACK does not delete every item. |
| F08 | Fill quota/disk, revoke permission, or abort a transaction | Preserve data/Outbox atomicity, show unsaved state explicitly, and bound retries. Do not erase the entire database as “recovery.” |
| F09 | Run old and new app/tab/process versions together and request migration | Show blocked/compatibility state, preserve existing commits, enforce old-writer rules, and recover from interrupted upgrades. |
| F10 | Suspend or kill the sync leader, replace it, then resume the old leader | A stale leader does not make destructive duplicate writes. Verify locks/fencing and server deduplication at their actual scopes. |
| F11 | Use an unsupported API, unavailable isolation, or failed worker startup/CSP | Preserve functionality with a fallback or explicitly report unsupported operation. Do not disable security to work around it. |
| F12 | Use a large dataset, high DPI, slow network, and long/background/resume operation | Tail latency, error rate, memory, queues, idle CPU, render/audio deadlines, IME, and accessibility meet predefined conditions. |

Query rules in F01/F02 differ from save rules in F04–F10. Set F12 load, duration, and devices from product requirements; do not call an arbitrary short run a long-term endurance test.

## Example recovery oracle

```text
intended operations = committed-on-server ∪ locally-pending ∪ explicitly-rejected
```

This is a conceptual comparison of operation-ID sets. Define business cancellation, compensation, or merge as separate categories, then verify their exclusivity and relationships. The same operation may temporarily appear in committed and pending after an ACK is lost; matching set counts alone cannot detect duplicate effects. Check business effects and receipts for each operation ID.

## Controlled performance experiment

Hold dataset, result, accuracy, concurrency, and settings constant while changing one factor. Do not change JS/WASM, UI/Worker, single/pool, and clone/transfer/shared memory together and then assert one cause. Add controls if needed, without implementing unsupported combinations merely for a test.

Separate instrumentation on/off, cold/warm, startup/steady costs, total completion/UI response, and total CPU/peak memory. CPU throttling is a stress test for that environment, not a full substitute for another OS, GPU, or physical device. [W08]

Use the [test record template](../assets/failure-matrix-template.md). For native or physical-device tests that cannot run, leave the procedure and required resources; do not invent results.
