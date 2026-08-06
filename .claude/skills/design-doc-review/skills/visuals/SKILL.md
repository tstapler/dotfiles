---
description: Check a design doc for prose that should be a diagram (architecture/sequence/flowchart/state) or a comparison table, based on mechanical structural signals in the text (step counts, participant counts, repeated comparison templates) — not taste. Does not evaluate content completeness (see design-doc-review:outline) or prose quality (see design-doc-review:readability). One check in the design-doc-review pipeline — run standalone or via design-doc-review:review.
---

# design-doc-review:visuals

Presentation-form check only — this skill does not evaluate whether the right topics are covered (see `design-doc-review:outline`) or whether prose is well-written (see `design-doc-review:readability`). It answers: **is this content trapped in a format that hides its structure from the reader?**

**Target**: {{args}} — a file path, or a doc already in context.

## Framework

Two independent detectors, both counting features of the actual text rather than judging quality:

1. **Diagram detector** — structural/behavioral content (topology, call order, state machines) encoded as linear prose is a format mismatch: prose is 1-D, the underlying information is 2-D (time × participant, or state × transition). Applies to the *Technical spec* layer of the Three-Layer Onion (how it works), not the *Problem* or decision-narrative layers — see guardrail on argumentative content below.
2. **Table detector** — N options scored against the same M criteria is a format mismatch when rendered as N separate paragraphs: the reader must hold every prior paragraph in memory to compare. Applies wherever the doc is enumerating parallel facts, most commonly *Alternatives Considered* / *Risks* / *Rollout stages*, not wherever it's making a values judgment.

Both detectors are counting exercises: extract the axes from the prose and see if 3+ points exist on each.

## Checklist

### Diagram signals — check each candidate paragraph/section against these

- [ ] **Sequence**: paragraph names 3+ steps, in order, where two or more different components/actors each send or receive something (e.g. "A calls B, B queries C, C returns to B, B notifies D") → flag as **sequence diagram** candidate.
- [ ] **Sequence — participant count**: a single interaction narrative names 4+ distinct components/services as senders or receivers → flag as **sequence diagram** candidate (participant count exceeds what a reader can track in prose).
- [ ] **State machine**: paragraph or list enumerates 3+ named states plus, for at least two of them, an explicit "when X happens, it transitions to Y" rule → flag as **state diagram** candidate.
- [ ] **Flowchart**: paragraph or numbered list describes a decision process with 2+ branch points ("if X, do A; otherwise do B, then check Y...") → flag as **flowchart** candidate.
- [ ] **Architecture / topology**: paragraph describes which components exist and how they connect/bound each other, containing 2+ spatial/topological prepositions ("sits between," "in front of," "proxies to," "upstream of," "on top of") → flag as **architecture (context/container) diagram** candidate.
- [ ] **Before/after topology change**: doc describes a migration/refactor where the set of callers or the request path changes, described in prose rather than as paired diagrams → flag as **before/after architecture diagram** candidate.
- [ ] **Density overrun**: a single paragraph exceeds ~150 words, or a single bullet list exceeds ~5 items, in the sole service of describing one flow/relationship → flag as diagram candidate (type per whichever of the above the content matches) regardless of whether individual sentences are otherwise fine.
- [ ] **Diagram-without-prose gap** (inverse finding): a diagram exists but has no adjacent sentence or caption stating what it shows or why it's structured that way → flag as missing companion prose, not a missing diagram.
- [ ] **Prose-without-diagram gap on multi-system flow**: doc describes a request/data flow crossing 3+ systems/services and never provides a diagram anywhere in the doc establishing the system boundary → flag as missing context diagram.

### Table signals — check each candidate paragraph/section against these

- [ ] **N×M pattern**: doc discusses 3+ alternatives/options, and 2+ of them are each evaluated against the same named criteria (cost, latency, risk, effort, etc.) → flag as **comparison table** candidate.
- [ ] **Template repetition**: 3+ paragraphs share an extractable sentence template ("Option X does <verb>, costs <value>, but <drawback>") → flag as **comparison table** candidate.
- [ ] **Pro/con list**: a bulleted list has 3+ items where each item carries an explicit pro and con (or a qualitative rating: Good/Fair/Poor, Low/Medium/High risk) → flag as **comparison table** candidate.
- [ ] **Column-header test**: for a candidate section, name 3+ shared column headers that every item's paragraph maps into without leftover unique narrative → if the test passes cleanly, flag as table candidate; if paragraphs contain "because" reasoning that resists reduction to a cell, do NOT flag (keep in prose — see guardrail).
- [ ] **Back-reference tell**: doc contains phrases like "as noted above for Option A" or "unlike the previous approach" used to compare items → flag as comparison table candidate (back-referencing signals a relational structure prose is failing to hold).
- [ ] **Malformed table** (inverse finding): an existing table has only 1 row or only 1 column of actual data → flag as "not two-dimensional, should be a list/bullets instead" (per Google dev-docs style: single-row/column tables aren't tables).

## Severity

| Severity | Meaning |
|---|---|
| Blocking | Reader cannot reliably reconstruct the flow/state machine/comparison from the prose alone — e.g. 4+ participant sequence in prose, or 3+ options × 3+ criteria spread across paragraphs with no table. Directly causes review friction ("wait, which calls which?"). |
| Notable | Format mismatch exists and adds real cognitive load, but the content is still recoverable with effort — e.g. a 3-step sequence in prose, a 3-option pro/con list not yet tabulated, a diagram present but missing a one-line caption. |
| Minor | Stylistic/consistency issue — e.g. a malformed single-row table, a density-overrun paragraph that's borderline (120–150 words), inconsistent diagram type for similar content elsewhere in the doc. |

## Output

Write full analysis (evidence quotes, axis extraction per flagged section) to `/tmp/lean-design-doc-review-visuals-<ts>.md`.

Return only this structured summary:

```json
{
  "category": "visuals",
  "status": "pass" | "fail",
  "count": <number of blocking+notable findings>,
  "findings": [
    {"section": "§3.2", "kind": "diagram" | "table", "suggested_type": "sequence" | "architecture" | "state" | "flowchart" | "comparison-table" | "malformed-table" | "missing-caption", "severity": "blocking" | "notable" | "minor", "note": "one line: the axis/count evidence + the fix direction"}
  ]
}
```

`status: "pass"` only if there are zero `blocking` findings.

## When invoked standalone (not via the coordinator)

Print findings as a table (Section | Kind | Suggested type | Severity | Note) rather than raw JSON. Ask the author before inserting a drafted diagram (mermaid) or table skeleton — never auto-insert visuals, since the correct diagram type/exact table columns require domain judgment the check can't verify from prose alone; propose the skeleton and the extracted axes, let the author fill and confirm.

## False-positive guardrails — do NOT flag

- **Single-component docs.** If the whole doc describes one service/component with no cross-service interaction, don't demand an architecture diagram — there's no topology to show.
- **2-item comparisons.** Two options compared once is a normal paragraph ("we chose A over B because..."); the N×M/table signals require 3+ options or 3+ shared criteria. Don't tabulate a binary choice.
- **Decision/argument content, not structure.** Values-tradeoffs, tenets, or "why we're doing this at all" reasoning (per Amazon 6-pager precedent) should stay prose even if it superficially lists pros/cons — flag only when the pros/cons are parallel *facts* about options (cost, latency measured), not competing *values* being weighed.
- **Cell content requiring causal "because" reasoning.** If collapsing a paragraph into a table row would strip the "why this fails under our workload" reasoning with no room to preserve it (and no hybrid table+prose-per-row option was considered), don't force the table — flag "hybrid: enumerate in table, keep rationale in prose" instead of a straight table demand.
- **Already-adequate diagrams.** If a diagram covering the flow already exists anywhere in the doc (not necessarily inline at the flagged paragraph), don't also flag the prose describing the same flow — check the whole doc for an existing diagram before flagging, not just the local section.
- **Short/low-stakes docs.** A one-pager or a doc explicitly scoped as a stub/RFC-lite shouldn't be held to the same density thresholds (150-word paragraph, 5-item bullet list) as a full design doc — scale the density thresholds down in severity (blocking→notable, notable→minor) for docs under ~2 pages.
- **Sequential lists that aren't flows.** A numbered list of unordered requirements, non-goals, or checklist items (no actor-to-actor handoff, no branching) is not a sequence-diagram candidate even if it has 3+ items — the sequence/flowchart signals require actors exchanging control or explicit branches, not just enumeration.
- **Single-row/column tables already flagged elsewhere.** Don't double-flag a malformed table both here and as a readability/outline finding — this check owns table *shape* (2D-ness), not table *content* accuracy.
