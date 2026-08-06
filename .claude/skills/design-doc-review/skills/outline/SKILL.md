---
description: Check a design doc / RFC's structure against the required topic set (problem, non-goals, alternatives, risks, rollout) AND verify every open question/decision ask names a decider, deadline, and default-if-silence. Flags missing or weak sections. One check in the design-doc-review pipeline — run standalone or via design-doc-review:review.
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

## Decision Ask (checked independently of the three layers)

The whole point of a design doc review is a room full of people's time spent extracting a decision. A doc can nail all three layers and still waste that time if the reader has to reconstruct "so what do you actually need from us?" by inference. Check this explicitly, not as a side effect of Layer 1/3 checks.

For **every** open question, decision request, or "needs review input" flag in the doc (usually but not always in an Open Questions / Decision Needed section):

- [ ] It is phrased as a concrete decision, not a topic — "should we scope this to Alternative B or the full process?" not "there's some ambiguity about scope"
- [ ] It names who decides (a person, a role, or "this review") — not left implicit
- [ ] It states a deadline or trigger ("before Wk 0 starts", "by end of review") — not open-ended
- [ ] It states a default-if-silence — what happens if nobody answers by the deadline. Absence of a default is what turns a question into permanent bikeshedding.
- [ ] Blocking questions (ones that gate the rest of the doc/plan) are visibly distinguished from informational ones — a reader shouldn't have to guess which of five "Open Questions" is load-bearing
- [ ] The set of asks is complete and non-redundant — every genuine decision point the doc raises anywhere in its body (not just ones the author happened to list) shows up in this set once, in one place, not scattered

This is the same "Decision requested" pattern `design-doc-review:readability` looks for in the main body (numbered asks, one owner, one default-if-silence, each per row) — that skill flags *prose* burying the ask; this check verifies the ask actually *exists* and is *complete* as a structural matter, independent of how well it reads.

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
- [ ] Decision Ask: every open question/decision request names a decider, a deadline, and a default-if-silence (see Decision Ask section above)
- [ ] Decision Ask: blocking vs. informational questions are distinguishable, and the set is complete/non-redundant
- [ ] Doc is not too long to read in one sitting for its stakes — if it is, does it push detail to an appendix rather than the main body (see the Proportionality note in CLAUDE.md: comments/PRs/docs should carry only what a reviewer of *this* artifact would ask for)

## Severity

| Severity | Meaning |
|---|---|
| `missing` | Topic absent entirely |
| `weak` | Topic present but not falsifiable/actionable — asserted rather than shown |
| `ok` | Present and reviewable as-is |

A `missing` or `weak` at Layer 1 outranks every Layer 2/3 finding — say so first. A `missing` or `weak` Decision Ask finding ranks with Layer 1: it doesn't matter how sound the content is if the review can't tell what it's being asked to decide — say it right after any Layer 1 findings.

## Output

Write full analysis (quotes, line refs, per-item reasoning) to `/tmp/lean-design-doc-review-outline-<ts>.md`.

Return only this structured summary (this is what a coordinator running this as a lean agent — see `lean-agent-loop` — reads; keep it small):

```json
{
  "category": "outline",
  "status": "pass" | "fail",
  "count": <number of missing+weak findings>,
  "findings": [
    {"layer": 1, "topic": "non-goals", "severity": "missing", "note": "one line, specific"},
    {"layer": "decision-ask", "topic": "open-question-1", "severity": "weak", "note": "one line, specific — e.g. missing default-if-silence"}
  ]
}
```

`status: "pass"` only if there are zero `missing` findings at any layer, zero `weak` findings at Layer 1, and zero `missing`/`weak` Decision Ask findings.

## When invoked standalone (not via the coordinator)

After writing the summary, print it as a table and stop — do not auto-fix. Auto-fixing is the coordinator's job (`design-doc-review:review`), because fixing an outline gap usually requires content only the author has (e.g. "what *is* the rollback plan"), not something this check can infer.
