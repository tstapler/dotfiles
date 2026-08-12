---
description: Check a design doc for verbosity, buried decisions, and cognitive-load issues, scaled to the doc's stakes. One check in the design-doc-review pipeline — run standalone or via design-doc-review:review.
---

# design-doc-review:readability

Prose-quality check only — this skill does not evaluate whether the right topics are covered (see `design-doc-review:outline` for that). It answers: **can a reviewer extract the decision and its risk from this text without excess effort?**

**Target**: {{args}} — a file path, or a doc already in context.

## Framework

Adapted from `docs:review-clarity` (cognitive-load theory / decision-focused writing), narrowed to design docs specifically and reconciled with the Proportionality rule in CLAUDE.md — **this check must not penalize a doc for putting rigor where it belongs.**

### The Three Questions

1. **Decision Focus** — what decision is the reader being asked to make?
2. **Obstacle Identification** — what would stop them making it confidently?
3. **Minimum Viable Information** — is that, and only that, in the main body?

### What to flag in the MAIN BODY

- **Buried decision/ask** — the thing the reader must decide is not in the first third of the doc, or is stated as narrative rather than named as a decision (compare to the "Decision requested" pattern: numbered asks, one owner, one default-if-silent, each per row)
- **Filler and hedge padding** — "very", "basically", "in order to", "it should be noted that", "due to the fact that" — cut-and-replace, not a style nit
- **Show-my-work** — investigation narrative left in the main body where a conclusion would do. (Exception: if the doc's own convention — e.g. an evidence/appendix split — already routes this to an appendix, that's correct and should NOT be flagged again.)
- **Unquantified risk language** — "significant risk", "should be fine" without a number, a measured event, or a link backing it. Ties to CLAUDE.md's "Evidence and Claims": a claim without a source the reader can check is the same defect whether it's a code comment or a design doc.
- **Passive voice hiding an actor** — "it was decided that" — who decided, and can the reader ask them?
- **Paragraph or section doing two jobs** — mixing "what we're building" with "why we're allowed to" with "how it degrades" in one block, so a reader skimming for one of those has to read all three
- **Missing front-load** — the doc doesn't let a reader stop after 30 seconds with the core message and the ask; critical risk/impact is not near the top

### What NOT to flag (proportionality guardrails)

- **Appendix detail carrying evidence, measurements, or a review record.** Long is not verbose if it's load-bearing and correctly demoted out of the main body. Check the ratio: main body should be readable in one sitting for the doc's stakes; appendices exist precisely so the main body can be short. Flag a bloated *main body*, not a long *document*.
- **Citations, links, and command output backing a claim.** These satisfy CLAUDE.md's evidence rule; don't ask to cut them for terseness — that would trade correctness for brevity, the wrong trade.
- **Hedged, uncertainty-owning language on a genuinely uncertain claim** ("may indicate", "consistent with", "not verified") — this is the CNE hedged-language convention CAP's own doc references; it is precision, not padding. Only flag hedging that is used to avoid a checkable claim the author could have made concrete.

### The 30-Second Test

Read only the first screen (title, TL;DR/summary if present, first section). Can you state the decision being asked and the biggest risk? If not, that's the highest-priority finding — everything else is secondary until this passes.

## Section-scoped invocation (long docs)

The coordinator (`design-doc-review:review`) may hand you one H2 section's text instead of the whole doc, for docs long enough that a single whole-doc pass loses precision. If invoked this way:

- You'll be told whether this is the doc's *first* section. If not, **skip the 30-Second Test and the missing-front-load check entirely** — they're about the doc's opening, not about every section restating a decision it was never meant to front. Run every other check normally against the section text you were given.
- If you're the first section, run the 30-second test and front-load check as usual — they were designed around exactly this scope already.
- Set `"section"` in each finding to the real heading you were given, not a placeholder.

## Severity

| Severity | Meaning |
|---|---|
| `blocking` | 30-second test fails, or the decision/ask is not identifiable in the main body |
| `notable` | Localized verbosity/hedge/unquantified-risk issue with a clear before/after fix |
| `nit` | Single filler word or minor phrasing — batch these, don't report individually |

## Output

Write full analysis (quotes, line refs, before/after rewrites) to `/tmp/lean-design-doc-review-readability-<ts>.md`.

Return only this structured summary:

```json
{
  "category": "readability",
  "status": "pass" | "fail",
  "count": <number of blocking+notable findings>,
  "findings": [
    {"section": "§5.4", "severity": "notable", "note": "one line: what's wrong + the fix direction"}
  ]
}
```

`status: "pass"` only if the 30-second test passes and there are zero `blocking` findings.

## When invoked standalone (not via the coordinator)

Print the summary as a table with before/after examples for the top 3 findings, then ask whether to apply the rewrites. Do not edit the file without that confirmation — this check runs directly against prose the author owns, unlike outline gaps which usually need author input anyway.
