---
description: Establish or confirm a piece of writing's audience, tone, and purpose before reviewing it. Phase 1 of the writing pipeline — run standalone or via writing:full.
---

# writing:scope

Every other check in this pipeline (`writing:tone`, `design-doc-review:readability`, `technical-writing-coach`, `writing-humanize`) needs to know who the text is for and what register it should hit. Getting that wrong produces confident, precise feedback aimed at the wrong target — a PR description reviewed as if it were a design doc, or a blog post held to a design doc's decision-focus standard. This phase exists so every later check shares one answer instead of each guessing its own.

**Target**: {{args}} — a file path, or text already in context.

## Step 1 — Detect what you can before asking

Read the target and check for signals that already answer some of this:

- **Design doc / RFC**: a Status/Tracking/Decision-requested header, or it lives under a `design-docs`-style repo with its own house-style `CLAUDE.md` (check for one). If so, audience and tone are largely fixed by that repo's convention — don't re-litigate them, just confirm.
- **PR description / commit message**: git context (is this text going into `gh pr create --body` or a commit?) — audience is reviewers of this specific change, tone is terse and evidence-first per this repo's own CLAUDE.md if one exists.
- **Blog post / external-facing**: no internal jargon assumed, audience is whoever the platform's readership is.
- **Personal note / journal**: audience is future-you; tone should stay in the author's own voice — this is the one case where `writing-humanize`'s AI-tell removal matters most, since a note in someone else's cadence is actively worse than one in the author's.

If the type is unambiguous from context, state your read and move to Step 3 without asking. Only ask when it's genuinely unclear or when a decision only the author can make is in play (see CLAUDE.md's escalation rule).

## Step 2 — Ask what you can't detect

When ambiguous, ask in one pass (not one question at a time):

```
questions:
  - question: "Who's the primary audience for this?"
    header: "Audience"
    options:
      - label: "Expert peers in this domain"
        description: "Can assume shared jargon and context"
      - label: "Cross-functional / mixed technical background"
        description: "Define terms on first use, less assumed context"
      - label: "External / general readership"
        description: "No internal jargon, no assumed org context"
  - question: "What register should this land in?"
    header: "Tone"
    options:
      - label: "Formal / decision-document"
        description: "Structured, evidence-cited, matches this repo's house style if one exists"
      - label: "Direct / conversational"
        description: "Plain sentences, contractions fine, minimal hedging"
      - label: "Match my own voice"
        description: "Preserve the author's existing cadence — flag AI-tells (writing-humanize) more aggressively"
```

Never infer "formal" as the default just because the source reads dense — that density might itself be the problem this whole workflow was invoked to fix. Ask rather than assume when the current draft's register and the target register might be the same mistake.

## Step 3 — Record the scope

Hold the answer as: `{audience, tone, doc_type, purpose}`. Don't write a sidecar file for a one-off review — that's persistence for something used once in this session. Only write `<target>.writing-scope.md` if the user says this doc will go through multiple review rounds across sessions and wants the scope to persist; otherwise pass it directly into the next phase's agent prompts.

State the resolved scope back to the user in one line before proceeding: `Scope: <doc_type>, audience=<audience>, tone=<tone>.`

## Handoff

`writing:full` calls this phase first and threads its output into every check agent's prompt in `writing:tone` and (if the target isn't already a design doc using `design-doc-review:review`'s own checks) `technical-writing-coach`.
