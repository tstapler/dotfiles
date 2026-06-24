---
description: Interview to define document audience, purpose, and Diataxis type — Phase 1 of the document writing workflow
---

# Define Document Audience & Purpose

Phase 1 of the document writing workflow. Conduct a focused interview to produce the audience-purpose statement that governs all downstream writing decisions.

**Document topic**: $ARGUMENTS

## Interview Protocol

Ask these questions in sequence. Wait for answers after each. Do not ask multiple questions at once.

### Question 1 — Reader Role
"Who is the primary reader? What is their role (developer, manager, end user, teammate, etc.) and their knowledge level relative to *this specific topic* — not their general expertise?"

### Question 2 — Reader Goal
"What does the reader need to accomplish after reading this? Pick the specific outcome:
- Complete a task they couldn't do before
- Learn a skill by doing it
- Look up a specific fact or value
- Understand *why* something works the way it does"

### Question 3 — Reader Gap
"What does the reader NOT know that you do? What's the curse-of-knowledge risk — what assumptions are you tempted to make that the reader can't share?"

### Question 4 — Scope Boundary
"What is explicitly out of scope? What will this document *not* cover, even if it's related?"

### Question 5 — Type Confirmation (Diataxis)
Based on answers 1–4, propose the best Diataxis type and confirm:

| Type | Reader state | Writer's job | Wrong when... |
|---|---|---|---|
| **Tutorial** | Doesn't know what they don't know | Guide by doing | Explaining instead of showing |
| **How-to** | Knows goal, needs path | Steps only, no context | Including background the reader didn't ask for |
| **Reference** | Needs exact answer | Complete, accurate, scannable | Writing prose instead of entries |
| **Explanation** | Wants to understand why | Context, tradeoffs, mental models | Embedding instructions |

Say: "Based on what you've described, this sounds like a [type] because [one reason]. Does that match what you're trying to write?"

## Output: Audience-Purpose Statement

After all answers, produce this artifact:

```
Document: [title or working title]
Type: [Diataxis type]

Audience: A [reader role] with [knowledge level relative to this topic]
Goal: reads this to [specific, concrete outcome]
Assumed knowledge: [2–4 things the reader already knows]
Not covered: [explicit scope boundary]

Test question: "A [reader role] with [knowledge level] reads this to [outcome] — can they do that after reading it?"
```

Print the completed statement. Ask: "Should I save this to `doc_plans/<topic>/audience-purpose.md`?"

If yes, save it there.

## Next Step

Run `/docs:outline` with this statement as input to generate the document skeleton.
