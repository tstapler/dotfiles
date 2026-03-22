---
name: claude-technique-evaluator
description: Evaluate new Claude and Claude Code techniques, tools, features, prompting patterns, or workflow changes for adoption value. Use when encountering blog posts, release notes, tutorials, community tips, or configuration changes related to Claude and want to assess whether they fit the user's existing workflow (Logseq wiki, Python tools monorepo, skills library), align with Anthropic best practices, and are worth adopting. Produces structured evaluations with go/no-go recommendations and integration paths.
---

# Claude Technique Evaluator

Evaluate new Claude techniques, tools, and workflow changes for adoption value against Anthropic best practices and the user's existing workflow.

## When to Use This Skill

**Use for:**
- Evaluating new Claude/Claude Code features (extended thinking, tool use patterns, MCP servers)
- Assessing prompting techniques from blog posts, tutorials, or community tips
- Reviewing workflow changes (new skills, commands, agents, model configurations)
- Comparing techniques against Anthropic's published best practices
- Deciding whether to adopt a tool, pattern, or configuration change

**Don't use for:**
- Building or implementing the technique (use `prompt-engineering` or `python-development`)
- General research without an adoption decision (use `research-workflow`)
- Creating Zettelkasten notes from evaluations (use `knowledge-synthesis` after evaluation)

## Core Evaluation Workflow

### Phase 1: Ingest and Understand

Accept input in any form:
- **URL**: Fetch and extract the technique description
- **File**: Read the document or code
- **Description**: Parse the user's explanation
- **Release notes**: Extract relevant changes

**Extract these elements:**
1. What is the technique/tool/feature?
2. What problem does it solve?
3. What does it change about how Claude is used?
4. What are the claimed benefits?

### Phase 2: Research Anthropic Standards

Verify the technique against official Anthropic guidance.

**Search strategy (use `research-workflow` patterns):**
1. Search Anthropic docs: `docs.anthropic.com` for official guidance
2. Search Anthropic engineering blog for related posts
3. Check Claude Code documentation for feature support
4. Search Anthropic cookbook/examples for recommended patterns

**Key questions:**
- Does Anthropic explicitly recommend this approach?
- Does it contradict any official guidance?
- Is it a supported feature or an undocumented hack?
- What are the official alternatives?

For detailed Anthropic best practices reference: see `references/anthropic-standards.md`

### Phase 3: Workflow Fit Analysis

Evaluate fit against the user's specific workflow.

**Check against:**
- Existing skills library at `~/.claude/skills/`
- Current CLAUDE.md configuration and tool priorities
- Python tools monorepo patterns (uv, Typer, Pydantic)
- Logseq wiki and knowledge synthesis workflow
- Current model selection and agent design patterns

**Assess:**
- Does this overlap with an existing skill? Which one?
- Would this replace, enhance, or conflict with current tools?
- What is the integration effort (minutes, hours, days)?
- Does it require changes to existing skills or CLAUDE.md?

For detailed workflow context: see `references/workflow-context.md`

### Phase 4: Score and Assess

Apply the evaluation framework across six dimensions:

| Dimension | Question | Scale |
|-----------|----------|-------|
| **Anthropic Alignment** | Does it follow official Anthropic guidance? | Strong / Moderate / Weak / Contradicts |
| **Integration Complexity** | How hard to adopt in current workflow? | Trivial / Low / Medium / High |
| **Benefit Magnitude** | How much value does it add? | Transformative / Significant / Moderate / Marginal |
| **Overlap Assessment** | Does it duplicate existing capabilities? | Novel / Extends / Partial Overlap / Full Overlap |
| **Risk Assessment** | Any downsides, instability, or concerns? | Minimal / Acceptable / Notable / Prohibitive |
| **Maturity Level** | How stable/proven is the technique? | Production / Stable / Beta / Experimental |

**Priority Score** (derived from dimensions):

| Priority | Criteria |
|----------|----------|
| **Adopt Now** | Strong alignment + Significant benefit + Low complexity + Novel |
| **Plan Adoption** | Good alignment + Moderate-Significant benefit + Medium complexity |
| **Monitor** | Acceptable alignment + Some benefit but High complexity or Experimental |
| **Skip** | Contradicts guidance OR Full overlap OR Prohibitive risk OR Marginal benefit |

### Phase 5: Produce Evaluation

Generate structured output using the evaluation template.

**Output requirements:**
- Structured for readability with clear sections
- Logseq-compatible formatting (can be saved as wiki page)
- Includes actionable next steps with specific commands or file changes
- Links to relevant Anthropic documentation
- Explicit go/no-go recommendation with reasoning

For the output template: see `references/evaluation-template.md`

## Quick Evaluation Mode

For simple yes/no questions about a technique, skip the full workflow:

1. Identify the technique in one sentence
2. Check if it aligns with or contradicts known Anthropic guidance
3. Check if the user already has this capability
4. Give a one-paragraph recommendation

## Skill Chaining

| Situation | Chain To |
|-----------|----------|
| Need to research Anthropic docs/blog | `research-workflow` |
| User wants evaluation saved as wiki note | `knowledge-synthesis` |
| Technique is a prompting pattern | `prompt-engineering` |
| Technique involves model choice | `model-selection` |
| Adoption requires new skill creation | `prompt-engineering` |

## Quality Standards

- Never recommend adopting a technique that contradicts official Anthropic guidance without explicit warning
- Always check for overlap with existing skills before recommending adoption
- Provide specific integration steps, not vague suggestions
- Cite sources for all Anthropic best practice claims
- Distinguish between official Anthropic guidance and community practices

## Progressive Context

- User's detailed workflow context: see `references/workflow-context.md`
- Anthropic best practices reference: see `references/anthropic-standards.md`
- Evaluation output template: see `references/evaluation-template.md`
