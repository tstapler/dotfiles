---
description: Check a design doc for verbosity, buried decisions, and cognitive-load issues, scaled to the doc's stakes. One check in the design-doc-review pipeline — run standalone or via design-doc-review:review.
---

# design-doc-review:readability

Prose-quality check only — this skill does not evaluate whether the right topics are covered (see `design-doc-review:outline` for that). It answers: **can a reviewer extract the decision and its risk from this text without excess effort?**

**Target**: {{args}} — a file path, or a doc already in context.

## Framework

Adapted from `docs:review-clarity` (cognitive-load theory / decision-focused writing), narrowed to design docs specifically and reconciled with the Proportionality rule in CLAUDE.md — **this check must not penalize a doc for putting rigor where it belongs.**

Governing standard for the main body: Dieter Rams' "as little design as possible" and Pascal's "I would have written a shorter letter, but I did not have the time" — every sentence in the main body should have to justify its presence to a reader trying to make the decision. The fix for a sentence that fails that test is rarely deletion of the underlying content; it's usually **removal from the reader's critical path** — cut it if it's genuinely padding, extract it to an appendix if it's real evidence the doc still needs to keep.

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
- **Overlong, unbroken paragraph** — a paragraph past ~5-6 sentences is [Google's Developer Documentation Style Guide's](https://developers.google.com/style/paragraph-structure) own signal that it's carrying more than one idea; that guide is already this repo's cited house style for technical writing (see CLAUDE.md's Writing Style section). Don't flag length in isolation — flag it when the paragraph is *also* doing more than one job (the check above) or blocks the 30-second test by forcing a scanning reader through unrelated sentences to find the one they need. Fix is `"rewrite"`: split at the actual idea boundary, not a blind line-break insertion that leaves one idea artificially fragmented.
- **Repetitive sentence structure** — three or more consecutive sentences opening the same way (same subject-verb pattern, same length, same clause order) reads stiff and monotonous — [JMU Writing Center](https://www.jmu.edu/learning/writing-center/link-library/grammar-punctuation-style/sentence-structure-variety.shtml), [Purdue OWL Sentence Variety](https://owl.purdue.edu/owl/general_writing/academic_writing/sentence_variety/index.html). Fix is `"rewrite"`: vary sentence length or combine two short simple sentences — don't just flag it as a vague "vary your sentences" note, name the actual run (e.g. "the last 4 sentences here all open with a bare subject + 'is'/'are'").
- **Missing paragraph break (markdown source)** — two topically distinct ideas run together as one unbroken block in the raw markdown, with no blank line between them, even if the rendered prose reads fine sentence-by-sentence. [Purdue OWL: On Paragraphs](https://owl.purdue.edu/owl/general_writing/academic_writing/paragraphs_and_paragraphing/index.html) — one idea per paragraph, and a new paragraph whenever a new point starts or the reader needs a pause. This is a markdown-mechanics check, not a prose-quality one: look for a topic-sentence shift mid-block with no blank line inserted before it. Fix is `"rewrite"`: insert the missing blank line at the actual idea boundary (a literal `\n\n`), don't just reflow the paragraph.
- **Missing front-load** — the doc doesn't let a reader stop after 30 seconds with the core message and the ask; critical risk/impact is not near the top
- **Extractable-to-appendix content (terseness pass)** — run this as its own explicit pass over the main body, section by section, after the checks above: for each paragraph, ask "does the reader need this to make the decision, or only to audit how the decision was reached?" Content in the second bucket — raw investigation logs, full benchmark tables, exhaustive edge-case enumeration, a second worked example once the first has made the point, background/history the reader doesn't need to act — is a **terseness finding with `"fix": "extract-to-appendix"`**, not a deletion. It stays in the doc, just not on the reader's critical path. Only recommend `"fix": "cut"` when the sentence is pure filler/hedge/restatement with zero evidentiary value even in an appendix (see the filler-and-hedge bullet above). Flag the specific paragraph/section, name what it's doing (evidence vs. decision-relevant), and say which bucket it falls in — don't just assert "too long."

### What NOT to flag (proportionality guardrails)

- **Appendix detail carrying evidence, measurements, or a review record — that is already in an appendix.** Long is not verbose if it's load-bearing and correctly demoted out of the main body. Check the ratio: main body should be readable in one sitting for the doc's stakes; appendices exist precisely so the main body can be short. Flag a bloated *main body*, not a long *document* — and don't re-flag content the terseness pass already moved.
- **Citations, links, and command output backing a claim.** These satisfy CLAUDE.md's evidence rule; don't ask to cut them for terseness — that would trade correctness for brevity, the wrong trade.
- **Hedged, uncertainty-owning language on a genuinely uncertain claim** ("may indicate", "consistent with", "not verified") — this is the CNE hedged-language convention CAP's own doc references; it is precision, not padding. Only flag hedging that is used to avoid a checkable claim the author could have made concrete.
- **A long paragraph that is genuinely one idea.** Google's own guidance is explicit that this is fine: "it's OK to have a paragraph with one sentence, and it can be OK if it's longer than 6 sentences as long as it's still about one idea." Don't force a split that would fragment a single point across artificial paragraph breaks.

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
    {"section": "§5.4", "severity": "notable", "fix": "cut" | "extract-to-appendix" | "rewrite", "note": "one line: what's wrong + the fix direction"}
  ]
}
```

`fix` defaults to `"rewrite"` for anything that isn't a pure-filler cut or a terseness-pass extraction (buried decisions, passive voice, mixed-purpose paragraphs, unquantified risk — these need new prose, not just relocation).

`status: "pass"` only if the 30-second test passes and there are zero `blocking` findings.

## When invoked standalone (not via the coordinator)

Print the summary as a table with before/after examples for the top 3 findings, then ask whether to apply the rewrites. For `"fix": "extract-to-appendix"` findings, propose the destination heading (an existing Appendix if the doc has one, otherwise a new `## Appendix` to create) alongside the before/after. Do not edit the file without that confirmation — this check runs directly against prose the author owns, unlike outline gaps which usually need author input anyway.
