# Reading the Chrome Performance Panel (Step 3)

## Recording a trace manually

1. Open DevTools → Performance tab
2. **CPU throttling**: set to `4×` or `6×` to simulate mobile (reproduces problems on fast machines)
3. Click **Record** → reproduce the slow action → **Stop**
4. Look at the **Main** thread row

## Reading the flamechart

| What you see | What it means |
|-------------|---------------|
| Red-flagged gray bars | Long Tasks (>50ms) — main thread blocked |
| Wide flat bars | High self-time — this function is expensive |
| Tall deep stacks | Long call chains — usually framework overhead, not your code |
| "Forced reflow" warning | Layout thrashing (read geometry + write style in a loop) |
| `(garbage collector)` bars | GC pressure — too many allocations |

**Bottom-Up tab**: Sort by "Self Time" to find the actual expensive function (not its callers).
**Call Tree tab**: Sort by "Total Time" to find which entry point triggers the most work.

## Key scripting events to find in the timeline

| Event name | Diagnosis |
|-----------|-----------|
| `Timer Fired` repeatedly | `setInterval` / `setTimeout` doing expensive work |
| `Animation Frame Fired` | `requestAnimationFrame` loop — check what's inside |
| `Recalculate Style` | CSS selector matching triggered — check if batched |
| `Layout` after `Recalculate Style` | Full layout reflow — check for layout thrashing |
| `GC Event` > 5ms frequently | Allocation churn — look for object creation in hot paths |
