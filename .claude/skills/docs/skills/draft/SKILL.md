---
description: Write a compressed, reader-first document draft from an outline — Phase 3 of the document writing workflow
---

# Draft Document from Outline

Phase 3 of the document writing workflow. Write the full draft following the outline produced by `/docs:outline`. Apply Diataxis type discipline, Every Page is Page One principles, and compression rules.

**Input**: $ARGUMENTS (outline inline, or path to outline.md)

If no input provided, ask: "Provide the outline or path to outline.md. (Run `/docs:outline` first.)"

## Pre-Draft Check

Before writing, confirm from the outline:
1. **Diataxis type** — which type governs this document?
2. **Reader outcome** — what can the reader do/know after reading?
3. **Scope boundary** — what is explicitly out of scope?

If any of these are unclear, ask before writing.

## Writing Rules

### Type discipline — enforce without exception

**Tutorial**: The reader learns by doing. Every step results in a visible, checkable state change. Never explain *why* while the reader is mid-task — explanation belongs in a linked Explanation doc. Keep steps atomic (one action per step).

**How-to**: Steps only. No background. No "why". If the reader needs to understand something to complete the step, make it a prerequisite, not inline prose. No introductory sections beyond prerequisites.

**Reference**: Structure, not narrative. Every entry has the same shape. Complete and accurate above readable. Tables and definition lists over prose. No opinions, no context — only facts.

**Explanation**: No instructions. This document does not tell the reader to do anything. It builds a mental model: context, mechanism, tradeoffs, limits. Invite curiosity; trust the reader to apply their own judgment.

### Every Page is Page One
- **Establish context in the first paragraph** — assume the reader arrived here directly from a search result
- **Serve one purpose** — do not try to contain adjacent topics; link to them instead
- **End with navigation** — where to go next (related how-tos, deeper explanation, reference)

### Compression (apply to every sentence)
- Lead with the most important thing (inverted pyramid)
- Start statements with verbs where possible
- **Cut these phrases entirely**: "you can", "there is/are", "in order to", "it should be noted that", "basically", "simply", "just", "very", "really", "at this point in time", "due to the fact that"
- One idea per sentence — split any sentence with "and" connecting two different concepts
- Concrete example over abstract description — if you can show it, show it
- If a sentence sounds like it belongs in a legal document or a press release, delete it

### Three Questions test (apply before outputting)
1. What specific decision or action does the reader need to take?
2. What prevents them from taking that action confidently?
3. Does every paragraph serve question 2? If not, cut it.

## Output Format

Write the complete document in markdown. Then append a **Compression Log** — two to four bullet points summarizing what you cut and why. This is not for the reader; it is a quality audit showing that compression decisions were deliberate.

Example format:
```markdown
[document content]

---
**Compression log**
- Removed background section on X — reader's goal doesn't require understanding why X exists
- Cut three "you can" constructions — converted to direct imperatives
- Moved explanation of Y to a note in "Further reading" — it's Explanation content inside a How-to
```

## Quality Gate

After drafting, verify:
- [ ] Every section title matches the declared Diataxis type's pattern
- [ ] No section mixes types (e.g., no explanation inside a how-to)
- [ ] First sentence of document states the outcome or purpose, not context
- [ ] Reader can complete the stated goal without asking a follow-up question the document could have anticipated

If any check fails, revise before delivering.

## Next Steps

- `/docs:review-clarity` — review against cognitive load and clarity criteria
- `/docs:refine-writing` — polish active voice, conciseness, precision
