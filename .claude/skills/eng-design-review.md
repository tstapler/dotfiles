---
name: eng-design-review
description: End-to-end design document / RFC review workflow. Downloads a Confluence
  page (or accepts pasted markdown), analyzes it against the three-layer onion framework,
  drafts tiered inline comments, pauses for user review, posts approved comments to
  Confluence, then surfaces open comment threads that need a response.
---

# Design Document Review

Full workflow for reviewing a design doc or RFC: fetch → analyze → draft comments → review with user → post → surface unanswered threads.

## Invoke With

```
/doc-review <confluence_url_or_page_id>
/doc-review <confluence_url_or_page_id> --focus "partitioning,autovacuum"
/doc-review --threads-only <confluence_url_or_page_id>
```

- Omit URL to review a doc already in context (pasted markdown).
- `--focus` scopes analysis to specific topics.
- `--threads-only` skips analysis and goes straight to Phase 4 (surface open threads).

---

## Phase 1 — Fetch Document

Use `mcp__claude_ai_Atlassian_Rovo__getConfluencePage` with `contentFormat: "markdown"`.

Extract from the URL or user input:
- `cloudId` — the Atlassian hostname, e.g. `betfanatics.atlassian.net`
- `pageId` — the numeric ID from the URL path (e.g. `/pages/3022553099`)

```
getConfluencePage(cloudId, pageId, contentFormat="markdown")
```

Save the page body to `/tmp/doc-review-<pageId>.md` for reference. Note the page title.

If the URL is not Confluence (e.g. a GitHub PR, Google Doc link, or pasted markdown), adapt:
- GitHub PR: use `gh pr view <number> --json body` for the description; use `mcp__claude_ai_Atlassian_Rovo__search` for related Confluence context.
- Pasted text: skip the fetch step and analyze the text directly.

Also fetch existing inline and footer comments to understand what has already been raised:
```
getConfluencePageInlineComments(cloudId, pageId, resolutionStatus="open")
getConfluencePageFooterComments(cloudId, pageId)
```

---

## Phase 2 — Analyze

### Three-Layer Onion Assessment

Evaluate the document against the three-layer structure from [[Design Documents]]:

**Layer 1 — Problem Layer**
- Is the problem statement clear and specific?
- Are stakeholders and affected systems identified?
- Are non-goals stated explicitly? (Non-goals are artificial constraints that prevent scope explosion — they are not just "things we won't do" but "things that could reasonably be goals but are explicitly excluded.")
- Are functional and non-functional requirements present?

**Layer 2 — Functional Specification**
- Does the doc describe how the system works from an external perspective?
- Are alternatives considered and rejected with rationale?
- Does the functional spec demonstrably satisfy the Layer 1 requirements?

**Layer 3 — Technical Specification**
- Does the implementation plan demonstrate feasibility?
- Are operational concerns addressed (monitoring, autovacuum, load testing, rollback)?
- Does the technical spec implement the Layer 2 functional spec?

**Fatal flaw rule:** If any layer has a fatal flaw, note it prominently. A broken Layer 1 makes Layer 2 moot; a broken Layer 2 makes Layer 3 moot.

### Domain-Specific Analysis

For each major technical decision in the document, probe:
1. **Are the assumptions stated and falsifiable?** Flag assumptions presented as facts.
2. **Are irreversible decisions called out?** These require stronger justification.
3. **Is there prior art at the org?** Check if a related decision was made previously and whether this doc acknowledges it.
4. **Are the operational implications addressed?** Steady-state concerns (vacuuming, autovacuum, compaction, log rotation, index maintenance) are commonly missing from design docs.
5. **Is the load testing plan concrete?** Vague "we will load test" is not the same as "we will test scenario X against instance type Y before go-live."

Apply relevant domain knowledge (PostgreSQL, Kafka, distributed systems, double-entry accounting, etc.) when the doc touches those areas.

---

## Phase 3 — Draft Comments

Write all comments to `/tmp/doc-review-<pageId>-comments.md`.

### Tiering

| Tier | Label | Criteria |
|------|-------|----------|
| 🔴 Critical | Must address before go-live | Correctness risk, data loss risk, irreversible decision missing justification, assumption that is demonstrably false |
| 🟡 Significant | Should discuss; risk if ignored | Design smell, missing operational concern, prior org decision not acknowledged, unquantified risk |
| 🔵 Note | Lower priority, good or neutral | Clarifying question, minor inconsistency, positive observation worth calling out |

### Comment Format

Each comment in the review file:

```markdown
## [TIER] COMMENT N — [Short title]

**Anchor text (from doc):**
> "[Exact quoted text from the document that the comment should attach to]"

**Comment body:**
[The actual comment text to post. Written in second person, direct, specific.
Cite evidence: schema, PR, prior doc, external reference.
End with a concrete question or actionable ask, not an open critique.]
```

### Anchor Text Rules

- Quote the exact rendered text (no markdown symbols like `**` or `` ` ``).
- Prefer unique phrases — short enough to select, specific enough to not repeat.
- If no good anchor exists in the text (e.g., the doc omits something entirely), write a footer comment instead (no anchor, posted at page level).
- Verify uniqueness: count how many times the anchor appears in the body.

### Comment Writing Guidelines

- Lead with the specific concern, not preamble.
- Cite evidence first, then the implication.
- One clear question per comment. Multi-issue comments get lost.
- Don't editorialize beyond what the evidence supports.
- Positive observations belong in 🔵 Notes — they help authors understand what worked.
- Keep it under 150 words unless code examples are needed.

---

## Phase 4 — User Review Gate

**STOP. Present the review file to the user before posting anything.**

Show:
1. Layer assessment summary (one line per layer: ✅ / ⚠️ / ❌)
2. Comment count by tier
3. Full list of comment titles with anchor text previews
4. Any comments already posted (mark as POSTED)

Ask:
> "Ready to review the full comments at `/tmp/doc-review-<pageId>-comments.md`. 
> Which comments should I post? (all / specific numbers / none)"

Wait for explicit approval. Do not post until the user says to proceed.

If the user edits comments or asks to change wording, update the file and confirm before posting.

---

## Phase 5 — Post Approved Comments

Post each approved comment as a Confluence inline comment using:
```
createConfluenceInlineComment(
  cloudId,
  pageId,
  body,
  contentFormat="markdown",
  inlineCommentProperties={
    textSelection: "<anchor text>",
    textSelectionMatchCount: <N>,
    textSelectionMatchIndex: 0
  }
)
```

For comments without a valid anchor (entire-doc concerns, missing sections), use:
```
createConfluenceFooterComment(cloudId, pageId, body, contentFormat="markdown")
```

After each successful post, mark the comment as POSTED in the review file and note the comment ID.

If posting fails (anchor not found, 400 error), try a shorter/different anchor from the same paragraph. If it still fails, fall back to a footer comment.

---

## Phase 6 — Surface Open Threads Needing Response

Fetch open inline and footer comments on the page:
```
getConfluencePageInlineComments(cloudId, pageId, resolutionStatus="open")
getConfluencePageFooterComments(cloudId, pageId)
```

For each open comment thread:
1. Read the thread including replies.
2. Determine: is there an unanswered question directed at the current user or requiring the doc author's response?
3. Classify:
   - **Needs your answer** — a direct question to you that has no reply
   - **Needs author answer** — a question that the doc author should address (surface for awareness)
   - **Informational** — a comment with no open question; skip

For threads **Needs your answer**, extract the question and present it:

```
THREAD [comment ID] — [anchor text preview]
Question: "[exact question text]"
→ Suggested response: [draft a concise answer based on context you have]
   Post? (yes / edit / skip)
```

Wait for user input per thread. Post approved responses using:
```
createConfluenceFooterComment(cloudId, commentId, parentCommentId=<id>, body)
```
or via:
```
createConfluenceInlineComment with parentCommentId=<id>
```

---

## Phase 7 — Summary

Print a final table:

| # | Tier | Title | Status |
|---|------|-------|--------|
| 1 | 🔴 Critical | house_bucket hot row | Posted (#3025633634) |
| 2 | 🟡 Significant | Eviction slip plan | Posted (#...) |
| 3 | 🔵 Note | entry_remaining HOT eligibility | Skipped by user |

Counts: X posted, Y skipped, Z thread replies posted.

---

## Token Optimization

- Fetch the full page once; save to `/tmp`. Do not re-fetch for each comment.
- Fetch all existing comments in one call each (inline + footer) at Phase 1.
- Do not load the full page body into analysis if only `--threads-only` was requested.
- For large pages (> 10K words), focus analysis on the sections relevant to `--focus` topics.
- Write drafts to `/tmp` files, not into context. Reference by path.

---

## Design Doc Quality Checklist (quick reference)

From [[Design Documents]] — three-layer onion + common pitfalls:

- [ ] Layer 1: Problem statement clear and specific
- [ ] Layer 1: Non-goals stated (not just what won't be done, but what could be done but isn't)
- [ ] Layer 1: NFRs explicit (throughput, latency, availability, retention)
- [ ] Layer 2: Alternatives considered with rejection rationale
- [ ] Layer 2: Functional spec maps to Layer 1 requirements
- [ ] Layer 3: Irreversible decisions called out and justified
- [ ] Layer 3: Operational concerns addressed (vacuum, autovacuum, index maintenance, monitoring)
- [ ] Layer 3: Load test plan concrete (scenario + instance type + acceptance criteria)
- [ ] Layer 3: Prior org decisions acknowledged (don't contradict without explanation)
- [ ] No RFC failure modes: not too long to read, decision mechanism named, not bikeshedding bait
