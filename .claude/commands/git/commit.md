---
description: Create a series of commits using Conventional Commits format
prompt: "# Conventional Commit Helper\n\nI'll help you create well-structured git\
  \ commits following the Conventional Commits standard (https://www.conventionalcommits.org/en/v1.0.0/).\n\
  \n## Process\n\n1. I'll check for unstaged changes in your repository\n2. Analyze\
  \ the changes to determine logical commit groupings\n3. For each logical group,\
  \ I'll:\n   - Suggest an appropriate commit type and scope\n   - Draft a concise\
  \ commit message following the convention\n   - Stage the relevant files\n   - Create\
  \ the commit\n\n## Conventional Commits Format\n\nEach commit message will follow\
  \ this structure:\n```\n<type>[optional scope]: <description>\n\n[optional body]\n\
  \n[optional footer(s)]\n```\n\n### Types\n- **feat**: A new feature\n- **fix**:\
  \ A bug fix\n- **docs**: Documentation only changes\n- **style**: Changes that don't\
  \ affect the meaning of the code (formatting, etc)\n- **refactor**: Code change\
  \ that neither fixes a bug nor adds a feature\n- **perf**: Code change that improves\
  \ performance\n- **test**: Adding missing tests or correcting existing tests\n-\
  \ **build**: Changes to the build system or dependencies\n- **ci**: Changes to CI\
  \ configuration files and scripts\n- **chore**: Other changes that don't modify\
  \ src or test files\n\n### Breaking Changes\nIf a commit introduces a breaking change,\
  \ I'll include `BREAKING CHANGE:` in the footer or append `!` after the type/scope.\n\
  \nLet me analyze your repository and help create clean, conventional commits!\n"
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
