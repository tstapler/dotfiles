# Capturing a Numeric Baseline and Verifying a Fix

## Playwright Baseline Script (Step 1)

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

## Verifying the Fix (Step 6)

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
