---
description: Generate document skeleton from audience-purpose statement using Diataxis type patterns — Phase 2 of the document writing workflow
---

# Generate Document Outline

Phase 2 of the document writing workflow. Generate a document skeleton based on the audience-purpose statement produced by `/docs:define`.

**Input**: $ARGUMENTS (audience-purpose statement inline, or path to audience-purpose.md)

If no input provided, ask: "What is the document type and who is it for? (Run `/docs:define` first for a guided interview.)"

## Structural Patterns by Diataxis Type

Use the declared type to select the correct skeleton. Do not mix patterns.

### Tutorial
```
# [Title: "Build/Create/Learn X"]

> What you'll accomplish: [concrete, checkable outcome — not "you'll learn about X"]

## Prerequisites
- [Specific item the reader must have or know — checkable]
- [Another prerequisite]

## Step 1: [Imperative verb] [specific action]
[placeholder: what happens here]

## Step 2: [Imperative verb] [specific action]
[placeholder]

## (repeat steps — each step does exactly one thing)

## Verify it works
[placeholder: what success looks like — specific, testable]

## What's next
[placeholder: links to related how-tos or deeper explanation]
```

### How-to
```
# [Title: "[Verb phrase] — e.g. 'Configure X for Y'"]

## Prerequisites
- [Only what's actually required — nothing informational]

## Steps

1. [Imperative verb] [specific action]
2. [Imperative verb] [specific action]
3. (continue)

## Result
[placeholder: what the completed state looks like]
```
Note: No background sections. No explanation. Steps only.

### Reference
```
# [Entity name]

[One sentence: what this is.]

## [Property/Parameter/Field name]

**Type**: [type]
**Default**: [value or "none"]
**Description**: [one sentence]
**Example**: [minimal working example]
**Constraints**: [edge cases, if any]

## (repeat entry structure for each item)
```
Note: No narrative prose. Every entry uses the same structure.

### Explanation
```
# [Title: "How/Why/What [concept] works"]

## What this is
[placeholder: definition without jargon — one paragraph]

## The problem it solves
[placeholder: the context that makes this concept necessary]

## How it works
[placeholder: mechanism — not instructions, understanding]

## [Key concept] vs. [adjacent concept]
[placeholder: where the boundary is and why it exists]

## Tradeoffs and constraints
[placeholder: when this approach wins, when it loses]

## When to use this / when not to
[placeholder: decision criteria]

## Further reading
[placeholder: links to related tutorials, how-tos, or reference — not summaries]
```

## Output

1. Print the skeleton with section headers filled in (not placeholders — real section titles based on the content)
2. Annotate each section: one-line note on what goes there
3. Add at the top: `Type: [Diataxis type] | Estimated length: ~[N × 200] words`
4. Flag any section that risks type mixing (e.g., explanation creeping into a how-to)

Ask: "Should I save this to `doc_plans/<topic>/outline.md`?"

## Next Step

Run `/docs:draft` with this outline as input to write the document.
