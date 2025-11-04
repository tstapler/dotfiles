# Command Development Guidelines

This file provides prompt engineering guidance specifically for developing and refining Claude Code slash commands in this directory.

## Command Structure Best Practices

### Command Architecture
Slash commands should be structured as clear, executable prompts that:
- Define a specific task or workflow
- Provide necessary context and constraints
- Specify expected outputs and success criteria
- Can be invoked with `/command-name [args]`

### Command Prompt Engineering Principles

#### 1. Clear Task Definition
Every command should start with explicit task definition:

```markdown
# /command-name - Brief description

Your task is to [specific action] following these requirements:

<context>
Why this task matters and what success looks like
</context>

<instructions>
1. [Step 1 with concrete actions]
2. [Step 2 with concrete actions]
3. [Step 3 with concrete actions]
</instructions>

<deliverables>
- [Expected output 1]
- [Expected output 2]
</deliverables>
```

#### 2. XML Tags for Structure
Commands with multiple components should use XML tags:

**Simple Command**:
```markdown
<task>
Analyze the codebase for [specific pattern]
</task>

<output_format>
Present findings as:
1. Summary (2-3 sentences)
2. Details (table format)
3. Recommendations (prioritized list)
</output_format>
```

**Complex Command**:
```markdown
<context>
Background information about the task
</context>

<requirements>
- Requirement 1
- Requirement 2
- Requirement 3
</requirements>

<workflow>
1. Step 1
   - Sub-step A
   - Sub-step B
2. Step 2
   - Sub-step A
</workflow>

<success_criteria>
- Criterion 1: [measurable]
- Criterion 2: [measurable]
</success_criteria>

<output_format>
Expected structure of results
</output_format>
```

#### 3. Chain-of-Thought for Complex Commands
Commands involving decisions or analysis should require explicit thinking:

```markdown
Before executing this command:

<thinking>
1. What is the current state?
2. What are the available options?
3. What are the trade-offs?
4. Which approach best fits the requirements?
</thinking>

After your analysis, proceed with the chosen approach.
```

#### 4. Multishot Examples for Format Specification
For commands with specific output formats, provide examples:

```markdown
## Expected Output Format

### Example 1: Simple Case
Input: [example input]
Output:
```
[example output with proper formatting]
```

### Example 2: Complex Case
Input: [complex input]
Output:
```
[complex output showing all format features]
```

### Example 3: Edge Case
Input: [edge case input]
Output:
```
[how to handle edge cases]
```
```

#### 5. Response Prefilling for Format Control
For commands requiring specific output structure, use prefilling:

```markdown
After completing the analysis, format your response as:

```json
{
  "summary": "
```

Or for markdown:

```markdown
Return your findings in this format:

## Summary

```

### Command Types and Patterns

#### 1. Analysis Commands
Commands that analyze code, data, or documentation:

```markdown
# /analyze-[target]

<task>
Analyze [target] for [specific aspects]
</task>

<analysis_dimensions>
- Dimension 1: [what to look for]
- Dimension 2: [what to look for]
- Dimension 3: [what to look for]
</analysis_dimensions>

<thinking_process>
For each file/component:
1. Assess against each dimension
2. Rate severity/impact (Low/Medium/High)
3. Identify specific instances
4. Suggest improvements
</thinking_process>

<output_format>
## Summary
[High-level findings]

## Detailed Analysis
| Component | Dimension | Severity | Finding | Recommendation |
|-----------|-----------|----------|---------|----------------|
| [name]    | [dim]     | [sev]    | [desc]  | [action]       |

## Recommendations
1. [Priority action 1]
2. [Priority action 2]
</output_format>
```

#### 2. Generation Commands
Commands that create new content:

```markdown
# /generate-[artifact]

<context>
Purpose and usage of the artifact to be generated
</context>

<requirements>
- Requirement 1: [specific constraint]
- Requirement 2: [specific constraint]
- Requirement 3: [specific constraint]
</requirements>

<template>
[Provide template or structure to follow]
</template>

<quality_standards>
The generated artifact must:
- [ ] Standard 1
- [ ] Standard 2
- [ ] Standard 3
</quality_standards>

<validation>
After generation, verify:
1. Check 1
2. Check 2
3. Check 3
</validation>
```

#### 3. Refactoring Commands
Commands that modify existing code/content:

```markdown
# /refactor-[target]

<task>
Refactor [target] to [goal]
</task>

<analysis_first>
Before making changes:
<thinking>
1. What is the current structure?
2. What are the pain points?
3. What refactoring patterns apply?
4. What are the risks?
</thinking>
</analysis_first>

<refactoring_principles>
Apply these principles:
- Principle 1: [e.g., Single Responsibility]
- Principle 2: [e.g., DRY]
- Principle 3: [e.g., Clear Naming]
</refactoring_principles>

<workflow>
1. Analyze current code structure
2. Identify refactoring opportunities
3. Plan changes (explain rationale)
4. Implement changes incrementally
5. Verify behavior preservation
</workflow>

<safety_checks>
- [ ] Behavior unchanged (tests still pass)
- [ ] No breaking API changes
- [ ] Code is more maintainable
</safety_checks>
```

#### 4. Workflow Commands
Commands that orchestrate multi-step processes:

```markdown
# /workflow-[name]

<context>
This workflow automates [process description]
</context>

<phases>
## Phase 1: [Name]
<objective>What this phase accomplishes</objective>

<steps>
1. [Action]
2. [Action]
</steps>

<deliverables>
- [Output 1]
- [Output 2]
</deliverables>

## Phase 2: [Name]
[Similar structure]

## Phase 3: [Name]
[Similar structure]
</phases>

<coordination>
Between phases:
1. Validate Phase N outputs before starting Phase N+1
2. Report progress after each phase
3. Handle errors gracefully (provide recovery options)
</coordination>

<final_report>
After completing all phases, provide:
- Summary of work done
- Key decisions made
- Files created/modified
- Next steps or follow-up recommendations
</final_report>
```

#### 5. Integration Commands
Commands that interact with external systems or agents:

```markdown
# /integrate-[system]

<task>
Integrate with [system] to [accomplish goal]
</task>

<prerequisites>
Verify these conditions before proceeding:
- [ ] Prerequisite 1
- [ ] Prerequisite 2
- [ ] Prerequisite 3
</prerequisites>

<integration_steps>
1. [Step with specific API/tool usage]
2. [Step with specific API/tool usage]
3. [Step with specific API/tool usage]
</integration_steps>

<error_handling>
If [error condition]:
- Action: [recovery step]
- Fallback: [alternative approach]
- Escalation: [when to ask user]
</error_handling>

<success_verification>
Verify integration succeeded by:
1. [Check 1]
2. [Check 2]
</success_verification>
```

## Claude 4-Specific Command Optimizations

### 1. Explicit Completeness Requirements
Claude 4 follows instructions literally. For comprehensive commands:

```markdown
IMPORTANT: Be comprehensive and thorough.
- Don't stop at minimum requirements
- Check ALL files in scope, not just a sample
- Include ALL relevant findings, not just highlights
- Provide complete implementation, not just examples
```

### 2. Action Authority Clarity
Be explicit about what the command should do vs. suggest:

```markdown
## Execution Authority
This command SHOULD:
- [Action Claude can take automatically]
- [Action Claude can take automatically]

This command SHOULD ASK FIRST:
- [Action requiring approval]
- [Action requiring approval]

This command MUST NOT:
- [Forbidden action]
- [Forbidden action]
```

### 3. Progress Reporting
Claude 4.5 is concise. For long-running commands:

```markdown
Progress Reporting:
- Report after each major step
- Use TodoWrite to track progress
- Provide interim summaries for long operations
- Explain what you're doing and why
```

## Command Parameter Patterns

### Optional Parameters with Defaults
```markdown
# /command [--param=value]

Parameters:
- `--param`: [Description] (default: [value])
- `--flag`: [Description] (optional, default: false)

If parameters are not provided:
1. Use defaults specified above
2. Explain which defaults were used
3. Note how different parameters would change behavior
```

### Required Context from Environment
```markdown
# /command

This command requires:
- Current directory: [requirement]
- Git state: [requirement]
- Existing files: [requirement]

Before executing:
1. Verify requirements using <thinking>
2. If requirements not met, explain what's missing
3. Suggest how to satisfy requirements
```

### Dynamic Parameter Validation
```markdown
# /command <required_param>

Parameter validation:
<thinking>
1. Is required_param provided?
2. Is required_param valid format?
3. Does required_param exist/make sense in context?
4. Are there any constraints violated?
</thinking>

If validation fails:
- Explain what's wrong clearly
- Suggest correct usage with example
- Don't proceed with invalid parameters
```

## Testing Commands

When developing new commands, test with:

### 1. Edge Cases
- Empty inputs
- Very large inputs
- Malformed data
- Missing files/resources
- Conflicting requirements

### 2. Error Conditions
- Permission issues
- Network failures
- Invalid state
- Resource constraints

### 3. Usage Patterns
- Minimal parameters
- All parameters specified
- Invalid parameter combinations
- Repeated execution

## Common Anti-Patterns to Avoid

### ❌ Don't Do This
```markdown
# /bad-command
Do something useful with the code.
```
Problems:
- Vague task definition
- No success criteria
- No output format
- No error handling

### ✅ Do This Instead
```markdown
# /good-command - Analyze code complexity

<task>
Analyze all Python files in the current directory for cyclomatic complexity,
identifying functions with complexity > 10 that should be refactored.
</task>

<analysis_process>
For each Python file:
1. Parse functions and methods
2. Calculate cyclomatic complexity
3. Identify complexity hotspots
4. Suggest refactoring strategies
</analysis_process>

<output_format>
## Summary
Total files: [N]
Functions analyzed: [N]
Functions needing refactoring: [N]

## High Complexity Functions
| File | Function | Complexity | Recommendation |
|------|----------|------------|----------------|
| [file] | [func] | [score] | [suggestion] |

## Suggested Refactoring Patterns
1. [Pattern for common case 1]
2. [Pattern for common case 2]
</output_format>

<error_handling>
If no Python files found:
- Report this clearly
- Suggest checking current directory
- Don't fail silently
</error_handling>
```

## Command Organization Best Practices

### Directory Structure
Commands should be organized by domain:
```
commands/
├── quality/          # Code quality commands
├── docs/            # Documentation commands
├── git/             # Git workflow commands
├── plan/            # Planning and architecture commands
├── jira/            # JIRA integration commands
└── knowledge/       # Knowledge management commands
```

### Naming Conventions
- Use kebab-case: `/command-name`
- Be specific: `/analyze-test-coverage` not `/analyze`
- Group with prefixes: `/plan-feature`, `/plan-sprint`
- Indicate scope: `/quality-check-file` vs `/quality-check-repo`

### Command Composition
Complex workflows can chain commands:
```markdown
# /complex-workflow

This workflow executes:
1. `/command-1` - [purpose]
2. `/command-2` - [purpose]
3. `/command-3` - [purpose]

<coordination>
After each command:
- Validate outputs meet requirements
- Pass relevant context to next command
- Handle failures gracefully
</coordination>
```

## Integration with Agents

Commands can delegate to specialized agents:

```markdown
# /command-with-agent

<decision>
<thinking>
1. Is this a simple task? → Execute directly
2. Is this a complex multi-step task? → Delegate to agent
3. Which agent is most appropriate?
</thinking>
</decision>

If delegating to agent:
<agent_invocation>
Use Task tool with subagent_type=[agent-name]

Provide agent with:
<context>
[Relevant background]
</context>

<requirements>
[Specific requirements]
</requirements>

<deliverables>
[Expected outputs]
</deliverables>

<success_criteria>
[How to evaluate success]
</success_criteria>
</agent_invocation>
```

## References

For comprehensive prompt engineering knowledge, see:
- Clear and Direct Prompting
- Multishot Prompting
- Chain-of-Thought Prompting
- XML Tags in Prompts
- System Prompts
- Response Prefilling
- Prompt Chaining
- Claude 4 Prompting Best Practices

All references available in the personal wiki at `logseq/pages/`.
