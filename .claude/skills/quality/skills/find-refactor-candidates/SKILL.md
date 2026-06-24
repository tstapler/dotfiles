---
description: Identify files that are good candidates for refactoring using various
  metrics
prompt: "# Find Refactoring Candidates\n\nI'll help you identify files that are prime\
  \ candidates for refactoring in $1 (or the current directory if not specified) using\
  \ various code quality metrics and patterns. I'll use shell commands to scan your\
  \ codebase and provide actionable insights.\n\n## Metrics to Identify Refactoring\
  \ Candidates\n\nI'll run the following analyses to find potential refactoring targets:\n\
  \n### 1. Code Complexity\n\n```bash\n# Find large files (potentially too many responsibilities)\n\
  find $1 -type f -name \"*.py\" -exec wc -l {} \\; | sort -nr | head -20\n\n# Count\
  \ functions/methods per file (Python)\nfor file in $(find $1 -name \"*.py\"); do\n\
  \  echo -n \"$file: \"\n  grep -c \"def \" \"$file\"\ndone | sort -t: -k2 -nr |\
  \ head -20\n\n# Find complex functions (high cyclomatic complexity)\n# Requires\
  \ radon package: pip install radon\nradon cc $1 -a -s\n```\n\n### 2. Change Frequency\
  \ (Git History)\n\n```bash\n# Files modified most frequently (may need better design)\n\
  git log --pretty=format: --name-only | sort | uniq -c | sort -nr | head -20\n\n\
  # Files with most contributors (many hands = potential inconsistency)\ngit log --pretty=format:\
  \ --name-only | sort | uniq -c | sort -nr | grep -v -e \"/\" | head -20\n\n# Hot\
  \ spots: files with most commits in last 90 days\ngit log --pretty=format: --name-only\
  \ --since=\"90 days ago\" | sort | uniq -c | sort -nr | head -20\n```\n\n### 3.\
  \ Code Smells\n\n```bash\n# Long lines (readability issues)\nfind $1 -type f -name\
  \ \"*.py\" -exec grep -l '.\\{100,\\}' {} \\;\n\n# Duplicate code fragments\n# Requires\
  \ pmd: https://pmd.github.io/\npmd cpd --minimum-tokens 100 --files $1 --language\
  \ python\n\n# TODO comments (technical debt indicators)\ngrep -r \"TODO\\|FIXME\"\
  \ $1 | wc -l\n\n# Code with many nested conditionals (cognitive complexity)\ngrep\
  \ -r -n -A 1 \"if.*if.*if\" $1\n```\n\n### 4. Static Analysis\n\n```bash\n# Run\
  \ flake8 (Python linting)\n# Requires flake8: pip install flake8\nflake8 $1 --count\
  \ --select=E9,F63,F7,F82 --show-source --statistics\n\n# Run pylint (more comprehensive\
  \ Python analysis)\n# Requires pylint: pip install pylint\nfind $1 -name \"*.py\"\
  \ | xargs pylint --output-format=text | grep -E \"^[CREF]:\"\n```\n\n### 5. Test\
  \ Coverage\n\n```bash\n# Find files with low test coverage\n# Requires coverage:\
  \ pip install coverage\ncoverage run -m pytest\ncoverage report -m | sort -k 4 -nr\
  \ | head -20\n```\n\n## Interpreting Results\n\nI'll analyze the output from these\
  \ commands and identify prime refactoring candidates based on:\n\n1. **Complexity\
  \ Hotspots**: Files with high cyclomatic complexity, many lines, or numerous functions\n\
  2. **Churn Rate**: Files that change frequently but may be poorly structured\n3.\
  \ **Technical Debt**: Files with many TODO/FIXME comments or linting errors\n4.\
  \ **Maintainability**: Files touched by many different developers over time\n5.\
  \ **Test Coverage**: Files with complex logic but inadequate test coverage\n\n##\
  \ Recommended Refactoring Approach\n\nFor each identified candidate, I'll suggest:\n\
  - Specific refactoring techniques appropriate for the issues found\n- Architectural\
  \ or design pattern improvements\n- Test-driven approaches to ensure behavior preservation\n\
  - Incremental refactoring strategies to manage risk\n\n## Additional Languages\n\
  \nWhile the examples above focus on Python, I can adapt the commands for other languages\
  \ including:\n\n- JavaScript/TypeScript\n- Java\n- C#\n- Ruby\n- Go\n- Rust\n\n\
  Let me analyze your codebase to find the most promising refactoring candidates based\
  \ on these metrics.\n"
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
