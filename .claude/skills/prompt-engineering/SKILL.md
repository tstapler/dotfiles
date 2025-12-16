---
name: prompt-engineering
description: Apply prompting techniques when creating prompts, agents, commands, system instructions, or SKILL.md files. Use for XML tags, multishot examples, chain-of-thought, response prefilling, and Claude 4-specific patterns.
---

# Prompt Engineering

Apply these techniques when creating prompts, agents, commands, or system instructions.

## Core Principles

- **Treat Claude as context-free**: Provide complete information
- **Be explicit**: Don't say "Analyze this" - say "Analyze for X, Y, Z risks with ratings"
- **Explain WHY**: Tell motivation, not just what to do
- **Define success criteria**: Specify what "good" looks like

## XML Tags for Structure

Use XML tags to separate prompt components:

```xml
<context>Background and rationale</context>
<instructions>
1. Specific task requirements
2. Edge case handling
</instructions>
<examples>
  <example>
    <input>Sample input</input>
    <output>Expected output</output>
  </example>
</examples>
<data>{{VARIABLE_DATA}}</data>
```

## Multishot Prompting (Few-Shot)

Provide 3-5 examples for complex tasks:

- Examples teach format AND correct behavior
- Show edge cases and variations
- Quality over quantity: one excellent > three mediocre
- Use consistent formatting across examples

**Best for**: JSON/XML generation, classifications, style matching

## Chain-of-Thought

For complex reasoning, request step-by-step thinking:

```xml
<thinking>
Step-by-step reasoning process
</thinking>
<answer>
Final conclusion
</answer>
```

**Best for**: Arithmetic, logic, multi-step analysis, decisions

## Response Prefilling

Guide output format by starting the assistant's reply:

```python
messages=[
  {"role": "user", "content": "Analyze this data: {{DATA}}"},
  {"role": "assistant", "content": "{\n  \"analysis\":"}
]
```

## Claude 4-Specific Patterns

| Behavior | How to Request |
|----------|----------------|
| Comprehensive output | "Include as many relevant features as possible" |
| Action vs suggestion | "Change this..." vs "Can you suggest..." |
| Summaries | "After completing, provide a quick summary" |

## System Prompts

Use system parameter for role/behavior, user for tasks:

```python
system="""You are a senior solutions architect.

Communication Style:
- Be concise and technical
- Provide concrete examples

Constraints:
- Never speculate without data
- Recommend industry-standard solutions first"""
```

## Anti-Patterns to Avoid

- Assuming shared knowledge
- Using vague descriptors ("be creative")
- Leaving format unspecified
- Telling what NOT to do (use positive instructions)
- Relying on implications

## Integration Pattern

1. Start with **clear, direct instructions**
2. Add **structure with XML tags** for complex prompts
3. Provide **examples via multishot** for format/style
4. Elicit **reasoning with CoT** for complex problems
5. Use **prefilling** to enforce specific output formats

## Long Context Tips

- Place long documents at TOP of context
- Put queries and instructions at BOTTOM
- Use prompt caching for frequently reused context
