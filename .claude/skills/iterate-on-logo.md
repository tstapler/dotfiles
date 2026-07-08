---
name: iterate-on-logo
description: "Use this skill when Tyler asks to iterate on a logo, run an adversarial critique-fix loop, or says 'critique and fix this until done'. Runs scored critique → targeted SVG fix cycles until no fixable issues remain."
---

# iterate-on-logo — Adversarial Critique-Fix Loop

Invoke with: "adversarially critique [iteration-N] and fix it, loop until done"

No subprocess calls. Execute inline. Read the target SVG first, then cycle.

---

## Scoring Rubric

Score each dimension 1–3. Max 15. A round with no 1s is done.

| Dimension | 1 — Broken | 2 — Acceptable | 3 — Strong |
|---|---|---|---|
| **home_read** | Primary metaphor illegible at 200px | Readable with effort | Instant read |
| **brand_fit** | Off-palette or wrong mood | Correct colors, weak mood | Colors + mood both land |
| **distinctiveness** | Generic icon | Recognizable category | Memorable silhouette |
| **favicon_16px** | Collapses to noise | Survives as silhouette | Distinct at 16px |
| **direction_clarity** | No sense of movement | Implied direction | Unambiguous departure vector |

Score ≥ 12 (all 2s or better): declare done, no further iteration.  
Any dimension at 1: fix it, increment iteration number, loop.  
Max 5 rounds — escalate if still failing after round 5.

---

## Geometry Verification (Sortie road icon)

Before writing any SVG that places elements near the road edges, verify clearance:

**Road edge equation** (viewBox 0 0 512 512, V from (72,472)→(256,164)←(440,472)):
```
left_edge_center(y)  = 72  + 184 * (472 - y) / 308
right_edge_center(y) = 440 - 184 * (472 - y) / 308
road_stroke_width    = 32
left_boundary(y)     = left_edge_center(y)  - 16   ← visible left limit
right_boundary(y)    = right_edge_center(y) + 16   ← visible right limit
```

**Rule**: Any element tip that faces the road must satisfy:
- Left-side elements: tip_x < left_boundary(y) at the element's y
- Right-side elements: tip_x > right_boundary(y) at the element's y

Compute at the y of each arm/element tip before writing the rect.

**Centerline perspective** (scale factor approach):
```
s(y) = (y - 164) / 308          ← 0 at horizon (164), 1 at bottom (472)
dash_length(y)   = 42 * s(y)    ← reference 42px at y≈431
dash_sw(y)       = 14 * s(y)    ← reference sw=14 at y≈431
gap(y)           = 28 * s(y)    ← gap shrinks proportionally
```
Apply at each dash midpoint, working bottom-up (near to far).

**Drawing order** (later = on top):
1. Cacti / background elements
2. Road edge lines
3. Centerline dashes
4. Sun rays
5. Horizon circle (caps ray bases)

---

## Loop Protocol

### Round start

1. Read the current iteration SVG
2. Score all 5 dimensions
3. Print: `Round N — score X/15`
4. List findings: dimension, score, specific pixel/geometry evidence

### Fix step (only if any dimension scored 1)

1. Address the lowest-scoring dimension first
2. Verify geometry before writing (use road edge formula above if applicable)
3. Write the new SVG to `logos/iterations/iteration-{N+1}.svg`
4. Update the "Current direction" section of `logos/preview.html`:
   - Add new card at top with label `{N+1} — [one-line fix description] ★ LATEST`
   - Move prior LATEST card down, drop the ★ LATEST badge
5. State what changed and why in one sentence

### Termination conditions

| Condition | Action |
|---|---|
| All dimensions ≥ 2 | Declare done. Print final score. |
| Round 5 reached with 1s remaining | Escalate — describe what can't be auto-fixed and why |
| Remaining issues require concept change | Stop, present the issue to the user |

---

## File paths (Sortie project)

| Resource | Path |
|---|---|
| Iteration SVGs | `logos/iterations/iteration-N.svg` |
| Preview | `logos/preview.html` |
| Concepts | `logos/concepts/concept-*.svg` |
