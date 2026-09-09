---
description: Create a series of commits using Conventional Commits format
---

# Conventional Commit Helper

I'll help you create well-structured git commits following the Conventional Commits standard (https://www.conventionalcommits.org/en/v1.0.0/).

## Process

1. I'll check for unstaged changes in your repository
2. Analyze the changes to determine logical commit groupings
   - **Structural vs. behavioral is the first split, before any other grouping.** Per Kent Beck's *Tidy First?*: a change that only restructures code (rename, extract, reorder, reformat) and a change that alters what the code does are never the same commit, even when they touch the same lines for the same reason. A reviewer can skim a pure-structural diff in seconds; a behavioral diff needs real scrutiny — mixing them forces the slow read on both.
   - If a rename/extract was done *to make room for* a behavior change, that's still two commits: the tidying first (`refactor:`), then the behavior change (`feat:`/`fix:`) on top of it.
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

