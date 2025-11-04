# Agent Development Guidelines

This file provides prompt engineering guidance specifically for developing and refining Claude Code agents in this directory.

## Agent Structure Best Practices

### System Prompt Architecture
Agents should have clear system prompts that define:

```yaml
agent_name:
  system_prompt: |
    ## Role and Expertise
    You are [specific role] with expertise in [domain].

    ## Communication Style
    - [Style guideline 1]
    - [Style guideline 2]
    - [Style guideline 3]

    ## Constraints and Boundaries
    - [What you should do]
    - [What you should not do]
    - [Decision-making framework]

    ## Output Requirements
    - [Format expectations]
    - [Quality standards]
    - [Deliverables structure]
```

### Agent Prompt Engineering Principles

#### 1. Clear Role Definition
- **Be specific about expertise**: Instead of "expert", specify "senior solutions architect with 15 years in cloud infrastructure"
- **Define boundaries**: What the agent SHOULD and SHOULD NOT do
- **Specify decision-making authority**: Can the agent make changes or only recommend?

**Example**:
```markdown
You are a senior database performance engineer specializing in PostgreSQL optimization.

What you do:
- Analyze query performance and suggest optimizations
- Review schema designs for scalability issues
- Provide concrete index recommendations with expected impact

What you don't do:
- Make changes to production databases without explicit approval
- Recommend solutions without explaining trade-offs
- Speculate about performance without data
```

#### 2. Structured Thinking with XML Tags
Agents handling complex tasks should use XML tags to organize their reasoning:

```xml
<analysis>
Current state assessment
</analysis>

<options>
Option 1: [approach] - Pros: [...] Cons: [...]
Option 2: [approach] - Pros: [...] Cons: [...]
</options>

<recommendation>
Chosen approach with justification
</recommendation>

<implementation>
Step-by-step plan
</implementation>
```

#### 3. Chain-of-Thought for Complex Decisions
For agents that make decisions, require explicit reasoning:

```markdown
Before taking action:
1. Use <thinking> tags to show your reasoning process
2. Consider alternatives explicitly
3. Explain why you chose your approach
4. Identify assumptions and risks
```

#### 4. Multishot Examples
Provide 3-5 examples of expected behavior for complex agents:

```markdown
## Example Interactions

### Example 1: Simple Optimization
User: "This query is slow"
Agent:
<analysis>
Query uses SELECT * and lacks indexes on WHERE clause columns
</analysis>
<recommendation>
1. Add index on user_id column
2. Select only needed columns
Expected improvement: 50-80% reduction in query time
</recommendation>

### Example 2: Complex Trade-off
[...]

### Example 3: Edge Case Handling
[...]
```

#### 5. Response Format Control
Use response prefilling to ensure consistent output structure:

```yaml
agent_name:
  response_format: |
    ## Analysis
    [Analysis section]

    ## Recommendations
    [Recommendations with priority]

    ## Implementation Steps
    1. [Step 1]
    2. [Step 2]
```

### Agent-Specific Prompt Patterns

#### Research/Analysis Agents
```markdown
Your task is to [research goal].

Research Process:
1. Identify key concepts and relationships
2. Search for both supporting AND contradicting evidence
3. Evaluate source credibility and relevance
4. Synthesize findings with explicit confidence levels

Output Structure:
<findings>
- Finding 1 [High confidence] (sources: X, Y)
- Finding 2 [Medium confidence] (sources: Z)
</findings>

<analysis>
Cross-cutting insights and patterns
</analysis>

<gaps>
What remains unknown or uncertain
</gaps>
```

#### Code Generation Agents
```markdown
When generating code:

1. **Understand requirements fully**:
   - Ask clarifying questions if specs are ambiguous
   - Confirm technology stack and constraints
   - Identify edge cases explicitly

2. **Plan before implementing**:
   <design>
   - Architecture approach
   - Key components and interactions
   - Error handling strategy
   </design>

3. **Generate with documentation**:
   - Include comments explaining WHY, not just WHAT
   - Add docstrings for functions
   - Provide usage examples

4. **Consider testing**:
   - Identify testable units
   - Suggest test cases for edge conditions
   - Note any testing limitations
```

#### Debugging/Review Agents
```markdown
Debugging Process:
1. Reproduce the issue (ask for specifics if unclear)
2. Analyze systematically (not just guess fixes)
3. Identify root cause (not just symptoms)
4. Propose solution with explanation
5. Suggest prevention strategies

Use this structure:
<investigation>
What I checked and what I found
</investigation>

<root_cause>
The actual underlying issue
</root_cause>

<solution>
The fix with step-by-step implementation
</solution>

<prevention>
How to avoid this in the future
</prevention>
```

## Claude 4-Specific Agent Optimizations

### 1. Explicit Feature Requests
Claude 4 follows instructions literally. For agents that should be comprehensive:

```markdown
IMPORTANT: When completing tasks:
- Include as many relevant features and capabilities as possible
- Go beyond basic requirements to create fully-featured implementations
- Don't stop at "good enough" - aim for production-ready quality
```

### 2. Action vs. Suggestion Clarity
Be explicit about the agent's authority:

```markdown
## Your Authority
- You SHOULD: [List of actions the agent can take directly]
- You SHOULD SUGGEST: [List of actions requiring approval]
- You MUST NOT: [List of forbidden actions]
```

### 3. Verbosity Control
Claude 4.5 is concise by default. If you want detailed outputs:

```markdown
After completing tasks:
- Provide a comprehensive summary of work done
- Explain key decisions and trade-offs
- Note any assumptions or limitations
- Suggest follow-up actions
```

## Integration Patterns for Agents

### Combining Techniques for Maximum Effect

**Pattern 1: Research Agent**
```markdown
System Prompt (role) + XML Structure (organization) + Chain-of-Thought (reasoning) + Multishot Examples (format demonstration)
```

**Pattern 2: Code Generation Agent**
```markdown
Clear Instructions (requirements) + Response Prefilling (format) + Multishot Examples (style) + Explicit Quality Criteria (standards)
```

**Pattern 3: Decision-Making Agent**
```markdown
System Prompt (authority) + Chain-of-Thought (reasoning) + XML Structure (options analysis) + Explicit Constraints (boundaries)
```

## Testing and Validation

When developing new agents:

1. **Test with edge cases**: Ambiguous requests, incomplete information, conflicting requirements
2. **Verify consistency**: Same input should produce similar outputs
3. **Check boundaries**: Ensure agent respects its defined scope
4. **Validate quality**: Outputs should meet defined standards
5. **Measure effectiveness**: Compare to baseline or previous versions

## Common Anti-Patterns to Avoid

### ❌ Don't Do This
```markdown
# Vague role
You are an expert in software development.

# No structure
Analyze the code and fix any issues.

# Assumed context
You know what good code looks like.
```

### ✅ Do This Instead
```markdown
# Specific role
You are a senior Python backend engineer specializing in FastAPI microservices,
with expertise in API design, async patterns, and production observability.

# Clear structure
Analyze the code following this process:
<analysis>
1. Architecture review
2. Code quality assessment
3. Security considerations
</analysis>

<recommendations>
Prioritized list of improvements with impact assessment
</recommendations>

# Explicit standards
Good code for our context means:
- FastAPI-specific best practices (dependency injection, proper async usage)
- Type hints on all functions
- Structured logging with context
- Error handling with appropriate HTTP status codes
```

## References

For comprehensive prompt engineering knowledge, see:
- Clear and Direct Prompting
- Multishot Prompting
- Chain-of-Thought Prompting
- XML Tags in Prompts
- System Prompts
- Response Prefilling
- Claude 4 Prompting Best Practices

All references available in the personal wiki at `logseq/pages/`.
