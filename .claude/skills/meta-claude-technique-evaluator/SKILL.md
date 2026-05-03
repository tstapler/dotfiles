---
name: meta-claude-technique-evaluator
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
- Building or implementing the technique (use `meta-prompt-engineering` or `code-python`)
- General research without an adoption decision (use `meta-research-workflow`)

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

**Search strategy (use `meta-research-workflow` patterns):**
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
| **Adoption Mode** | Can it be used as-is, or does it need changes first? | As-Is / Minor Tweaks / Fork & Adapt / Build from Scratch |

**Adoption Mode guidance:**
- **As-Is**: Copy the skill's SKILL.md (and any `scripts/`) into `~/.claude/skills/<name>/`, fork the source repo to `tstapler/` on GitHub for update control, and use immediately with no modifications needed
- **Minor Tweaks**: Fork to `tstapler/`, copy into `~/.claude/skills/<name>/`, then apply small adjustments (fix install commands, adjust paths, update docs) before use
- **Fork & Adapt**: Fork to `tstapler/`, copy into `~/.claude/skills/<name>/`, then rework significantly — the core concept is sound but the implementation needs changes for this workflow
- **Build from Scratch**: Concept is valuable but source implementation is not reusable; author a new skill from scratch in `~/.claude/skills/<name>/SKILL.md` using the upstream as inspiration only

**Priority Score** (derived from dimensions):

| Priority | Criteria |
|----------|----------|
| **Adopt Now (As-Is)** | Strong alignment + Significant benefit + Low complexity + Novel + As-Is or Minor Tweaks |
| **Adopt Now (Adapted)** | Strong alignment + Significant benefit + Low-Medium complexity + Novel + Fork & Adapt or Build from Scratch |
| **Plan Adoption** | Good alignment + Moderate-Significant benefit + Medium complexity (any adoption mode) |
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

### Phase 6: Knowledge Synthesis (Always Run — Do Not Wait for User Request)

After producing the evaluation, immediately chain to `knowledge-synthesis` to persist the results. This is mandatory, not optional.

**Create three artifacts**:

1. **Wiki page** at `logseq/pages/<TechniqueName>.md`:
   - Core Definition, Background/Context, Key Characteristics, Applications/Usage
   - Comparison table vs. closest existing tools (especially Claude Code built-ins)
   - Evaluation section: verdict, date, 2-sentence rationale, re-evaluate trigger
   - Related Concepts with `[[Wiki Links]]`
   - Tags: 3-7 `#[[Tag]]` entries per knowledge-synthesis guidelines

2. **Daily synthesis entry** appended to `logseq/pages/Knowledge Synthesis - YYYY-MM-DD.md`:
   - Context: why the evaluation was done
   - Key Findings: bullet list of the most important discoveries
   - Condensed Evaluation Dimensions table from Phase 4
   - Verdict + re-evaluate trigger (if Monitor/Plan)
   - Related Concepts with `[[Wiki Links]]`
   - Sources with URLs
   - Tags

3. **Journal reference** in `logseq/journals/YYYY_MM_DD.md`:
   - One-line entry: `- Evaluated [[TechniqueName]] — verdict: [Adopt Now/Plan/Monitor/Skip] — see [[Knowledge Synthesis - YYYY-MM-DD]]`

**Check before creating wiki page**: search `logseq/pages/` for existing pages on the same topic to update rather than duplicate.

## Quick Evaluation Mode

For simple yes/no questions about a technique, skip the full workflow:

1. Identify the technique in one sentence
2. Check if it aligns with or contradicts known Anthropic guidance
3. Check if the user already has this capability
4. Give a one-paragraph recommendation

## Skill Chaining

| Situation | Chain To |
|-----------|----------|
| Need to research Anthropic docs/blog | `meta-research-workflow` |
| After every evaluation (automatic) | `knowledge-synthesis` — always run Phase 6 without waiting for user request |
| Technique is a prompting pattern | `meta-prompt-engineering` |
| Technique involves model choice | `meta-model-selection` |
| Adoption requires new skill creation | `meta-prompt-engineering` |

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
