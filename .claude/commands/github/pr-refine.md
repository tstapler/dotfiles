---
title: PR Refine
description: Review a pull request and suggest refinement options, then document them as a structured feature plan
arguments: [pr_url_or_number]
---

# Pull Request Refinement & Planning

Review an existing pull request, suggest comprehensive refinement options, and create a structured feature plan for improvements using industry best practices.

## Prerequisites Check

First, I'll verify prerequisites and gather PR information:

```bash
# Check GitHub CLI availability
gh --version

# Verify authentication
gh auth status

# Get repository context
git remote -v
git branch --show-current
```

## Step 1: PR Analysis

I'll analyze the pull request to understand current state:

```bash
# Extract PR number from URL or use directly
PR_NUMBER="${1:-}"

# If URL provided, extract PR number
if [[ "$PR_NUMBER" == *"github.com"* ]]; then
  PR_NUMBER=$(echo "$PR_NUMBER" | grep -oE '[0-9]+$')
fi

# Get PR details
gh pr view $PR_NUMBER --json title,body,state,author,createdAt,updatedAt,labels,milestone,reviewRequests,reviews,statusCheckRollup,comments,commits,files,additions,deletions,changedFiles

# Get PR diff
gh pr diff $PR_NUMBER

# Get PR files changed
gh pr view $PR_NUMBER --json files --jq '.files[].path'

# Get commit history
gh pr view $PR_NUMBER --json commits --jq '.commits[].commit.message'

# Get review comments
gh api repos/{owner}/{repo}/pulls/$PR_NUMBER/comments

# Get PR checks status
gh pr checks $PR_NUMBER
```

## Step 2: Multi-Dimensional Review

I'll perform a comprehensive review across multiple dimensions:

### Size & Scope Analysis
**Research-backed guidelines:**
- **Ideal PR size**: 50-200 lines of code
- **Maximum recommended**: 250 lines
- **Review effectiveness**: 200-400 LOC yields 70-90% defect discovery
- **Review time**: PRs over 400 lines take 50% longer to review per line

I'll analyze:
- Total lines changed
- Number of files modified
- Scope of changes (feature, bug fix, refactor)
- Opportunities to split into smaller PRs

### Code Quality Assessment
- **Design patterns**: Appropriate usage and opportunities
- **SOLID principles**: Adherence and violations
- **Clean Code**: Naming, readability, maintainability
- **DRY violations**: Code duplication
- **Complexity**: Cyclomatic complexity, cognitive load
- **Error handling**: Comprehensive and appropriate
- **Security**: OWASP top 10 considerations

### Testing Coverage
- **Test presence**: Are all changes tested?
- **Test quality**: Unit vs integration appropriateness
- **Test patterns**: Following testing best practices
- **Coverage metrics**: Line, branch, and path coverage
- **Edge cases**: Boundary conditions handled
- **Test maintainability**: Avoiding fragile tests

### Documentation Quality
- **PR description**: Following template best practices
- **Code comments**: Necessary and helpful
- **API documentation**: Updated for public interfaces
- **README updates**: Reflecting new features/changes
- **Migration guides**: For breaking changes
- **Architecture decisions**: ADRs for significant choices

### Commit Structure
- **Conventional Commits**: Format compliance
- **Logical commits**: One concern per commit
- **Commit size**: Atomic, reviewable units
- **Commit messages**: Clear and descriptive
- **History cleanliness**: No merge commits, clean rebase

### Performance Considerations
- **Algorithm efficiency**: O(n) analysis
- **Database queries**: N+1 problems, index usage
- **Memory usage**: Leaks, unnecessary allocations
- **Caching opportunities**: Reducing redundant work
- **Async operations**: Proper concurrency handling

### Architecture Alignment
- **Pattern consistency**: Following project patterns
- **Layer separation**: Clean boundaries
- **Dependency direction**: Following architecture rules
- **Module cohesion**: Single responsibility
- **Technical debt**: New vs addressed

## Step 3: Generate Refinement Suggestions

Based on the analysis, I'll create categorized refinement suggestions:

### Critical Refinements (Must Fix)
Issues that block merge or create significant problems:
- Security vulnerabilities
- Breaking changes without migration path
- Failing tests or broken CI
- Performance regressions
- Data loss risks

### High Priority Improvements
Significant quality improvements:
- Missing test coverage for critical paths
- SOLID principle violations
- Complex code needing simplification
- Inadequate error handling
- Documentation gaps for public APIs

### Medium Priority Enhancements
Good improvements for maintainability:
- Code duplication removal
- Better naming conventions
- Additional edge case tests
- Performance optimizations
- Comment improvements

### Low Priority Polish
Nice-to-have refinements:
- Style consistency
- Additional documentation
- Refactoring opportunities
- Test improvements
- Code organization

## Step 4: PR Splitting Strategy

If the PR is too large, I'll suggest how to split it:

### Vertical Slicing (Preferred)
Split by complete features/fixes:
1. **Infrastructure changes** - Database, config, dependencies
2. **Core implementation** - Business logic, main feature
3. **UI/API changes** - Frontend, endpoints
4. **Tests** - Comprehensive test suite
5. **Documentation** - Guides, API docs

### Horizontal Slicing (When Necessary)
Split by technical layers:
1. **Data layer** - Models, migrations, repositories
2. **Business layer** - Services, domain logic
3. **Presentation layer** - Controllers, views
4. **Cross-cutting** - Logging, security, caching

### Commit-Based Splitting
If commits are well-structured:
1. Cherry-pick logical commit groups
2. Create focused PRs from commit sets
3. Maintain commit message quality
4. Preserve logical progression

## Step 5: Create Feature Plan

I'll use the `/plan:feature` command to document the refinement plan:

```
/plan:feature PR-$PR_NUMBER Refinement Plan:

## Current State
- PR #$PR_NUMBER: [Title]
- Author: [Author]
- Size: [Lines changed] lines across [Files] files
- Purpose: [Extracted from PR description]

## Refinement Objectives
1. [Objective 1 - e.g., Improve test coverage]
2. [Objective 2 - e.g., Split into smaller PRs]
3. [Objective 3 - e.g., Address code quality issues]

## Critical Issues to Address
[List of must-fix issues identified]

## Improvement Opportunities
[List of enhancement suggestions]

## Proposed PR Structure (if splitting)
1. PR 1: [Description] - [Estimated LOC]
2. PR 2: [Description] - [Estimated LOC]
3. PR 3: [Description] - [Estimated LOC]

## Implementation Plan
[Detailed steps to implement refinements]

## Success Criteria
- All critical issues resolved
- Test coverage meets project standards
- PR size within recommended limits
- Clear documentation and commit structure
- Passing CI/CD checks
```

## Step 6: Generate Actionable Report

I'll create a comprehensive refinement report:

```markdown
# Pull Request Refinement Report

**PR**: #$PR_NUMBER - [Title]
**Author**: [Author]
**Review Date**: [Current date]
**Current Status**: [Status and checks]

---

## Executive Summary

**Overall Assessment**: [Good/Needs Work/Requires Major Changes]
**Estimated Refinement Effort**: [Hours/Days]
**Recommendation**: [Approve/Request Changes/Split PR]

### Key Metrics
- **Size**: [LOC] lines ([Above/Within/Below] recommended)
- **Test Coverage**: [%] ([Adequate/Insufficient])
- **Code Quality**: [Score/10]
- **Documentation**: [Complete/Partial/Missing]

---

## Detailed Findings

### 🔴 Critical Issues (Block Merge)
1. **[Issue Title]**
   - Location: `file:line`
   - Description: [What's wrong]
   - Impact: [Why it matters]
   - Fix: [How to resolve]
   - Effort: [Small/Medium/Large]

### 🟡 High Priority Improvements
1. **[Improvement Title]**
   - Location: `file:line`
   - Current: [Current state]
   - Suggested: [Better approach]
   - Benefit: [Why improve]
   - Effort: [Small/Medium/Large]

### 🟢 Medium Priority Enhancements
[List of good-to-have improvements]

### 🔵 Low Priority Polish
[List of nice-to-have refinements]

---

## PR Restructuring Recommendation

### Current Structure Problems
- [Problem 1 - e.g., Too many concerns in single PR]
- [Problem 2 - e.g., Mixing features with refactoring]
- [Problem 3 - e.g., Difficult to review effectively]

### Proposed Split Strategy
**PR 1: [Infrastructure/Foundation]**
- Files: [List of files]
- Purpose: [What it accomplishes]
- Size: ~[LOC] lines
- Dependencies: None

**PR 2: [Core Implementation]**
- Files: [List of files]
- Purpose: [What it accomplishes]
- Size: ~[LOC] lines
- Dependencies: PR 1

**PR 3: [Tests & Documentation]**
- Files: [List of files]
- Purpose: [What it accomplishes]
- Size: ~[LOC] lines
- Dependencies: PR 1, PR 2

---

## Implementation Checklist

### Before Refining
- [ ] Discuss plan with PR author
- [ ] Agree on split strategy
- [ ] Backup current branch
- [ ] Create feature branches

### During Refinement
- [ ] Address critical issues
- [ ] Implement high priority improvements
- [ ] Split PR if needed
- [ ] Update tests
- [ ] Update documentation
- [ ] Verify CI passes

### After Refinement
- [ ] Self-review changes
- [ ] Update PR descriptions
- [ ] Request re-review
- [ ] Verify all checks pass
- [ ] Update related issues

---

## Commit Message Templates

### For Fixes
```
fix: [description of fix]

- Addresses review comment about [issue]
- Fixes [specific problem]
- Improves [aspect]

Refs: #$PR_NUMBER
```

### For Improvements
```
refactor: [description of improvement]

- Simplifies [complex code]
- Improves [readability/performance]
- Follows [pattern/principle]

Refs: #$PR_NUMBER
```

### For Splits
```
feat: [feature part 1/3] - [description]

Extracted from #$PR_NUMBER as part of PR split strategy.
This PR contains [what's included].

Part of: #[epic/issue]
Next: #[next PR number]
```

---

## Success Metrics

### Review Efficiency
- **Target review time**: < 60 minutes
- **Review cycles**: 1-2 maximum
- **Time to merge**: < 24 hours after approval

### Code Quality
- **Test coverage**: > 80%
- **Complexity**: < 10 cyclomatic
- **Duplication**: < 3%
- **Security**: No critical vulnerabilities

### PR Health
- **Size**: 50-200 lines ideal
- **Files changed**: < 10 files
- **Clear purpose**: Single responsibility
- **Clean history**: Logical commits

---

## Next Steps

1. **Immediate Actions**
   - [Action 1 with owner]
   - [Action 2 with timeline]

2. **Follow-up Tasks**
   - [Task 1 for tracking]
   - [Task 2 for future]

3. **Long-term Improvements**
   - [Process improvement 1]
   - [Team learning opportunity]

---

## References

- [GitHub PR Best Practices](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/getting-started/best-practices-for-pull-requests)
- [Conventional Commits](https://www.conventionalcommits.org)
- [Clean Code Principles](https://github.com/ryanmcdermott/clean-code-javascript)
- Project ADRs: [List relevant ADRs]
```

## Step 7: Track with Project Coordinator

After generating the refinement plan, I'll delegate tracking to the project coordinator:

```
@task project-coordinator

Track the following PR refinement tasks for PR #$PR_NUMBER:

[Insert refinement plan and checklist]

Please:
1. Create ATOMIC tasks for each refinement item
2. Organize by priority (Critical → Low)
3. Group related improvements for efficiency
4. Estimate effort for each task
5. Create a tracking structure in TODO.md
6. Define success criteria for PR approval
```

## Error Handling

### If PR Not Found
- Verify PR number/URL is correct
- Check repository context
- Ensure proper GitHub authentication

### If Analysis Fails
- Check GitHub API limits
- Verify repository permissions
- Ensure PR is accessible

### If Too Complex
- Focus on highest-impact improvements
- Suggest incremental refinement approach
- Prioritize critical issues first

## Integration with Other Commands

This command works well with:
- `/git:create-pr` - Creating refined PRs after split
- `/code:review` - Detailed code quality analysis
- `/plan:feature` - Comprehensive planning documentation
- `/quality:architecture-review` - Deep design analysis
- `/code:refactor` - Implementing suggested improvements

## Success Criteria

This command succeeds when:
✅ PR is thoroughly analyzed across all dimensions
✅ Clear, prioritized refinement suggestions provided
✅ Actionable implementation plan created
✅ Feature plan documented for tracking
✅ Author has clear next steps
✅ Review efficiency is improved

## Best Practices Applied

✅ **GitHub Best Practices** - Optimal PR size and structure
✅ **Conventional Commits** - Clean commit history
✅ **Code Review Research** - Evidence-based size recommendations
✅ **Testing Pyramid** - Appropriate test coverage
✅ **Clean Code** - Maintainability focus
✅ **SOLID Principles** - Design quality
✅ **Security First** - OWASP considerations
✅ **Documentation** - Comprehensive and clear

---

Let me analyze PR #$1 and provide comprehensive refinement suggestions!