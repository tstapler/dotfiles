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

Never skip this. "It feels slow" is not a measurement. Run this Playwright script before touching code; compare after fixes.

```javascript
// scripts/perf-baseline.js — run with: node scripts/perf-baseline.js
const { chromium } = require('playwright');

async function captureBaseline(url, scenarioFn, label = 'baseline') {
  const browser = await chromium.launch();
  const page = await browser.newPage();

  // Inject Web Vitals + Long Task observer
  await page.addInitScript(() => {
    window.__perfData__ = { longTasks: [], vitals: {} };
    new PerformanceObserver(list => {
      list.getEntries().forEach(e => window.__perfData__.longTasks.push({
        duration: e.duration, startTime: e.startTime
      }));
    }).observe({ entryTypes: ['longtask'] });
  });

  // Capture Chrome trace
  await browser.startTracing(page, {
    path: `trace-${label}.json`,
    screenshots: false,
    categories: ['devtools.timeline', 'v8', 'blink.user_timing', 'disabled-by-default-v8.cpu_profiler'],
  });

  const before = await page.metrics();
  await page.goto(url, { waitUntil: 'networkidle' });
  await scenarioFn(page);
  const after = await page.metrics();

  await browser.stopTracing();

  const delta = {
    scriptDuration:    (after.ScriptDuration    - before.ScriptDuration).toFixed(3),
    layoutCount:        after.LayoutCount        - before.LayoutCount,
    recalcStyleCount:   after.RecalcStyleCount   - before.RecalcStyleCount,
    heapGrowthMB:      ((after.JSHeapUsedSize    - before.JSHeapUsedSize) / 1024 / 1024).toFixed(2),
    nodes:              after.Nodes              - before.Nodes,
  };

  const longTasks = await page.evaluate(() => window.__perfData__.longTasks);
  console.log(`\n=== ${label} ===`);
  console.log('Metrics delta:', delta);
  console.log(`Long tasks (>50ms): ${longTasks.length}`, longTasks.map(t => `${t.duration.toFixed(0)}ms`));

  await browser.close();
  return { delta, longTasks, traceFile: `trace-${label}.json` };
}

// Usage:
captureBaseline('http://localhost:8543', async (page) => {
  await page.click('[data-testid="sessions-list"]');
  await page.waitForSelector('[data-testid="session-item"]');
}, 'sessions-list');
```

**Load the `.json` trace file**: Open Chrome DevTools → Performance tab → drag-and-drop the file. This gives you the exact flamechart, long tasks, and timeline for the scenario.

---

## Step 2 — Add React `<Profiler>` to Slow Subtrees

Wrap the component tree you suspect. `onRender` fires every commit; log `actualDuration` to spot expensive trees.

```tsx
import { Profiler, type ProfilerOnRenderCallback } from 'react';

const onRender: ProfilerOnRenderCallback = (
  id,             // which Profiler ("SessionList")
  phase,          // "mount" | "update" | "nested-update"
  actualDuration, // ms spent rendering this update
  baseDuration,   // ms if no memoization (worst-case reference)
) => {
  if (actualDuration > 16) {  // > 1 frame at 60fps
    console.warn(`[Profiler] ${id} (${phase}): ${actualDuration.toFixed(1)}ms  (base: ${baseDuration.toFixed(1)}ms)`);
  }
};

// Wrap the subtree under investigation:
<Profiler id="SessionList" onRender={onRender}>
  <SessionList />
</Profiler>
```

**Key ratio**: `actualDuration / baseDuration`
- Near **1.0** → memoization is absent or not helping; every component in the subtree re-renders
- Near **0.1** → memoization works; only ~10% of the subtree re-renders on updates

**React Performance Tracks (React 19 + Chrome DevTools)**: Open DevTools Performance panel, record, and look for the "Scheduler" and "Components" tracks. These appear automatically in dev builds. Look for:
- Wide bars in the **Blocking** lane → synchronous updates blocking interaction
- **Cascading updates** flag → a render triggered another render (typically `useEffect` setting state)

---

## Step 3 — Read the Chrome Performance Panel

### Recording a trace manually

1. Open DevTools → Performance tab
2. **CPU throttling**: set to `4×` or `6×` to simulate mobile (reproduces problems on fast machines)
3. Click **Record** → reproduce the slow action → **Stop**
4. Look at the **Main** thread row

### Reading the flamechart

| What you see | What it means |
|-------------|---------------|
| Red-flagged gray bars | Long Tasks (>50ms) — main thread blocked |
| Wide flat bars | High self-time — this function is expensive |
| Tall deep stacks | Long call chains — usually framework overhead, not your code |
| "Forced reflow" warning | Layout thrashing (read geometry + write style in a loop) |
| `(garbage collector)` bars | GC pressure — too many allocations |

**Bottom-Up tab**: Sort by "Self Time" to find the actual expensive function (not its callers).  
**Call Tree tab**: Sort by "Total Time" to find which entry point triggers the most work.

### Key scripting events to find in the timeline

| Event name | Diagnosis |
|-----------|-----------|
| `Timer Fired` repeatedly | `setInterval` / `setTimeout` doing expensive work |
| `Animation Frame Fired` | `requestAnimationFrame` loop — check what's inside |
| `Recalculate Style` | CSS selector matching triggered — check if batched |
| `Layout` after `Recalculate Style` | Full layout reflow — check for layout thrashing |
| `GC Event` > 5ms frequently | Allocation churn — look for object creation in hot paths |

---

## Step 4 — Diagnose by Layer

### React re-render cascade

**Symptom**: `<Profiler>` shows `actualDuration` close to `baseDuration`; Components track shows most of the tree re-rendering on every keystroke.

**Cause lookup**:

| Anti-pattern | Fix |
|-------------|-----|
| Inline `style={{ }}` or `onClick={() => fn()}` on a memoized child | Extract to `const` at module scope (objects) or `useCallback` (functions) |
| Context value is a new object every render | `useMemo(() => ({ count, setCount }), [count])` around context value |
| Array index used as `key` | Use stable item IDs as keys |
| `useEffect` sets state unconditionally | Derive value during render with `useMemo`; don't sync state to props |
| Expensive compute on every render | `useMemo(() => heavyFn(input), [input])` |

**why-did-you-render** (development only — install `@welldone-software/why-did-you-render`):
```javascript
// src/wdyr.js — import BEFORE React in dev only
if (process.env.NODE_ENV === 'development') {
  const whyDidYouRender = require('@welldone-software/why-did-you-render');
  whyDidYouRender(React, { trackAllPureComponents: true });
}
// Then on a specific component:
MyComponent.whyDidYouRender = true;
```
Console output: "Re-rendered — same props" with the specific prop that changed identity.

### Long tasks / JS-heavy interaction

**Symptom**: Performance panel shows red-flagged tasks >50ms on interaction; INP > 200ms.

Fix pattern — break work with `scheduler.yield()`:
```javascript
async function processLargeList(items) {
  const results = [];
  for (let i = 0; i < items.length; i++) {
    results.push(expensiveTransform(items[i]));
    // Yield every 50 items to unblock user input
    if (i % 50 === 0) {
      await scheduler.yield();  // or: await new Promise(r => setTimeout(r, 0));
    }
  }
  return results;
}
```

Use React's `startTransition` for non-urgent state updates that trigger expensive re-renders:
```javascript
const [isPending, startTransition] = useTransition();

function handleInput(value) {
  setInputValue(value);  // urgent — updates the input immediately
  startTransition(() => {
    setFilteredResults(expensiveFilter(value));  // non-urgent — can be interrupted
  });
}
```

### Layout thrashing

**Symptom**: "Forced reflow" warnings in Performance panel; `Layout` events interleaved with JS in the flamechart.

```javascript
// BAD — read → write → read (browser forced to relayout twice)
elements.forEach(el => {
  const w = el.offsetWidth;         // READ: forces layout
  el.style.width = (w + 10) + 'px'; // WRITE: invalidates layout
});

// GOOD — batch all reads, then all writes (one layout)
const widths = elements.map(el => el.offsetWidth);           // all READs
elements.forEach((el, i) => el.style.width = (widths[i] + 10) + 'px'); // all WRITEs
```

Properties that force layout: `offsetWidth/Height`, `clientWidth/Height`, `scrollTop`, `getBoundingClientRect()`, `getComputedStyle()`.

### Bundle size / dead code

**Measure unused JS** with the Playwright coverage API:
```javascript
await page.coverage.startJSCoverage();
await page.goto(url, { waitUntil: 'networkidle' });
// Interact with the main scenario
const coverage = await page.coverage.stopJSCoverage();

let used = 0, total = 0;
for (const entry of coverage) {
  total += entry.text.length;
  for (const range of entry.ranges) used += range.end - range.start;
}
console.log(`JS used: ${(used / total * 100).toFixed(1)}% of ${(total / 1024).toFixed(0)}KB`);
```

**Visualize with source-map-explorer** (works with any bundler):
```bash
npm install --save-dev source-map-explorer
npm run build
npx source-map-explorer 'build/static/js/*.js'
```

**What to look for**:
- Duplicate packages (two versions of same library)
- Large utility libraries included whole (e.g., all of lodash instead of `lodash/get`)
- `node_modules` in the critical bundle that should be lazy-loaded

Fix: dynamic `import()` for non-critical routes (React.lazy + Suspense):
```tsx
const HeavyPanel = React.lazy(() => import('./HeavyPanel'));

<Suspense fallback={<Spinner />}>
  <HeavyPanel />
</Suspense>
```

---

## Step 5 — Memory Leak Detection

**Symptom**: JS Heap in Task Manager grows over time and doesn't return to baseline after GC.

### Quick check via Playwright

```javascript
const before = await page.metrics();
// Perform 10 cycles of the leaky action (e.g., open/close modal)
for (let i = 0; i < 10; i++) {
  await page.click('[data-testid="open-modal"]');
  await page.click('[data-testid="close-modal"]');
}
// Force GC if possible, then wait
await page.evaluate(() => window.gc && window.gc());
await page.waitForTimeout(500);
const after = await page.metrics();

const leakMB = (after.JSHeapUsedSize - before.JSHeapUsedSize) / 1024 / 1024;
console.log(`Heap growth after 10 cycles: ${leakMB.toFixed(2)}MB`);
if (leakMB > 5) console.warn('Likely memory leak — investigate with DevTools Heap Snapshot');
```

### Chrome DevTools Memory panel workflow

1. **Heap Snapshot** → take snapshot A (baseline)
2. Perform the leaky action N times
3. **Heap Snapshot** → take snapshot B
4. Switch to **Comparison** view (dropdown in snapshot B)
5. Sort by **# New** — these objects were allocated and not freed

**Look for**:
- `Detached HTMLDivElement` / `Detached HTMLSpanElement` — DOM nodes removed from the tree but still referenced in JS
- React component instances that should have been unmounted
- Event listener accumulation (`EventListener` objects growing)

**Most common React leak**:
```tsx
// BAD — event listener added but never removed
useEffect(() => {
  window.addEventListener('resize', updateLayout);
  // missing cleanup!
}, []);

// GOOD
useEffect(() => {
  window.addEventListener('resize', updateLayout);
  return () => window.removeEventListener('resize', updateLayout);
}, []);
```

---

## Step 6 — Verify the Fix

Run the same baseline script from Step 1 with a new label; compare numbers:

```bash
node scripts/perf-baseline.js  # saves trace-after.json
```

**Pass criteria**:
- `scriptDuration` delta reduced by target %
- Long task count reduced or longest task < 50ms
- `<Profiler>` `actualDuration / baseDuration` ratio improved
- No new long tasks introduced elsewhere (check the full trace)
- If fixing a memory leak: heap growth across 10 cycles < 1MB

Load `trace-after.json` in DevTools alongside `trace-baseline.json` and confirm the specific long task is gone.

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
