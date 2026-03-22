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
- Present in structured format
- Highlight key insights and relationships

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

## Multi-Topic Research Protocol

For queries with 2+ distinct subtopics, use parallel subagent delegation instead of sequential in-context research:

1. **Write `research/research_plan.md` first** — list each subtopic, its search strategy, and a 3–5 search cap
2. **Delegate in parallel** — spawn one Task subagent per subtopic (up to 3 simultaneously); each subagent writes findings to `research/findings-<subtopic>.md`
3. **Synthesize from files** — read findings files back into context only at synthesis time; do not accumulate subagent output in-context

This isolates each subtopic's context window, preventing degradation across long research sessions (see `context-engineering` skill for the underlying principle).

## Best Practices

- Use tools proactively in parallel when appropriate
- Document each step of analysis
- Complex tasks should trigger the full workflow
- Always verify critical information from multiple sources
