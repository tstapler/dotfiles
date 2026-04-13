---
name: research-workflow
description: Apply systematic research methodology for multi-step research, fact-finding, web search, or verification tasks. Use when performing Brave Search, Puppeteer navigation, or synthesizing information from multiple sources.
---

# Research Workflow

Follow this systematic approach for research, fact-finding, or web verification tasks.

## Core Workflow

### 1. Initial Analysis

- Break down the query into core components
- Identify key concepts and relationships
- **For multi-subtopic queries (2+ distinct aspects): write `research_plan.md` first** — list subtopics, assign search strategy per subtopic, and commit to scope before searching
- Determine which tools will be most effective

### 2. Primary Search (Brave Search)

- Start with broad context searches
- Use targeted follow-up searches for specific aspects
- Apply search parameters strategically (count, offset)
- Document and analyze search results

### 3. Deep Verification (Puppeteer/WebFetch)

- Navigate to key websites identified in search
- Take screenshots of relevant content
- Extract specific data points
- Click through and explore relevant links

### 4. Data Processing

- Use REPL/Analysis for complex calculations
- Process CSV files or structured data
- Create visualizations when helpful

### 5. Synthesis & Presentation

- Combine findings from all tools
- Present using the **ADR-Ready Summary** format (see below)
- Highlight key insights and trade-offs
- End with a concrete recommendation, not a survey

## Brave Search Guidelines

**CRITICAL RATE LIMIT**: 1 request per second

- NEVER make consecutive calls without sleeping 1+ seconds
- OR run a different command between searches

**Search cap**: 3–5 searches maximum per subtopic — scope each subtopic in `research_plan.md` before starting to prevent runaway token usage.

**Best practices**:
- Use `count` parameter for result volume
- Apply `offset` for pagination
- Combine multiple related searches
- Document queries for reproducibility
- Include full URLs, titles, descriptions
- Note search date/time for each query

## Puppeteer Guidelines

- Take screenshots of key evidence
- Use selectors precisely for interaction
- Handle navigation errors gracefully
- Document URLs and interaction paths
- Verify you arrived at correct page; retry if not

## Source Documentation Requirements

**All findings must include**:
- Full URLs and titles
- Access dates
- Source links for quotes
- Citation metadata from search results

---

## Research Output Standard

Every findings file must meet this standard before synthesis. A complete software engineering research output answers five questions:

1. **What exists?** — Options, libraries, patterns, prior art
2. **How do they compare?** — Trade-off matrix on axes relevant to the decision
3. **What can go wrong?** — Failure modes, risks, known production issues
4. **What does adoption cost?** — Migration path, learning curve, operational burden
5. **What should we do?** — A concrete recommendation with stated reasoning

A findings file that only answers question 1 is incomplete. Do not synthesize until all five are addressed.

---

## Design Review Template

Use this structure for every `research/findings-<subtopic>.md` file. Fill every section; write "N/A — not applicable" rather than omitting a section.

```markdown
# Findings: <Subtopic>

## Summary
One paragraph. What this subtopic covers and the key conclusion.

## Options Surveyed
Brief list of candidates examined (libraries, patterns, approaches).

## Trade-off Matrix
| Option | <Axis 1> | <Axis 2> | <Axis 3> | Notes |
|--------|----------|----------|----------|-------|
| ...    | ...      | ...      | ...      | ...   |

Choose axes relevant to the decision (e.g., consistency guarantees, network overhead,
conflict resolution model, query expressiveness, ecosystem maturity, license).
Rate comparatively (High/Med/Low or a short phrase), not with made-up scores.

## Risk and Failure Modes
For each top candidate, list:
- Known production failure modes (data loss, split-brain, silent corruption, etc.)
- Conditions that trigger them
- Mitigations available

## Migration and Adoption Cost
- Effort to integrate into the current codebase
- Dependencies introduced
- Breaking changes or incompatibilities
- Rollback difficulty if adoption fails

## Operational Concerns
- Monitoring and observability hooks available
- Debugging experience (tooling, log quality, error messages)
- Upgrade path / release cadence / maintenance burden

## Prior Art and Lessons Learned
- Production deployments (open source projects, public post-mortems, conference talks)
- What worked, what failed, what surprised teams

## Open Questions
Questions that cannot be answered from research alone and require a prototype or spike:
- [ ] <Question> — blocks decision on: <what it affects>

## Recommendation
**Recommended option**: <Name>

**Reasoning**: Why this option over the next-best alternative. Be explicit about which
trade-offs were weighted most heavily and why (e.g., "we prioritized offline-first
correctness over query expressiveness because...").

**Conditions that would change this recommendation**: What would make a different
option correct (e.g., "if the team grows past 5 engineers, X becomes preferable because...").

## Pending Web Searches
The following queries should be run by the parent agent and results appended below:

1. `<exact search query>` — reason: <why this matters>
```

---

## Trade-off Analysis Guidance

When comparing options, resist listing pros and cons in isolation. Instead:

**Choose axes that reflect the actual decision constraints.** For a local-first sync library the axes might be: conflict resolution model, offline correctness, bundle size, query capability, and license. For an event sourcing framework: event store maturity, projection rebuild time, schema evolution strategy, and operational tooling.

**Compare options against each other on each axis**, not against an abstract ideal. "Library A has good performance" is not useful. "Library A processes 50k events/sec vs Library B's 8k on the same hardware" is.

**Name the dominant trade-off explicitly.** Every meaningful architectural choice involves a fundamental tension (consistency vs. availability, simplicity vs. flexibility, etc.). Name it in the Summary and explain which side the recommendation lands on and why.

**Weight axes by project context.** State which axes matter most for this specific decision (e.g., "correctness under partition is non-negotiable; bundle size is a secondary concern"). This makes the recommendation defensible when the context changes.

---

## ADR-Ready Synthesis

When all subagents complete, synthesize findings into a single `research/synthesis.md` using this structure. This file is the direct input to `/plan:adr`.

```markdown
# Research Synthesis: <Topic>

## Decision Required
One sentence: what architectural decision this research informs.

## Context
Why this decision is being made now. What constraints or goals drive it.

## Options Considered
| Option | Summary | Key Trade-off |
|--------|---------|---------------|
| ...    | ...     | ...           |

## Dominant Trade-off
The fundamental tension this decision navigates. Which options land on which side.

## Recommendation
**Choose**: <Option>

**Because**: <2–4 sentences of reasoning that reference specific trade-offs from the
findings, not generic claims.>

**Accept these costs**: <What we give up by choosing this option.>

**Reject these alternatives**:
- <Option B>: rejected because <specific reason tied to our context>
- <Option C>: rejected because <specific reason tied to our context>

## Open Questions Before Committing
- [ ] <Question requiring a prototype/spike>
- [ ] <Question requiring a proof-of-concept>

If this list is non-empty, a spike should be scheduled before writing the ADR.

## Sources
Links to the findings files this synthesis draws from.
```

---

## Multi-Topic Research Protocol

For queries with 2+ distinct subtopics, use parallel subagent delegation instead of sequential in-context research:

1. **Write `research/research_plan.md` first** — list each subtopic, its search strategy, a 3–5 search cap, and the axes to use in the trade-off matrix
2. **Delegate in parallel** — spawn one Task subagent per subtopic (up to 3 simultaneously); each subagent writes findings to `research/findings-<subtopic>.md` using the Design Review Template
3. **Synthesize from files** — read findings files back into context only at synthesis time; produce `research/synthesis.md` using the ADR-Ready Synthesis format

This isolates each subtopic's context window, preventing degradation across long research sessions.

---

## Subagent Web Search Protocol

Subagents launched via the `Agent` tool often cannot access `WebSearch` directly (permission is scoped to the parent context). Use a two-phase approach:

### Phase 1 — Subagent: Training knowledge + search request list

Each subagent:
1. Fills the Design Review Template using training knowledge, marking uncertain claims with `[TRAINING_ONLY — verify]`
2. Appends a `## Pending Web Searches` section listing exact queries the parent should run

### Phase 2 — Parent agent: Run searches and append results

After all subagents complete, the parent agent:
1. Reads each `## Pending Web Searches` section from the findings files
2. Runs each query via `WebSearch` (1 second between queries per rate limit)
3. Appends a `## Web Search Results` section to each findings file with results and source URLs
4. Updates any `[TRAINING_ONLY — verify]` claims that the search results clarify

The parent runs all searches in a single pass across all files to maximize efficiency.

### Subagent prompt template for web-search-limited environments

When spawning research subagents, include this instruction:

> Web search may not be available to you. If `WebSearch` is denied, continue with training knowledge and fill every section of the Design Review Template. Mark uncertain claims `[TRAINING_ONLY — verify]`. Add a `## Pending Web Searches` section listing exact queries you would have run. The parent agent will execute them and update your findings.

---

## Best Practices

- Use tools proactively in parallel when appropriate
- Complex tasks should trigger the full workflow
- Always verify critical claims from multiple sources
- `[TRAINING_ONLY — verify]` marks make it easy to target parent web searches
- A findings file without a Recommendation section is not complete — always end with a concrete choice, not a survey
- Open Questions that require prototyping should block the ADR, not be deferred silently
