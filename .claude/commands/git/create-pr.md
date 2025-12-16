---
title: Create Pull Request
description: Create a well-structured pull request following best practices for description, testing, and review
arguments: []
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

## PR Description Generation

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
