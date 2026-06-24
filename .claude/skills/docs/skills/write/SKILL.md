---
description: Guided end-to-end document writing workflow — runs all phases in sequence with approval gates between each
---

# Write a Document (Full Workflow)

Orchestrates the complete document writing workflow: audience definition → structure → draft → review. Each phase produces an artifact; each gate requires approval before proceeding.

**Document topic**: $ARGUMENTS

If no topic provided, ask: "What document are you writing? Give me a working title or topic."

---

## Phase 1: Audience & Purpose

Run this interview before writing a single word. Ask questions one at a time.

### Q1 — Reader role
"Who is the primary reader? What's their role and their knowledge level *relative to this specific topic*?"

### Q2 — Reader goal
"What does the reader need after reading this? One of:
- Complete a specific task
- Learn a skill by doing it
- Look up a specific fact or value
- Understand *why* something works a certain way"

### Q3 — Reader gap
"What does the reader NOT know yet that you do? What's the biggest curse-of-knowledge risk?"

### Q4 — Scope boundary
"What is explicitly out of scope — even if related?"

### Q5 — Type confirmation
Based on answers 1–4, propose the Diataxis type:

| Type | Reader state | Your job |
|---|---|---|
| **Tutorial** | Doesn't know what they don't know | Guide by doing — no explanation mid-task |
| **How-to** | Knows goal, needs the path | Steps only — omit context |
| **Reference** | Needs exact answer | Complete, accurate, scannable |
| **Explanation** | Wants to understand why | Context, tradeoffs, mental models — no instructions |

Say: "This sounds like a **[type]** because [one-line reason]. Does that fit?"

### Phase 1 output — Audience-Purpose Statement
```
Document: [title]
Type: [Diataxis type]

Audience: A [reader role] with [knowledge level relative to this topic]
Goal: reads this to [specific, concrete outcome]
Assumed knowledge: [2–4 items]
Out of scope: [explicit boundary]
```

**Gate 1**: Print the statement. Ask: "Does this accurately capture what you're writing? Any corrections before I build the outline?"

Wait for confirmation. Revise if needed. Do not proceed until approved.

---

## Phase 2: Outline

Generate the skeleton using the confirmed type. Use the correct structural pattern:

**Tutorial**: Learning objective → prerequisites → numbered steps (each does one thing) → verify it works → what's next

**How-to**: Verb-phrase title → prerequisites (only what's required) → numbered imperative steps → result

**Reference**: Entry name → type/signature → one-sentence description → parameters/values → minimal example → constraints. Repeat per entry.

**Explanation**: What this is → the problem it solves → mechanism → adjacent concept comparison → tradeoffs → when to use / when not to → further reading

Fill in real section titles (not placeholders). Add a one-line annotation per section explaining what goes there. Include at the top: `Type: [type] | Estimated length: ~[N] words`

Flag any section that risks type-mixing.

**Gate 2**: Print the outline. Ask: "Does this structure match what you need? Any sections to add, remove, or reorder?"

Wait for confirmation. Revise if needed. Do not proceed until approved.

---

## Phase 3: Draft

Write the complete document from the confirmed outline. Apply all rules below without exception.

### Type discipline
- **Tutorial**: Steps produce visible, checkable state changes. Never explain *why* mid-task.
- **How-to**: Steps only. Zero background. If understanding is required, it's a prerequisite, not inline prose.
- **Reference**: Structure over narrative. Every entry identical shape. Complete and accurate above all else.
- **Explanation**: No instructions. Builds mental model only. Does not tell the reader to do anything.

### Every Page is Page One
- First paragraph establishes context — assume the reader arrived directly, not sequentially
- Serve one purpose; link to adjacent topics rather than containing them
- End with navigation: where to go next

### Compression
- Lead with the most important thing
- Start sentences with verbs where possible
- Cut without mercy: "you can", "there is/are", "in order to", "it should be noted", "basically", "simply", "just", "very"
- One idea per sentence
- Concrete example over abstract description

### Three Questions test — apply before delivering
1. What specific decision or action does the reader need?
2. What prevents them from acting confidently?
3. Does every paragraph serve question 2? If not, cut it.

### Quality gate (self-check before outputting)
- [ ] Every section title matches the declared type's pattern
- [ ] No section mixes types
- [ ] First sentence states the outcome or purpose — not context
- [ ] Reader can complete the stated goal without a follow-up question the document could have answered

After the document, append a **Compression log** (2–4 bullets: what was cut and why).

**Gate 3**: Print the draft. Ask: "Does this draft work? Options:
1. ✅ Done — I'll take it as-is
2. 🔍 Run clarity review (`/docs:review-clarity`)
3. ✏️ Polish the writing (`/docs:refine-writing`)
4. 🔄 Revise — [describe what to change]"

---

## Phase 4: Review (if requested)

If the user selects option 2 (clarity review), apply the full Three Questions Framework + cognitive load review from `/docs:review-clarity`.

If the user selects option 3 (polish), apply compression and style rules from `/docs:refine-writing`.

Deliver the revised document. Return to Gate 3.

---

## Saving Artifacts

At any gate, if the user says "save this", write:
- Audience-purpose statement → `doc_plans/<topic>/audience-purpose.md`
- Outline → `doc_plans/<topic>/outline.md`
- Draft → `doc_plans/<topic>/draft.md`
- Final → `doc_plans/<topic>/<topic>.md`
