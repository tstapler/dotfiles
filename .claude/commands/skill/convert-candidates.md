---
title: Analyze Skill Conversion Candidates
description: Analyze text, commands, or other content to determine if it should be converted to a Claude Agent Skill
arguments:
  - name: content
    description: The content to analyze (text, file path, command name, or description of functionality)
    required: true
---

# Skill Conversion Candidate Analysis

Analyze the provided content to determine if it would benefit from being converted to a Claude Agent Skill.

**Content to analyze**: $ARGUMENTS

---

## Analysis Framework

### Step 1: Content Identification

First, identify what type of content was provided:

1. **File path** - Read and analyze the file contents
2. **Slash command reference** (e.g., `/jira:create`) - Read the command file and analyze
3. **Raw text/instructions** - Analyze the text directly
4. **Conceptual description** - Analyze the described functionality

If a file path or command reference is provided, read the content first before proceeding.

### Step 2: Skill Suitability Assessment

Evaluate the content against these criteria for skill conversion:

#### Strong Indicators FOR Skill Conversion

| Indicator | Description | Weight |
|-----------|-------------|--------|
| **Reusable across projects** | Would this be useful in multiple different projects? | High |
| **Domain expertise** | Does it encode specialized knowledge (financial, legal, technical)? | High |
| **Complex workflows** | Does it involve multi-step processes that benefit from standardization? | High |
| **Executable code needed** | Would bundled scripts (Python, JS) add deterministic value? | High |
| **Progressive disclosure opportunity** | Is there tiered content (core instructions + detailed reference)? | Medium |
| **Organizational knowledge** | Does it capture brand guidelines, coding standards, or team conventions? | Medium |
| **Token optimization potential** | Would structured formats significantly reduce token usage? | Medium |

#### Strong Indicators AGAINST Skill Conversion

| Indicator | Description | Weight |
|-----------|-------------|--------|
| **Project-specific** | Only relevant to one specific codebase | High |
| **Simple/linear** | Just a simple prompt without complexity | High |
| **Ephemeral** | Content that changes frequently | Medium |
| **No executable component** | Pure text with no benefit from bundled scripts | Low |
| **Single-use** | Only needed occasionally for one-off tasks | Medium |

### Step 3: Scoring and Recommendation

Based on the assessment, provide a clear recommendation:

**Scoring Scale**:
- **9-10**: Excellent skill candidate - highly recommended
- **7-8**: Good skill candidate - recommended
- **5-6**: Moderate candidate - consider based on usage frequency
- **3-4**: Weak candidate - probably better as a command
- **1-2**: Poor candidate - keep as-is or simple command

### Step 4: Present Analysis to User

Present your findings in this format:

```
## Skill Conversion Analysis

### Content Summary
[Brief description of what was analyzed]

### Suitability Score: X/10

### Assessment

**Strengths for Skill Conversion:**
- [Strength 1]
- [Strength 2]
- [Strength 3]

**Weaknesses/Concerns:**
- [Concern 1]
- [Concern 2]

### Recommendation
[RECOMMENDED | CONSIDER | NOT RECOMMENDED]

[Explanation of recommendation]

### If Converted to Skill

**Suggested Skill Name**: [lowercase-with-hyphens]
**Suggested Description**: [Clear description of when to use]

**Proposed Structure**:
- SKILL.md: [What would go here]
- reference.md: [If needed, what would go here]
- scripts/: [If needed, what scripts]
- resources/: [If needed, what resources]

**Estimated Token Budget**: [Rough estimate]
```

### Step 5: Offer Skill Creation

After presenting the analysis, if the score is 5 or higher, ask the user:

"Would you like me to create this skill using `/skill:create`? I can invoke the skill creation workflow with the suggested name and purpose."

**If the user agrees**, invoke the `/skill:create` command with:
- `skill_name`: The suggested skill name
- `skill_purpose`: The suggested description
- `location`: Ask user preference (project or user)

**If the user declines or score is below 5**, suggest alternatives:
- Keep as a slash command (if it's currently a command)
- Create a simpler command instead
- Document the knowledge elsewhere

---

## Examples

### Example 1: Good Skill Candidate

**Input**: "I have detailed instructions for analyzing PostgreSQL query performance, including scripts to parse EXPLAIN output and calculate statistics"

**Analysis**:
- Score: 8/10
- Reusable: Yes (any project with PostgreSQL)
- Domain expertise: Yes (database optimization)
- Executable code: Yes (parsing scripts add value)
- Recommendation: RECOMMENDED

### Example 2: Poor Skill Candidate

**Input**: "A command that runs `git status` and formats the output"

**Analysis**:
- Score: 2/10
- Too simple: Just wraps a single command
- No domain expertise: Basic git usage
- No executable benefit: Shell command is sufficient
- Recommendation: NOT RECOMMENDED - keep as simple command or alias

### Example 3: Moderate Candidate

**Input**: "/jira:create command for creating Jira tickets"

**Analysis**:
- Score: 6/10
- Reusable: Partially (depends on Jira usage)
- Organizational knowledge: Yes (ticket standards)
- But: Heavily dependent on external API (MCP)
- Recommendation: CONSIDER - evaluate usage frequency

---

## Notes

- Skills are best for encoding **stable, reusable knowledge** with **executable components**
- Commands are better for **simple prompts** or **project-specific workflows**
- The progressive disclosure architecture of skills (SKILL.md + reference files) is most valuable when there's significant content to tier
- Consider maintenance burden: skills require more structure than commands
