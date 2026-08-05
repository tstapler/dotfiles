---
description: Check a design doc / RFC's structure against the required topic set (problem, non-goals, alternatives, risks, rollout, decision mechanism). Flags missing or weak sections. One check in the design-doc-review pipeline — run standalone or via design-doc-review:review.
---

# design-doc-review:outline

Structural check only — this skill does not touch prose quality (see `design-doc-review:readability` for that). It answers one question per section: **is the topic covered, and covered well enough to make a decision from?**

**Target**: {{args}} — a file path, or a doc already in context.

## Framework — Three-Layer Onion

Adapted from [[Design Documents]] / `eng-design-review`. A design doc has three layers; a flaw in a lower-numbered layer makes the ones above it moot, so check in this order and stop escalating severity once a layer is broken.

**Layer 1 — Problem**
- Problem statement: specific, not generic ("latency is bad" vs "p99 write latency exceeds 400ms under X load")
- Stakeholders / affected systems named
- **Non-goals stated explicitly** — not just "things we won't do" but things that could reasonably be in scope and are deliberately excluded. A doc with goals but no non-goals almost always scope-creeps in review.
- Functional and non-functional requirements present (throughput, latency, availability, retention — whatever applies)

**Layer 2 — Functional spec**
- Describes how the system behaves from the outside, before describing how it's built
- Alternatives considered, with a rejection rationale each — not just "we chose X" but "we considered Y and Z, rejected because..."
- The functional spec visibly satisfies the Layer 1 requirements (traceable, not asserted)

**Layer 3 — Technical spec**
- Implementation plan demonstrates feasibility, not just intent
- Operational concerns addressed: monitoring, rollback, load/capacity testing, steady-state maintenance (whatever the domain's equivalent of autovacuum/compaction/index maintenance is)
- Irreversible decisions are called out as irreversible and carry stronger justification than reversible ones
- Prior art / prior org decisions in the same space are acknowledged, not silently contradicted

## Checklist

- [ ] L1: Problem statement is specific and falsifiable
- [ ] L1: Non-goals stated (not just omissions)
- [ ] L1: Requirements explicit (functional + non-functional)
- [ ] L2: Alternatives considered with rejection rationale
- [ ] L2: Functional spec traces to L1 requirements
- [ ] L3: Irreversible decisions flagged and justified
- [ ] L3: Operational concerns addressed
- [ ] L3: Rollback / reversal plan stated
- [ ] L3: Prior org decisions acknowledged
- [ ] A decision mechanism is named (who decides, by when, what happens on silence) — its absence is what turns an RFC into permanent bikeshedding
- [ ] Doc is not too long to read in one sitting for its stakes — if it is, does it push detail to an appendix rather than the main body (see the Proportionality note in CLAUDE.md: comments/PRs/docs should carry only what a reviewer of *this* artifact would ask for)

## Severity

| Severity | Meaning |
|---|---|
| `missing` | Topic absent entirely |
| `weak` | Topic present but not falsifiable/actionable — asserted rather than shown |
| `ok` | Present and reviewable as-is |

A `missing` or `weak` at Layer 1 outranks every Layer 2/3 finding — say so first.

## Output

Write full analysis (quotes, line refs, per-item reasoning) to `/tmp/lean-design-doc-review-outline-<ts>.md`.

Return only this structured summary (this is what a coordinator running this as a lean agent — see `lean-agent-loop` — reads; keep it small):

```json
{
  "category": "outline",
  "status": "pass" | "fail",
  "count": <number of missing+weak findings>,
  "findings": [
    {"layer": 1, "topic": "non-goals", "severity": "missing", "note": "one line, specific"}
  ]
}
```

`status: "pass"` only if there are zero `missing` findings at any layer and zero `weak` findings at Layer 1.

## When invoked standalone (not via the coordinator)

After writing the summary, print it as a table and stop — do not auto-fix. Auto-fixing is the coordinator's job (`design-doc-review:review`), because fixing an outline gap usually requires content only the author has (e.g. "what *is* the rollback plan"), not something this check can infer.
