---
title: UX Review
description: Conduct comprehensive UX review using ux-expert agent and document findings with project-coordinator
arguments: [scope]
---

# UX Review Command

Conduct a comprehensive User Experience review of the project (or specific scope) using the specialized ux-expert agent, then document all recommendations and findings using the project-coordinator agent.

## Scope

${1:-.}

Review scope: `${1:-.}` (defaults to entire project if not specified)

## Process

This command will:

1. **Launch ux-expert agent** to conduct comprehensive UX review including:
   - Usability heuristics evaluation (Nielsen's 10 principles)
   - Accessibility audit (POUR principles, WCAG compliance)
   - Visual hierarchy and information architecture assessment
   - Interaction design patterns review
   - Mobile-specific considerations
   - Design system consistency checks

2. **Launch project-coordinator agent** to:
   - Document all findings in structured format
   - Create actionable tasks for each recommendation
   - Prioritize issues by severity (critical, high, medium, low)
   - Track recommendations in project planning system

## Expected Deliverables

- Comprehensive UX review report with findings organized by category
- Prioritized list of recommendations with severity levels
- Documented tasks in project planning system (TODO.md or equivalent)
- References to relevant UX principles and best practices

## Instructions to Claude

**Step 1**: Launch the `ux-expert` agent to review the specified scope (`${1:-.}`). The agent should:

- Identify all user-facing components, pages, and interfaces in scope
- Apply Nielsen's 10 usability heuristics
- Evaluate accessibility using POUR principles
- Assess visual design and information hierarchy
- Review interaction patterns and user flows
- Identify friction points and usability issues
- Check mobile responsiveness and touch targets
- Verify consistency with design system (if applicable)
- Provide specific, actionable recommendations for each issue
- Prioritize findings by severity

**Step 2**: After the ux-expert agent completes its review, launch the `project-coordinator` agent to:

- Create structured documentation of all UX findings
- Organize recommendations by category (usability, accessibility, visual design, interaction design)
- Create actionable tasks with clear acceptance criteria
- Prioritize tasks based on severity and impact
- Update project planning documents (TODO.md or similar)
- Link to relevant design patterns, resources, or examples

**Important**: Launch both agents using the Task tool. The ux-expert agent should complete its full review before the project-coordinator agent begins documentation.

Execute this workflow now for scope: `${1:-.}`
