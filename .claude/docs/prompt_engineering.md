# Prompt Engineering Best Practices

## Core Prompting Principles (Based on Claude 4 & Anthropic Guidelines)

### Clear and Direct Prompting

- **Treat Claude as a brilliant but context-free colleague**: Provide complete information without assuming shared knowledge
- **Golden Rule**: If a colleague with minimal context would be confused, Claude will be too
- **Be explicit with requirements**:
  - Don't: "Analyze this contract"
  - Do: "Analyze this contract for data privacy risks, SLA commitments, and liability caps. Provide risk ratings (Low/Medium/High) for each clause."
- **Explain motivations**: Tell WHY something matters, not just WHAT to do
  - Example: "Never use ellipses because text-to-speech engines cannot pronounce them"
- **Define success criteria**: Specify what "good" looks like with concrete metrics

### Claude 4-Specific Behaviors

- **Explicit Feature Requests**: Claude 4 follows instructions literally; request comprehensiveness explicitly
  - Instead of: "Create an analytics dashboard"
  - Use: "Create an analytics dashboard. Include as many relevant features and interactions as possible. Go beyond the basics to create a fully-featured implementation."
- **Action vs Suggestion**: Be clear about whether you want recommendations or direct action
  - "Can you suggest changes?" → Claude provides suggestions only
  - "Change this function to improve performance" → Claude makes changes
- **Verbosity Control**: Claude 4.5 is concise by default; request summaries explicitly if needed
  - Add: "After completing tasks involving tool use, provide a quick summary of the work you've done"

### XML Tags for Structure

- **Use XML tags to separate prompt components clearly**:
  - `<context>`: Background information
  - `<instructions>`: Task requirements
  - `<examples>`: Demonstration cases
  - `<data>`: Input data to process
  - `<output_format>`: Expected structure
- **Benefits**: Prevents ambiguity, enables programmatic extraction, improves parsing accuracy
- **Pattern for Complex Prompts**:

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

### Multishot Prompting (Few-Shot Examples)

- **Provide 3-5 examples for complex or nuanced tasks**:
  - Examples teach format and structure as much as correct answers
  - Show edge cases and variations in examples
  - Ensure examples demonstrate ONLY desired behaviors
- **Quality over quantity**: One excellent example > three mediocre ones
- **Use consistent formatting** across all examples
- **Effective for**:
  - Format-critical tasks (JSON/XML generation)
  - Nuanced classifications (sentiment, categorization)
  - Style matching (brand voice, technical precision)

### Chain-of-Thought Prompting

- **For complex reasoning, request step-by-step thinking**:
  - Add: "Let's think step by step" (zero-shot CoT)
  - Or: "Show your reasoning process before answering"
- **Structure with XML tags**:

```xml
<thinking>
Step-by-step reasoning process
</thinking>
<answer>
Final conclusion
</answer>
```

- **Benefits**: Reduces errors, enables verification, improves quality on complex tasks
- **Use for**: Arithmetic, logic, multi-step analysis, decision-making

### System Prompts for Persistent Behavior

- **Use system parameter for role and behavioral guidelines**:
  - System: WHO you are (role, expertise, constraints)
  - User: WHAT to do (specific tasks and data)
- **Example system prompt**:

```python
system="""You are a senior solutions architect with expertise in cloud infrastructure.

Communication Style:
- Be concise and technical
- Provide concrete examples
- Cite specific technologies and patterns

Constraints:
- Never speculate without data
- Always consider cost and scalability
- Recommend industry-standard solutions first"""
```

### Response Prefilling

- **Guide initial response format by starting the assistant's reply**:

```python
messages=[
  {"role": "user", "content": "Analyze this data: {{DATA}}"},
  {"role": "assistant", "content": "{\n  \"analysis\":"}
]
```

- **Use to**: Enforce JSON output, skip preambles, set tone, ensure format compliance

### Long Context Optimization

- **Place long documents at the top of context** for best performance
- **Put queries and instructions at the bottom**
- **Use prompt caching** for frequently reused context components
- **Claude 4.5 context awareness**: Understands token budget and makes informed decisions

## Prompting Anti-Patterns to Avoid

### What NOT to Do

- ❌ **Assume shared knowledge**: Model has no memory of previous sessions
- ❌ **Use vague descriptors**: "Be creative", "use good judgment" lack specificity
- ❌ **Leave format unspecified**: Causes inconsistent outputs
- ❌ **Skip edge case handling**: Undefined behavior for unusual inputs
- ❌ **Rely on implications**: State requirements explicitly
- ❌ **Tell what NOT to do**: Focus on positive instructions
  - Instead of: "Do not use markdown"
  - Say: "Write in smoothly flowing prose paragraphs"

### Common Pitfalls

- **Insufficient context**: Add 2-3 sentences explaining output purpose
- **Ambiguous requirements**: Use concrete specs instead of subjective descriptors
- **Format assumptions**: Show exact format with template or detailed specification
- **Poor example selection**: Examples should represent real use case complexity

## Integration Patterns

### Combining Techniques for Maximum Effect

1. **System Prompt** (role and behavior) + **Clear Instructions** (specific task) + **Examples** (format demonstration)
2. **XML Tags** (structure) + **Chain-of-Thought** (reasoning) + **Prefilling** (format enforcement)
3. **Multishot Examples** (pattern learning) + **Explicit Instructions** (edge case handling)

### Hierarchical Application

1. Start with **clear, direct instructions**
2. Add **structure with XML tags** for complex prompts
3. Provide **examples via multishot** for format/style
4. Elicit **reasoning with CoT** for complex problems
5. Use **prefilling** to enforce specific output formats

## Practical Application Guidelines

### For Code Generation

- Specify language, version, framework, and style requirements
- Provide example code structure when possible
- Request comments/documentation explicitly if needed
- Use CoT for complex algorithms: "Explain your approach before implementing"

### For Analysis Tasks

- Define analysis dimensions explicitly
- Specify output structure (findings, recommendations, confidence)
- Request both supporting and contradicting evidence
- Use XML tags to separate data from instructions

### For Content Creation

- Specify target audience and expertise level
- Define tone, style, and length requirements
- Provide style examples for consistency
- Request specific structural elements explicitly

### For Research and Synthesis

- Ask for hypothesis-driven investigation
- Request cross-referencing across sources
- Specify evidence quality standards
- Use structured output formats for findings
