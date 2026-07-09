# context-viz — Context Window Sankey Visualizer

Generates a self-contained HTML artifact showing Claude Code context window usage as a Sankey diagram flowing from total capacity → categories → top sub-items.

---

## When invoked

1. Tell the user: "Run `/context all expand` and paste the output here, or I'll use whatever context data is already visible in our conversation."
2. Parse the data (see **Parsing** below).
3. Build the HTML page (see **HTML Template** below).
4. Call the `Artifact` tool with `file_path` pointing to the generated file, `favicon` = "📊", and a one-sentence `description`.

---

## Parsing `/context` output

### Top-level table

```
Context Usage  Model: claude-sonnet-4-6  Tokens: 91k / 200k (45%)
Category        | Tokens | Percentage
System prompt   |  6.6k  |  3.3%
System tools    | 29.9k  | 14.9%
MCP tools       | 38.1k  | 19.0%
Custom agents   |  2.7k  |  1.4%
Memory files    | 10.5k  |  5.3%
Skills          |  3.1k  |  1.5%
Messages        |   110  |  0.1%
Free space      |   76k  | 38.0%
```

Parse rules:
- Extract `totalTokens` from "Tokens: Xk / 200k" — use 200000 as capacity if missing.
- Extract `usedTokens` from the same line.
- For each row, strip whitespace, parse the token value (handle `k` suffix → multiply by 1000).
- Map category names to short keys:

| Raw name        | Key          | Color         |
|-----------------|--------------|---------------|
| System prompt   | system       | #6366f1 (indigo) |
| System tools    | tools        | #8b5cf6 (violet) |
| MCP tools       | mcp          | #ec4899 (pink)   |
| Custom agents   | agents       | #f59e0b (amber)  |
| Memory files    | memory       | #10b981 (emerald)|
| Skills          | skills       | #14b8a6 (teal)   |
| Messages        | messages     | #3b82f6 (blue)   |
| Free space      | free         | #6b7280 (gray)   |

### Sub-items (expanded output)

After each category block there may be indented sub-items, e.g.:

```
  MCP tools (38.1k)
    brave-search: 2.1k
    context7: 4.8k
    slack: 12.3k
    ...
```

Or memory files:

```
  Memory files (10.5k)
    ~/.claude/CLAUDE.md: 3.2k
    ~/.claude/RTK.md: 0.4k
    /project/CLAUDE.md: 6.9k
```

Parse rules for sub-items:
- Match lines starting with 2+ spaces followed by `name: Xk` or `name (Xk)`.
- Group under the preceding category.
- Keep top 6 sub-items per category by token count; collapse the rest into "Other".
- If no sub-items present, show a single node for that category with no children.

---

## HTML Template

Write a complete self-contained HTML file. Use the structure below verbatim for the Sankey — substitute `SANKEY_DATA` with the JSON built from parsing.

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Context Window Usage</title>
<style>
  /* === Reset & base === */
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    background: #0f172a; color: #e2e8f0;
    min-height: 100vh; padding: 24px;
  }
  h1 { font-size: 1.4rem; font-weight: 700; color: #f1f5f9; margin-bottom: 4px; }
  .subtitle { font-size: 0.85rem; color: #94a3b8; margin-bottom: 24px; }

  /* === Sankey container === */
  #sankey { width: 100%; overflow-x: auto; }
  svg text { font-family: inherit; }

  /* === Summary table === */
  table { width: 100%; border-collapse: collapse; margin-top: 32px;
          font-size: 0.85rem; }
  th { text-align: left; padding: 8px 12px; color: #94a3b8;
       border-bottom: 1px solid #1e293b; font-weight: 600; }
  td { padding: 8px 12px; border-bottom: 1px solid #1e293b; }
  tr:hover td { background: #1e293b; }
  .bar-cell { width: 160px; }
  .bar-bg { background: #1e293b; border-radius: 4px; height: 8px; overflow: hidden; }
  .bar-fill { height: 8px; border-radius: 4px; }

  /* === Usage pill === */
  .usage-pill {
    display: inline-flex; align-items: center; gap: 8px;
    background: #1e293b; border-radius: 9999px;
    padding: 6px 16px; font-size: 0.9rem; margin-bottom: 20px;
  }
  .usage-pct { font-weight: 700; font-size: 1.1rem; }
</style>
</head>
<body>
<h1>Context Window Usage</h1>
<p class="subtitle" id="subtitle">Loading…</p>

<div class="usage-pill">
  <span>Used:</span>
  <span class="usage-pct" id="pct-label">—</span>
  <span id="token-label" style="color:#94a3b8">— / 200k tokens</span>
</div>

<div id="sankey"></div>

<table>
  <thead>
    <tr>
      <th>Category</th>
      <th>Tokens</th>
      <th>%</th>
      <th class="bar-cell">Usage</th>
    </tr>
  </thead>
  <tbody id="table-body"></tbody>
</table>

<script>
// ─── DATA ───────────────────────────────────────────────────────────────────
const DATA = SANKEY_DATA; // replaced at generation time

// ─── HELPERS ────────────────────────────────────────────────────────────────
function fmtK(n) {
  if (n >= 1000) return (n / 1000).toFixed(n >= 10000 ? 0 : 1) + 'k';
  return String(Math.round(n));
}

// ─── SUBTITLE & PILLS ───────────────────────────────────────────────────────
const cap = DATA.capacity;
const used = DATA.usedTokens;
const pct = ((used / cap) * 100).toFixed(1);
document.getElementById('subtitle').textContent =
  `Model: ${DATA.model}  ·  Snapshot taken ${DATA.timestamp}`;
document.getElementById('pct-label').textContent = pct + '%';
document.getElementById('token-label').textContent =
  `${fmtK(used)} / ${fmtK(cap)} tokens`;

// ─── SUMMARY TABLE ──────────────────────────────────────────────────────────
const tbody = document.getElementById('table-body');
DATA.categories.forEach(cat => {
  const p = ((cat.tokens / cap) * 100).toFixed(1);
  const tr = document.createElement('tr');
  tr.innerHTML = `
    <td><span style="display:inline-block;width:10px;height:10px;
        border-radius:2px;background:${cat.color};margin-right:6px;
        vertical-align:middle"></span>${cat.label}</td>
    <td>${fmtK(cat.tokens)}</td>
    <td>${p}%</td>
    <td class="bar-cell">
      <div class="bar-bg">
        <div class="bar-fill" style="width:${Math.min(p,100)}%;background:${cat.color}"></div>
      </div>
    </td>`;
  tbody.appendChild(tr);
});

// ─── SANKEY ──────────────────────────────────────────────────────────────────
(function drawSankey() {
  const W = Math.min(window.innerWidth - 48, 900);
  const H = 420;
  const PAD = { top: 20, right: 20, bottom: 20, left: 20 };
  const COL_W = 24;          // node width
  const GAP = 6;             // gap between flows

  // Build node list: [root, ...categories, ...subitems]
  const nodes = [];
  const links = [];

  // Root node
  nodes.push({ id: 'root', label: `Total\n${fmtK(cap)}`, color: '#475569', value: cap });

  // Category nodes + links from root
  DATA.categories.forEach(cat => {
    if (cat.key === 'free') return; // free shown separately
    nodes.push({ id: cat.key, label: cat.label, color: cat.color, value: cat.tokens });
    links.push({ source: 'root', target: cat.key, value: cat.tokens });
  });

  // Free space node
  const freecat = DATA.categories.find(c => c.key === 'free');
  if (freecat) {
    nodes.push({ id: 'free', label: 'Free space', color: freecat.color, value: freecat.tokens });
    links.push({ source: 'root', target: 'free', value: freecat.tokens });
  }

  // Sub-item nodes + links from categories
  DATA.categories.forEach(cat => {
    if (!cat.children || cat.children.length === 0) return;
    cat.children.forEach(child => {
      const sid = cat.key + '_' + child.label.replace(/\W+/g, '_');
      nodes.push({ id: sid, label: child.label, color: cat.color + 'bb', value: child.tokens });
      links.push({ source: cat.key, target: sid, value: child.tokens });
    });
  });

  // Layout: 3 columns  [root | categories | subitems]
  const cols = [
    nodes.filter(n => n.id === 'root'),
    nodes.filter(n => DATA.categories.map(c=>c.key).includes(n.id) || n.id === 'free'),
    nodes.filter(n => !DATA.categories.map(c=>c.key).includes(n.id) && n.id !== 'root')
  ];

  const innerH = H - PAD.top - PAD.bottom;
  const colX = [
    PAD.left,
    PAD.left + (W - PAD.left - PAD.right - COL_W) * 0.3,
    PAD.left + (W - PAD.left - PAD.right - COL_W) * 0.65
  ];

  // Scale: total value maps to innerH
  const scale = v => (v / cap) * innerH;

  // Assign Y positions within each column
  function layoutCol(col, colIdx) {
    const totalFlow = col.reduce((s, n) => s + n.value, 0);
    const totalGap = GAP * (col.length - 1);
    let y = PAD.top + (innerH - scale(totalFlow) - totalGap) / 2;
    col.forEach(n => {
      n.x = colX[colIdx];
      n.y = y;
      n.h = Math.max(scale(n.value), 2);
      y += n.h + GAP;
    });
  }

  cols.forEach((col, i) => layoutCol(col, i));

  // Build id → node map
  const nodeMap = {};
  nodes.forEach(n => nodeMap[n.id] = n);

  // SVG
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('width', W);
  svg.setAttribute('height', H);
  svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
  svg.style.display = 'block';

  // Draw flows (paths)
  const sourceOffsets = {}, targetOffsets = {};
  links.forEach(lk => {
    const src = nodeMap[lk.source];
    const tgt = nodeMap[lk.target];
    if (!src || !tgt) return;

    const so = sourceOffsets[lk.source] || 0;
    const to = targetOffsets[lk.target] || 0;
    const h = Math.max(scale(lk.value), 1);

    const x0 = src.x + COL_W;
    const y0 = src.y + so;
    const x1 = tgt.x;
    const y1 = tgt.y + to;
    const cx = (x0 + x1) / 2;

    const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    path.setAttribute('d', `M${x0},${y0} C${cx},${y0} ${cx},${y1} ${x1},${y1}
                             L${x1},${y1+h} C${cx},${y1+h} ${cx},${y0+h} ${x0},${y0+h} Z`);
    path.setAttribute('fill', tgt.color);
    path.setAttribute('opacity', '0.35');
    svg.appendChild(path);

    sourceOffsets[lk.source] = so + h + 1;
    targetOffsets[lk.target] = to + h + 1;
  });

  // Draw nodes (rectangles)
  nodes.forEach(n => {
    const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
    rect.setAttribute('x', n.x);
    rect.setAttribute('y', n.y);
    rect.setAttribute('width', COL_W);
    rect.setAttribute('height', Math.max(n.h, 2));
    rect.setAttribute('fill', n.color);
    rect.setAttribute('rx', 3);
    svg.appendChild(rect);

    // Label
    const isLeft = n.id === 'root';
    const isRight = cols[2].includes(n);
    const lx = isLeft ? n.x - 6 : n.x + COL_W + 6;
    const anchor = isLeft ? 'end' : 'start';
    const ly = n.y + n.h / 2;

    if (n.h > 8) { // only label if tall enough
      const lines = n.label.split('\n');
      lines.forEach((line, i) => {
        const t = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        t.setAttribute('x', lx);
        t.setAttribute('y', ly + (i - (lines.length - 1) / 2) * 13);
        t.setAttribute('text-anchor', anchor);
        t.setAttribute('dominant-baseline', 'middle');
        t.setAttribute('font-size', isRight ? '10' : '11');
        t.setAttribute('fill', '#cbd5e1');
        t.textContent = line;
        svg.appendChild(t);
      });
    }
  });

  document.getElementById('sankey').appendChild(svg);
})();
</script>
</body>
</html>
```

### Building `SANKEY_DATA`

Replace the `SANKEY_DATA` placeholder with a JSON literal of this shape:

```json
{
  "model": "claude-sonnet-4-6",
  "timestamp": "2026-07-02 14:30",
  "capacity": 200000,
  "usedTokens": 91000,
  "categories": [
    {
      "key": "system",
      "label": "System prompt",
      "color": "#6366f1",
      "tokens": 6600,
      "children": []
    },
    {
      "key": "mcp",
      "label": "MCP tools",
      "color": "#ec4899",
      "tokens": 38100,
      "children": [
        { "label": "slack",     "tokens": 12300 },
        { "label": "context7",  "tokens": 4800 },
        { "label": "Other",     "tokens": 21000 }
      ]
    },
    {
      "key": "free",
      "label": "Free space",
      "color": "#6b7280",
      "tokens": 76000,
      "children": []
    }
  ]
}
```

Include all categories; include `children` only for categories that have expanded sub-item data in the pasted output.

---

## Output

- Write the HTML to the scratchpad directory (use `$SCRATCHPAD` or `/tmp/context-viz.html` if scratchpad unavailable).
- Call `Artifact` with:
  - `file_path`: path to the written file
  - `favicon`: "📊"
  - `description`: "Claude Code context window usage — Sankey diagram + summary table"
  - `label`: "context-viz v1"

---

## Edge cases

- No sub-items in output → `children: []` for all categories; Sankey shows only two columns.
- Missing "Free space" row → compute it as `capacity - sum(all other categories)`.
- Token value like `110` (no k suffix) → treat as raw integer.
- If user doesn't paste output, remind them: "Run `/context all expand` (or just `/context`) and paste here."
