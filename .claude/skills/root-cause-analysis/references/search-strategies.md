# Advanced Search Strategies for Logseq

Patterns for effectively searching the personal-wiki knowledge base at `~/Documents/personal-wiki`.

## Logseq Structure Overview

```
~/Documents/personal-wiki/logseq/
  journals/
    YYYY_MM_DD.md     # Daily entries, incident notes, debugging sessions
  pages/
    *.md              # Zettelkasten notes, technology docs, incident postmortems
```

## Search Priority Order

1. **Exact error message** - Often documented verbatim
2. **Service/component name** - Links to related issues
3. **Technology + problem** - General patterns
4. **Time-based** - Recent journals most relevant
5. **Tag-based** - Incident/debugging classifications

## Grep Patterns

### Basic Error Search

```bash
# Exact error type
Grep pattern="NullPointerException" path="~/Documents/personal-wiki/logseq/" output_mode="content" -C 3

# Error with context (case insensitive)
Grep pattern="connection refused" path="~/Documents/personal-wiki/logseq/" -i output_mode="content" -C 5

# Multiple error types
Grep pattern="OOMKilled|OutOfMemory|memory pressure" path="~/Documents/personal-wiki/logseq/" -i
```

### Service-Specific Search

```bash
# Service name in context
Grep pattern="UserService.*(error|exception|failed)" path="~/Documents/personal-wiki/logseq/" -i

# Service with specific issue
Grep pattern="ats-sportsbook.*(timeout|crash|oom)" path="~/Documents/personal-wiki/logseq/" -i
```

### Wiki Link Search

```bash
# Find pages linking to concept
Grep pattern="\\[\\[Kubernetes\\]\\]" path="~/Documents/personal-wiki/logseq/"

# Find incident-tagged content
Grep pattern="#\\[\\[incident\\]\\]|#\\[\\[debugging\\]\\]" path="~/Documents/personal-wiki/logseq/"

# Find related concepts
Grep pattern="\\[\\[PostgreSQL\\]\\].*deadlock|deadlock.*\\[\\[PostgreSQL\\]\\]" path="~/Documents/personal-wiki/logseq/"
```

### Stack Trace Patterns

```bash
# Java stack trace
Grep pattern="at [a-z]+\\.[a-zA-Z]+\\.[A-Z]" path="~/Documents/personal-wiki/logseq/"

# Python traceback
Grep pattern="File \".*\", line [0-9]+" path="~/Documents/personal-wiki/logseq/"

# Exception chain
Grep pattern="Caused by:|Traceback" path="~/Documents/personal-wiki/logseq/" output_mode="content" -A 10
```

## Glob Patterns

### Time-Based Filtering

```bash
# Current month journals
Glob pattern="~/Documents/personal-wiki/logseq/journals/2026_01_*.md"

# Last week (adjust dates)
Glob pattern="~/Documents/personal-wiki/logseq/journals/2026_01_{21..28}.md"

# Specific quarter
Glob pattern="~/Documents/personal-wiki/logseq/journals/2026_0{1..3}_*.md"
```

### Topic-Based Filtering

```bash
# Technology pages
Glob pattern="~/Documents/personal-wiki/logseq/pages/*Kubernetes*.md"
Glob pattern="~/Documents/personal-wiki/logseq/pages/*Java*.md"
Glob pattern="~/Documents/personal-wiki/logseq/pages/*PostgreSQL*.md"

# Incident pages
Glob pattern="~/Documents/personal-wiki/logseq/pages/*Incident*.md"
Glob pattern="~/Documents/personal-wiki/logseq/pages/*Outage*.md"
Glob pattern="~/Documents/personal-wiki/logseq/pages/*Postmortem*.md"

# How-to guides
Glob pattern="~/Documents/personal-wiki/logseq/pages/How-To*.md"
```

## Multi-Stage Search Strategy

### Stage 1: Broad Discovery

```bash
# Find all files mentioning the error
Grep pattern="[error signature]" path="~/Documents/personal-wiki/logseq/" output_mode="files_with_matches"
```

### Stage 2: Context Extraction

```bash
# Get context from discovered files
Grep pattern="[error signature]" path="~/Documents/personal-wiki/logseq/" output_mode="content" -C 10
```

### Stage 3: Related Content

```bash
# Find pages linked from discovered content
# (After finding [[Related Page]] links in Stage 2)
Read file_path="~/Documents/personal-wiki/logseq/pages/Related Page.md"
```

### Stage 4: Temporal Context

```bash
# Find journal entries around incident date
# If incident was on 2026-01-15:
Glob pattern="~/Documents/personal-wiki/logseq/journals/2026_01_{13..17}.md"
```

## Search Result Interpretation

### High-Value Indicators

- `#[[incident]]` or `#[[debugging]]` tags
- "Root cause:" or "Solution:" phrases
- Links to external issue trackers
- Code snippets with fix comments
- "Caused by" explanations

### Context Clues

```
Look for patterns like:
- "Fixed by..." - Direct solution
- "Related to [[X]]" - Connected issues
- "See also:" - Additional context
- "Update:" or "Resolution:" - Evolution of understanding
```

## Combining Search Results

### Cross-Reference Pattern

```
1. Search error message -> Find incident page
2. Read incident page -> Find related service pages
3. Read service pages -> Find configuration details
4. Search configuration -> Find historical changes
```

### Evidence Accumulation

```markdown
## Evidence Log

### Wiki Findings
1. [Date] logseq/journals/YYYY_MM_DD.md - [Summary]
2. [Date] logseq/pages/ServiceName.md - [Summary]

### Pattern Recognition
- Same error seen: [N] times
- Common context: [Pattern]
- Previous resolution: [Action]
```

## Performance Tips

### Narrow Before Broad

```bash
# Start specific
Grep pattern="exact error message" path="~/Documents/personal-wiki/logseq/pages"

# Then broaden if needed
Grep pattern="error type" path="~/Documents/personal-wiki/logseq/"
```

### Use Files Mode First

```bash
# Find relevant files
Grep pattern="[term]" output_mode="files_with_matches" head_limit=10

# Then get content from specific files
Grep pattern="[term]" path="specific/file.md" output_mode="content"
```

### Limit Output

```bash
# Prevent context overload
Grep pattern="[term]" head_limit=20 output_mode="content" -C 3
```

## Common Search Failures and Fixes

| Failure | Cause | Fix |
|---------|-------|-----|
| No results | Too specific | Broaden pattern, remove qualifiers |
| Too many results | Too broad | Add service name, date range |
| Wrong results | Ambiguous term | Add context words, use exact phrase |
| Missing context | Files mode only | Switch to content mode with -C |
