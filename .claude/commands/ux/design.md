---
title: UX Design
description: Generate design recommendations and guidance for new features using ux-expert agent
arguments: [feature_description]
---

# UX Design Command

Generate comprehensive design recommendations and guidance for a new feature, component, or interface using the specialized ux-expert agent.

## Feature Description

${1:-Please describe the feature you want to design}

## Process

This command will launch the **ux-expert agent** to provide design guidance including:

1. **User Flow and Information Architecture**
   - Recommended user journey and task flows
   - Information hierarchy and content structure
   - Navigation patterns and wayfinding

2. **UI Pattern Recommendations**
   - Appropriate design patterns for the use case
   - Examples from established design systems
   - Component composition and layout suggestions
   - Responsive design considerations

3. **Interaction Design**
   - Input methods and controls
   - Feedback mechanisms (loading, success, errors)
   - Micro-interactions and transitions
   - State management (empty, loading, error, success)

4. **Accessibility Requirements**
   - Keyboard navigation patterns
   - Screen reader considerations
   - ARIA roles and attributes needed
   - Color contrast and visual requirements
   - Focus management

5. **Visual Design Guidance**
   - Visual hierarchy principles
   - Typography and spacing recommendations
   - Color usage and semantic meaning
   - Iconography and imagery guidance

6. **Mobile and Responsive Considerations**
   - Touch target sizing and placement
   - Gesture support recommendations
   - Progressive disclosure patterns
   - One-handed use considerations

7. **Similar Patterns and Examples**
   - References to existing design system components
   - Industry standard patterns
   - Best-in-class examples

## Expected Deliverables

- Comprehensive design guidance document
- Recommended UI patterns with rationale
- Accessibility checklist for the feature
- References to relevant design patterns and systems
- Implementation considerations and gotchas

## Instructions to Claude

**Step 1**: Launch the `ux-expert` agent with the following context:

**Feature to Design**: ${1:-Please describe the feature you want to design}

**Agent Task**: Provide comprehensive design guidance for this feature including:

1. **Understanding the Use Case**
   - Identify primary user goals and tasks
   - Consider different user types and contexts
   - Map critical user flows step-by-step

2. **Pattern Research**
   - Search the user's zettelkasten for relevant design patterns using Grep/Read tools
   - Search online for established patterns in major design systems (Material Design, Carbon, Polaris, Atlassian)
   - Identify similar features in well-designed products

3. **Design Recommendations**
   - Recommend specific UI patterns with justification
   - Provide layout and composition guidance
   - Suggest appropriate components and interactions
   - Include accessibility requirements from the start

4. **Implementation Guidance**
   - List key states to design (default, hover, active, disabled, loading, error, success, empty)
   - Identify potential usability pitfalls to avoid
   - Suggest quick wins vs. enhanced experiences
   - Provide mobile-specific considerations

5. **Design Validation**
   - Create checklist for validating the design against usability heuristics
   - List accessibility requirements to verify
   - Suggest usability testing approaches

**Step 2**: Format the recommendations in a clear, structured document that can be used by designers and developers.

Execute this workflow now for: ${1:-Please describe the feature you want to design}
