---
title: Prune Documentation
description: Remove duplication, outdated content, and condense documentation while following Diataxis principles
---

# Prune and Consolidate Documentation

This command orchestrates a comprehensive documentation pruning workflow using specialized subagents.

## Workflow Overview

1. **Analysis Phase**: Use doc-quality-analyzer subagent for systematic analysis
2. **Organization Phase**: Use project-coordinator subagent for task breakdown

Please use the doc-quality-analyzer subagent to systematically prune and consolidate our documentation:

## Phase 1: Discovery and Assessment

1. **Inventory all documentation**:
   - Scan all `.md` files in the project
   - Create a comprehensive list with file paths and purposes
   - Identify the apparent content type (tutorial, how-to, reference, explanation)

2. **Identify duplication**:
   - Find content that appears in multiple files
   - Detect overlapping or redundant explanations
   - Flag near-duplicate sections that cover the same topics

3. **Detect outdated content**:
   - Find references to files, classes, or features that no longer exist
   - Identify commands or code examples that don't work anymore
   - Flag documentation with old dates or version references
   - Check for references to deprecated tools or practices

## Phase 2: Pruning Analysis

1. **Classify duplication severity**:
   - **Critical duplication**: Exact copies that should be consolidated
   - **High duplication**: Very similar content with minor variations
   - **Medium duplication**: Related content that could be merged
   - **Low duplication**: Acceptable repetition for context

2. **Assess outdated content**:
   - **Remove entirely**: Completely obsolete information
   - **Update in place**: Fixable with minor edits
   - **Consolidate**: Merge with other content during pruning

3. **Identify condensation opportunities**:
   - Verbose explanations that could be more concise
   - Examples that could be simplified
   - Redundant context that's repeated unnecessarily

## Phase 3: Diataxis Compliance Check

Before making changes, verify:
1. **Content type alignment**: Ensure each document serves one primary Diataxis purpose
2. **Appropriate location**: Check if content belongs in its current location
3. **Cross-references**: Verify that consolidation won't break important links
4. **Preservation of value**: Ensure we're not losing important institutional knowledge

## Phase 4: Execute Pruning

For each identified issue:

1. **Remove complete duplicates**:
   - Keep the most comprehensive or well-written version
   - Update all references to point to the kept version
   - Delete the redundant files

2. **Consolidate related content**:
   - Merge similar documentation into single, authoritative sources
   - Maintain Diataxis separation (don't mix tutorials with reference)
   - Preserve valuable details from all sources

3. **Delete obsolete content**:
   - Remove documentation for features that no longer exist
   - Delete outdated command references
   - Remove references to deprecated tools

4. **Condense verbose content**:
   - Tighten prose while maintaining clarity
   - Simplify examples where appropriate
   - Remove unnecessary repetition

## Phase 5: Verification

After pruning:
1. **Check for broken links**: Ensure all internal references still work
2. **Verify completeness**: Confirm no critical information was lost
3. **Test examples**: Validate that remaining code examples still work
4. **Review structure**: Ensure Diataxis principles are maintained

## Output Requirements

Provide:

1. **Executive Summary**:
   - Total files analyzed
   - Files to be deleted
   - Files to be consolidated
   - Files to be updated
   - Estimated documentation size reduction

2. **Detailed Pruning Plan**:
   - Specific files to delete with justification
   - Consolidation recommendations with target files
   - Content to condense with specific sections
   - Before/after structure comparison

3. **Risk Assessment**:
   - Content that seems outdated but might still be relevant
   - High-risk deletions that need human review
   - Dependencies that might be affected

4. **Action Plan**:
   - Prioritized list of changes
   - Specific file operations (delete, merge, edit)
   - Order of operations to minimize disruption

## Guidelines

- **Preserve over delete**: When in doubt, flag for review rather than delete
- **Consolidate thoughtfully**: Don't merge content that serves different purposes
- **Maintain Diataxis**: Keep tutorials, how-tos, references, and explanations separate
- **Document decisions**: Explain why content is being removed or consolidated
- **Respect structure**: Don't break existing navigation patterns without good reason

Be thorough but conservative. The goal is to improve documentation quality and maintainability, not to minimize file count at any cost.

## Phase 6: Task Organization with project-coordinator Subagent

After the doc-quality-analyzer subagent completes the pruning analysis, use the project-coordinator subagent to organize the work into atomic tasks.

Invoke the project-coordinator subagent with the following context:

```
Use the project-coordinator subagent to organize documentation pruning tasks.

I've completed a comprehensive documentation pruning analysis. Please help me organize the findings into an ATOMIC task hierarchy following the AIC (ATOMIC-INVEST-CONTEXT) framework.

**Context**:
We analyzed [N] documentation files, identified [M] items to prune/consolidate across the following categories:
- Files to delete: [COUNT]
- Files to consolidate: [COUNT]
- Files to update: [COUNT]
- Estimated size reduction: [PERCENTAGE]

**Findings Summary by Priority**:

**Priority 0 (Critical - Dangerous or Incorrect Content)**:
[List P0 findings - factually incorrect information, security issues, broken examples]

**Priority 1 (High - Significant Quality Impact)**:
[List P1 findings - major duplication, significantly outdated content, structural issues]

**Priority 2 (Medium - Nice to Have)**:
[List P2 findings - minor improvements, style consistency, Diataxis violations]

**Priority 3 (Low - Future Consideration)**:
[List P3 findings - optional enhancements, minor cleanup]

**Dependencies Identified**:
[Note any dependencies between documentation changes - e.g., must consolidate before deleting]

**Constraints**:
- Preserve institutional knowledge - backup before major deletions
- Maintain Diataxis framework separation (don't mix content types)
- Test examples and commands before removing documentation
- Update cross-references when moving/consolidating content
- Each task should be 1-4 hours of focused work

**Request**:
1. Create a project task document in `docs/tasks/documentation-pruning.md` using the AIC framework
2. Break down pruning work into atomic tasks (1-4 hours each) with:
   - Specific files to modify/delete/consolidate
   - Clear success criteria
   - Context boundaries (3-5 files per task)
   - Testing requirements (validate examples, check links)
3. Identify task dependencies (e.g., Task 2.1 "Consolidate X and Y" must complete before Task 2.2 "Delete Y")
4. Recommend the next action to start with (prioritize high-impact quick wins or critical fixes)
5. Provide progress tracking structure for the pruning epic
```

**Expected Output**: The project-coordinator subagent will create a structured task document with:
- Epic overview for documentation pruning
- Story breakdown (e.g., "Story 1: Remove dangerous content", "Story 2: Consolidate duplicates")
- Atomic tasks with file-level specificity
- Dependency visualization
- Clear next action recommendation
