/* Local, bounded diagnostic probe. Not an INP/FPS/presentation measurement library. */
(function (root) {
  "use strict";
  function createFrontendRuntimeProbe(options = {}) {
    const maxEntries = options.maxEntries === undefined ? 300 : options.maxEntries;
    const autoStopMs = options.autoStopMs === undefined ? 15000 : options.autoStopMs;
    const eventDurationThreshold = options.eventDurationThreshold === undefined ? 16 : options.eventDurationThreshold;
    if (!Number.isInteger(maxEntries) || maxEntries < 1 || maxEntries > 5000) throw new RangeError("maxEntries: integer 1..5000");
    if (!Number.isFinite(autoStopMs) || autoStopMs < 0 || autoStopMs > 120000) throw new RangeError("autoStopMs: 0..120000");
    if (!Number.isFinite(eventDurationThreshold) || eventDurationThreshold < 16) throw new RangeError("eventDurationThreshold must be >=16 ms");
    const frameSampling = options.sampleAnimationFrames === true;
    const ring = new Array(maxEntries);
    let head = 0, count = 0, dropped = 0, active = true;
    let rafId = null, timerId = null, lastFrame = null;
    const observers = [], errors = [], observedTypes = [];
    const finite = value => typeof value === "number" && Number.isFinite(value) ? value : null;
    const now = () => root.performance && typeof root.performance.now === "function" ? finite(root.performance.now()) : null;
    const startedAt = now();
    let stoppedAt = null;
    function push(value) {
      if (!active) return;
      if (count < maxEntries) { ring[(head + count) % maxEntries] = value; count++; }
      else { ring[head] = value; head = (head + 1) % maxEntries; dropped++; }
    }
    function sanitize(entry, type) {
      const value = {kind: type, startTime: finite(entry.startTime), duration: finite(entry.duration)};
      if (type === "event") {
        value.processingStart = finite(entry.processingStart);
        value.processingEnd = finite(entry.processingEnd);
        value.interactionId = finite(entry.interactionId);
        // Standard event names only; never target, DOM content, keys, URLs or script attribution strings.
        if (typeof entry.name === "string" && /^[a-z]{1,32}$/.test(entry.name)) value.eventType = entry.name;
      } else if (type === "long-animation-frame") {
        value.blockingDuration = finite(entry.blockingDuration);
        value.renderStart = finite(entry.renderStart);
        value.styleAndLayoutStart = finite(entry.styleAndLayoutStart);
        value.firstUIEventTimestamp = finite(entry.firstUIEventTimestamp);
        value.scriptCount = Array.isArray(entry.scripts) ? entry.scripts.length : null;
      }
      return value;
    }
    const PO = root.PerformanceObserver;
    const supported = PO && Array.isArray(PO.supportedEntryTypes) ? PO.supportedEntryTypes : [];
    for (const type of ["longtask", "long-animation-frame", "event"]) {
      if (!supported.includes(type)) continue;
      let observer = null;
      try {
        observer = new PO(list => {
          if (!active) return;
          for (const entry of list.getEntries()) push(sanitize(entry, type));
        });
        const settings = {type, buffered: false};
        if (type === "event") settings.durationThreshold = eventDurationThreshold;
        observer.observe(settings);
        observers.push({observer, type});
        observedTypes.push(type);
      } catch (error) {
        if (observer) observer.disconnect();
        errors.push({type, error: error && error.name ? error.name : "Error"});
      }
    }
    const doc = root.document;
    function visibilityChanged() { lastFrame = null; }
    function onFrame(timestamp) {
      if (!active) return;
      const hidden = doc && doc.visibilityState === "hidden";
      const stamp = finite(timestamp);
      if (hidden || stamp === null) lastFrame = null;
      else {
        if (lastFrame !== null && stamp >= lastFrame) push({kind: "raf-callback-interval", startTime: lastFrame, duration: stamp - lastFrame});
        lastFrame = stamp;
      }
      rafId = root.requestAnimationFrame(onFrame);
    }
    if (frameSampling && typeof root.requestAnimationFrame === "function") {
      if (doc && typeof doc.addEventListener === "function") doc.addEventListener("visibilitychange", visibilityChanged);
      rafId = root.requestAnimationFrame(onFrame);
    }
    function snapshot() {
      const entries = [];
      for (let i = 0; i < count; i++) entries.push({...ring[(head + i) % maxEntries]});
      return {
        schemaVersion: 1, active, startedAt, stoppedAt,
        observedTypes: [...observedTypes], unsupportedTypes: ["longtask", "long-animation-frame", "event"].filter(t => !supported.includes(t)),
        errors: errors.map(e => ({...e})), dropped, entries,
        animationFrameSampling: frameSampling && typeof root.requestAnimationFrame === "function",
        caveats: ["No INP, Core Web Vitals, real FPS or physical presentation is calculated.",
          "Raw observed durations are thresholded and may omit events; absence is not zero cost.",
          "rAF callback intervals are not displayed frame times and frame sampling perturbs idle activity.",
          "Bounded local memory only; no network, DOM contents, URLs or key values are collected."]
      };
    }
    function stop() {
      if (!active) return snapshot();
      for (const item of observers) {
        if (typeof item.observer.takeRecords === "function") {
          for (const entry of item.observer.takeRecords()) push(sanitize(entry, item.type));
        }
        item.observer.disconnect();
      }
      if (rafId !== null && typeof root.cancelAnimationFrame === "function") root.cancelAnimationFrame(rafId);
      if (timerId !== null && typeof root.clearTimeout === "function") root.clearTimeout(timerId);
      if (doc && typeof doc.removeEventListener === "function") doc.removeEventListener("visibilitychange", visibilityChanged);
      lastFrame = null; active = false; stoppedAt = now();
      return snapshot();
    }
    if (autoStopMs > 0 && typeof root.setTimeout === "function") timerId = root.setTimeout(stop, autoStopMs);
    return Object.freeze({snapshot, stop});
  }
  if (typeof module === "object" && module.exports) module.exports = {createFrontendRuntimeProbe};
  else root.createFrontendRuntimeProbe = createFrontendRuntimeProbe;
})(typeof globalThis === "object" ? globalThis : this);
