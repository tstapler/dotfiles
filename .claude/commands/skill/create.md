---
title: Create Agent Skill
description: Create a new Claude Agent Skill following Anthropic's best practices with prompt engineering guidance
arguments:
  - name: skill_name
    description: Name of the skill (lowercase-with-hyphens, max 64 chars)
    required: true
  - name: skill_purpose
    description: Brief description of what the skill does (max 1024 chars)
    required: true
  - name: location
    description: Where to create the skill (project or user)
    required: false
---

# Create Agent Skill

Create a new Claude Agent Skill following Anthropic's best practices for progressive disclosure, token optimization, and effective skill design.

---

## Overview

This command guides you through creating a production-quality Agent Skill based on:
- Anthropic's Agent Skills architecture (progressive disclosure, hybrid knowledge+code)
- Real-world examples from Claude Cookbooks (financial analyzer, brand guidelines, financial modeling)
- Token optimization patterns (75-80% reduction strategies)
- Security best practices and development workflow

**Skill to create**: ${1:-my-skill}
**Purpose**: ${2:-Describe what this skill does}
**Location**: ${3:-project} (Options: project, user)

---

## Workflow

### Phase 1: Skill Requirements Analysis

Before creating any files, use the **prompt-engineering agent** to design the skill:

<task subagent_type="prompt-engineering">
Design an Agent Skill with the following requirements:

**Skill Name**: ${1:-my-skill}
**Purpose**: ${2:-Describe what this skill does}

**Design Requirements**:

1. **Name and Description Optimization**
   - Validate skill name follows format: lowercase-alphanumeric-with-hyphens (max 64 chars)
   - Craft description that clearly conveys WHEN to use this skill (max 1024 chars)
   - Think from Claude's perspective: what helps triggering decisions?
   - Examples:
     - ✅ Good: "analyzing-financial-statements" + "Calculate financial ratios from statements and generate analysis reports"
     - ❌ Bad: "finance" (too generic) or "comprehensive-financial-ratio-calculation-and-analysis-tool" (too long)

2. **Progressive Disclosure Architecture**
   - Design 3-level content hierarchy:
     - **Level 1 (Metadata)**: Name + description in YAML frontmatter
     - **Level 2 (Core Instructions)**: Main SKILL.md body (target <5,000 tokens)
     - **Level 3+ (Contextual)**: Additional files loaded only when needed
   - Identify what content belongs at each level
   - Keep mutually exclusive contexts in separate files

3. **Hybrid Knowledge + Code Strategy**
   - Determine what should be declarative instructions vs. executable code
   - Plan bundled scripts for deterministic operations (parsing, calculations, transformations)
   - Design scripts to serve dual purpose: executable tool + reference documentation
   - Consider: Python for data processing, JavaScript for web operations, shell for system tasks

4. **Token Optimization**
   - Apply patterns from financial applications:
     - Structure over text: Use JSON/CSV/structured formats vs. natural language
     - Focus over comprehensiveness: Multiple focused files vs. monolithic docs
     - Pipeline over monolith: Sequential generation allowing earlier outputs to inform later steps
     - Separation over inclusion: Keep mutually exclusive contexts separate
   - Estimate token budget for each component

5. **Security Considerations**
   - Never hardcode API keys or sensitive data
   - Plan input sanitization for bundled scripts
   - Identify external network connections requiring audit
   - Consider access control needs

6. **Directory Structure**
   - Plan required files:
     ```
     ${1:-my-skill}/
     ├── SKILL.md              # REQUIRED
     ├── reference.md          # Optional: technical documentation
     ├── examples.md           # Optional: usage examples
     ├── scripts/              # Optional: executable code
     │   ├── process.py
     │   └── utils.js
     └── resources/            # Optional: templates, data files
         └── template.xlsx
     ```

**Deliverables**:
1. Optimized skill name and description
2. Content hierarchy design (what goes in each level)
3. List of files to create with purpose for each
4. Script specifications (if needed): language, purpose, key functions
5. Token budget estimate
6. Security considerations checklist
7. Complete SKILL.md template with YAML frontmatter and markdown body
</task>

### Phase 2: Create Skill Directory Structure

Based on the prompt-engineering agent's design, create the skill directory:

**Location determination**:
- **Project skill**: `.claude/skills/${1:-my-skill}/` (visible to all project users)
- **User skill**: `~/.claude/skills/${1:-my-skill}/` (personal, available across all projects)

**Create directories**:
```bash
# For project skill
mkdir -p .claude/skills/${1:-my-skill}/{scripts,resources}

# For user skill
mkdir -p ~/.claude/skills/${1:-my-skill}/{scripts,resources}
```

### Phase 3: Create SKILL.md (Core Instructions)

**File**: `SKILL.md` in the skill directory

**Template structure** (use the prompt-engineering agent's output):
```markdown
---
name: ${1:-my-skill}
description: [Use the optimized description from prompt-engineering agent]
---

# ${1:-My Skill Title}

[Brief introduction explaining what this skill does and when to use it]

## Core Instructions

### When to Use This Skill
- Use case 1: [specific scenario]
- Use case 2: [specific scenario]
- Use case 3: [specific scenario]

### Main Workflow

1. **Step 1**: [First major step]
   - Substep details
   - Considerations

2. **Step 2**: [Second major step]
   - Substep details
   - Considerations

3. **Step 3**: [Third major step]
   - Substep details
   - Considerations

### Key Principles
- **Principle 1**: Explanation
- **Principle 2**: Explanation
- **Principle 3**: Explanation

### Best Practices
- Practice 1
- Practice 2
- Practice 3

### Common Pitfalls
- ❌ **Pitfall 1**: What to avoid and why
- ❌ **Pitfall 2**: What to avoid and why

### Progressive Context Loading
- For detailed technical reference, see: `reference.md`
- For code examples, see: `examples.md`
- For executable scripts, see: `scripts/` directory

### Security Notes
[If applicable: input validation, API key handling, data sanitization]

## Token Budget
Estimated tokens: [from prompt-engineering agent analysis]
```

**Quality standards**:
- Keep SKILL.md body under 5,000 tokens
- Use clear, imperative instructions
- Reference additional files for detailed content
- Think from Claude's execution perspective

### Phase 4: Create Supporting Files

Based on the prompt-engineering agent's design, create additional files:

#### Optional: reference.md
**Purpose**: Technical documentation, API references, detailed specifications
**Load trigger**: When Claude needs deep technical details
**Content**: Comprehensive reference material that would bloat SKILL.md

#### Optional: examples.md
**Purpose**: Code examples, sample outputs, usage demonstrations
**Load trigger**: When Claude needs concrete examples
**Content**: Working examples showing skill usage patterns

#### Optional: scripts/
**Purpose**: Executable code for deterministic operations
**Design principles**:
- Comprehensive type hints
- Error handling with graceful fallbacks
- Clear separation of concerns
- Dual-purpose: executable + documentation
- Security: input sanitization, no hardcoded secrets

**Example Python script structure**:
```python
#!/usr/bin/env python3
"""
Brief description of what this script does.

This script serves dual purposes:
1. Executable tool Claude can run directly
2. Reference documentation Claude can read for understanding
"""

from typing import Dict, List, Optional
import json
import sys

def safe_operation(value: float, divisor: float) -> Optional[float]:
    """
    Safely perform operation with error handling.

    Args:
        value: Input value
        divisor: Divisor value

    Returns:
        Result or None if error
    """
    try:
        if divisor == 0:
            return None
        return value / divisor
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return None

def main():
    """Main entry point for script execution."""
    # Implementation
    pass

if __name__ == "__main__":
    main()
```

#### Optional: resources/
**Purpose**: Templates, data files, configuration files
**Examples**: Excel templates, JSON schemas, sample datasets

### Phase 5: Evaluation and Testing

Create test cases to validate the skill:

1. **Representative Tasks**
   - List 3-5 tasks this skill should handle
   - Run Claude with the skill on these tasks
   - Observe skill loading patterns (is it triggered appropriately?)

2. **Token Usage Analysis**
   - Measure actual tokens used for typical operations
   - Compare to token budget estimate
   - Identify optimization opportunities

3. **Error Scenarios**
   - Test with invalid inputs
   - Test edge cases
   - Verify error handling in scripts

4. **Security Audit**
   - Review for hardcoded secrets
   - Check input sanitization
   - Verify external network access is documented

### Phase 6: Iteration Based on Usage

Monitor and refine:

1. **Usage Patterns**
   - Is Claude loading the skill at appropriate times?
   - Are there false positives (loaded unnecessarily)?
   - Are there false negatives (not loaded when needed)?

2. **Token Optimization**
   - Are all files being used efficiently?
   - Can mutually exclusive content be separated further?
   - Can structured formats replace natural language?

3. **Collaborative Refinement**
   - Ask Claude to capture successful approaches into skill context
   - When Claude goes off-track, ask for self-reflection on what went wrong
   - Let Claude help evolve its own skill based on experience

### Phase 7: Documentation and Sharing

Create skill documentation:

**README.md in skill directory**:
```markdown
# ${1:-My Skill}

${2:-Brief description}

## Installation

**Project-wide** (shared with team):
\`\`\`bash
cp -r ${1:-my-skill} /path/to/project/.claude/skills/
\`\`\`

**Personal** (available across all projects):
\`\`\`bash
cp -r ${1:-my-skill} ~/.claude/skills/
\`\`\`

## Usage

This skill is automatically discovered by Claude when relevant.

**Triggers**: [Description of when Claude should use this skill]

**Example tasks**:
- Task example 1
- Task example 2
- Task example 3

## Structure

- \`SKILL.md\`: Core instructions (loaded when skill is relevant)
- \`reference.md\`: Technical documentation (loaded for detailed queries)
- \`scripts/\`: Executable code for deterministic operations
- \`resources/\`: Templates and data files

## Security

- ✅ No hardcoded secrets
- ✅ Input sanitization in scripts
- ✅ External connections documented

## Version History

- v1.0.0 (YYYY-MM-DD): Initial release

## Contributing

[Instructions for contributing improvements]
```

---

## Best Practices Summary

### Naming and Discovery
- ✅ Use descriptive, specific names (not too generic, not too long)
- ✅ Write descriptions that answer "when should this be used?"
- ✅ Think from Claude's perspective for triggering decisions

### Progressive Disclosure
- ✅ Keep SKILL.md under 5,000 tokens
- ✅ Split large content into separate referenced files
- ✅ Keep mutually exclusive contexts separate

### Token Optimization
- ✅ Prefer structured formats over natural language
- ✅ Create focused files rather than monolithic documents
- ✅ Use pipelines where earlier outputs inform later steps

### Code Quality
- ✅ Comprehensive type hints and error handling
- ✅ Design scripts for dual purpose (executable + documentation)
- ✅ Clear separation of concerns

### Security
- ✅ Never hardcode API keys or sensitive data
- ✅ Sanitize all inputs to bundled scripts
- ✅ Document all external network connections
- ✅ Audit less-trusted skills thoroughly

### Development Process
- ✅ Start with evaluation (identify capability gaps from real tasks)
- ✅ Build incrementally based on actual needs
- ✅ Monitor how Claude actually uses the skill
- ✅ Iterate collaboratively with Claude

---

## Real-World Examples Reference

Consult these examples for patterns:

1. **Financial Statement Analyzer** (hybrid knowledge + code)
   - SKILL.md: Instructions for 20+ financial ratios
   - calculate_ratios.py: FinancialRatioCalculator class with type hints, error handling
   - Shows dual-purpose scripts: executable + documentation

2. **Brand Guidelines Enforcer** (organizational knowledge capture)
   - Exact color palettes, typography hierarchies, logo rules
   - Document-type-specific guidelines
   - Transforms abstract standards into executable instructions

3. **Financial Modeling** (complex workflows)
   - Multi-step analysis workflows
   - Cross-format generation (Excel → PowerPoint → PDF → Word)
   - Domain-specific modeling patterns

---

## Command Completion

After creating the skill, verify:

- [ ] Skill directory created in correct location
- [ ] SKILL.md exists with proper YAML frontmatter
- [ ] Name is lowercase-alphanumeric-with-hyphens (max 64 chars)
- [ ] Description is clear and under 1024 chars
- [ ] Supporting files created as needed
- [ ] Scripts include type hints and error handling
- [ ] No hardcoded secrets or sensitive data
- [ ] README.md documents usage and installation
- [ ] Tested on representative tasks
- [ ] Token usage measured and optimized

**Skill location**:
- Project: `.claude/skills/${1:-my-skill}/`
- User: `~/.claude/skills/${1:-my-skill}/`

**Next steps**:
1. Test skill on representative tasks
2. Monitor Claude's usage patterns
3. Iterate based on observations
4. Share with team (if project skill) or use across projects (if user skill)

---

## Additional Resources

- **Conceptual**: See [[Agent Skills]] Zettel for architecture and principles
- **Practical**: See [[Knowledge Synthesis - 2025-12-11]] for cookbook examples
- **Best Practices**: Anthropic's [Agent Skills article](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)
- **Code Examples**: [Claude Cookbooks skills directory](https://github.com/anthropics/claude-cookbooks/tree/main/skills)