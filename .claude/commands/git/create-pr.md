---
description: Create a well-structured pull request following best practices for description,
  testing, and review
prompt: "# Create Pull Request\n\nI'll help you create a high-quality pull request\
  \ following industry best practices from GitHub, Conventional Commits, and software\
  \ engineering research.\n\n## Prerequisites Check\n\nBefore creating a PR, I'll\
  \ verify:\n\n```bash\n# Check git status\ngit status\n\n# Verify we're on the correct\
  \ branch\ngit branch --show-current\n\n# Check branch is pushed to remote\ngit branch\
  \ -vv\n\n# Verify GitHub CLI is available\ngh --version\n```\n\n### If Prerequisites\
  \ Fail\n\n**If gh CLI is not installed:**\n```bash\n# macOS with Homebrew\nbrew\
  \ install gh\n\n# Authenticate with GitHub\ngh auth login\n\n# Verify authentication\n\
  gh auth status\n```\n\n**If branch is not pushed:**\n```bash\n# Push current branch\
  \ with upstream tracking\ngit push -u origin $(git branch --show-current)\n```\n\
  \n## Pre-PR Validation Checklist\n\nI'll verify all of these items before creating\
  \ the PR:\n\n### Code Quality\n- [ ] Code follows project style guidelines\n- [\
  \ ] All linters pass (eslint, pylint, Black, etc.)\n- [ ] Code formatter applied\n\
  - [ ] No commented-out code or debug statements\n- [ ] No sensitive data or credentials\
  \ in code\n\n### Testing\n- [ ] All existing tests pass locally\n- [ ] New tests\
  \ added for new functionality\n- [ ] Test coverage meets project threshold\n- [\
  \ ] Edge cases identified and tested\n- [ ] Integration tests pass if applicable\n\
  - [ ] Manual testing completed for UI changes\n\n### Build and Compilation\n- [\
  \ ] Project builds without errors\n- [ ] No new compiler warnings\n- [ ] Dependencies\
  \ properly declared\n- [ ] Build artifacts verified\n\n### Git Hygiene\n- [ ] Branch\
  \ is up-to-date with base branch\n- [ ] Commits follow conventional commits format\n\
  - [ ] No merge commits (rebased if necessary)\n- [ ] Branch has descriptive name\n\
  - [ ] Commit history is clean and logical\n\n### Documentation\n- [ ] Code comments\
  \ added where necessary\n- [ ] README updated if public API changed\n- [ ] API documentation\
  \ updated\n- [ ] Migration guide provided for breaking changes\n\n## PR Size Analysis\n\
  \nI'll analyze the changes to ensure optimal PR size:\n\n**Research-backed guidelines:**\n\
  - **Ideal size**: 50-200 lines of code changed\n- **Maximum recommended**: 250 lines\n\
  - **Review effectiveness**: 200-400 LOC yields 70-90% defect discovery\n\nIf changes\
  \ exceed recommended size, I'll suggest breaking them down into smaller, logical\
  \ PRs.\n\n## Commit Message Validation\n\nI'll verify all commits follow Conventional\
  \ Commits format:\n\n### Format Structure\n```\n<type>[optional scope]: <description>\n\
  \n[optional body]\n\n[optional footer(s)]\n```\n\n### Valid Commit Types\n- `feat:`\
  \ - New feature (MINOR version)\n- `fix:` - Bug fix (PATCH version)\n- `docs:` -\
  \ Documentation only\n- `style:` - Code style/formatting\n- `refactor:` - Code refactoring\n\
  - `perf:` - Performance improvements\n- `test:` - Test changes\n- `build:` - Build\
  \ system changes\n- `ci:` - CI/CD changes\n- `chore:` - Maintenance tasks\n- `revert:`\
  \ - Reverting changes\n\n### Breaking Changes\n- Use `BREAKING CHANGE:` in footer\
  \ OR\n- Append exclamation mark after type/scope: `feat!:` or `feat(api)!:`\n\n\
  ## PR Template Detection\n\n**Before writing any PR body, check the repo for an\
  \ existing template:**\n\n```bash\n# Standard GitHub template locations (check in\
  \ this order)\nfor path in \\\n  \".github/pull_request_template.md\" \\\n  \".github/PULL_REQUEST_TEMPLATE.md\"\
  \ \\\n  \"docs/pull_request_template.md\" \\\n  \"PULL_REQUEST_TEMPLATE.md\"; do\n\
  \  [ -f \"$path\" ] && echo \"Found: $path\" && cat \"$path\" && break\ndone\n\n\
  # Multiple-template directory (list options for user to choose)\nls .github/PULL_REQUEST_TEMPLATE/*.md\
  \ 2>/dev/null\n```\n\n**If a template is found:**\n- Use it as the base structure\
  \ for the PR body\n- Fill in the template's placeholders with content from the actual\
  \ changes\n- Remove any instructions/boilerplate lines from the template that say\
  \ \"delete this line\" or similar\n- Do NOT substitute the template with a different\
  \ format\n\n**If no template is found:** use the description format below.\n\n##\
  \ PR Description Generation (no template found)\n\nI'll create a comprehensive PR\
  \ description following this template:\n\n```markdown\n## What?\n[Clear description\
  \ of changes made]\n\n## Why?\n[Business/engineering goal and motivation]\n\n##\
  \ How?\n[Technical approach and significant design decisions]\n\n## Testing\n###\
  \ Test Coverage\n- Unit tests: [coverage percentage]\n- Integration tests: [yes/no]\n\
  - Manual testing: [what was tested]\n\n### How to Test\n1. [Step-by-step instructions\
  \ for reviewers]\n2. [...]\n3. [...]\n\n### Expected Results\n[What reviewers should\
  \ see when testing]\n\n## Type of Change\n<!-- Mark with \"x\" -->\n- [ ] Bug fix\
  \ (non-breaking change that fixes an issue)\n- [ ] New feature (non-breaking change\
  \ that adds functionality)\n- [ ] Breaking change (fix or feature causing existing\
  \ functionality to break)\n- [ ] Documentation update\n- [ ] Refactoring (no functional\
  \ changes)\n- [ ] Performance improvement\n- [ ] Chore (dependency updates, build\
  \ config, etc.)\n\n## Breaking Changes\n[If applicable, describe breaking changes\
  \ and provide migration guide]\n\n## Performance Impact\n[Describe any performance\
  \ implications]\n\n## Security Considerations\n[Any security implications or changes]\n\
  \n## Screenshots/Recordings\n[For UI changes - before/after screenshots or screen\
  \ recordings]\n\n## Related Issues\nCloses #[issue-number]\nRelated to #[issue-number]\n\
  \n## Additional Notes\n[Technical debt, future improvements, known limitations,\
  \ review focus areas]\n\n## Review Checklist\n- [ ] Code follows project conventions\n\
  - [ ] Self-review completed\n- [ ] Comments added for complex logic\n- [ ] Documentation\
  \ updated\n- [ ] No new warnings\n- [ ] Tests added and passing\n- [ ] Commits follow\
  \ conventional format\n```\n\n## Branch Analysis\n\nI'll analyze the commit history\
  \ to understand the full scope:\n\n```bash\n# Get base branch (usually main or master)\n\
  BASE_BRANCH=$(git remote show origin | grep 'HEAD branch' | cut -d' ' -f5)\n\n#\
  \ Show commits that will be in PR\ngit log ${BASE_BRANCH}...HEAD --oneline\n\n#\
  \ Show full diff that will be in PR\ngit diff ${BASE_BRANCH}...HEAD --stat\n\n#\
  \ Show changed files\ngit diff ${BASE_BRANCH}...HEAD --name-only\n```\n\n## Creating\
  \ the PR\n\nAfter validation, I'll create the PR using:\n\n```bash\n# Create PR\
  \ with generated description\ngh pr create \\\n  --title \"[Generated from commits]\"\
  \ \\\n  --body \"$(cat <<'EOF'\n[Generated description]\nEOF\n)\" \\\n  --web\n\
  ```\n\n### PR Title Best Practices\n\n**Good titles:**\n- Be specific and descriptive\n\
  - Use imperative mood (\"Add feature\" not \"Added feature\")\n- Reference ticket\
  \ number if applicable\n- Front-load important information\n- Keep under 72 characters\n\
  \n**Examples:**\n```\nAdd user authentication with OAuth2 support (#123)\nFix race\
  \ condition in payment processing\nRefactor database connection pool for performance\n\
  Update deployment docs for Kubernetes\nRemove deprecated API v1 endpoints (BREAKING)\n\
  ```\n\n## Post-PR Tasks\n\nAfter creating the PR, I'll:\n\n1. Add relevant labels\n\
  2. Request specific reviewers\n3. Link to project boards\n4. Set milestone if applicable\n\
  5. Mark as draft if still WIP\n6. Return the PR URL\n\n## Error Handling\n\n**If\
  \ validation fails:**\n- I'll identify specific issues\n- Provide actionable remediation\
  \ steps\n- Wait for you to fix issues before proceeding\n\n**If gh CLI fails:**\n\
  - Verify authentication: `gh auth status`\n- Check repository permissions\n- Ensure\
  \ remote repository exists\n\n**If branch conflicts with base:**\n- Suggest rebasing:\
  \ `git rebase origin/main`\n- Guide through conflict resolution\n- Re-run validation\
  \ after rebase\n\n## Best Practices Applied\n\nThis command implements:\n\n✅ **GitHub\
  \ Official Best Practices** - PR description structure and content\n✅ **Conventional\
  \ Commits Specification** - Commit message validation\n✅ **Research-Based Size Guidelines**\
  \ - Optimal 50-200 LOC recommendation\n✅ **Comprehensive Testing** - Pre-merge validation\
  \ checklist\n✅ **Security First** - Credential and security scanning\n✅ **Review\
  \ Optimization** - Structured description for efficient review\n\n## Advanced Options\n\
  \n### Custom Base Branch\nIf you need to target a different base branch:\n```bash\n\
  gh pr create --base feature-branch --head current-branch\n```\n\n### Draft PR\n\
  For work-in-progress:\n```bash\ngh pr create --draft\n```\n\n### Multiple Reviewers\n\
  ```bash\ngh pr create --reviewer user1,user2,team-name\n```\n\n## Metrics and Success\
  \ Criteria\n\n**Healthy PR characteristics:**\n- Time to first review: < 4 hours\n\
  - Time to merge: < 1 day for small PRs\n- Number of review cycles: 1-2 average\n\
  - PR size: 50-200 lines average\n- Review comments: 3-10 per PR\n\n## References\n\
  \nThis command is based on:\n- GitHub Official Documentation (https://docs.github.com/en/pull-requests)\n\
  - Conventional Commits Specification (https://www.conventionalcommits.org)\n- Cisco\
  \ Systems Code Review Research (200-400 LOC optimal)\n- Graphite PR Size Research\
  \ (https://graphite.dev/blog)\n- PullRequest.com Best Practices\n\n---\n\nLet me\
  \ analyze your current branch and help you create a well-structured PR!\n"
---

# Create Pull Request

I'll help you create a high-quality pull request following industry best practices from GitHub, Conventional Commits, and software engineering research.

## Prerequisites Check

Before creating a PR, I'll verify:

```bash
# Check git status
git status

# Verify we're on the correct branch
git branch --show-current

# Check branch is pushed to remote
git branch -vv

# Verify GitHub CLI is available
gh --version
```

### If Prerequisites Fail

**If gh CLI is not installed:**
```bash
# macOS with Homebrew
brew install gh

# Authenticate with GitHub
gh auth login

# Verify authentication
gh auth status
```

**If branch is not pushed:**
```bash
# Push current branch with upstream tracking
git push -u origin $(git branch --show-current)
```

## Pre-PR Validation Checklist

I'll verify all of these items before creating the PR:

### Code Quality
- [ ] Code follows project style guidelines
- [ ] All linters pass (eslint, pylint, Black, etc.)
- [ ] Code formatter applied
- [ ] No commented-out code or debug statements
- [ ] No sensitive data or credentials in code

### Testing
- [ ] All existing tests pass locally
- [ ] New tests added for new functionality
- [ ] Test coverage meets project threshold
- [ ] Edge cases identified and tested
- [ ] Integration tests pass if applicable
- [ ] Manual testing completed for UI changes

### Build and Compilation
- [ ] Project builds without errors
- [ ] No new compiler warnings
- [ ] Dependencies properly declared
- [ ] Build artifacts verified

### Git Hygiene
- [ ] Branch is up-to-date with base branch
- [ ] Commits follow conventional commits format
- [ ] No merge commits (rebased if necessary)
- [ ] Branch has descriptive name
- [ ] Commit history is clean and logical

### Documentation
- [ ] Code comments added where necessary
- [ ] README updated if public API changed
- [ ] API documentation updated
- [ ] Migration guide provided for breaking changes

## PR Size Analysis

I'll analyze the changes to ensure optimal PR size:

**Research-backed guidelines:**
- **Ideal size**: 50-200 lines of code changed
- **Maximum recommended**: 250 lines
- **Review effectiveness**: 200-400 LOC yields 70-90% defect discovery

If changes exceed recommended size, I'll suggest breaking them down into smaller, logical PRs.

## Commit Message Validation

I'll verify all commits follow Conventional Commits format:

### Format Structure
```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

### Valid Commit Types
- `feat:` - New feature (MINOR version)
- `fix:` - Bug fix (PATCH version)
- `docs:` - Documentation only
- `style:` - Code style/formatting
- `refactor:` - Code refactoring
- `perf:` - Performance improvements
- `test:` - Test changes
- `build:` - Build system changes
- `ci:` - CI/CD changes
- `chore:` - Maintenance tasks
- `revert:` - Reverting changes

### Breaking Changes
- Use `BREAKING CHANGE:` in footer OR
- Append exclamation mark after type/scope: `feat!:` or `feat(api)!:`

## PR Template Detection

**Before writing any PR body, check the repo for an existing template:**

```bash
# Standard GitHub template locations (check in this order)
for path in \
  ".github/pull_request_template.md" \
  ".github/PULL_REQUEST_TEMPLATE.md" \
  "docs/pull_request_template.md" \
  "PULL_REQUEST_TEMPLATE.md"; do
  [ -f "$path" ] && echo "Found: $path" && cat "$path" && break
done

# Multiple-template directory (list options for user to choose)
ls .github/PULL_REQUEST_TEMPLATE/*.md 2>/dev/null
```

**If a template is found:**
- Use it as the base structure for the PR body
- Fill in the template's placeholders with content from the actual changes
- Remove any instructions/boilerplate lines from the template that say "delete this line" or similar
- Do NOT substitute the template with a different format

**If no template is found:** use the description format below.

## PR Description Generation (no template found)

I'll create a comprehensive PR description following this template:

```markdown
## What?
[Clear description of changes made]

## Why?
[Business/engineering goal and motivation]

## How?
[Technical approach and significant design decisions]

## Testing
### Test Coverage
- Unit tests: [coverage percentage]
- Integration tests: [yes/no]
- Manual testing: [what was tested]

### How to Test
1. [Step-by-step instructions for reviewers]
2. [...]
3. [...]

### Expected Results
[What reviewers should see when testing]

## Type of Change
<!-- Mark with "x" -->
- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)
- [ ] Breaking change (fix or feature causing existing functionality to break)
- [ ] Documentation update
- [ ] Refactoring (no functional changes)
- [ ] Performance improvement
- [ ] Chore (dependency updates, build config, etc.)

## Breaking Changes
[If applicable, describe breaking changes and provide migration guide]

## Performance Impact
[Describe any performance implications]

## Security Considerations
[Any security implications or changes]

## Screenshots/Recordings
[For UI changes - before/after screenshots or screen recordings]

## Related Issues
Closes #[issue-number]
Related to #[issue-number]

## Additional Notes
[Technical debt, future improvements, known limitations, review focus areas]

## Review Checklist
- [ ] Code follows project conventions
- [ ] Self-review completed
- [ ] Comments added for complex logic
- [ ] Documentation updated
- [ ] No new warnings
- [ ] Tests added and passing
- [ ] Commits follow conventional format
```

## Branch Analysis

I'll analyze the commit history to understand the full scope:

```bash
# Get base branch (usually main or master)
BASE_BRANCH=$(git remote show origin | grep 'HEAD branch' | cut -d' ' -f5)

# Show commits that will be in PR
git log ${BASE_BRANCH}...HEAD --oneline

# Show full diff that will be in PR
git diff ${BASE_BRANCH}...HEAD --stat

# Show changed files
git diff ${BASE_BRANCH}...HEAD --name-only
```

## Creating the PR

After validation, I'll create the PR using:

```bash
# Create PR with generated description
gh pr create \
  --title "[Generated from commits]" \
  --body "$(cat <<'EOF'
[Generated description]
EOF
)" \
  --web
```

### PR Title Best Practices

**Good titles:**
- Be specific and descriptive
- Use imperative mood ("Add feature" not "Added feature")
- Reference ticket number if applicable
- Front-load important information
- Keep under 72 characters

**Examples:**
```
Add user authentication with OAuth2 support (#123)
Fix race condition in payment processing
Refactor database connection pool for performance
Update deployment docs for Kubernetes
Remove deprecated API v1 endpoints (BREAKING)
```

## Post-PR Tasks

After creating the PR, I'll:

1. Add relevant labels
2. Request specific reviewers
3. Link to project boards
4. Set milestone if applicable
5. Mark as draft if still WIP
6. Return the PR URL

## Error Handling

**If validation fails:**
- I'll identify specific issues
- Provide actionable remediation steps
- Wait for you to fix issues before proceeding

**If gh CLI fails:**
- Verify authentication: `gh auth status`
- Check repository permissions
- Ensure remote repository exists

**If branch conflicts with base:**
- Suggest rebasing: `git rebase origin/main`
- Guide through conflict resolution
- Re-run validation after rebase

## Best Practices Applied

This command implements:

✅ **GitHub Official Best Practices** - PR description structure and content
✅ **Conventional Commits Specification** - Commit message validation
✅ **Research-Based Size Guidelines** - Optimal 50-200 LOC recommendation
✅ **Comprehensive Testing** - Pre-merge validation checklist
✅ **Security First** - Credential and security scanning
✅ **Review Optimization** - Structured description for efficient review

## Advanced Options

### Custom Base Branch
If you need to target a different base branch:
```bash
gh pr create --base feature-branch --head current-branch
```

### Draft PR
For work-in-progress:
```bash
gh pr create --draft
```

### Multiple Reviewers
```bash
gh pr create --reviewer user1,user2,team-name
```

## Metrics and Success Criteria

**Healthy PR characteristics:**
- Time to first review: < 4 hours
- Time to merge: < 1 day for small PRs
- Number of review cycles: 1-2 average
- PR size: 50-200 lines average
- Review comments: 3-10 per PR

## References

This command is based on:
- GitHub Official Documentation (https://docs.github.com/en/pull-requests)
- Conventional Commits Specification (https://www.conventionalcommits.org)
- Cisco Systems Code Review Research (200-400 LOC optimal)
- Graphite PR Size Research (https://graphite.dev/blog)
- PullRequest.com Best Practices

---

Let me analyze your current branch and help you create a well-structured PR!
