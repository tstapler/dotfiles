---
name: browser-profiling
description: Profile Chrome/JavaScript/React apps to diagnose slowness. Covers triage (load vs interaction vs scroll), Playwright-based baseline capture, React Profiler component, Chrome Performance panel interpretation, bundle analysis, memory leak detection, and fix verification. Invoke when a browser or React app is noticeably slow and you need to find and fix the bottleneck.
---

# Browser / React Performance Profiling

End-to-end workflow: triage the complaint → capture numeric baseline → isolate the layer (browser vs React vs network) → deep-dive the bottleneck → fix → verify the fix matches the baseline.

## Triage Table — Classify Before You Profile

| Symptom | Likely Layer | Primary Tool |
|---------|-------------|-------------|
| Slow initial page load | Network / bundle | Lighthouse, bundle analyzer, coverage API |
| Slow after clicking / typing | JS / React renders | Performance panel, React `<Profiler>` |
| Scrolling jank / dropped frames | Layout thrashing / paint | FPS meter, Performance panel during scroll |
| Memory grows and never recovers | Memory leak | Memory panel Heap Snapshot + Allocation Timeline |
| App slow only on low-end devices | Long tasks / large bundles | Performance panel with 6× CPU throttle |

---

## Step 1 — Capture a Numeric Baseline

Never skip this. "It feels slow" is not a measurement. Run a Playwright script before touching code that captures `page.metrics()` deltas, long-task counts, and a Chrome trace file — then compare after fixes.

See [Baseline Capture and Fix Verification](references/baseline-and-verification.md) for the full `perf-baseline.js` script and the Step 6 verification workflow.

---

## Step 2 — Add React `<Profiler>` to Slow Subtrees

Wrap the suspect component tree in a `<Profiler>`; its `onRender` callback reports `actualDuration` (this render) vs `baseDuration` (worst case without memoization).

**Key ratio**: `actualDuration / baseDuration`
- Near **1.0** → memoization is absent or not helping; every component in the subtree re-renders
- Near **0.1** → memoization works; only ~10% of the subtree re-renders on updates

In the Chrome DevTools Performance panel (React 19+), the "Scheduler" and "Components" tracks show wide bars in the **Blocking** lane (synchronous updates) or a **Cascading updates** flag (a render triggering another render).

See [React Profiler and Re-render Detection](references/react-profiler.md) for the `<Profiler>` code and the `why-did-you-render` dev tool.

---

## Step 3 — Read the Chrome Performance Panel

1. Open DevTools → Performance tab
2. Set **CPU throttling** to `4×`–`6×` to simulate mobile (reproduces problems that don't show on fast machines)
3. Click **Record** → reproduce the slow action → **Stop**
4. Read the **Main** thread row: Bottom-Up tab sorted by Self Time finds the expensive function; Call Tree tab sorted by Total Time finds the entry point that triggers the most work

See [Reading the Chrome Performance Panel](references/chrome-performance-panel.md) for the flamechart legend and key event names to search for.

---

## Step 4 — Diagnose by Layer

Once you know the layer (from Step 1's trace or Step 3's panel), match the symptom to a fix:

| Layer | Symptom |
|-------|---------|
| React re-render cascade | `<Profiler>` ratio near 1.0; most of the tree re-renders on every keystroke |
| Long tasks / JS-heavy interaction | Red-flagged tasks >50ms on interaction; INP > 200ms |
| Layout thrashing | "Forced reflow" warnings; `Layout` events interleaved with JS |
| Bundle size / dead code | Slow initial load; large `node_modules` in the critical bundle |

See [Diagnose by Layer](references/diagnose-by-layer.md) for the anti-pattern tables and fix code for each (memoization, `scheduler.yield()`/`startTransition`, batched reads/writes, `source-map-explorer` + `React.lazy`).

---

## Step 5 — Memory Leak Detection

**Symptom**: JS Heap grows over time in Task Manager and doesn't return to baseline after GC.

Quick check: run 10 cycles of the suspect action via Playwright, force GC, and compare `page.metrics()` heap size before/after — growth over ~5MB warrants a DevTools Heap Snapshot comparison (sort by "# New" objects). The most common React leak is a missing `useEffect` cleanup for an event listener.

See [Memory Leak Detection](references/memory-leak-detection.md) for the Playwright check script and the DevTools Heap Snapshot workflow.

---

## Step 6 — Verify the Fix

Re-run the Step 1 baseline script with a new label and compare against the original trace. Pass criteria: reduced `scriptDuration` delta, fewer/shorter long tasks, improved `<Profiler>` ratio, no new long tasks elsewhere, and (for leaks) heap growth under 1MB across 10 cycles. Full checklist in [Baseline Capture and Fix Verification](references/baseline-and-verification.md).

---

## Quick Reference

| Goal | What to use |
|------|------------|
| Establish numeric baseline | `page.metrics()` before/after + `browser.startTracing()` |
| Find expensive React subtree | `<Profiler id="X" onRender={onRender}>` |
| Find why a component re-rendered | React DevTools Components track → click component → "Why did this render?" |
| Find long tasks | Performance panel red-flagged bars / `PerformanceObserver longtask` |
| Find layout thrashing | Performance panel → "Forced reflow" warnings |
| Identify unused JS | `page.coverage.startJSCoverage()` |
| Visualize bundle composition | `npx source-map-explorer 'build/static/js/*.js'` |
| Find memory leaks | Memory panel Heap Snapshot comparison (before/after cycles) |
| Move work off main thread | `startTransition`, `scheduler.yield()`, Web Workers |
| Reproduce mobile conditions | CPU throttling 4–6× in DevTools Performance panel |

## Common Pitfalls

- **Profiling a dev build** — React dev builds are 2–3× slower than production; always profile a production or `profiling` build for realistic numbers. Use `react-dom/profiling` to keep Profiler tracks in production.
- **One `<Profiler>` wrapping the entire app** — too coarse to find the bottleneck; wrap the specific subtree you suspect
- **Optimizing without a baseline** — if you don't measure before, you can't prove the fix worked; always capture `page.metrics()` deltas
- **`useMemo`/`useCallback` without React.memo children** — these only help when a memoized child exists; adding them without a `React.memo`-wrapped consumer is pure overhead
- **Fixing inline objects in JSX without measuring first** — sometimes the cost is in computation, not re-render count; check `<Profiler>` before assuming the cause
- **Missing `key` stability after "fixing" keys** — switching from index keys to IDs is correct, but only if the IDs are stable across renders; generated UUIDs on each render are worse than index keys
- **Memory panel without forcing GC first** — always click the trash can icon (Force GC) in the Memory panel before taking a snapshot to avoid counting GC-eligible objects as leaks
- **Long task fix that only moves the work** — `startTransition` delays work; it doesn't eliminate it. If the work is truly too expensive, it needs to be broken up or moved to a Worker.
