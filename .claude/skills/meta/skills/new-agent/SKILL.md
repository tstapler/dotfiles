---
description: Guide through creating a new purpose-built agent for specialized tasks
  with proper configuration
prompt: "# Creating New Claude Code Agent: `${1:-example-agent}`\n\nI'll help you\
  \ create a new purpose-built agent for specialized tasks, following your established\
  \ agent configuration patterns.\n\n## Agent Configuration\n\n**Agent Name**: `${1:-example-agent}`\
  \ (kebab-case format)\n**Specialization Domain**: `${2:-general-purpose}`\n**Model\
  \ Preference**: `${3:-sonnet}` (Options: sonnet, opus, haiku - prefer sonnet for\
  \ speed)\n\n## Agent Creation Process\n\n### Step 1: Define Agent Scope and Expertise\n\
  \n**Core Questions to Answer:**\n- What specific domain expertise does this agent\
  \ provide?\n- When should users invoke this agent vs. general Claude?\n- What tools\
  \ are essential for this agent's function?\n- What knowledge areas require deep,\
  \ specialized context?\n\n### Step 2: Analyze Context Efficiency Potential\n\n**High\
  \ Priority Candidates (Create Agent):**\n- Complex, multi-step workflows requiring\
  \ specialized knowledge\n- Domain-specific expertise (JIRA, testing, architecture,\
  \ etc.)\n- Repetitive tasks with established patterns and best practices\n- Workflows\
  \ requiring consistent methodology and quality standards\n- Tasks that benefit from\
  \ maintained context and state\n\n**Low Priority Candidates (Keep as Command):**\n\
  - Simple, procedural workflows\n- One-time or infrequent tasks\n- Basic formatting\
  \ or templating operations\n- Tasks requiring minimal specialized knowledge\n\n\
  ### Step 3: Create Agent File Structure\n\n**File Location**: `/Users/tylerstapler/.claude/agents/${1:-example-agent}.md`\n\
  \n**Required YAML Frontmatter:**\n```yaml\n---\nname: ${1:-example-agent}\ndescription:\
  \ Use this agent when [specific trigger conditions]. This agent should be invoked\
  \ [when to use it based on context and examples].\n\nExamples:\n- <example>\n  Context:\
  \ [Situation description]\n  user: \"[Example user request]\"\n  assistant: \"[Response\
  \ showing agent invocation]\"\n  <commentary>\n  [Explanation of why this agent\
  \ is appropriate for this scenario]\n  </commentary>\n  </example>\n\ntools: [list\
  \ of required tools or * for all tools]\nmodel: ${3:-sonnet}\n---\n```\n\n### Step\
  \ 4: Define Agent Expertise and Methodology\n\n**Core Structure:**\n1. **Mission\
  \ Statement**: Clear purpose and role definition\n2. **Key Expertise Areas**: Domain-specific\
  \ knowledge and competencies\n3. **Methodology/Process**: Step-by-step approach\
  \ for handling requests\n4. **Quality Standards**: Non-negotiable requirements and\
  \ success criteria\n5. **Best Practices**: Domain-specific patterns and recommendations\n\
  \n### Step 5: Implementation Template\n\nBased on your inputs, here's the agent\
  \ template:\n\n```markdown\n---\nname: ${1:-example-agent}\ndescription: Use this\
  \ agent when you need specialized ${2:-general-purpose} expertise. This agent should\
  \ be invoked when [specific conditions that warrant specialized knowledge over general\
  \ Claude capabilities].\n\nExamples:\n- <example>\n  Context: User needs ${2:-general-purpose}\
  \ assistance.\n  user: \"I need help with [specific ${2:-general-purpose} task]\"\
  \n  assistant: \"I'll use the ${1:-example-agent} agent to provide specialized ${2:-general-purpose}\
  \ expertise\"\n  <commentary>\n  Since this requires ${2:-general-purpose} domain\
  \ knowledge, the ${1:-example-agent} agent is the appropriate choice.\n  </commentary>\n\
  \  </example>\n\ntools: *\nmodel: ${3:-sonnet}\n---\n\nYou are a ${2:-general-purpose}\
  \ specialist with deep expertise in [specific domain areas]. Your role is to provide\
  \ expert-level assistance while maintaining [specific quality standards].\n\n##\
  \ Core Mission\n\n[Define the primary purpose and value proposition of this agent]\n\
  \n## Key Expertise Areas\n\n### **[Domain Area 1]**\n- [Specific competency]\n-\
  \ [Related skill or knowledge]\n- [Best practices and patterns]\n\n### **[Domain\
  \ Area 2]**  \n- [Specific competency]\n- [Related skill or knowledge]\n- [Best\
  \ practices and patterns]\n\n## Methodology\n\n### **Phase 1: [Process Step]**\n\
  [Description of what happens in this phase]\n\n### **Phase 2: [Process Step]**\n\
  [Description of what happens in this phase]\n\n### **Phase 3: [Process Step]**\n\
  [Description of what happens in this phase]\n\n## Quality Standards\n\nYou maintain\
  \ these non-negotiable standards:\n- [Standard 1]: [Description and rationale]\n\
  - [Standard 2]: [Description and rationale]\n- [Standard 3]: [Description and rationale]\n\
  \n## Professional Principles\n\n- [Principle 1]: [How this guides your work]\n-\
  \ [Principle 2]: [How this guides your work]\n- [Principle 3]: [How this guides\
  \ your work]\n\nRemember: [Key reminder about the agent's core purpose and value]\n\
  ```\n\n## Current Agent Ecosystem\n\n**Existing Specialized Agents:**\n- `pr-reviewer`:\
  \ Code review and software engineering best practices\n- `java-test-debugger`: Java\
  \ testing framework debugging and fixes\n- `github-debugger`: GitHub Actions and\
  \ CI/CD troubleshooting\n- `jira-project-manager`: FBG JIRA and project management\
  \ workflows\n- `knowledge-synthesis`: Zettelkasten research and knowledge integration\n\
  \n## Agent Design Principles\n\n**Context Efficiency Guidelines:**\n- **High Specialization**:\
  \ Focus on narrow, deep expertise vs. broad knowledge\n- **Consistent Methodology**:\
  \ Establish repeatable processes and quality standards  \n- **Tool Optimization**:\
  \ Include only tools essential for the domain\n- **Model Selection**: Prefer sonnet\
  \ for speed and efficiency; use opus only for extremely complex reasoning tasks;\
  \ use haiku for simple tasks\n- **Clear Boundaries**: Define exactly when to use\
  \ this agent vs. general Claude\n\n**Usage Pattern Design:**\n- **Trigger Conditions**:\
  \ Make it obvious when to invoke this agent\n- **Example Scenarios**: Provide concrete\
  \ examples with commentary\n- **Value Proposition**: Clearly articulate why specialization\
  \ matters\n- **Quality Standards**: Define what makes this agent's output superior\n\
  \n## Implementation Steps\n\n1. **Create Agent File**: `/Users/tylerstapler/.claude/agents/${1:-example-agent}.md`\n\
  2. **Define Specialization**: Focus on specific domain expertise\n3. **Configure\
  \ Tools**: Include essential tools for the domain\n4. **Set Quality Standards**:\
  \ Define non-negotiable requirements\n5. **Test and Refine**: Validate agent performance\
  \ vs. general Claude\n6. **Document Usage**: Update any relevant workflow documentation\n\
  \nWould you like me to create this `${1:-example-agent}` agent now based on your\
  \ specifications? Please confirm:\n- **Agent Name**: `${1:-example-agent}`\n- **Specialization\
  \ Domain**: `${2:-general-purpose}`\n- **Model**: `${3:-sonnet}` (prefer sonnet\
  \ for better performance)\n- **Specific Expertise Areas**: [Please specify the key\
  \ domains]\n- **Essential Tools**: [Please specify required tools]\n"
---

# Creating New Claude Code Agent: `${1:-example-agent}`

I'll help you create a new purpose-built agent for specialized tasks, following your established agent configuration patterns.

## Agent Configuration

**Agent Name**: `${1:-example-agent}` (kebab-case format)
**Specialization Domain**: `${2:-general-purpose}`
**Model Preference**: `${3:-sonnet}` (Options: sonnet, opus, haiku - prefer sonnet for speed)

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
model: ${3:-sonnet}
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
model: ${3:-sonnet}
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
- **Model Selection**: Prefer sonnet for speed and efficiency; use opus only for extremely complex reasoning tasks; use haiku for simple tasks
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
- **Model**: `${3:-sonnet}` (prefer sonnet for better performance)
- **Specific Expertise Areas**: [Please specify the key domains]
- **Essential Tools**: [Please specify required tools]
