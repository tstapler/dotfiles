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

Write a complete self-contained HTML file with the Sankey diagram, a summary table, and a usage pill. Use the template in [HTML Template](references/html-template.md) verbatim — substitute `SANKEY_DATA` with the JSON built from parsing (below).

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

## References

- [HTML Template](references/html-template.md) — the full self-contained artifact page (styles, Sankey renderer, summary table)
