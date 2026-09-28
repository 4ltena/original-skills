# Boundary contract worksheet

Status: not-run. Give a reason for every N/A item. Do not treat example values as measurements.

## Scope / invariants
Target operation, changed commit, runtime/version, entity/account scope:
Authoritative state and scope / transient UI state / cache / durable state / server authority:
Output equivalence and tolerance / invariants / operations whose meaning must remain unchanged:

## Execution and transfer
| Boundary ID | Producer owner/context | Consumer owner/context | Payload format and size | Calls/sec | Clone/transfer/shared/FFI | Clock domain |
|---|---|---|---|---|---|---|
| B1 | Not filled in | Not filled in | Not filled in | Not measured | Not filled in | Not filled in |

## Lifecycle / capacity
Pool cold/warm / maximum concurrency / shutdown owner:
Limits: pending items/bytes, inflight items/bytes, completed results, cache, durable queue:
Producer admission / backpressure / UI when full / permanent errors / retry and retention:
Ownership and mutability / use after transfer / shared publication / lock scope:
Cancellation requested/acknowledged/stopped/discarded / late replies / worker restart / view destruction:

## Protocol / storage
Protocol/schema compatibility / validation / sessionEpoch / requestId / generation:
operationId scope and retention across retries / base-to-next revision / resync on gaps:
Local transaction boundary / API that confirms commit / failure scope guaranteed:
Source of server idempotency, authorization, and receipt contracts / unknown guarantees:
Old/new clients, leader changes, migration, permission/account switches:

## Evidence
Trace/log path and interval / source location / fault test IDs / unverified items:
