---
title: Conventional Commits
description: Create a series of commits using Conventional Commits format
arguments: []
---

# Conventional Commit Helper

I'll help you create well-structured git commits following the Conventional Commits standard (https://www.conventionalcommits.org/en/v1.0.0/).

## Process

1. I'll check for unstaged changes in your repository
2. Analyze the changes to determine logical commit groupings
3. For each logical group, I'll:
   - Suggest an appropriate commit type and scope
   - Draft a concise commit message following the convention
   - Stage the relevant files
   - Create the commit

## Conventional Commits Format

Each commit message will follow this structure:
```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

### Types
- **feat**: A new feature
- **fix**: A bug fix
- **docs**: Documentation only changes
- **style**: Changes that don't affect the meaning of the code (formatting, etc)
- **refactor**: Code change that neither fixes a bug nor adds a feature
- **perf**: Code change that improves performance
- **test**: Adding missing tests or correcting existing tests
- **build**: Changes to the build system or dependencies
- **ci**: Changes to CI configuration files and scripts
- **chore**: Other changes that don't modify src or test files

### Breaking Changes
If a commit introduces a breaking change, I'll include `BREAKING CHANGE:` in the footer or append `!` after the type/scope.

Let me analyze your repository and help create clean, conventional commits!
