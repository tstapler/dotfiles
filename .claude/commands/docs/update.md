---
description: Analyze current changes and update any related outdated documentation
prompt: "# Update Documentation Based on Current Changes\n\nThis command uses the\
  \ `doc-quality-analyzer` agent to systematically update documentation based on recent\
  \ code changes.\n\n## Agent Delegation\n\nUse the following directive to invoke\
  \ the agent:\n\n```\n@task doc-quality-analyzer\n\nAnalyze current changes and update\
  \ related documentation.\n\n**Task**: Review recent code changes and update any\
  \ affected documentation to ensure accuracy and completeness.\n\n**Process**:\n\n\
  1. **Identify current changes**:\n   - Run `git status` to see modified files\n\
  \   - Run `git diff` to understand the nature of changes\n   - Identify which components,\
  \ features, or systems are affected\n\n2. **Find related documentation**:\n   -\
  \ Search for documentation that references the changed files or components\n   -\
  \ Identify docs that describe the features being modified\n   - Look for references\
  \ to changed APIs, configurations, or workflows\n\n3. **Analyze documentation freshness**:\n\
  \   - Check if the found documentation still accurately reflects the changes\n \
  \  - Identify outdated commands, code examples, or descriptions\n   - Flag missing\
  \ context that should be added based on the changes\n\n4. **Update outdated documentation**:\n\
  \   - Make specific edits to align documentation with current code\n   - Add new\
  \ sections if the changes introduce new functionality\n   - Remove obsolete information\
  \ that no longer applies\n   - Ensure consistency with the Diataxis framework\n\n\
  5. **Verify completeness**:\n   - Ensure all affected documentation has been updated\n\
  \   - Check that examples and commands still work\n   - Verify that cross-references\
  \ are still valid\n\n**Focus**: Documentation that is directly impacted by the current\
  \ changes. Be thorough but pragmatic - prioritize accuracy and completeness over\
  \ perfection.\n```\n\n## Usage\n\nSimply run this command after making code changes\
  \ and before creating a PR:\n\n```bash\n/docs:update\n```\n\nThe agent will automatically\
  \ identify changes, find affected documentation, and update it accordingly.\n"
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
