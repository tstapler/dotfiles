---
name: claude-technique-evaluator
description: Evaluate new Claude prompting patterns, tools, or workflow changes. Produces go/no-go recommendations and integration plans.
---

# Claude Technique Evaluator

Evaluate new LLM techniques, tools, and workflow proposals for adoption value. Assess them against Anthropic standards and your local development workflow.

## When to Use

- **Use when**: Evaluating a new prompting pattern, Claude Code configuration, tool integration (e.g., new MCP server), or workflow modification.
- **Do NOT use when**: Implementing a chosen technique, researching non-AI topics, or writing code.

## Evaluation Framework

Perform the evaluation in three steps:

### 1. Core Profile
- **Target**: What is the technique/tool?
- **Problem**: What specific friction or bottleneck does it solve?
- **Claim**: What are the claimed benefits (tokens, speed, accuracy)?

### 2. Alignment & Workflow Check
Verify alignment against these two baselines:
- **Anthropic Best Practices**: Does it align with official guidance (e.g., system prompt usage, prompt caching structures)?
- **Local Workflow Fit**:
  - **Environment**: Does it fit with `uv`, Python CLI tools, and `rtk` (Rust Token Killer)?
  - **Memory**: Does it integrate with your Logseq Zettelkasten memory architecture?
  - **Overhead**: Does it add too many context tokens? (Check token budget).

### 3. Priority Scoring
Score the technique on a 1–4 scale across six dimensions:

| Dimension | Definition | Scale / Values |
| :--- | :--- | :--- |
| **Anthropic Alignment** | Adherence to official guidance | Strong / Moderate / Weak / Contradicts |
| **Integration Complexity** | Friction to implement locally | Trivial / Low / Medium / High |
| **Benefit Magnitude** | Impact on speed, quality, or tokens | Transformative / Significant / Moderate / Marginal |
| **Overlap Assessment** | Duplication of existing skills | Novel / Extends / Partial Overlap / Full Overlap |
| **Risk Assessment** | Potential for regression or instability | Minimal / Acceptable / Notable / Prohibitive |
| **Maturity Level** | Stability of the feature or tool | Production / Stable / Beta / Experimental |

Based on these dimensions, assign one of these four verdicts:
- **ADOPT NOW**: Strong alignment + High benefit + Low complexity.
- **PLAN ADOPTION**: High benefit + Medium complexity. Requires design plan.
- **MONITOR**: High complexity or Experimental maturity. Re-evaluate later.
- **SKIP**: Contradicts guidance, duplicates existing tools, or offers marginal benefit.

---

## Output Template

Generate all evaluations in this format:

```markdown
# Evaluation: [Technique Name]

**Verdict**: **[ADOPT NOW / PLAN ADOPTION / MONITOR / SKIP]**

### Summary
- **Problem**: [1-sentence description of the problem solved]
- **Solution**: [1-sentence description of the proposed technique]
- **Impact**: [Expected token savings, speedup, or quality improvement]

### Scoring Profile
- **Anthropic Alignment**: [Value] — [1-sentence rationale]
- **Integration Complexity**: [Value] — [1-sentence rationale]
- **Benefit Magnitude**: [Value] — [1-sentence rationale]
- **Overlap**: [Value] — [1-sentence rationale]
- **Risk**: [Value] — [1-sentence rationale]
- **Maturity**: [Value] — [1-sentence rationale]

### Integration Path
1. **Files to Modify**: [List specific config or code paths]
2. **Commands**: [Provide exact commands to run/test]
3. **Verification**: [Describe how to verify the integration works]
```

## Quick Evaluation Mode

For simple, single-prompt patterns, output a brief 2-paragraph evaluation:
1. **Profile**: State what the pattern is and whether it aligns with Anthropic docs.
2. **Action**: Recommend SKIP or ADOPT with a 1-sentence integration instruction.