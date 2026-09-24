---
description: Adversarially review a doc's outline/section flow against outlining best practices — coverage gaps, wrong ordering, redundant sections, buried decisions, hollow headings — independent of prose quality. One check in the writing pipeline — run standalone or via writing:full.
---

# writing:outline-flow

A doc can pass every prose-level check (structure density, tone, humanize) and still be hard to
follow because the *sections themselves* are in the wrong order, duplicate each other, or don't earn
their place. This check looks at the skeleton, not the sentences — it's the adversarial counterpart
to `docs:outline`'s generative patterns: instead of building a skeleton from best practices, it tries
to break an existing one against them.

**Target**: {{args}} — a file path, or an `outline.md` snapshot already in context (see
`writing:full` Phase 0/2). **Requires** the scope from `writing:scope`: `{audience, tone, doc_type,
purpose}`. If no outline snapshot exists yet, derive one first (real section titles + one-line
annotation each, same shape `docs:outline`/`writing:full` Phase 5 produce) — don't review prose to
find structural findings, review the skeleton.

## What to check

Work from the outline (headings + one-line annotations), not the full prose. Try to find fault, not
just confirm coverage:

- **Missing expected section for the declared type** — a design doc missing Problem, Proposal,
  Alternatives, Risks, or Rollout (the set `design-doc-review:outline` already enforces at the
  prose level — flag it here too, cheaper, from the outline alone); a Diataxis-typed doc missing its
  canonical section (`docs:outline`'s per-type patterns — a How-to with no Result, a Tutorial with no
  Verify step).
- **Wrong-order section** — a section that needs context the reader hasn't been given yet (Risks or
  Alternatives placed before enough Problem/Proposal exists to evaluate them), or a type-mixing
  section embedded mid-document (an Explanation-shaped "why this works" buried inside a How-to's
  steps).
- **Redundant section / duplicated fact across sections** — two outline entries whose one-line
  annotations cover the same ground. This is a real, recurring failure mode, not a hypothetical one:
  the same open-items list appearing in four different sections of a doc, worded differently each
  time, was found and fixed in exactly this shape in a prior review. Flag the pair, name the one
  section that should own the fact, and say the others should link to it instead of restating it.
- **Section that doesn't earn its place** — read each annotation cold against the declared
  `purpose`/`audience`: if this section were deleted, would the reader lose something they need for
  the stated goal? If not, it's a cut or merge candidate, not a keep.
- **Buried decision** — for `purpose` = decision/approval-seeking: does the outline let the reader
  reach the ask within the first 1-2 sections (TL;DR / Decision requested), or does it bury the ask
  after several sections of exposition the reader has to get through first?
- **Hollow/vague heading names** — a heading that doesn't say what's actually in the section (the
  same "hollow qualifier phrasing" pattern logged in `../../CHECKLIST.md`, applied at the heading
  level rather than mid-sentence).

## What NOT to flag

- A doc type that legitimately needs a long linear build (a Tutorial's numbered steps, a Reference's
  repeated per-entry structure) — don't flag "too many sections" when the type's own pattern requires
  repetition.
- Two sections citing the same fact for *different* purposes (a Risks row citing a Problem-section
  incident for context) — that's a supporting citation, not duplication. Only flag when two sections'
  *primary* content is the same information, not when one references the other.
- A missing section a Diataxis type explicitly excludes by design (a How-to has no "why" section on
  purpose — don't ask for one).
- Ordering that's unusual but has a stated reason already in the doc (e.g. a design doc that opens
  with Non-goals because scope creep was the reviewers' top concern) — a deliberate, justified choice
  isn't a finding.

## Severity

| Severity | Meaning |
|---|---|
| `blocking` | A required section for the declared type is missing entirely, or the decision/ask is unreachable without reading the whole doc |
| `notable` | A section is misordered, redundant, or doesn't earn its place, with a clear fix (move/merge/cut/rename) |
| `nit` | A single heading reads hollow/vague; batch these |

## Output

```json
{
  "category": "outline-flow",
  "status": "pass" | "fail",
  "scope": {"audience": "...", "tone": "...", "doc_type": "..."},
  "count": <number of blocking+notable findings>,
  "findings": [
    {"section": "...", "severity": "notable", "issue": "missing-section" | "wrong-order" | "redundant-section" | "doesnt-earn-place" | "buried-decision" | "hollow-heading", "note": "one line: what's wrong + the fix direction (move X after Y / merge X into Y / cut X / rename X to Y)"}
  ]
}
```

`status: "pass"` only if there are zero `blocking` findings and no unresolved `redundant-section`
pair.

## When invoked standalone (not via the coordinator)

Print the findings against the outline snapshot, then ask before applying any move/merge/cut — those
are structural edits and change what a reader finds where, unlike a prose-level rewrite. Cutting a
section is always author-input-needed, never auto-applied; moving or renaming is mechanically
fixable once the author confirms the direction.
