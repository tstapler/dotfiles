# Writing/editorial checks: research log and implementation map

Running record of every mechanical writing/editing check across the `writing` and
`design-doc-review` plugins — what it catches, the evidence behind the rule, and where it's
implemented. Add to this whenever research grounds a new check (or changes an existing threshold)
so the next person doesn't have to re-derive the citation trail. This file does not duplicate each
skill's own instructions — it's the index of *why* a rule exists and *where* to go change it.

## Implemented

| Check | Catches | Evidence / citation | Implemented in |
|---|---|---|---|
| Overlong, unbroken paragraph | A paragraph carrying more than one idea, hurting scannability | [Google Developer Documentation Style Guide, Paragraph structure](https://developers.google.com/style/paragraph-structure): >5-6 sentences signals multiple ideas — already this repo's cited house style per `CLAUDE.md`'s Writing Style section | `design-doc-review:readability` |
| Wall of text (soft signal) | A block of prose with no internal line breaks — the default shape LLMs fall back to in short-form writing | [`avoid-ai-writing`](https://github.com/conorbronsdon/avoid-ai-writing) project notes; mechanism traced to attention allocation on separator tokens, [SepLLM, arXiv:2412.12094](https://arxiv.org/abs/2412.12094). **Caveat, from that same project**: a standalone detector was reverted because dense human paragraphs share the same shape — register/redundant-context matter more than shape alone, so this is corroborating evidence, never a sole trigger | `writing-humanize` (Structural Signature Scan table + `references/research-notes.md`) |
| Unsourced claim / missing citation | A factual statement with no link, file:line, or command output backing it | `CLAUDE.md`'s own "Evidence and Claims" section (this org's already-agreed standard — this check mechanizes it, doesn't invent a new one); general fact-checking practice ("how do you know this?" test, verify-before-publish) is standard across editorial fact-checking guides | `design-doc-review:evidence` (new) |
| Source named but not linked | "Per the runbook" / "as X's doc says" with no URL — still pushes verification onto the reader | Same `CLAUDE.md` section, explicit: naming a source without a link is the same defect as no source | `design-doc-review:evidence` |
| Unsupported superlative/absolute | "the fastest", "the only", "always", "never" asserted without comparative proof | Standard fact-checking practice: every superlative is a factual claim requiring documentation, not rhetorical flourish | `design-doc-review:evidence` |
| Confidence mismatch | A claim stated as settled fact when the doc's own evidence only supports "probably"/"consistent with" | `CLAUDE.md`: "Label confidence: VERIFIED... vs INFERRED/UNVERIFIED" | `design-doc-review:evidence` |
| Non-sequitur / unsupported causal leap | Conclusion doesn't follow from the stated evidence (correlation presented as causation) | `CLAUDE.md`: "Consistent-with is not because-of" | `design-doc-review:evidence` |
| Internal contradiction | Two statements in the same doc that can't both be true | Standard editorial coherence check; no single external citation, just internal logical consistency | `design-doc-review:evidence` |
| Repetitive sentence structure | 3+ consecutive sentences with the same opening pattern/length, reading stiff and monotonous | [JMU Writing Center: Sentence Structure and Variety](https://www.jmu.edu/learning/writing-center/link-library/grammar-punctuation-style/sentence-structure-variety.shtml); [Purdue OWL: Sentence Variety](https://owl.purdue.edu/owl/general_writing/academic_writing/sentence_variety/index.html) | `design-doc-review:readability` |
| Missing paragraph break (markdown source) | Two topically distinct ideas run together as one unbroken block with no blank line, even when the prose itself reads fine sentence-by-sentence | [Purdue OWL: On Paragraphs](https://owl.purdue.edu/owl/general_writing/academic_writing/paragraphs_and_paragraphing/index.html) — one idea per paragraph, new paragraph on topic shift or when the reader needs a pause | `design-doc-review:readability` |
| Hollow qualifier phrasing | A heading/sentence built from a bare noun plus a distancing adverb ("The primitive, generically") that names the category of what follows instead of its content — grammatically fine, reads robotic | Design-docs repo `CLAUDE.md` Tone section: "say it the way you'd say it out loud to the reviewer, not the way a formal memo would"; flagged in review as reading "terrible, robotic" | `writing:tone` |

## Planned / candidates for future research

Nothing queued right now. Add a row here (check name + one-line hypothesis) as soon as a pattern
is *noticed*, even before it's researched — the research pass can happen later, but the observation
shouldn't get lost between sessions.

## How to add a new check

1. **Notice the pattern first** — from actual review sessions, not in the abstract. Add a one-line
   entry under "Planned" above so it isn't lost.
2. **Research before encoding a threshold.** Use `meta-research-workflow` (or a focused `WebSearch`
   pass for a narrow, single-topic question) to find a citable source for *why* the pattern matters
   and *what numeric/structural threshold* is defensible — don't invent a number. If the pattern is
   already covered by this org's own standing rules (`CLAUDE.md`), cite that directly; it's the
   more authoritative and more stable source.
3. **Decide which skill owns it.** `design-doc-review:*` for design-doc/ADR-specific checks (ties to
   the decision-focused Three Questions framework); `writing-humanize` for AI-detection/authenticity
   signals; `writing:tone` for register/audience mismatch. A check can belong to more than one if the
   two lenses ask genuinely different questions about the same surface signal (see how the paragraph
   checks above split: readability asks "is this one idea", humanize asks "is this an AI shape").
4. **Follow the existing JSON-summary contract** in `design-doc-review:review`'s registry, or the
   existing audit-report format in `writing-humanize`/`writing:tone` — don't invent a new output
   shape per check.
5. **Add the false-positive guardrail up front, not after the fact.** Every check above has an
   explicit "don't flag this" case (Google's own "OK if it's genuinely one idea", `avoid-ai-writing`'s
   soft-signal caveat, evidence's "correctly hedged uncertainty is not a gap"). Write it into the
   same pass that adds the check, since retrofitting it later means the check has already produced
   false positives in the meantime.
6. **Register it**: add a row to `design-doc-review:review`'s Registry table (and its Phase 0/1/2/5
   mentions) if it's a design-doc-review check, or the relevant `writing:*` orchestration if not.
7. **Log it here**, in the Implemented table above, with the citation — that's the whole point of
   this file existing.
