---
description: Comprehensive writing review — auto-detects document type and runs appropriate clarity, humanization, and style checks in parallel, then applies edits.
prompt: |
  # Writing Review

  You are running a full writing review on: **{{args}}**

  ## Step 1 — Read and Classify

  Read the document at {{args}}. Classify it into one of these types:

  | Type | Signals |
  |---|---|
  | **personal** | first-person, event/occasion, invitations, travel guides, letters |
  | **technical** | code, APIs, architecture, procedures, reference docs |
  | **persuasive** | cover letters, proposals, pitches, marketing copy |
  | **informational** | announcements, FAQs, how-to guides, policies |

  ## Step 2 — Dispatch Parallel Reviews

  Launch the following agents **simultaneously** using the Agent tool, tailored to the classified type:

  ### Always run (all types):
  - **Agent A — Clarity & Flow**: Review for: sentence length variance, passive voice, jarring transitions, paragraph structure, information hierarchy. Quote specific problem text with suggested rewrites. Do NOT edit the file.
  - **Agent B — Humanization & Voice**: Audit for AI-sounding vocabulary (delve, robust, seamless, leverage, pivotal, utilize, etc.), flat burstiness (too many same-length sentences), formulaic openers/closers, em-dash overuse, hedging. Quote specific problem text with suggested rewrites. Do NOT edit the file.

  ### Add for **personal** type:
  - **Agent C — Tone & Warmth**: Is the voice consistent and genuinely personal, or does it drift into bureaucratic/clinical language in places? Flag every section where the tone shifts register. Suggest rewrites that match the warmest, most personal moments in the document.

  ### Add for **technical** type:
  - **Agent C — Precision & Accuracy**: Check for undefined jargon, vague quantifiers, inconsistent terminology, and missing specificity. Flag passive constructions in procedures.

  ### Add for **persuasive** type:
  - **Agent C — Impact & Conviction**: Does the writing lead with the strongest point? Are there buried lede moments? Check for hedging that weakens the argument.

  ## Step 3 — Synthesize

  Collect all agent findings. Merge and deduplicate — if two agents flag the same passage, consolidate into one fix. Prioritize by impact:
  1. Tone/register breaks (highest impact on reader experience)
  2. Robotic or AI-sounding vocabulary
  3. Structural issues (flow, transitions, hierarchy)
  4. Sentence-level style (burstiness, passive voice)

  ## Step 4 — Apply Edits

  Edit the file directly, applying the prioritized fixes. For each edit:
  - Preserve the author's intent and any factual content exactly
  - Match the warmest/most human moments in the document as the target register
  - Do not add content that wasn't implied — only improve what's there

  ## Step 5 — Report

  After editing, give the user a brief summary:
  - Document type detected
  - Top 3 patterns fixed and why they mattered
  - Any issues you chose NOT to fix and why (e.g., intentional register, factual constraints)
  - Word count before/after if significantly changed
---
