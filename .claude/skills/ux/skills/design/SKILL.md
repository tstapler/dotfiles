---
description: Generate design recommendations and guidance for new features using ux-expert
  agent
prompt: "# UX Design Command\n\nGenerate comprehensive design recommendations for\
  \ a feature using the `ux-expert` agent. Automatically reads from an existing PRD\
  \ in `docs/tasks/` if one exists, so UX builds on PM work rather than starting blind.\n\
  \n## Input\n\n`{{args}}` — either a feature name matching an existing `docs/tasks/<name>.md`,\
  \ or a free-form description.\n\n## Instructions to Claude\n\n**Step 1: Check for\
  \ existing PRD**\n\nBefore launching the agent, check whether a feature doc already\
  \ exists:\n- Look for `docs/tasks/{{args}}.md` or a close match (use Glob)\n- If\
  \ found, read it — the agent will use it as context\n- If not found, proceed with\
  \ the description as-is\n\n**Step 2**: Launch the `ux-expert` agent with the following\
  \ context:\n\n**Feature**: {{args}}\n\n**Existing PRD** (if found above): [paste\
  \ content or path]\n\n**Agent Task**: Provide comprehensive UX design guidance for\
  \ this feature.\n\nIf a PRD was found:\n- Extract the user goals, JTBD, and acceptance\
  \ criteria from it\n- Design for the specific users and outcomes defined in the\
  \ PRD\n- Flag any UX concerns about the scope or assumptions in the PRD\n\nIf no\
  \ PRD exists:\n- Note that no PRD was found and flag this — ideally the `pm-product-management`\
  \ skill should be run first\n- Proceed with available description, but call out\
  \ missing context explicitly\n\n**Design deliverables**:\n\n1. **User Flow and Information\
  \ Architecture**\n   - Step-by-step user journey for the primary task\n   - Information\
  \ hierarchy and content structure\n   - Navigation patterns and entry/exit points\n\
  \n2. **UI Pattern Recommendations**\n   - Specific patterns for the use case with\
  \ justification\n   - Component composition and layout\n   - Responsive / mobile\
  \ considerations\n\n3. **Key States**\n   - All states that must be designed: empty,\
  \ loading, error, success, disabled, edge cases\n   - Transitions and feedback mechanisms\n\
  \n4. **Accessibility Requirements**\n   - Keyboard navigation\n   - Screen reader\
  \ / ARIA needs\n   - Color contrast, focus management\n   - Touch target sizing\
  \ (min 44x44px)\n\n5. **Usability Validation Checklist**\n   - Nielsen heuristics\
  \ applicable to this feature\n   - POUR accessibility checks\n   - Potential friction\
  \ points and how to address them\n\n**Step 3**: Append UX guidance to the existing\
  \ feature doc (if one exists) under a `## UX Design` section, or output as a standalone\
  \ document.\n\n**Step 4**: Confirm whether the UX readiness gate is met so the feature\
  \ can proceed to `@project-coordinator` for task breakdown:\n- [ ] User flow mapped\n\
  - [ ] Key states identified\n- [ ] Accessibility requirements noted\n\nExecute this\
  \ workflow now for: {{args}}\n"
---

# UX Design Command

Generate comprehensive design recommendations for a feature using the `ux-expert` agent. Automatically reads from an existing PRD in `docs/tasks/` if one exists, so UX builds on PM work rather than starting blind.

## Input

`$ARGUMENTS` — either a feature name matching an existing `docs/tasks/<name>.md`, or a free-form description.

## Instructions to Claude

**Step 1: Check for existing PRD**

Before launching the agent, check whether a feature doc already exists:
- Look for `docs/tasks/$ARGUMENTS.md` or a close match (use Glob)
- If found, read it — the agent will use it as context
- If not found, proceed with the description as-is

**Step 2**: Launch the `ux-expert` agent with the following context:

**Feature**: $ARGUMENTS

**Existing PRD** (if found above): [paste content or path]

**Agent Task**: Provide comprehensive UX design guidance for this feature.

If a PRD was found:
- Extract the user goals, JTBD, and acceptance criteria from it
- Design for the specific users and outcomes defined in the PRD
- Flag any UX concerns about the scope or assumptions in the PRD

If no PRD exists:
- Note that no PRD was found and flag this — ideally the `pm-product-management` skill should be run first
- Proceed with available description, but call out missing context explicitly

**Design deliverables**:

1. **User Flow and Information Architecture**
   - Step-by-step user journey for the primary task
   - Information hierarchy and content structure
   - Navigation patterns and entry/exit points

2. **UI Pattern Recommendations**
   - Specific patterns for the use case with justification
   - Component composition and layout
   - Responsive / mobile considerations

3. **Key States**
   - All states that must be designed: empty, loading, error, success, disabled, edge cases
   - Transitions and feedback mechanisms

4. **Accessibility Requirements**
   - Keyboard navigation
   - Screen reader / ARIA needs
   - Color contrast, focus management
   - Touch target sizing (min 44x44px)

5. **Usability Validation Checklist**
   - Nielsen heuristics applicable to this feature
   - POUR accessibility checks
   - Potential friction points and how to address them

**Step 3**: Append UX guidance to the existing feature doc (if one exists) under a `## UX Design` section, or output as a standalone document.

**Step 4**: Confirm whether the UX readiness gate is met so the feature can proceed to `@project-coordinator` for task breakdown:
- [ ] User flow mapped
- [ ] Key states identified
- [ ] Accessibility requirements noted

Execute this workflow now for: $ARGUMENTS
