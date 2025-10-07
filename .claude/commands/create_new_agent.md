---
title: Create New Claude Code Agent
description: Guide through creating a new purpose-built agent for specialized tasks with proper configuration
arguments: [agent_name, specialization_domain, model_preference]
---

# Creating New Claude Code Agent: `${1:-example-agent}`

I'll help you create a new purpose-built agent for specialized tasks, following your established agent configuration patterns.

## Agent Configuration

**Agent Name**: `${1:-example-agent}` (kebab-case format)
**Specialization Domain**: `${2:-general-purpose}` 
**Model Preference**: `${3:-opus}` (Options: opus, sonnet, haiku)

## Agent Creation Process

### Step 1: Define Agent Scope and Expertise

**Core Questions to Answer:**
- What specific domain expertise does this agent provide?
- When should users invoke this agent vs. general Claude?
- What tools are essential for this agent's function?
- What knowledge areas require deep, specialized context?

### Step 2: Analyze Context Efficiency Potential

**High Priority Candidates (Create Agent):**
- Complex, multi-step workflows requiring specialized knowledge
- Domain-specific expertise (JIRA, testing, architecture, etc.)
- Repetitive tasks with established patterns and best practices
- Workflows requiring consistent methodology and quality standards
- Tasks that benefit from maintained context and state

**Low Priority Candidates (Keep as Command):**
- Simple, procedural workflows
- One-time or infrequent tasks
- Basic formatting or templating operations
- Tasks requiring minimal specialized knowledge

### Step 3: Create Agent File Structure

**File Location**: `/Users/tylerstapler/.claude/agents/${1:-example-agent}.md`

**Required YAML Frontmatter:**
```yaml
---
name: ${1:-example-agent}
description: Use this agent when [specific trigger conditions]. This agent should be invoked [when to use it based on context and examples].

Examples:
- <example>
  Context: [Situation description]
  user: "[Example user request]"
  assistant: "[Response showing agent invocation]"
  <commentary>
  [Explanation of why this agent is appropriate for this scenario]
  </commentary>
  </example>

tools: [list of required tools or * for all tools]
model: ${3:-opus}
---
```

### Step 4: Define Agent Expertise and Methodology

**Core Structure:**
1. **Mission Statement**: Clear purpose and role definition
2. **Key Expertise Areas**: Domain-specific knowledge and competencies
3. **Methodology/Process**: Step-by-step approach for handling requests
4. **Quality Standards**: Non-negotiable requirements and success criteria
5. **Best Practices**: Domain-specific patterns and recommendations

### Step 5: Implementation Template

Based on your inputs, here's the agent template:

```markdown
---
name: ${1:-example-agent}
description: Use this agent when you need specialized ${2:-general-purpose} expertise. This agent should be invoked when [specific conditions that warrant specialized knowledge over general Claude capabilities].

Examples:
- <example>
  Context: User needs ${2:-general-purpose} assistance.
  user: "I need help with [specific ${2:-general-purpose} task]"
  assistant: "I'll use the ${1:-example-agent} agent to provide specialized ${2:-general-purpose} expertise"
  <commentary>
  Since this requires ${2:-general-purpose} domain knowledge, the ${1:-example-agent} agent is the appropriate choice.
  </commentary>
  </example>

tools: *
model: ${3:-opus}
---

You are a ${2:-general-purpose} specialist with deep expertise in [specific domain areas]. Your role is to provide expert-level assistance while maintaining [specific quality standards].

## Core Mission

[Define the primary purpose and value proposition of this agent]

## Key Expertise Areas

### **[Domain Area 1]**
- [Specific competency]
- [Related skill or knowledge]
- [Best practices and patterns]

### **[Domain Area 2]**  
- [Specific competency]
- [Related skill or knowledge]
- [Best practices and patterns]

## Methodology

### **Phase 1: [Process Step]**
[Description of what happens in this phase]

### **Phase 2: [Process Step]**
[Description of what happens in this phase]

### **Phase 3: [Process Step]**
[Description of what happens in this phase]

## Quality Standards

You maintain these non-negotiable standards:
- [Standard 1]: [Description and rationale]
- [Standard 2]: [Description and rationale]
- [Standard 3]: [Description and rationale]

## Professional Principles

- [Principle 1]: [How this guides your work]
- [Principle 2]: [How this guides your work]
- [Principle 3]: [How this guides your work]

Remember: [Key reminder about the agent's core purpose and value]
```

## Current Agent Ecosystem

**Existing Specialized Agents:**
- `pr-reviewer`: Code review and software engineering best practices
- `java-test-debugger`: Java testing framework debugging and fixes
- `github-debugger`: GitHub Actions and CI/CD troubleshooting
- `jira-project-manager`: FBG JIRA and project management workflows
- `knowledge-synthesis`: Zettelkasten research and knowledge integration

## Agent Design Principles

**Context Efficiency Guidelines:**
- **High Specialization**: Focus on narrow, deep expertise vs. broad knowledge
- **Consistent Methodology**: Establish repeatable processes and quality standards  
- **Tool Optimization**: Include only tools essential for the domain
- **Model Selection**: Choose model based on complexity (opus for complex reasoning, sonnet for balanced, haiku for simple)
- **Clear Boundaries**: Define exactly when to use this agent vs. general Claude

**Usage Pattern Design:**
- **Trigger Conditions**: Make it obvious when to invoke this agent
- **Example Scenarios**: Provide concrete examples with commentary
- **Value Proposition**: Clearly articulate why specialization matters
- **Quality Standards**: Define what makes this agent's output superior

## Implementation Steps

1. **Create Agent File**: `/Users/tylerstapler/.claude/agents/${1:-example-agent}.md`
2. **Define Specialization**: Focus on specific domain expertise
3. **Configure Tools**: Include essential tools for the domain
4. **Set Quality Standards**: Define non-negotiable requirements
5. **Test and Refine**: Validate agent performance vs. general Claude
6. **Document Usage**: Update any relevant workflow documentation

Would you like me to create this `${1:-example-agent}` agent now based on your specifications? Please confirm:
- **Agent Name**: `${1:-example-agent}`
- **Specialization Domain**: `${2:-general-purpose}`
- **Model**: `${3:-opus}`
- **Specific Expertise Areas**: [Please specify the key domains]
- **Essential Tools**: [Please specify required tools]