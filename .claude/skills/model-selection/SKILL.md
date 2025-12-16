---
name: model-selection
description: Select appropriate Claude model (Opus 4.5, Sonnet, Haiku) for agents, commands, or Task tool invocations based on task complexity, reasoning depth, and cost/speed requirements.
---

# Model Selection Guide

Select the appropriate Claude model based on task requirements.

## Quick Decision Matrix

```
Is deep reasoning across multiple domains required?
├── YES → Opus 4.5
└── NO → Is specialized domain analysis needed?
    ├── YES → Sonnet
    └── NO → Is it pure execution/formatting?
        ├── YES → Haiku
        └── NO → Default to Sonnet
```

## Model Overview

| Model | Strengths | Cost/Speed | Use When |
|-------|-----------|------------|----------|
| **Opus 4.5** | Deep reasoning, synthesis, architecture | Highest/Slower | Complex multi-domain tasks |
| **Sonnet** | Balanced reasoning, efficient | Moderate | Specialized domain tasks |
| **Haiku** | Fast execution, simple tasks | Lowest/Fastest | Formatting, pattern matching |

## Use Opus 4.5 For

**Deep Architectural Reasoning**:
- System architecture across multiple domains
- Trade-off analysis with competing constraints
- Novel design patterns or hybrid approaches

**Complex Synthesis**:
- Combining knowledge from multiple sources
- Creating plans from ambiguous requirements
- Cross-cutting concerns (security, performance, scalability)

**Meta-Cognitive Tasks**:
- Prompt engineering and agent design
- Code review with deep pattern recognition
- UX analysis requiring user psychology

**Multi-Agent Coordination**:
- Orchestrating parallel work streams
- Feature decomposition into parallel components

## Use Sonnet For

**Focused Domain Expertise**:
- Database optimization within known patterns
- Test debugging with established methodologies
- CI/CD pipeline troubleshooting
- Git operations and PR management

**Execution-Oriented Tasks**:
- Running test suites and analyzing failures
- Parsing logs for known patterns
- Generating documentation from code
- Creating tickets from templates

**Time-Sensitive Operations**:
- Quick debugging cycles
- Rapid iteration on test fixes
- Interactive development sessions

## Use Haiku For

**Pure Formatting**:
- Commit message formatting
- Code style adjustments
- Template filling

**Pattern Matching Without Reasoning**:
- Finding duplicate content
- Extracting metrics from files
- Simple search and replace

**Shell Script Execution**:
- Running predefined commands
- Collecting build outputs
- Simple file operations

## Cost Optimization Tips

- Don't use Opus for simple debugging loops
- Don't use Haiku for tasks requiring nuanced understanding
- Consider task duration: Opus for one-time planning, Sonnet for iterative work

## When to Upgrade/Downgrade

**Upgrade to Opus when**:
- Agent produces shallow analysis
- Tasks require synthesizing from multiple codebases
- Users report missing important considerations

**Downgrade to Haiku when**:
- Agent does mostly formatting/transformation
- Reasoning is minimal and pattern-based
- Speed is critical and quality is consistent
