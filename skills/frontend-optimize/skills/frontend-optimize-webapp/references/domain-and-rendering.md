# Strict use of UI/domain separation, differential updates, and drawing

## 1. Don't make the UI framework a domain engine, but don't over-partition it either.

Check whether the original copy, index, editing rule, and sync retry of a large number of records are being rewritten just for the convenience of views mounting/unmounting. Separate the logical domain API and UI adapter, and clarify the pure query/command, revision, and subscription ranges. There is no obligation to move even small local UI state to an external library or worker. [H21][H22]

Check whether Effect is used in the copy chain of derived state. Separate values that can be derived during rendering, processing that belongs to events, and Effects that are synchronized with external systems. Check the update fan-out, number of subscribers, and calculation cost in your profile before making the minimum changes. [H22]

## 2. Memo / external store / patch

`useMemo` is not a deep clone or thread boundary, but a calculation cache when changing dependencies. It only stabilizes object identity and does not deep compare all domains. Memo is not used to guarantee correctness or persistence, but to measure additional retention memory and dependency maintenance. [H04]

If you use `useSyncExternalStore`, it will return the same snapshot when there are no changes, and will return the mutable original without hiding the changes. Avoid unnecessary full copy for each update. Check starting/cancelling the subscription, selector granularity, and matching SSR/server snapshot and hydration. Check the optimization assumptions of existing frameworks/compilers by version. [H21]

When placing the original copy in the Worker, instead of sending the entire record snapshot to the UI every time, the required query result or patch with version is used as a candidate. However, it detects baseRevision mismatch and performs bounded resync, and does not mix partial patches of different revisions. Do not adopt patching until [boundary contract](boundaries-and-protocol.md) is satisfied.

## 3.Layout and dependence

Check the range made dirty by style change and the subsequent synchronous calculation by geometry read with trace. If possible, group reads for the old layout, then group writes. However, if the **after** geometry is semantically required, it would be a bug to move the read forward and use the old value. Consider measuring the minimum number of times that dependence is maintained and reading at the next layout opportunity if necessary. [W14]

Even if you alternate write → read in rAF, the forced layout will not disappear automatically. Even when solving with ResizeObserver etc., measure the feedback loop and the number of notifications. Batchization, containment, and virtualization are adopted while maintaining focus/IME/scroll anchor/a11y.

## 4. Layer memory and GPU

Layer is not one-to-one with each DOM node. We do not say that adding `transform/opacity/will-change` will always move to GPU for free. Even if layout/paint is reduced, the load on layer texture, raster, upload, compositor/GPU queue may increase. [W01][W04]

A simple **approximation** for uncompressed RGBA8:

```text
bytes ≈ width_css × height_css × DPR² × 4
1920 × 1080 × 4 = 8,294,400 bytes ≈ 8.29 MB ≈ 7.91 MiB  (DPR=1)
```

If DPR=2 in the same CSS area, the simple estimate is 4 times. This is an arithmetic example in this document and is not an actual GPU allocation. Actual usage varies depending on tile, padding, multi-buffering, mipmap, pixel format, compression, partial raster, etc. Measure actual trace/counter and long-term memory before and after layer promotion.

Paint invalidation reduction and JS/V8 JIT/GC are different causes. Check the possibility that raster/GPU/presentation is clogged even if main is free. Even if you move Canvas to Worker, the work on the GPU side will not disappear.

## 5. Dedicated pipeline and quality

OffscreenCanvas, WebGL/WebGPU, AudioWorklet see [exclusive contract](workers-and-scheduling.md). Take advantage of the differences between DOM manipulation and pixel/audio processing while leaving input coordinates, resize/DPR, text/IME overlay, a11y, context loss, and audio underrun as separate responsibilities.

Do not compare the results of lowering appearance, resolution, accuracy, and sample rate as implementation optimizations of the same quality. Adaptive policy that changes quality is set as a separate scenario as an approved requirement, and stability during switching is also measured.
