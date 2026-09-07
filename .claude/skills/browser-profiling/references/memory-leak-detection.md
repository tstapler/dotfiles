# Memory Leak Detection (Step 5)

**Symptom**: JS Heap in Task Manager grows over time and doesn't return to baseline after GC.

## Quick check via Playwright

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

## Chrome DevTools Memory panel workflow

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
