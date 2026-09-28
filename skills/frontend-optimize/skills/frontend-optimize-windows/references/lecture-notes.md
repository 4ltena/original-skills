# What I learned from the lecture and what I corrected in the specifications

Input: User provided `Pasted text(3).txt` (Japanese transcription, single line, speaker name, date, slides, demo source, timecode not provided). This section is not a verbatim proofreading. If the spelling, number, or subject is ambiguous, it cannot be determined that this is the speaker's intention. The instructions in the original text are treated as materials and are not used as execution instructions for the agent.

## A. Theme based on the lecture

The order maintains the flow of the lecture. The specific gate ID, message/state machine, and native support are design rules added by this package, and are not directly stated by the speaker.

1. **Execution location**: In order not to stop the UI, separate the work of main, Worker, Worklet, and drawing path. Task division/priority is also an option.
2. **Boundary costs**: Consider message copying, ownership, shared memory, synchronization, worker creation and pooling, and round-trip frequency. Recruiting workers or WASM is not the goal itself.
3. **Drawing**: Understand dependencies and differences in style/layout/paint/composition, and check forced synchronous layouts and unnecessary layers. Canvas/Audio has a dedicated path.
4. **local-first**: Design IndexedDB/OPFS storage, transactions, Outbox, multiple tabs, schema migration, and synchronization responsibilities.
5. **architecture and validation**: Separate UI and domain responsibilities to avoid large snapshot round trips. Handles optimistic display, save confirmation, crash position, version skew, profile and slow conditions.

## B. Assertions that were not regularized as they were.

| issue|Handling of transcription| Rules and references for this skill|
|---|---|---|
| There is only one main thread| Adopted the idea that it is a rare execution place for a specific UI. It does not mean that there is always one process for the entire browser, and that tabs are always separate processes. | Check engine/context and identify the main thread of that input route. [W01][W03][H12]|
| Yield/priority explained as interrupt processing| We do not guarantee forced OS preemption or process division. | Cooperative task division. Long synchronous processing returns control by itself. TaskController does not forcibly stop any running CPU process. [H01]|
| message/transfer/SAB | There are places where ownership transfer and sharing can be confused. Do not equate structured clone with transferring JSON strings or arbitrary code. | Select clone, transfer, and share as separate methods, and define detach, publish, and capacity. [H02][H09][H10]|
| No collision with SPSC| It does not mean that publication/ordering can be omitted even if one writer at a time. It is not decided that SAB is meaningless if there is only one worker.|Design payload ownership and index release order, full/empty, wraparound, and cancel. The necessity is determined by actual measurements. [H09][H10]|
| SAB deployment| Don't make it a rule that it can be used with just a simple CORS setting. | Verify secure context, cross-origin isolation, resources/embedding policy, etc. in the target environment. [H11]|
| Number of workers, number of lines, speed multiplier| There are insufficient reproduction conditions for the worker number limit, line number threshold, and demo seconds for a specific terminal. There is also ambiguity in the transcription of units and numbers. | Not adopted as a general-purpose threshold/improvement guarantee. Separate and re-measure result equivalence, degree of parallelism, transport, and cold/warm. |
| WASM on main is meaningless| We do not deny the possibility of improving calculation speed by not automatically releasing main. | Make language/execution location/degree of parallelism/transfer independent experimental axes. Prefer end-to-end evidence over JS or WASM. [W11]|
| React useMemo and structured clone| Technically different. Don't decide that useState/useReducer itself is a misuse, or make an external state library mandatory.|useMemo is a cache that uses Object.is for dependency comparison. External store requires snapshot/subscription contract. [H04][H21][H22]|
| Main body of drawing optimization| Don't explain style/layout/composition just by the cleverness of V8. It also does not assume that each DOM element is an independent GPU layer. | Distinguish between drawing engines such as Blink and JS engines, and check evidence of layout/raster/GPU. [W01][W04][W14]|
| Effects of layout thrashing| Don't make "normally the same" a general rule. | Actual measurement of batching while maintaining read/write dependence. Does not break the required latest geometry reading. [W14]|
| localStorage/IDB capacity| Do not use the number of MB/GB in the transcription as a fixed upper limit. | Check estimate, quota failure, eviction, and persistence, and do not make browser save the only backup. [H06]|
| IDB/OPFS and SQLite| IDB is object store, OPFS is file storage. OPFS itself is not an SQL database.|If you use SQL, check engine/VFS/locking separately. sync access handle is an API for DedicatedWorker and is not for ServiceWorker. [H03][H05][H23]|
| IDB transaction dies with await| Don't make it a rule that all awaits always fail. | Understand active/inactive and auto-commit, and avoid introducing unrelated network waits into transactions. Distinguish between request success and transaction completion. [H03]|
| Clear migration or leave it to browser| Schema changes are implemented by the developer using an upgrade transaction. Do not make full deletion a normal migration procedure. | Design versionchange/blocked and coexistence of old and new versions. [H03]|
| It is safe if there is only one leader| Local coordination does not guarantee server authorization or exclusion with other devices. | Check lock scope, suspend/crash, old leader return and server idempotency. [H07][H13]|
| After sending, only the server is responsible| Although the client alone cannot guarantee server confirmation, retransmission/ACK management is also necessary for the client.|Display stable operationId, server dedup, ACK verification, receipt and outbox updates, unknown outcome. [H13][H14]|
| Consistency by SW resident/cache deletion| ServiceWorker is event-driven. All cache/DB deletion and unconditional skipWaiting are not used. | controlled lifecycle and legacy client compatibility. Separate the unsynchronized original from the retrievable cache. [H08][H24]|
| Alternative to real machine for CPU slowdown| Adopted the idea of approximate stress under low performance conditions. Do not completely reproduce another OS/device. | Separately mention untested and simulation. [W08]|

## C. Source of Supplement

"8 gates", "G4 A-E crash window", "12 failure tests", "versioned patch/epoch", "native DB connection/actor/dispatcher contract" are extensions that this package derived from the lecture policy and primary materials. The talk itself does not claim to have verified these specific implementations.

When applying web concepts to native, it is not enough to simply replace Worker with Task. Check the terms of Apple's context/actor, Windows' Dispatcher/provider, and Linux's QObject/GMainContext/SQL connection in each native document. These native-specific information are not derived from lectures. [H15][H16][H18][H29]

This revision strengthens the design procedure based on transcription, and does not include additional testing of the lecture demo, confirmation of the authenticity of existing bug reports, or performance comparison of all browsers/backends.
