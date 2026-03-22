# Evaluation Output Template

Use this template for structured evaluation output. Format is Logseq-compatible.

## Template

```markdown
- # Claude Technique Evaluation: [Technique Name]
  collapsed:: true
  tags:: #[[Claude Techniques]] #[[Evaluations]]
  date:: [[YYYY_MM_DD]]
  priority:: [Adopt Now / Plan Adoption / Monitor / Skip]
  source:: [URL or description of source]
  -
  - ## Summary
    - **Technique**: [One-sentence description]
    - **Source**: [URL or reference]
    - **Category**: [Prompting / Tool / Feature / Configuration / Workflow]
    - **Priority**: [Adopt Now / Plan Adoption / Monitor / Skip]
  -
  - ## What It Does
    - [2-3 bullet description of the technique]
  -
  - ## Evaluation Scores
    - | Dimension | Rating | Notes |
      |-----------|--------|-------|
      | Anthropic Alignment | [Strong/Moderate/Weak/Contradicts] | [Brief explanation] |
      | Integration Complexity | [Trivial/Low/Medium/High] | [Effort estimate] |
      | Benefit Magnitude | [Transformative/Significant/Moderate/Marginal] | [What improves] |
      | Overlap Assessment | [Novel/Extends/Partial/Full Overlap] | [Which existing skill] |
      | Risk Assessment | [Minimal/Acceptable/Notable/Prohibitive] | [Key concern] |
      | Maturity Level | [Production/Stable/Beta/Experimental] | [Evidence] |
  -
  - ## Anthropic Alignment Details
    - **Official guidance says**: [What Anthropic recommends]
    - **This technique**: [How it aligns or diverges]
    - **Sources**: [Links to relevant Anthropic docs]
  -
  - ## Workflow Fit
    - **Overlaps with**: [Existing skill/tool or "None"]
    - **Would enhance**: [Existing capability it improves]
    - **Integration point**: [Where it connects to current workflow]
    - **Effort estimate**: [Time to integrate]
  -
  - ## Recommendation
    - **Verdict**: [Adopt Now / Plan Adoption / Monitor / Skip]
    - **Rationale**: [2-3 sentences explaining the decision]
  -
  - ## Next Steps
    - (if adopting)
    - [ ] [Specific action 1 with file path or command]
    - [ ] [Specific action 2]
    - [ ] [Specific action 3]
  -
  - ## Related
    - [[Prompt Engineering]]
    - [[Claude Code]]
    - [Other relevant wiki pages]
```

## Usage Notes

- Replace all `[bracketed]` values with actual content
- The `collapsed:: true` property keeps the evaluation compact in Logseq
- Tags enable filtering all evaluations via `#[[Claude Techniques]]` and `#[[Evaluations]]`
- Date property uses Logseq date link format for journal cross-referencing
- Next steps should include absolute file paths for any file modifications
- For "Skip" verdicts, next steps section can be omitted
- For "Monitor" verdicts, include a re-evaluation trigger (e.g., "Re-evaluate when feature exits beta")

## Saving Evaluations to Wiki

To save an evaluation as a permanent Zettelkasten note:
1. Use the template above as output
2. Save to `~/Documents/personal-wiki/logseq/pages/eval-[technique-name].md`
3. Chain to `knowledge-synthesis` skill for full wiki integration
