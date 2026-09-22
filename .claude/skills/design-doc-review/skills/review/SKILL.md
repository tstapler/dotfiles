---
description: Run the full design-doc-review pipeline (outline + readability + evidence, extensible) as parallel lean agents, then auto-fix findings in a loop with fresh unanchored re-verification each round, per the lean-agent-loop skill. Entry point for reviewing an engineering design doc / RFC.
---

# design-doc-review:review

Coordinator for the design-doc-review pipeline. Runs each check as an independent lean agent (see the `lean-agent-loop` skill — read it if you haven't loaded it this session), collects small structured summaries, then drives a fix→reverify loop until every check passes or a round cap is hit.

**Target**: {{args}} — a file path to the design doc. If omitted, use the doc already in context.

This skill does not invent checks — it dispatches to whatever lives under `design-doc-review/skills/*` other than itself. Today that's `outline`, `readability`, `evidence`, `visuals`, and `publish-compat`. Adding a new check later (e.g. `risk-completeness`) means adding one `skills/<name>/SKILL.md` following the same JSON-summary contract — no change needed here beyond adding it to the registry below. See `../../../writing/CHECKLIST.md` for the research/citation trail behind each check's threshold.

## Registry

| Check | Skill | Fixable automatically? |
|---|---|---|
| Structure / topic coverage | `design-doc-review:outline` | Rarely — most gaps need author input (e.g. "what's the actual rollback plan"). Coordinator proposes a stub + a question, does not invent content. |
| Prose / cognitive load / terseness | `design-doc-review:readability` | Yes — filler removal, hedge cleanup, front-loading, splitting mixed-purpose paragraphs, overlong-paragraph splits, and appendix-extraction (`"fix": "extract-to-appendix"`) are mechanical. |
| Unsourced claims / internal incoherence | `design-doc-review:evidence` | Rarely for the claim itself — a missing citation usually needs the author to say where the fact came from. Sometimes fixable: if the coordinator can locate and verify the actual source itself (a file/line, a command it can re-run), it can add the citation without author input; never invent one. |
| Missing diagrams / comparison tables | `design-doc-review:visuals` | Rarely — coordinator can propose a mermaid/table skeleton with extracted axes, but correct diagram type and exact table columns need author confirmation; never auto-insert. |
| Markdown constructs that break on the actual publish target (Confluence/Google Docs) | `design-doc-review:publish-compat` | Often, once the finding is `verified: true` — swapping an unsupported code-fence language, moving content that precedes the H1, converting a diagram fence to an image are mechanical. Anything `verified: false` (lookup was unavailable) is author-input: flag it, don't auto-fix a guess. |

## Phase 0 — Section split (long docs)

A single agent reading an entire long doc for a section-local check loses precision — attention spreads thin and later sections get skimmed. Before dispatch, count lines. Under ~150 lines, skip this phase and dispatch each check whole-doc as in Phase 1.

Over ~150 lines, split the body by H2 headings (`^## `). Not every check benefits equally from splitting:

- **`outline` and `publish-compat` always run whole-doc**, regardless of length. Outline's checks are global ("does a non-goals section exist *anywhere*", "does the functional spec trace to Layer 1 requirements stated elsewhere") — scoping it to one section would produce false `missing` findings for topics a *different* section covers. `publish-compat`'s target-detection (frontmatter, docspan mapping) and its highest-severity check (content before the single H1, duplicate H1s) are structurally whole-doc; splitting it would also mean re-doing target detection per section for no benefit, since the same target applies to the whole file.
- **`readability` and `visuals` are section-local** and fan out one agent per H2 section on long docs:
  - `readability`: one agent per section, each given only that section's text. Tell only the agent handling the doc's *first* section that it's first — the 30-second test and the missing-front-load check apply only there; a later section isn't a front-load violation for not re-stating a decision it was never supposed to front. Other agents run every other check normally.
  - `visuals`: one agent per section, each given that section's text **plus** a coordinator-supplied list of headings elsewhere in the doc that already contain a diagram or table (grep `^```(mermaid|d2)`, `!\[`, or table-pipe rows across the whole doc first — same signal `scripts/doc_report.py`'s `diagram` property uses). Without that list, a per-section agent can't honor the "already-adequate diagram exists elsewhere in the doc" guardrail, since it never sees the rest of the doc.
- **`evidence` is section-local but needs one extra input for its internal-contradiction check**: one agent per H2 section, each given that section's text **plus** a coordinator-supplied one-line-per-section list of every other section's headline claims (grep each section's first sentence after its heading, or its most decision-relevant line, as a cheap proxy — doesn't need to be exhaustive). Without that list, tell the per-section agent to skip the internal-contradiction sub-check for that invocation rather than silently missing cross-section contradictions it has no way to see.

Merge each check's per-section results into the same JSON contract it already returns before moving to Phase 2: sum `count` across sections, concatenate `findings` (the section split already gives you a real heading for the `section` field — use it instead of `§N.M`), `status: "fail"` if any section reported `fail`.

## Phase 1 — Dispatch (parallel lean agents)

Launch one agent per registry row, **in a single message** (tier A, per lean-agent-loop) — or, for a doc split per Phase 0, one agent per (check, section) pair for `readability`/`visuals` plus one whole-doc agent each for `outline` and `publish-compat`, all still in that same single message. Each agent prompt is exactly that check's own instructions plus its target (the whole doc, or one section plus the Phase 0 context noted above) — do not summarize prior findings into the prompt; there are none yet on round 1.

```
Agent "outline": run design-doc-review:outline against <path>. Return only its JSON summary.
Agent "readability": run design-doc-review:readability against <path>. Return only its JSON summary.
Agent "evidence": run design-doc-review:evidence against <path>. Return only its JSON summary.
Agent "visuals": run design-doc-review:visuals against <path>. Return only its JSON summary.
Agent "publish-compat": run design-doc-review:publish-compat against <path>. Return only its JSON summary.
```

Split-doc example (readability only shown; visuals follows the same shape with the diagram-location list added):

```
Agent "readability:§Problem" (first section): run design-doc-review:readability against
  the "## Problem" section of <path> below. This is the doc's first section — apply the
  30-second test and missing-front-load check. <section text>
Agent "readability:§Rollout": run design-doc-review:readability against the "## Rollout"
  section of <path> below. This is not the doc's first section — skip the 30-second test
  and missing-front-load check, apply everything else. <section text>
```

If parallel dispatch is unavailable, drop to the next tier in lean-agent-loop's degraded-mode table (B: parallel foreground, C: serial, D: self-serial) and say which tier ran when you report results. Never report "skipped review" for a capability reason — only round-cap or genuine pass justifies stopping.

## Phase 2 — Triage

Combine the JSON summaries from all checks that ran. If every check reports `status: "pass"` → skip to Phase 5 (report clean, no rounds needed).

Otherwise, split findings into:
- **Author-input-needed** (outline `missing`/`weak` findings, mostly; any `publish-compat` finding with `"verified": false`; and any `evidence` finding where the coordinator cannot itself locate and verify the missing source) — these become questions for the user, not autofixes. Never invent a rollback plan, a non-goals list, a rejection rationale, or a citation — that would put words (or sources) in the author's mouth without evidence, which is exactly what CLAUDE.md's evidence rule forbids. The same principle applies to an unverified publish-compat guess: presenting it as a confirmed fix would be inventing a fact the coordinator didn't actually check.
- **Mechanically fixable** (readability `notable`/`blocking` findings including `"fix": "extract-to-appendix"`; `publish-compat` findings with `"verified": true`; any `evidence` finding where the coordinator can independently locate and verify the actual source and add the citation; and any outline finding that's genuinely just "add a stub heading, content TBD") — these drive the fix loop below.

Present both lists to the user before touching the file. Ask which mechanically-fixable findings to apply (default: all) and note which author-input items remain open regardless of what's fixed.

## Phase 3 — Fix loop

```
GOAL: zero mechanically-fixable findings remain, or 3 rounds elapsed
ROUND CAP: 3 (design docs are short-lived artifacts under active edit; don't loop indefinitely on prose)

--- Round N ---
1. Apply approved fixes directly (Edit tool) — this coordinator applies them itself; it
   does not delegate the edit to a lean agent, since the fix needs the surrounding
   document context that a stateless agent would have to be re-fed anyway.
2. Re-dispatch FRESH agents for every check that was not already passing — same tier as
   Phase 1, same prompts, NO memory of round N-1's findings fed in. This is the
   "unanchored re-review principle" from lean-agent-loop: a fresh agent either fails to
   re-find a fixed issue (confirms the fix) or finds it again independently (proves the
   fix was insufficient) — an agent primed with "here's what you found last time" can't
   tell you which.
3. Coordinator (not the agents) diffs round N's summary against round N-1's:
   - Finding gone → fixed, record it
   - Finding persists → fix was insufficient; try again next round or flag for the user
     if this is round 3
   - New finding appeared → note it; a mechanical fix sometimes introduces a new
     readability issue (e.g. front-loading a decision can orphan a paragraph) — this is
     exactly the "round 2 finds defects in round 1's fix" case lean-agent-loop calls out
     as non-optional to check for.
4. All mechanically-fixable findings gone → DONE, go to Phase 5.
   Round cap hit with findings remaining → go to Phase 5 and report what's left, plus
   which tier ran each round.
```

## Phase 4 — Author-input items

For every author-input-needed finding still open (outline gaps, mostly, plus any evidence finding the coordinator couldn't verify itself), present it as a question rather than a fix:

```
[Layer 1] Non-goals — MISSING. The doc lists goals but no non-goals; without them,
scope will creep in review. What's explicitly out of scope here?

[Evidence, §Rollout] "This has run in prod for months without incident" — UNSOURCED.
No link, ticket, or dashboard backing this. Where does this claim come from?
```

Do not close these on your own judgment. If the user answers inline, write their answer into the doc under the right heading and re-run the outline (or evidence) check once (not the full loop) to confirm it now passes.

## Phase 5 — Report

```
design-doc-review: <path>
Tier: <A|B|C|D — say which, per round if it changed>
Rounds run: <N> / 3

| Check | Round 1 | Final | 
|---|---|---|
| outline | fail (3) | fail (1 — author input pending) |
| readability | fail (5) | pass |
| evidence | fail (2) | fail (1 — author input pending) |
| visuals | pass | pass |
| publish-compat | fail (2, target: confluence-markdown-confluence) | pass |

Fixed automatically: <count>
Needs author input (see Phase 4 questions above): <count>
Persisted after 3 rounds (needs a human look): <count, if any>
```

State plainly if the loop stopped on the round cap with findings remaining — that's a real, reportable outcome, not a failure to hide.

## Anti-patterns (inherited from lean-agent-loop, apply here specifically)

- Don't feed round N-1's findings into round N's check-agent prompt — the coordinator tracks state, the agents don't.
- Don't merge outline + readability into one mega-agent "just check the doc" — they're different lenses with different fixability; keep them separate so each stays sharp.
- Don't skip round 2 because round 1's fixes "looked right" — re-verification is the point, not a formality.
- Don't auto-fix an outline `missing` by writing plausible-sounding content — that's fabricating a claim, which is the failure mode CLAUDE.md's evidence rules exist to prevent. Ask instead.
- Don't apply a `publish-compat` finding with `"verified": false` as if it were confirmed — an unverified guess about what a sync tool will do to the doc is exactly the kind of unchecked claim CLAUDE.md's evidence rules exist to catch; surface it as a question, not a fix.
- Don't treat readability's `"fix": "extract-to-appendix"` as a cut — the content still belongs in the doc. Move it to an appendix heading (creating one if none exists) rather than deleting it.
- Don't fabricate a citation for an `evidence` finding to make it "pass" faster. If you can't independently locate and verify the actual source, it's author-input, full stop — an invented-but-plausible-looking link is worse than an honest gap, since it launders an unverified claim as verified.
