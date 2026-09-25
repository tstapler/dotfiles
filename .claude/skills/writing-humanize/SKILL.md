---
name: writing-humanize
description: Review and rewrite text to reduce AI detection signals and increase authenticity. Flags overrepresented AI vocabulary, structural signatures (uniform paragraph lengths, formulaic openers/closers, transition-word overuse), burstiness flatness, hedging, abstract nominalizations, and missing specificity. Produces flagged audit with line-level rewrites. Use on cover letters, personal statements, blog posts, essays, and documentation where the author's voice must read as genuinely human.
---

# Writing Humanize

Audit text for AI detection signals and rewrite to increase authenticity, sentence-rhythm variation, and authorial specificity.

**Optional input**: a `voiceProfile` from `writing:scope` Step 2.5 (evidence-backed dimensions extracted from the author's own prior writing, not an adjective). When present, judge Step 4's authenticity checks against its named dimensions and quoted evidence instead of generic defaults — a profile makes "does this sound like them" checkable, not just "does this sound like a person."

## When to Use This Skill

- Cover letters, personal statements, graduate school essays
- Blog posts or articles where voice and credibility matter
- Documentation written with AI assistance that needs a human editorial pass
- Any text being submitted to a platform with AI detection screening

## The Two Metrics That Drive AI Detection

GPTZero and similar detectors use two core signals:

**Perplexity** — how unpredictable each word choice is. AI runs low (predictable, safe word choices). Human writing surprises.

**Burstiness** — how much sentence-length complexity varies. AI runs flat. Humans alternate: a short punch. Then a long, clause-heavy sentence that builds toward something.

Both must improve. Fixing vocabulary without fixing rhythm leaves the structural fingerprint intact.

## Audit Protocol

Run in sequence. Flag every instance with location and rewrite suggestion.

### Step 1 — Vocabulary Scan

Check for flagged terms from `references/word-lists.md`:
- **Tier 1** (50–269× overrepresented): delve, realm, nuanced, multifaceted, tapestry, robust, pivotal, seamless, leverage, harness, underscore, testament, cutting-edge, intricate
- **Tier 2** (transition overuse): moreover, furthermore, additionally, it is worth noting
- **Em dash overuse**: flag every em dash where a comma or period would be natural

For each hit: identify the sentence, explain why it signals AI, offer a concrete replacement.

### Step 2 — Structural Signature Scan

Check paragraph-level patterns:

| Signal | What to Look For | Fix |
|--------|-----------------|-----|
| Uniform length | Every paragraph 3–5 sentences, similar word counts | Break one short (1–2 sentences). Expand one long. |
| Wall of text | 4+ sentences / 100+ words delivered as one unbroken block with no internal line break — the default shape LLMs fall back to in chat, PR/issue comments, and DMs | Break at thought boundaries, one idea per line-group, the way a person actually types a reply. Treat as a **soft signal only** — an ordinary dense human paragraph can share this exact shape, so weight it alongside register and redundant-context tells below, not as a standalone detector. |
| Formulaic opener | "In today's rapidly evolving landscape..." or similar throat-clearing | Cut entirely or replace with a specific claim or scene |
| Formulaic closer | "In conclusion, it is clear that..." | End on a specific image, an open question, or a direct call |
| Transition-word boundary | moreover/furthermore starting 2+ consecutive paragraphs | Remove or replace with a direct pivot sentence |
| Participial opening overuse | 3+ sentences opening with a present participle ("Leveraging...", "Building on...") | Rewrite as declarative or imperative |

### Step 3 — Burstiness Check

Count sentence lengths (in words) across the full text. Calculate:
- Mean sentence length
- Longest sentence / shortest sentence ratio
- Run of 3+ consecutive sentences within 3 words of the mean (flat zone)

**Target**: ratio ≥ 3:1 (longest to shortest). Flat zones of 4+ sentences should be broken.

Report the distribution. Rewrite one flat zone as an example.

### Step 4 — Authenticity Scan

Check for tells that AI describes rather than experiences:

| Tell | Example | Fix |
|------|---------|-----|
| No anecdote / all abstract | "I have experience managing cross-functional teams" | Specific: who, when, what broke, what happened |
| Hedging density | might, could, arguably, it's important to note (>3 per 300 words) | Commit to the claim or cut it |
| Abstract nominalization | "implementation", "utilization", "optimization" hiding who did what | "We shipped", "Sarah rebuilt", "I cut latency by 40ms" |
| Positivity bias | No tension, no failure, no contradiction | Add one thing that went wrong or one position held against consensus |
| Passive agency | "It was decided that..." / "Steps were taken to..." | Name the agent |
| Unmotivated paragraph disconnection | Coherence signaled only by paragraph breaks, with no connective tissue tying a paragraph to what preceded it — AI text underuses discourse markers relative to human writing, not the overuse pattern people expect | Add the connector that's actually true: "but", "so", "that's why", a callback to the prior claim — whatever the real logical relationship is, stated |
| Reflexive both-sidesing | A concession/counterargument pair inserted where nothing in the source calls for balance — distinct from generic hedging (Step 4's Hedging density row): this is manufactured symmetry, not uncertainty | Cut the unearned "on the other hand" — if the source doesn't actually weigh both sides, the text shouldn't perform weighing them |

### Step 5 — Synthesis and Rewrite Offer

After flagging, offer three options:
1. **Audit only** — Return the flagged report, let the user rewrite
2. **Targeted rewrites** — Rewrite each flagged passage inline, preserving the user's intent
3. **Full humanized draft** — Rewrite the entire text applying all fixes; user reviews

Default to option 2 unless the user specifies otherwise.

## Output Format

```
HUMANIZE AUDIT: [document type] — [word count]

VOCABULARY FLAGS (N found)
[line/paragraph] "exact phrase" → TIER 1 hit: [word]
  Suggestion: [concrete replacement]

STRUCTURAL FLAGS (N found)
[signal type] — [location description]
  Fix: [specific instruction]

BURSTINESS REPORT
Mean sentence length: X words
Longest/Shortest ratio: X:1
Flat zones: [locations]
Example rewrite: [before] → [after]

AUTHENTICITY FLAGS (N found)
[tell type] — [exact phrase or passage]
  Fix: [specific instruction or rewrite]

SUMMARY
Risk level: LOW / MEDIUM / HIGH
Top 3 priority changes: [ordered list]
```

## Quality Standards

- Every flag must cite the exact text, not a paraphrase
- Every suggestion must be concrete — not "be more specific" but "add the year, the company name, or the metric"
- Never remove the author's argument, only the AI fingerprint
- Preserve register: if the source is casual, rewrites stay casual
- Do not introduce new claims the author didn't make
- **Fix structure, not just vocabulary.** A synonym swap or breaking one paragraph in two is
  evidentially weak — it treats the fingerprint as word choice when it's mostly argument order and
  paragraph-opening strategy. A real fix reorganizes how the passage makes its point, not just what
  words it uses to make it.

## Non-goals

This skill makes AI-assisted text sound authentic in the stated author's voice. It does not, and
should never be used to, fabricate a fake human byline, invented credentials, or a false claim of
unassisted authorship where disclosure is required or expected — those are different problems
(see the Sports Illustrated/AdVon undisclosed-AI-byline case for what that failure mode looks like
in practice). "Sound like the author" and "hide that AI was involved" are not the same request, and
this skill only ever does the former.

---

## Related Skills

| Skill | When to apply |
|-------|--------------|
| `knowledge-synthesis` | Polish Zettelkasten notes or wiki pages after synthesis |
| `knowledge-confluence-sync` | Publish humanized documentation to Confluence |
| `meta-prompt-engineering` | Improve prompts that generate the text being humanized |

## Reference Files

- `references/word-lists.md` — Full flagged vocabulary, tier rationale, and safe substitutions
- `references/research-notes.md` — Detection mechanism detail, burstiness math, source citations
