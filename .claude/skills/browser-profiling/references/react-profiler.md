# React `<Profiler>` and Re-render Detection (Step 2)

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

## why-did-you-render (development only)

Install `@welldone-software/why-did-you-render`:

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
