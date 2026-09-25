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
| Redundant section across an outline (same fact, multiple sections) | The same list/claim restated in several sections with different wording instead of living in one place with the others linking to it | Direct occurrence: `titus-state-ownership-nop/README.md`'s "still open" RPO/census items appeared in four sections (TL;DR, Versioned intent in KV, Rollout, Remaining validation) before a 2026-09-23 review consolidated them — found by reading the doc, not by this check (which didn't exist yet); this check exists so the next occurrence is caught from the outline snapshot instead of a full read | `writing:outline-flow` |
| Missing/misordered/unearned outline section, buried decision | A required section absent for the declared type, a section needing context the reader hasn't reached yet, or a decision-document outline that doesn't reach the ask in the first section or two | `docs:outline`'s Diataxis structural patterns (missing-section case); `design-doc-review:outline`'s required-topic-set (design-doc case); Three Questions framework already cited in `docs:write` (buried-decision case) — this check applies all three at the outline-snapshot level, before prose exists to review | `writing:outline-flow` |
| Vague tone label instead of evidence-backed profile | `writing:scope`'s tone field was a bare adjective ("conversational"), which every downstream check (and the model doing any rewrite) fills in from its own defaults instead of the actual author's voice | Cross-angle research convergence (2026-09-24 research workflow): unaltered-exemplar few-shot beats flattened samples ([DEV Community writeup](https://dev.to/thatechmaestro/replicate-an-authors-writing-style-using-prompt-engineering-insights-from-an-experiment-with-2hfk)); 8-dimension forensic-linguist extraction with quoted evidence, PersonalBench ([arXiv:2608.19746](https://arxiv.org/pdf/2608.19746)); stylometric feature grounding, "I Am No One" ([arXiv:2609.12341](https://arxiv.org/html/2609.12341)); professional ghostwriters' "Voice Bible" practice. **Caveat from PersonalBench itself**: even this technique never fully closes the human/LLM authorship gap across 50 authors tested — ship as a real improvement, not a claim of indistinguishability | `writing:scope` Step 2.5 (voice-profile extraction), consumed by `writing:tone` and `writing:full`'s fix loop |
| Fix-loop style drift over multiple rounds | A model re-drifts toward generic phrasing over a long fix session even after an initial style framing, because that framing isn't restated | Trial-Error-Explain in-context learning, TICL ([arXiv:2502.08972](https://arxiv.org/abs/2502.08972)) — self-generated negative example + explanation appended to the next round's prompt, reported up to 91.5% win rate over tuning-free baselines on fixing generic-phrasing bias | `writing:full` Phase 5 (restate constraints every round + carry a growing drift-log) |
| Unmotivated paragraph disconnection | AI text signals coherence via paragraph breaks alone and *underuses* discourse markers relative to human writing — the opposite of the "too many transitions" assumption | 2026-09-24 research workflow, detection-avoidance angle (source: workflow synthesis citing discourse-marker-density research; not independently re-verified beyond the workflow's own citation) | `writing-humanize` Step 4 (Authenticity Scan table) |
| Reflexive both-sidesing | A concession/counterargument pair inserted where nothing in the source calls for balance — a distinct, sycophancy-adjacent pattern from generic hedging | Same 2026-09-24 research workflow, detection-avoidance angle | `writing-humanize` Step 4 (Authenticity Scan table) |

## Planned / candidates for future research

- **Entity-grid referential coherence** — trace whether key entities are referred back to
  consistently (natural pronoun substitution) vs. over-explicit re-naming or dropped threads between
  paragraphs. Flagged by the 2026-09-24 research workflow as harder to operationalize as a heuristic
  than the other new checks above — needs a concrete detection method worked out before
  implementation, not just the hypothesis.

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
