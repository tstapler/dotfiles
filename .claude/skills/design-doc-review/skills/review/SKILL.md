---
description: Run the full design-doc-review pipeline (outline + readability, extensible) as parallel lean agents, then auto-fix findings in a loop with fresh unanchored re-verification each round, per the lean-agent-loop skill. Entry point for reviewing an engineering design doc / RFC.
---

# design-doc-review:review

Coordinator for the design-doc-review pipeline. Runs each check as an independent lean agent (see the `lean-agent-loop` skill — read it if you haven't loaded it this session), collects small structured summaries, then drives a fix→reverify loop until every check passes or a round cap is hit.

**Target**: {{args}} — a file path to the design doc. If omitted, use the doc already in context.

This skill does not invent checks — it dispatches to whatever lives under `design-doc-review/skills/*` other than itself. Today that's `outline` and `readability`. Adding a new check later (e.g. `evidence-quality`, `risk-completeness`) means adding one `skills/<name>/SKILL.md` following the same JSON-summary contract — no change needed here beyond adding it to the registry below.

## Registry

| Check | Skill | Fixable automatically? |
|---|---|---|
| Structure / topic coverage | `design-doc-review:outline` | Rarely — most gaps need author input (e.g. "what's the actual rollback plan"). Coordinator proposes a stub + a question, does not invent content. |
| Prose / cognitive load | `design-doc-review:readability` | Yes — filler removal, hedge cleanup, front-loading, splitting mixed-purpose paragraphs are mechanical rewrites. |

## Phase 1 — Dispatch (parallel lean agents)

Launch one agent per registry row, **in a single message** (tier A, per lean-agent-loop). Each agent prompt is exactly that check's own instructions plus the target path — do not summarize prior findings into the prompt; there are none yet on round 1.

```
Agent "outline": run design-doc-review:outline against <path>. Return only its JSON summary.
Agent "readability": run design-doc-review:readability against <path>. Return only its JSON summary.
```

If parallel dispatch is unavailable, drop to the next tier in lean-agent-loop's degraded-mode table (B: parallel foreground, C: serial, D: self-serial) and say which tier ran when you report results. Never report "skipped review" for a capability reason — only round-cap or genuine pass justifies stopping.

## Phase 2 — Triage

Combine the two JSON summaries. If both `status: "pass"` → skip to Phase 5 (report clean, no rounds needed).

Otherwise, split findings into:
- **Author-input-needed** (outline `missing`/`weak` findings, mostly) — these become questions for the user, not autofixes. Never invent a rollback plan, a non-goals list, or a rejection rationale — that would put words in the author's mouth without evidence, which is exactly what CLAUDE.md's evidence rule forbids.
- **Mechanically fixable** (readability `notable`/`blocking` findings, and any outline finding that's genuinely just "add a stub heading, content TBD") — these drive the fix loop below.

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

For every author-input-needed finding still open (outline gaps, mostly), present it as a question rather than a fix:

```
[Layer 1] Non-goals — MISSING. The doc lists goals but no non-goals; without them,
scope will creep in review. What's explicitly out of scope here?
```

Do not close these on your own judgment. If the user answers inline, write their answer into the doc under the right heading and re-run the outline check once (not the full loop) to confirm it now passes.

## Phase 5 — Report

```
design-doc-review: <path>
Tier: <A|B|C|D — say which, per round if it changed>
Rounds run: <N> / 3

| Check | Round 1 | Final | 
|---|---|---|
| outline | fail (3) | fail (1 — author input pending) |
| readability | fail (5) | pass |

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
