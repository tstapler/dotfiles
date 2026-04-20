# Anthropic Best Practices Reference

Key Anthropic best practices for evaluating techniques against official guidance.

## Prompting Best Practices (docs.anthropic.com)

### Fundamental Principles
- Be specific and clear with instructions
- Use XML tags for structured prompts
- Provide examples (multishot) for complex output formats
- Use system prompts for persistent behavior/role definition
- Place long documents early, instructions late (long context optimization)

### Advanced Techniques
- **Chain-of-thought**: Request step-by-step reasoning for complex tasks
- **Response prefilling**: Start assistant reply to enforce format
- **Prompt caching**: Reuse static context across API calls
- **Extended thinking**: Enable for complex reasoning (supported in Claude 3.5+)

### Anti-Patterns (Anthropic Warns Against)
- Assuming shared context without providing it
- Using negative instructions ("don't do X") instead of positive ones
- Leaving output format unspecified
- Overloading a single prompt with too many tasks
- Using vague descriptors without concrete criteria

## Claude Code Best Practices

### Configuration
- CLAUDE.md for project-level instructions (checked into repo)
- ~/.claude/CLAUDE.md for user-global instructions
- Skills system for reusable domain expertise
- Commands for user-invokable workflows

### Tool Usage
- Prefer dedicated tools over Bash for file operations
- Use Task tool for parallel or delegated work
- MCP servers for extended capabilities

### Agent Design
- Narrow specialization over broad coverage
- Progressive disclosure for context efficiency
- Clear trigger conditions in descriptions
- Skill chaining for cross-domain tasks

## Model Selection (Official Guidance)

| Model | Best For |
|-------|----------|
| **Opus** | Deep reasoning, synthesis, architecture, complex multi-domain |
| **Sonnet** | Balanced speed/quality, focused domain tasks, iterative work |
| **Haiku** | Fast execution, formatting, simple pattern matching |

## Evaluation Red Flags

Techniques that should be scrutinized carefully:

| Red Flag | Why |
|----------|-----|
| Contradicts official docs | May be outdated or based on older model behavior |
| Relies on undocumented behavior | Could break with model updates |
| Requires prompt injection patterns | Security risk, unreliable |
| Claims to "jailbreak" or bypass safety | Against ToS, unreliable |
| Based on very old model version | Claude 4.x behavior differs significantly from 2.x/3.x |
| No source or attribution | Cannot verify claims |
| "One weird trick" framing | Usually overstated benefit |

## Evaluation Green Flags

Techniques that are likely worth adopting:

| Green Flag | Why |
|------------|-----|
| Cited in official Anthropic docs | Officially supported |
| Published on Anthropic engineering blog | Vetted by the team |
| In Anthropic cookbook/examples | Demonstrated with code |
| Aligns with existing skill patterns | Low integration friction |
| Addresses a known gap in current workflow | Clear value proposition |
| Community-validated with multiple sources | Battle-tested |

## Key Anthropic Resources

- Documentation: `docs.anthropic.com`
- Engineering blog: `anthropic.com/engineering`
- API reference: `docs.anthropic.com/en/api`
- Prompt engineering guide: `docs.anthropic.com/en/docs/build-with-claude/prompt-engineering`
- Claude Code docs: `docs.anthropic.com/en/docs/claude-code`
- Anthropic cookbook: `github.com/anthropics/anthropic-cookbook`
- Agent Skills article: `anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills`
