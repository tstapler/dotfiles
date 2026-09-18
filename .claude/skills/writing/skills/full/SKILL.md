---
description: Full writing-quality workflow — scope (audience/tone) -> multi-facet review (structure, readability, visuals, tone, humanize) as parallel subagents -> fix loop with fresh re-verification -> report. Entry point for improving any piece of writing, not just design docs.
---

# writing:full

Orchestrator for the general-purpose writing pipeline: establish who this is for and how it should sound, then run every applicable quality check as independent lean agents (see the `lean-agent-loop` skill), then fix and re-verify until clean or a round cap is hit. Mirrors `sdd:full`'s phase structure — each phase below delegates to its own skill and never duplicates that skill's logic — and reuses `design-doc-review:review`'s pipeline wholesale when the target is a design doc, rather than re-implementing structure/readability/visuals checks a second time.

**Target**: {{args}} — a file path. If omitted, use the doc already in context.

## Phase 1 — Scope

Run `writing:scope` against the target. Get back `{audience, tone, doc_type, purpose}`. Do not proceed until this resolves — every later phase's agent prompts need it.

## Phase 2 — Dispatch (parallel lean agents)

**If `doc_type` is "design doc / RFC"**: this repo already has a purpose-built pipeline for that shape (Decision requested / Non-goals / Alternatives / Risks structure, publish-target compatibility). Don't duplicate it — dispatch `design-doc-review:review` as one of the parallel agents below, and layer only the checks it doesn't already do (`writing:tone`, `writing-humanize`) alongside it:

```
Agent "design-doc-review": run design-doc-review:review against <path>. Return its final report (already includes its own fix loop).
Agent "tone": run writing:tone against <path>. Scope: {audience, tone, doc_type, purpose}. Return only its JSON summary.
Agent "humanize": run writing-humanize against <path>. Return its structured audit output.
```

**Otherwise** (blog post, PR description, general doc, personal note): dispatch the general-purpose checks directly:

```
Agent "structure": run technical-writing-coach against <path>, focused on the SUCCESS framework and decision-oriented density for this doc_type/purpose. Return findings with severity.
Agent "tone": run writing:tone against <path>. Scope: {audience, tone, doc_type, purpose}. Return only its JSON summary.
Agent "humanize": run writing-humanize against <path>. Return its structured audit output.
```

Launch all agents for the chosen branch **in a single message** (tier A, per `lean-agent-loop`). If parallel dispatch is unavailable, drop to the next tier in that skill's degraded-mode table and say which tier ran.

Skip `writing-humanize` entirely when scope's `tone` is not "match my own voice" and the doc_type is a design doc or other structured technical document where AI-authorship is disclosed/expected (check the doc's own header, e.g. this repo's "Discovery — AI-accelerated" status convention) — running an AI-detection-evasion audit on a document that says it's AI-accelerated is answering a question nobody asked. Still run it when `tone` is "match my own voice" regardless of doc_type, since voice-preservation is the point either way.

## Phase 3 — Triage

Combine results. `design-doc-review:review` (if dispatched) has already triaged and fixed its own findings — treat its report as final for those facets, don't re-triage them. For `writing:tone` and `writing-humanize`/`technical-writing-coach` findings:

- **Mechanically fixable**: humanize's vocabulary/structural/rhythm flags, tone's register/jargon mismatches with a clear direction, technical-writing-coach's density/structure fixes.
- **Author-input-needed**: anything where the fix requires content only the author has (a missing anecdote for authenticity, a purpose the author hasn't actually decided on yet).

Present both lists before touching the file. Ask which mechanically-fixable findings to apply (default: all).

## Phase 4 — Fix loop

Same shape as `design-doc-review:review`'s Phase 3: apply approved fixes directly (this coordinator edits, it doesn't delegate the edit to a lean agent), then re-dispatch **fresh** agents for every check that wasn't already passing — no memory of the prior round's findings fed in. Round cap: 3. A finding that persists after round 3 gets reported, not silently dropped.

## Phase 5 — Report

```
writing:full: <path>
Scope: doc_type=<...>, audience=<...>, tone=<...>
Tier: <A|B|C|D>
Rounds run: <N> / 3

| Check | Round 1 | Final |
|---|---|---|
| design-doc-review (if applicable) | ... | ... |
| structure (technical-writing-coach, if applicable) | fail (N) | pass |
| tone | fail (N) | pass |
| humanize | ... | ... |

Fixed automatically: <count>
Needs author input: <count>
Persisted after 3 rounds: <count, if any>
```
