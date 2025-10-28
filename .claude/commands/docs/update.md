---
title: Update Documentation
description: Analyze current changes and update any related outdated documentation
---

# Update Documentation Based on Current Changes

This command uses the `doc-quality-analyzer` agent to systematically update documentation based on recent code changes.

## Agent Delegation

Use the following directive to invoke the agent:

```
@task doc-quality-analyzer

Analyze current changes and update related documentation.

**Task**: Review recent code changes and update any affected documentation to ensure accuracy and completeness.

**Process**:

1. **Identify current changes**:
   - Run `git status` to see modified files
   - Run `git diff` to understand the nature of changes
   - Identify which components, features, or systems are affected

2. **Find related documentation**:
   - Search for documentation that references the changed files or components
   - Identify docs that describe the features being modified
   - Look for references to changed APIs, configurations, or workflows

3. **Analyze documentation freshness**:
   - Check if the found documentation still accurately reflects the changes
   - Identify outdated commands, code examples, or descriptions
   - Flag missing context that should be added based on the changes

4. **Update outdated documentation**:
   - Make specific edits to align documentation with current code
   - Add new sections if the changes introduce new functionality
   - Remove obsolete information that no longer applies
   - Ensure consistency with the Diataxis framework

5. **Verify completeness**:
   - Ensure all affected documentation has been updated
   - Check that examples and commands still work
   - Verify that cross-references are still valid

**Focus**: Documentation that is directly impacted by the current changes. Be thorough but pragmatic - prioritize accuracy and completeness over perfection.
```

## Usage

Simply run this command after making code changes and before creating a PR:

```bash
/docs:update
```

The agent will automatically identify changes, find affected documentation, and update it accordingly.
