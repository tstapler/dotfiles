---
title: Refine Documentation Writing
description: Improve documentation writing style and clarity using technical writing best practices
arguments: [file_or_content]
---

# Refine Documentation Writing

This command uses the `technical-writing-coach` agent to improve documentation clarity, conciseness, and impact.

## Agent Delegation

Use the following directive to invoke the agent:

```
@task technical-writing-coach

Improve the following documentation for clarity and impact.

**Content to Review**: $ARGUMENTS

**Task**: Analyze the documentation and provide specific improvements following technical writing best practices.

**Analysis Areas**:

1. **Clarity**:
   - Identify passive voice that should be active
   - Flag unclear pronoun references
   - Check for undefined technical terms
   - Verify one main idea per sentence

2. **Conciseness**:
   - Remove redundant phrases ("in order to", "it should be noted that")
   - Eliminate filler words and unnecessary qualifiers
   - Simplify complex sentence structures
   - Use parallel structure for procedures and lists

3. **Precision**:
   - Replace vague language with specific, measurable terms
   - Ensure consistent terminology throughout
   - Provide concrete examples over abstract concepts
   - Verify technical accuracy

4. **Structure**:
   - Check hierarchical organization
   - Verify information is presented logically
   - Ensure headings are descriptive
   - Group related concepts together

**Deliverables**:
- Specific revision suggestions with before/after examples
- Explanation of why each change improves readability
- Identification of recurring patterns to watch for
- Updated version of the documentation

**Focus**: Transform verbose, passive, or unclear writing into focused, active, decision-oriented documentation that emphasizes what actually counts.
```

## Usage Examples

```bash
# Refine a specific documentation file
/docs:refine-writing docs/architecture/database-design.md

# Refine documentation content directly
/docs:refine-writing "The system performs validation of input data before processing occurs"
```

##Expected Improvements

The agent will transform documentation by:
- ✅ Converting passive voice to active voice
- ✅ Eliminating redundancy and filler words
- ✅ Making vague terms specific and measurable
- ✅ Improving organization and structure
- ✅ Ensuring technical accuracy and consistency
- ✅ Providing clear, actionable feedback

## Quality Standards

All refined documentation will meet:
- Sentences average 15-20 words
- Technical terms defined when introduced
- Procedures use numbered steps with clear actions
- Each paragraph contains one main concept
- Code examples are syntactically correct
- Terminology is consistent throughout