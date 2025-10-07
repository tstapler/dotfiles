---
title: Find Refactor Candidates
description: Identify files that are good candidates for refactoring using various metrics
arguments: [target_directory]
---

# Find Refactoring Candidates

I'll help you identify files that are prime candidates for refactoring in $1 (or the current directory if not specified) using various code quality metrics and patterns. I'll use shell commands to scan your codebase and provide actionable insights.

## Metrics to Identify Refactoring Candidates

I'll run the following analyses to find potential refactoring targets:

### 1. Code Complexity

```bash
# Find large files (potentially too many responsibilities)
find $1 -type f -name "*.py" -exec wc -l {} \; | sort -nr | head -20

# Count functions/methods per file (Python)
for file in $(find $1 -name "*.py"); do
  echo -n "$file: "
  grep -c "def " "$file"
done | sort -t: -k2 -nr | head -20

# Find complex functions (high cyclomatic complexity)
# Requires radon package: pip install radon
radon cc $1 -a -s
```

### 2. Change Frequency (Git History)

```bash
# Files modified most frequently (may need better design)
git log --pretty=format: --name-only | sort | uniq -c | sort -nr | head -20

# Files with most contributors (many hands = potential inconsistency)
git log --pretty=format: --name-only | sort | uniq -c | sort -nr | grep -v -e "/" | head -20

# Hot spots: files with most commits in last 90 days
git log --pretty=format: --name-only --since="90 days ago" | sort | uniq -c | sort -nr | head -20
```

### 3. Code Smells

```bash
# Long lines (readability issues)
find $1 -type f -name "*.py" -exec grep -l '.\{100,\}' {} \;

# Duplicate code fragments
# Requires pmd: https://pmd.github.io/
pmd cpd --minimum-tokens 100 --files $1 --language python

# TODO comments (technical debt indicators)
grep -r "TODO\|FIXME" $1 | wc -l

# Code with many nested conditionals (cognitive complexity)
grep -r -n -A 1 "if.*if.*if" $1
```

### 4. Static Analysis

```bash
# Run flake8 (Python linting)
# Requires flake8: pip install flake8
flake8 $1 --count --select=E9,F63,F7,F82 --show-source --statistics

# Run pylint (more comprehensive Python analysis)
# Requires pylint: pip install pylint
find $1 -name "*.py" | xargs pylint --output-format=text | grep -E "^[CREF]:"
```

### 5. Test Coverage

```bash
# Find files with low test coverage
# Requires coverage: pip install coverage
coverage run -m pytest
coverage report -m | sort -k 4 -nr | head -20
```

## Interpreting Results

I'll analyze the output from these commands and identify prime refactoring candidates based on:

1. **Complexity Hotspots**: Files with high cyclomatic complexity, many lines, or numerous functions
2. **Churn Rate**: Files that change frequently but may be poorly structured
3. **Technical Debt**: Files with many TODO/FIXME comments or linting errors
4. **Maintainability**: Files touched by many different developers over time
5. **Test Coverage**: Files with complex logic but inadequate test coverage

## Recommended Refactoring Approach

For each identified candidate, I'll suggest:
- Specific refactoring techniques appropriate for the issues found
- Architectural or design pattern improvements
- Test-driven approaches to ensure behavior preservation
- Incremental refactoring strategies to manage risk

## Additional Languages

While the examples above focus on Python, I can adapt the commands for other languages including:

- JavaScript/TypeScript
- Java
- C#
- Ruby
- Go
- Rust

Let me analyze your codebase to find the most promising refactoring candidates based on these metrics.