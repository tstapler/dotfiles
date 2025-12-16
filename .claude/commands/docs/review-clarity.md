---
description: Review documentation for clarity, conciseness, and technical precision using cognitive load theory and decision-focused writing
allowed-tools: Read, Glob, Grep, Edit, MultiEdit, Write
---

# Documentation Clarity Review

Review the specified documentation file(s) using research-backed technical writing principles to ensure they are tight, terse, and technically precise for efficient human consumption.

**Target**: $ARGUMENTS

## Review Framework

Apply the **Three Questions Framework** (from [[Technical Writing - What Actually Counts]]):
1. **Decision Focus**: What specific decision does the reader need to make?
2. **Obstacle Identification**: What prevents them from making that decision confidently?
3. **Minimum Viable Information**: What is the least information needed to overcome those obstacles?

## Review Criteria

### 1. Cognitive Load Optimization (Based on [[Cognitive Load Theory in Technical Documentation]])

**Working Memory Limit**: Humans process 7±2 chunks. Reduce extraneous cognitive load.

- **Spatial Contiguity**: Related information appears physically close together
- **Coherence Principle**: Remove interesting but irrelevant information
- **Chunking**: Group information into 5-7 item clusters maximum
- **Progressive Disclosure**: Layer from overview to implementation details
- **Given-New Structure**: Progress from familiar to new information

### 2. Conciseness (Cut the Fluff)

- Remove filler words: "very", "really", "basically", "actually", "just", "simply", "in fact"
- Eliminate redundant phrases: "in order to" → "to", "at this point in time" → "now", "due to the fact that" → "because"
- Delete obvious statements and unnecessary context ("Context Dumping" anti-pattern)
- Avoid "Show My Work Problem": Include conclusions and actions, not reasoning process
- **Active Voice Preference**: "Configure the database" vs "The database should be configured"
- One idea per sentence, one topic per paragraph

### 3. Technical Precision

- Use specific, concrete terms over vague descriptions
- Include exact values, not approximations ("30 seconds" not "about half a minute")
- Define acronyms on first use, then use consistently
- Ensure code examples are correct and runnable
- Verify technical claims are accurate
- Name components explicitly rather than using pronouns

### 4. Information Architecture (Inverted Pyramid)

- **Front-Load Impact**: Critical information and risk factors appear first
- **Tier 1/2/3 Hierarchy**: Essential (decision-making) → Important (implementation) → Optional (context)
- Use descriptive headings that convey meaning (not just "Overview")
- Prefer bullet lists and tables over prose for comparisons
- Keep paragraphs short (3-5 sentences max)
- Use code blocks for commands, configs, and examples

### 5. Actionable Content

- **Problem → Solution → Action** pattern: Lead with problem, present solution, specify actions
- Lead with "what" and "how", not "why" (unless context is critical)
- Provide concrete examples, not abstract descriptions
- Include copy-pasteable commands and code
- Make next steps obvious with explicit action items
- Use **Priority Indicators**: CRITICAL (blocks progress), REQUIRED (necessary), CONSIDER (optimization)

### 6. Diátaxis Alignment (if applicable)

Check document type matches content:
- **Tutorial**: Learning-oriented, step-by-step for beginners
- **How-to Guide**: Task-oriented instructions for specific goals
- **Explanation**: Understanding-oriented discussions of concepts
- **Reference**: Information-oriented technical descriptions

Don't mix types—each document should have one primary purpose.

## Anti-Patterns to Flag

From [[Technical Writing - What Actually Counts]]:
- **Comprehensive Coverage Trap**: Documenting everything instead of what matters for decisions
- **Show My Work Problem**: Including reasoning process instead of conclusions and actions
- **Feature Documentation**: Describing what systems do rather than what users accomplish
- **Academic Writing Style**: Passive voice, abstract language, buried action items
- **Context Dumping**: Extensive background without clear relevance to current decisions
- **Split Attention**: Related information separated by irrelevant content

## The 30-Second Test

Can a knowledgeable reader understand the core message and required action within 30 seconds? If not, restructure for clarity.

## Output Format

For each file reviewed, provide:

1. **Summary**: One-line assessment + 30-second test result (pass/fail)
2. **Cognitive Load Issues**: Information processing overhead problems with line references
3. **Conciseness Issues**: Words/phrases to cut with before/after examples
4. **Structure Issues**: Organization and hierarchy problems
5. **Anti-Patterns Found**: Which patterns from the list above are present
6. **Suggested Edits**: Specific before/after improvements prioritized by impact
7. **Recommended Actions**: Prioritized list (CRITICAL/REQUIRED/CONSIDER)

After identifying issues, ask if I should apply the fixes automatically.

## Review Process

1. Read the target file(s)
2. Apply the Three Questions Framework to assess purpose
3. Run the 30-Second Test
4. Identify violations using criteria above
5. Categorize by cognitive load impact (high/medium/low)
6. Provide specific, actionable feedback with line references
7. Offer to apply fixes if requested
