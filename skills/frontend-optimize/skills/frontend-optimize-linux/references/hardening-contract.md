# Acceptance contract — applicability, evidence, and stop conditions

Version 1.1.0. This document turns the lecture themes of protecting the UI execution context, paying boundary costs, and handling persistence and synchronization failures into this skill's operating rules. It is not an API specification. Read it with the [lecture notes](lecture-notes.md) and [measurement contract](measurement-contract.md).

## Norms and scope

**MUST** is required when applicable; **MUST NOT** is prohibited; **SHOULD** requires a reason for any exception and an alternative check. Do not weaken the project's existing security or approval rules. This contract guides the agent's reasoning and reporting; it is not a sandbox or automated proof system.

**Rigor does not mean adding more mechanisms.** Do not add Workers, SAB, an external state library, a database, or an Outbox to every small UI change. Prefer the smallest change that preserves existing guarantees. Separate UI and domain responsibilities logically first; moving them to another thread or process requires additional evidence.

Record each gate as `pass / fail / not-run / not-applicable`. Explain `not-applicable` from the scenario and change scope. “Too inconvenient,” “already implemented,” and “this is only about performance” are not reasons. An unrelated existing defect may go into a separate issue, but known data corruption on the path being optimized is not unrelated.

## Eight gates

| ID | Applies when | Required evidence and pass condition | If unmet |
|---|---|---|---|
| G0 Scope & baseline | Every change | Fix the source revision, runtime/build/device, representative action, dataset, cold/warm state, observed endpoint, primary metric, and guardrails before changing code. Explain if measurement is impossible. | Do not claim an improvement rate or `accepted` without a baseline. |
| G1 Execution & authority | Every change | Identify the executors and waits from input through domain, apply, and display. For each state, identify its owner, authoritative copy, lifetime, and write authority. Mark the write path N/A for read-only work. | Do not accept a design justified only by “async” or “another thread.” |
| G2 Intervention admission | Every change | Identify the causal interval, falsification condition, and smallest change. Consider removing unnecessary work and full recomputation first. For offloading, compare startup, copy, queue, compute, reply, UI apply, and resource costs. | Do not accept a demo speedup or shorter main-thread time alone. |
| G3 Boundary protocol | Changes to async boundaries, notifications, threads/processes, IPC, shared state, or pools | Define ownership, message/version, queue bounds, producer backpressure, ordering/duplicates, cancellation, stale results, errors, restart, and shutdown. Check both sides of the boundary. | Do not accept unbounded queues, unowned data, or stale-result overwrites. |
| G4 Durability & acknowledgment | Changes affecting edits, saves, sends, local-first behavior, authoritative caches, or save-state displays | Distinguish optimistic application, local commit, and server ACK. Establish required durability, transaction scope, retry idempotency, failure UI, and evidence for the existing server contract. | Do not call enqueue/send a completed save or silently drop uncertain operations. |
| G5 Lifecycle & compatibility | Changes affecting lifecycle, stores/caches/schemas/protocols, multiple windows/tabs, permissions, or deployment | Record a version compatibility table, stop/resume/crash behavior, old/new coexistence, migration, revoked permission, account switching, cleanup, and recovery. | Do not delete unsynced data, disable security, or force a reload without authorization. |
| G6 Fault & regression | Every change; choose tests for the affected paths | Verify the normal path and applicable [fault tests](failure-injection.md), output equivalence, IME/accessibility/visual behavior, queue/memory/energy, and slow or long-running conditions. | Performance gains do not offset correctness failures. Mark unrun tests `not-run`. |
| G7 Evidence & adoption | Every change | Provide comparable before/after results, change in the causal interval, raw evidence, all applicable gate results, rollback scope, and unknowns. | Helper exit code 0, averages alone, or static review alone cannot justify `accepted`. |

G0/G1/G2/G6/G7 always apply. Evaluate G3/G4/G5 every time and read their contracts when applicable. G4 applies if reordering or moving work changes an existing save guarantee, even without a new persistence mechanism.

## Invariants

1. **Equivalent results.** Fix comparison conditions for search, edits, sorting, image work, and numerical work. Specify tolerances in advance. Reducing quality or result count needs a separately approved proposal.
2. **Bounded retention.** Define item and byte limits for queues, worker/task/connection limits for pools, byte/entry/lifetime limits for caches, and log retention. When unacknowledged operations exceed capacity, explicitly reject new input, wait to save, or offer export rather than silently deleting them.
3. **Distinct endpoints.** Input accepted, UI applied, locally committed, server acknowledged, and display presented are different events. Measure faster synchronous work, optimistic feedback, and actual task completion separately.
4. **Explainable failure.** Represent pending, failed, uncertain, and conflict states. Retry and recovery must not duplicate or lose effects. Report unknown server guarantees as unknown.
5. **Safe observation.** Do not log credentials or raw documents without bounds. Use correlation IDs and summaries, and check profiler overhead, limits, and shutdown.

## Decision rules

- `accepted`: Every applicable gate passes, N/A reasons are valid, predefined performance/resource/functional conditions hold, and the scope is stated.
- `rejected`: A guardrail fails, results are wrong/lost/duplicated, comparable performance worsens, or a required safety contract is violated. Record alternatives for addressing the cause.
- `inconclusive`: Measurement was sound, but noise, confounding, or insufficient effect prevents a decision. Do not cherry-pick trials.
- `unverified`: Required evidence such as a device, permissions, trace, or fault test is missing. Leave static review, an instrumentation change, execution steps, and the missing-evidence list as deliverables.

Continue investigation and feasible implementation when execution is blocked, but distinguish a finished report from a verified optimization. If a legitimate existing constraint prevents a gate from passing, propose a narrower scope or design change rather than passing it without evidence.
