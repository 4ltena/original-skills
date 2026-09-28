# Scheduling/Worker/Shared Memory Recruitment Agreement

For G2/G3/G5. Identify the execution subject using [execution model](runtime-map.md) before reading. Processing migration is not a substitute for processing volume reduction.

## 1. Admission: What to transfer

First, use profile to separate computation, queue wait, clone, and DOM dependence. If you can change the total sort to index, consider it first. If the offload candidate reads the UI directly, it takes the small input snapshot needed on the UI side and separates it into pure computation. Do not assume that UI objects and DOM are touched by workers. [H12]

```text
total observed path:
  prepare -> startup/admission -> serialize/transfer -> queue wait
          -> compute -> reply -> result decode -> UI apply -> render
```

The diagram prevents costs from being overlooked, and is not a simple sum of parallel sections. Measure payload size/calls, peak memory, total CPU, input-to-feedback and input-to-result. Awaiting the result does not return the Worker's calculation to main; the problem is waiting for completion due to dependencies.

## 2.Yield and priority

`async`/Promise does not specify the execution location. Simply repeating microtasks may not create the task boundaries necessary for input/render. Divide the process into **sufficiently short work units** to allow some leeway for the observed deadline. [W20][W09]

```js
// Check the feature in the target Window/Worker context before use.
async function yieldToOtherTasks() {
  if (globalThis.scheduler && typeof globalThis.scheduler.yield === 'function') {
    await globalThis.scheduler.yield();
  } else {
    await new Promise(resolve => setTimeout(resolve, 0));
  }
}
```

Fallback does not guarantee equal priority or guarantee the display of the next frame. Affected by timer throttling and lifecycle. The fixed "every 50ms" is not treated as a frame budget. This function does not forcefully split a single heavy native call/WASM call in the middle. [W09][H01]

The priority of `postTask` is `user-blocking / user-visible / background`. When using TaskController/TaskSignal, check the presence of the API and the signal's abort/priority contract. Dynamic priority changes are handled differently depending on whether there is an explicit priority or not. Cancellation is differentiated between queued tasks and processes that have already started execution. Measure starvation and queue age without setting all priorities to the highest. [H01]

## 3. Selection of execution mechanism

| Mechanism| Candidate uses| Confirmation when hiring|
|---|---|---|
| DedicatedWorker | Heavy calculation of page/app, index, decode, worker compatible storage| startup, module/CSP, port, error/restart, pool limit, end of owner. |
| SharedWorker | Connection/index etc. shared between supported clients| Browser support, storage partition, connection client collection, and termination of the last client. Don't make it a persistent daemon. |
| ServiceWorker | fetch/cache, corresponding background event| event lifetime/update. Do not use CPU job pool or resident sync loop. |
| Worklet | Dedicated pipeline for Audio etc.| Scope/support/deadline by API. Don't consider it a general-purpose worker or always a dedicated OS thread.|

Do not assume that the same script URL will be shared across different partitions or scopes. SharedWorker/ServiceWorker is not a shared state with another terminal or a global login lock. [H12][H08][W21]

## 4. Clone / transfer / share

| method| Data ownership | judgment to use| Failure to verify|
|---|---|---|---|
| structured clone | Copy the corresponding value/structure to the receiver| Small to medium payload, simple request/result. There is no need to separate JSON stringization. | unsupported value, huge graph, serialize/allocation/GC, type/size validation. |
| transferable ArrayBuffer etc.| Transfer ownership of the corresponding resource. ArrayBuffer is sender detach| When one side finishes using a large binary and passes it to the receiving side| Sender reuse/detach of another view, owner in case of error, lack of return pool. |
| SharedArrayBuffer | Shares the same memory block. SAB is not transferable|When copying rules and the complexity of a shared protocol can be justified| data race, publication, full/empty, stop/privileges/restart. |

Structured clone is not a mechanism to send arbitrary functions/DOM/code. Not all types have the same copy cost. Transfer also does not guarantee "zero-copy of all processes", and costs such as packing/unpacking, view construction, GPU upload, etc. remain separately. [H02]

```js
// Illustrative ownership hand-off. Transfer the buffer instead of the TypedArray view itself.
const bytes = new Uint8Array(4096);
worker.postMessage({kind: 'block', buffer: bytes.buffer}, [bytes.buffer]);
// After success: sender side buffer is detached. Do not use bytes continuously.
```

This fragment is an explanatory example that omits the queue limit and error processing, and is not a production pool. The buffer is reused after confirming the ownership returned by the receiving side. [H02]

## 5.gate to add to SAB/Atomics

MUST check: secure context, `crossOriginIsolated`, target API, creation possibility of both window/worker, hosting/WebView deployment policy. COOP `same-origin` and COEP `require-corp` are examples of typical configurations and should not be added unconditionally. Check the impact of the real environment including third-party resources, iframes, popup integration/OAuth, and CORS/CORP. Passing with security disabled is prohibited. [H11]

If the feature is not available, provide an explicit fallback such as transfer/clone/batch, or explain that the feature is not supported. First, consider a design that can function without SAB.

The following specifications are also specified for the SPSC ring buffer. [H09][H10]

- One producer writes an unpublished slot and publishes the write index atomically after completion. The consumer only reads the published range and publishes the read index after consuming it.
- Simply making the index atomic does not automatically make simultaneous read/write of the payload safe. Do not overlap areas owned by producer/consumer.
- Define full/empty distinction, wraparound, capacity, maximum message, partial record, closed state, and recovery upon abnormal termination.
- wait/notify requires a loop to check the predicate and an end condition. Do not substitute the notification itself for payload or success.
- Do not use blocking `Atomics.wait` in the main thread. Don't busy-wait in the UI. No waiting or locking in audio callback. Do not use `waitAsync` etc. without checking compatibility and designing timeout/cancel.

Do not implement MPSC/MPMC only with SPSC index rules. Do not use mutex-free/lock-free/wait-free as the same term. Prefer existing verified implementations and simple message designs over inventing new untested shared memory algorithms for optimization.

## 6.Pool / backpressure / cancel

The design of renewing workers for each operation should be reviewed after measuring cold startup. The pool is reused when appropriate and determines the maximum number of workers, idle lifetime, startup failure, and resource budget. ``Start as many CPU logical cores as possible'' is not always the correct answer. Small jobs may be dominated by pool/transfer fixed costs.

Obtain credits before sending, and collect credits and buffer in case of completion/cancellation/failure. Even if you set a limit only on the receiver's internal queue, you cannot prevent the backlog of postMessages. Perform input burst and worker crash tests. Latest-wins is a candidate for search, but it is not diverted to the editing log.

Simply sending a cancel message to an existing worker's synchronous loop may not process the process until the loop ends. Compare things like chunking it and returning it to the event loop, safely checking the shared cancel flag, and as a last resort, terminating and restoring the state. Distinguish between suspension of calculation and non-acceptance of late result.

## 7. Comparison experiment between WASM and drawing offload

Separate JS vs WASM, main vs worker, single vs pool, clone vs transfer vs shared with the same algorithm/data/precision. Includes module fetch/compile/instantiate, memory growth, JS↔WASM times, copy, and reply. WASM on main may also shorten the calculation, but it does not automatically save from main. Don't rely on the demo ratio to guarantee your improvement.

OffscreenCanvas is not a mechanism to move the DOM itself to the worker. Check the compatibility with the target context/engine and define canvas transfer, resize/DPR, input coordinates, context loss, UI overlay/a11y, and lifecycle. Don't confuse submit completion with display completion, measure the raster/GPU side as well. [W12]

AudioWorklet must meet the render callback deadline. Allocate a buffer in advance and do not include blocking I/O, lock waits, unbounded calculations, or sequential logs. According to the actual frame length and sample rate, we do not assume that it is fixed at 128 frames in all implementations. Separate specifications such as draft renderSizeHint and shipping support. Definition and observation during underrun are also required when supplying in a ring with a worker. [H28][W13]
