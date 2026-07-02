---
description: Identify files that are good candidates for refactoring using various metrics
---

# Find Refactoring Candidates

I'll help you identify files that are prime candidates for refactoring in $1 (or the current directory if not specified) using various code quality metrics and patterns. I'll use shell commands to scan your codebase and provide actionable insights.

## Metrics to Identify Refactoring Candidates

I'll run the following analyses to find potential refactoring targets:

### 1. Code Complexity

**Go** (if the target is a Go module — check for `go.mod` before falling back to the Python tools below):

```bash
# Find large files (potentially too many responsibilities)
find $1 -type f -name "*.go" -not -name "*_test.go" -exec wc -l {} \; | sort -nr | head -20

# Cyclomatic complexity per function
go install github.com/fzipp/gocyclo/cmd/gocyclo@latest
gocyclo -top 20 $1

# Cognitive complexity per function (often a better maintainability proxy than cyclomatic)
go install github.com/uudashr/gocognit/cmd/gocognit@latest
gocognit -top 20 $1

# Largest structs by field count, functions with the most parameters — ast-grep structural
# queries catch god-objects and primitive-obsession signals gocyclo/gocognit don't.
# See the code-hotspot-analysis skill for concrete sg patterns.
```

**Python**:

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

### 2. Change Frequency and Hotspot Scoring (Git History)

Raw commit-frequency-per-file (below) tells you *what* changes a lot, but not whether that churn is happening in complex, risky code or in a trivial file that just gets touched often for benign reasons. For a real signal, combine churn with complexity into a **hotspot score** (`commits × complexity`) and look at **co-change pairs** (files that change together across commits, regardless of whether they import each other) — this is CodeScene's actual technique, not just "sort files by commit count." See the `code-hotspot-analysis` skill for the full methodology (tool stack: `code-maat`, or a co-change script fallback) and run it before treating the raw frequency numbers below as conclusive.

```bash
# Files modified most frequently (may need better design) — a starting signal, not the final answer
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

1. **Hotspot Score** (the primary signal — see `code-hotspot-analysis`): complexity × churn, not either alone. A complex file nobody touches is low priority; a simple file that changes constantly is usually fine; a complex file that changes constantly is where bugs and slow PRs concentrate.
2. **Temporal Coupling**: file pairs that change together across commits despite no import relationship — often reveals a missing abstraction boundary that static analysis alone won't surface.
3. **Complexity Hotspots**: Files with high cyclomatic/cognitive complexity, many lines, or numerous functions — useful in isolation only when churn data isn't available.
4. **Technical Debt**: Files with many TODO/FIXME comments or linting errors
5. **Maintainability**: Files touched by many different developers over time — a codebase signal about code, not a metric for evaluating people
6. **Test Coverage**: Files with complex logic but inadequate test coverage

## Recommended Refactoring Approach

For each identified candidate, I'll suggest:
- Specific refactoring techniques appropriate for the issues found
- Architectural or design pattern improvements
- Test-driven approaches to ensure behavior preservation
- Incremental refactoring strategies to manage risk

## Additional Languages

Go and Python have concrete tooling above. For other languages, the same two-axis approach (complexity + churn, per `code-hotspot-analysis`) still applies — swap in the language's complexity tool and keep the git-history/hotspot-scoring commands as-is (they're language-agnostic):

- JavaScript/TypeScript: `eslint` complexity rules, or `plato`/`es6-plato` for a complexity report
- Java: `pmd`'s cyclomatic-complexity ruleset, or `checkstyle`
- C#: `Microsoft.CodeAnalysis.Metrics` / Visual Studio's built-in code metrics
- Ruby: `flog`/`flay` (flog for complexity, flay for duplication)
- Rust: `cargo-geiger` doesn't cover this; `rust-code-analysis` (Mozilla) has complexity metrics

Let me analyze your codebase to find the most promising refactoring candidates based on these metrics.

