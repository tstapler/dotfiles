---
description: Full writing-quality workflow — scope (audience/tone) -> outline/flow review -> multi-facet prose review (structure, readability, visuals, tone, humanize) as parallel subagents -> fix loop with fresh re-verification -> report. Entry point for improving any piece of writing, not just design docs.
---

# writing:full

Orchestrator for the general-purpose writing pipeline: establish who this is for and how it should sound, then check that the skeleton flows before polishing any sentence, then run every applicable prose-quality check as independent lean agents (see the `lean-agent-loop` skill), then fix and re-verify until clean or a round cap is hit. Mirrors `sdd:full`'s phase structure — each phase below delegates to its own skill and never duplicates that skill's logic — and reuses `design-doc-review:review`'s pipeline wholesale when the target is a design doc, rather than re-implementing structure/readability/visuals checks a second time.

**Target**: {{args}} — a file path. If omitted, use the doc already in context.

See `../../CHECKLIST.md` for the running index of every mechanical check across this pipeline —
what it catches, the research/citation behind it, and where it's implemented. Add to that file
(not here) whenever a new pattern is noticed or researched; this file stays about orchestration.

## Phase 0 — Outline snapshot (bridge to `docs:*`)

`docs:write`'s own review gate and this pipeline used to be two disconnected islands — a doc
authored via `docs:define`→`docs:outline`→`docs:draft` had no path back into `writing:full`'s
fuller check set, and `writing:full` had no record of the outline a doc was built from, so a later
review pass re-derived structure from scratch every time.

**Topic key**: the target's parent directory name if the file is `README.md`/`index.md` (matches
this repo's `<project>/README.md` convention and `docs:write`'s `doc_plans/<topic>/`), else the
target's basename without extension. For a multi-file project directory (several docs sharing one
`doc_plans/<topic>/outline.md`, e.g. this repo's `<project>/README.md` plus sibling appendix docs),
extend the existing file with a section per doc rather than creating a second topic key for the
same project.

Look for `doc_plans/<topic>/outline.md`. If it exists, read it and carry it into Phase 2 as known
structure context — Phase 2 checks the *current* doc against that outline's sections, not a
re-derived skeleton. If it doesn't exist, don't block; derive one now (real section titles + a
one-line annotation each) for Phase 2 to work from, and Phase 6 writes it to disk either way.

## Phase 1 — Scope

Run `writing:scope` against the target. Get back `{audience, tone, doc_type, purpose}`. Do not proceed until this resolves — every later phase's agent prompts need it.

## Phase 2 — Outline review (flow)

Prose-level polish on a skeleton that's in the wrong shape just rewrites the same passage twice once
the skeleton gets fixed — so structure gets adversarially checked before any sentence does.

Dispatch `writing:outline-flow` against the Phase 0 outline snapshot, with the Phase 1 scope. It
looks for missing/misordered/redundant/unearned sections and hollow heading names — see that skill
for the full check list and severity table.

Findings split the same way Phase 4 will split prose findings, but land here, immediately, not in
the shared triage:

- **Mechanically fixable structural moves** (reorder, rename a hollow heading, merge two sections
  whose annotations duplicate each other) — apply directly. Default: apply all `notable`+ findings
  unless the user says otherwise; a `nit`-only heading-name batch still needs a one-line confirm
  since renaming is user-facing.
- **Cuts and "does this section earn its place" calls** — always author-input-needed per
  `writing:outline-flow`'s own contract. Present the finding and the reasoning, then wait.

Re-run `writing:outline-flow` once after applying fixes (fresh agent, no memory of round 1) to
confirm the reorder/merge didn't introduce a new redundant-section or wrong-order finding. Cap at 2
rounds here — this phase is cheaper to re-run than Phase 5's prose fix loop, but an outline that
still doesn't converge after 2 rounds is a sign the doc's scope itself is unsettled, which is a
Phase 1 problem, not something more structural churn fixes.

Only after this phase reports `pass` (or the user explicitly accepts a persisting `notable` finding)
does Phase 3 dispatch against the doc's *current* section order — dispatching prose checks against a
skeleton that's about to move wastes the round.

## Phase 3 — Dispatch (parallel lean agents)

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

## Phase 4 — Triage

Combine results. `design-doc-review:review` (if dispatched) has already triaged and fixed its own findings — treat its report as final for those facets, don't re-triage them. For `writing:tone` and `writing-humanize`/`technical-writing-coach` findings:

- **Mechanically fixable**: humanize's vocabulary/structural/rhythm flags, tone's register/jargon mismatches with a clear direction, technical-writing-coach's density/structure fixes.
- **Author-input-needed**: anything where the fix requires content only the author has (a missing anecdote for authenticity, a purpose the author hasn't actually decided on yet).

Present both lists before touching the file. Ask which mechanically-fixable findings to apply (default: all).

## Phase 5 — Fix loop

Same shape as `design-doc-review:review`'s Phase 3: apply approved fixes directly (this coordinator edits, it doesn't delegate the edit to a lean agent), then re-dispatch **fresh** agents for every check that wasn't already passing — no memory of the prior round's findings fed in. Round cap: 3. A finding that persists after round 3 gets reported, not silently dropped.

## Phase 6 — Report

```
writing:full: <path>
Scope: doc_type=<...>, audience=<...>, tone=<...>
Tier: <A|B|C|D>
Outline-flow rounds: <N> / 2
Prose rounds run: <N> / 3

| Check | Round 1 | Final |
|---|---|---|
| outline-flow | fail (N) | pass |
| design-doc-review (if applicable) | ... | ... |
| structure (technical-writing-coach, if applicable) | fail (N) | pass |
| tone | fail (N) | pass |
| humanize | ... | ... |

Fixed automatically: <count>
Needs author input: <count>
Persisted after rounds: <count, if any>
```

Then write/update `doc_plans/<topic>/outline.md` (same topic key as Phase 0) with the doc's final
*actual* section titles plus a one-line annotation per section — not a Diataxis placeholder
skeleton, a record of what's really there now, post-flow-fixes. This is the other half of the
Phase 0 bridge: the next `writing:full` run on this doc starts from real structure instead of
re-deriving it, and `docs:update`/`docs:prune` on the same doc get a structure map without
re-reading the whole file. Skip this write only if the doc's own repo convention already tracks
structure elsewhere (e.g. this repo's `_manifest.yaml`-driven multi-file docs) — say so instead of
writing a redundant copy.
