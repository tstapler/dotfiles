---
name: browser-profiling
description: Profile Chrome/JavaScript/React apps to diagnose slowness. Covers triage (load vs interaction vs scroll), Playwright-based baseline capture, React Profiler component, Chrome Performance panel interpretation, bundle analysis, memory leak detection, fix verification, and programmatic large-trace analysis via Perfetto's trace_processor (the pprof-equivalent for Chrome traces). Invoke when a browser or React app is noticeably slow and you need to find and fix the bottleneck, or when you have a downloaded `.json`/`.json.gz` Performance-panel trace to analyze.
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

## Step 3.5 — Analyzing a Trace Programmatically (Perfetto `trace_processor` — the pprof of Chrome traces)

A DevTools Performance recording — from the manual "Record → Save profile..." flow, or `browser.startTracing()` in Step 1 — is a JSON array of trace events (`ts`, `dur`, `ph`, `name`, `cat`, `pid`/`tid`, `args`). On a real session this file is routinely **hundreds of MB**, and it is the exact same mistake as `curl`-ing a raw Go pprof profile to grep by hand: `jq`, `python -m json.load`, or `grep` over the whole array is slow, easy to get subtly wrong (matching the wrong process/thread, double-counting nested slices), and burns a huge amount of context if the output lands in a conversation. **Load it into Perfetto's `trace_processor` and query it with SQL instead** — this is the direct equivalent of `go tool pprof -top`: one purpose-built tool does the parsing/indexing, and you get ranked, aggregated answers instead of raw event soup.

### Get the tool (one-time)

```bash
curl -LO https://get.perfetto.dev/trace_processor
chmod +x trace_processor
# First run downloads the native binary for your platform to ~/.local/share/perfetto/prebuilts (cached after).
```

`trace_processor` loads Chrome's JSON trace format directly — **including gzipped `.json.gz` downloads**, no manual `gunzip` needed. It also loads `.perfetto-trace` protobuf traces, `.heapprofile` files, and Android traces, so the same tool covers Playwright's `browser.startTracing()` output and a manually-downloaded DevTools trace.

### Query mode (non-interactive — prefer this for scripted/agent use)

```bash
./trace_processor -q <(echo "SELECT name, COUNT(*) AS cnt, SUM(dur) AS total_ns FROM slice GROUP BY name ORDER BY total_ns DESC LIMIT 20;") mytrace.json.gz
```

Or drop into the interactive SQL shell for exploration: `./trace_processor mytrace.json.gz` then type queries at the `>` prompt. Durations (`dur`, `ts`) are in **nanoseconds**.

### Canonical queries (the `-top` / `-list` equivalents)

```sql
-- Top 20 event names by total time across the whole trace (go tool pprof -top)
SELECT name, COUNT(*) AS cnt, SUM(dur) AS total_ns
FROM slice GROUP BY name ORDER BY total_ns DESC LIMIT 20;

-- Long tasks (>50ms) on a named thread, with wall-clock offset from trace start
SELECT (s.ts - (SELECT MIN(ts) FROM slice)) / 1e6 AS ms_from_start,
       s.dur / 1e6 AS dur_ms, s.name, t.name AS thread
FROM slice s
JOIN thread_track tt ON s.track_id = tt.id
JOIN thread t ON tt.utid = t.utid
WHERE s.dur > 50 * 1e6
ORDER BY s.dur DESC LIMIT 30;

-- Discover what counter tracks exist before querying one blind (mirrors
-- "list available tag keys before guessing an ASL query" for Atlas) —
-- Chrome's JS-heap counter is typically named 'JS Heap' or similar; verify
-- per-trace rather than assuming.
SELECT DISTINCT name FROM counter_track;

-- JS heap size over time once you have the exact counter_track name
SELECT c.ts, c.value
FROM counter c JOIN counter_track ct ON c.track_id = ct.id
WHERE ct.name = 'JS Heap' ORDER BY c.ts;

-- GC pauses (self time), ranked — allocation-churn signal
SELECT name, COUNT(*) AS cnt, SUM(dur) AS total_ns, AVG(dur) AS avg_ns
FROM slice WHERE name LIKE '%GC%' GROUP BY name ORDER BY total_ns DESC;
```

**Gotcha learned the hard way**: a multi-process/multi-tab trace mixes every process's counters and threads in one file — `SELECT MIN(value) FROM counter ...` across all processes can return a near-zero value that belongs to an unrelated tab/extension, not the page you're debugging. Filter to the right `pid`/`upid` first (`SELECT * FROM process;` to find it) rather than trusting an unscoped aggregate.

### When to still use the DevTools UI instead

`trace_processor` is for *ranking and aggregating* — finding which function/task/counter dominates, across a trace too large to eyeball. It does not replace:
- **The flamechart itself** for understanding *why* a specific task is slow (call stack, nesting) — drag the same trace file into DevTools Performance panel for that.
- **Heap Snapshot comparison** (Step 5) — a `.heapsnapshot` is a different format (object graph, not a timeline) and needs the Memory panel or `--inuse` uses; `trace_processor` cannot substitute for finding *which objects* are retained, only *how much* memory a counter shows over time.

### LLM-native alternative

A community MCP server (`perfetto-1` on mcpmarket.com) wraps `trace_processor_shell` and lets an LLM run PerfettoSQL queries directly against a trace without shelling out — worth adopting if this analysis becomes frequent enough to justify adding an MCP server, but the `curl`+SQL-file approach above needs no setup and is fine for occasional use.

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
