# Diagnose by Layer (Step 4)

## React re-render cascade

**Symptom**: `<Profiler>` shows `actualDuration` close to `baseDuration`; Components track shows most of the tree re-rendering on every keystroke.

**Cause lookup**:

| Anti-pattern | Fix |
|-------------|-----|
| Inline `style={{ }}` or `onClick={() => fn()}` on a memoized child | Extract to `const` at module scope (objects) or `useCallback` (functions) |
| Context value is a new object every render | `useMemo(() => ({ count, setCount }), [count])` around context value |
| Array index used as `key` | Use stable item IDs as keys |
| `useEffect` sets state unconditionally | Derive value during render with `useMemo`; don't sync state to props |
| Expensive compute on every render | `useMemo(() => heavyFn(input), [input])` |

See [React Profiler](react-profiler.md) for the `why-did-you-render` tool that pinpoints which prop changed identity.

## Long tasks / JS-heavy interaction

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

## Layout thrashing

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

## Bundle size / dead code

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
