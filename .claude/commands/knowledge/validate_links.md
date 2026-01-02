---
title: Validate Links
description: Validates all [[wiki links]] and #[[tag links]] in the Logseq repository to ensure they point to existing pages
tools: Read, Glob, Grep, Bash
---

# Validate Links Command

Validates all [[wiki links]] and #[[tag links]] in the Logseq repository to ensure they point to existing pages.

## Installation

The `logseq-validate-links` tool is part of the stapler-logseq-tools package. Ensure it's installed:

```bash
cd ~/Documents/personal-wiki
uv install -e .
```

This will make the `logseq-validate-links` command available in your environment.

## Usage

```bash
# Basic validation - shows broken links only
logseq-validate-links validate

# Validation with detailed output
logseq-validate-links validate --show-valid

# Create stub pages for missing links
logseq-validate-links validate --create-missing

# Quick check for missing links only
logseq-validate-links missing

# Show wiki statistics and analysis
logseq-validate-links stats
```

## Features

### Validation (`validate` command)
- Scans all `.md` files in `logseq/pages/` and `logseq/journals/`
- Extracts all `[[wiki links]]` and `#[[tag links]]`
- Reports broken links (links to non-existent pages)
- Shows which files contain broken links
- Option to auto-create stub pages for missing links
- Exits with error code if broken links found (useful for CI/CD)

### Missing Links (`missing` command)
- Quick scan to list all missing links
- Useful for getting a simple list of pages that need to be created
- Supports file pattern filtering

### Statistics (`stats` command)
- Overall wiki health metrics
- Total files, pages, unique links, and tags
- Most connected files (files with most outbound links)
- Missing link count

### Enhanced Connection Analysis (NEW)
**Integrate with `logseq-analyze connections` for deeper insights**:

```bash
# Run connection analysis for comprehensive link health
cd ~/Documents/personal-wiki
uv run logseq-analyze connections logseq/

# Provides:
# - Orphaned pages (no incoming links)
# - Poorly connected pages (< 3 total connections)
# - Hub pages (highly connected, > 10 links)
# - Average connections per page
# - Link distribution statistics
```

This goes beyond simple broken link detection to identify:
- **Isolated content** that needs integration
- **Important hubs** that may need expansion
- **Connection patterns** in your knowledge graph

## Command Line Options

### `validate` command:
- `--show-valid`: Include valid links in detailed output
- `--create-missing`: Automatically create stub pages for missing links
- `--exclude-tags`: Don't validate tag links (`#[[tags]]`)

### `missing` command:
- `--file-pattern`: File pattern to search (default: `*.md`)

## Example Output

```
🔗 Broken Links Found
┏━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Missing Page       ┃ Referenced In                ┃
┡━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ New Concept        │ 2025_09_08.md               │
│ Technical Topic    │ Some Page.md, Another.md    │
└────────────────────┴──────────────────────────────┘

📊 Link Validation Summary
┏━━━━━━━━━━━━━━━━┳━━━━━━━┓
┃ Metric         ┃ Count ┃
┡━━━━━━━━━━━━━━━━╇━━━━━━━┩
│ Total Pages    │   156 │
│ Files Validated│    89 │
│ Valid Links    │   423 │
│ Broken Links   │     2 │
│ Tag Links      │    78 │
└────────────────┴───────┘
```

## Integration with Development Workflow

### Pre-commit Hook
Add to `.git/hooks/pre-commit`:
```bash
#!/bin/bash
logseq-validate-links validate
if [ $? -eq 1 ]; then
    echo "❌ Commit blocked: Broken links found"
    echo "Run 'logseq-validate-links validate --create-missing' to fix"
    exit 1
fi
```

### CI/CD Integration
```yaml
# GitHub Actions example
- name: Validate Wiki Links
  run: |
    cd ~/Documents/personal-wiki
    uv run logseq-validate-links validate
```

### Daily Health Check
```bash
# Add to cron or scheduled task
logseq-validate-links stats > wiki_health_report.txt
```

## Stub Page Creation

When using `--create-missing`, the tool creates basic stub pages with this template:

```markdown
- **Core Definition**: [Page Name]

## Background/Context
- TODO: Add context and background information

## Key Characteristics/Principles
- TODO: Add key characteristics

## Related Concepts
- TODO: Add related concept links

## Significance
- TODO: Add significance and importance

**Related Topics**: #[[TODO]]
```

This ensures all links resolve while providing a structured template for future content development.

## Enhanced Workflow: Comprehensive Link Health Check

### Step 1: Traditional Link Validation
```bash
# Check for broken links
logseq-validate-links validate
```

### Step 2: Connection Analysis
```bash
# Analyze connection patterns
cd ~/Documents/personal-wiki
uv run logseq-analyze connections logseq/
```

### Step 3: Combined Insights
Merge results to identify:
- **Broken links** → Create stub pages or remove references
- **Orphaned pages** → Add incoming links from related content
- **Poorly connected** → Enhance with bidirectional links
- **Hub pages** → Consider splitting or expanding

### Step 4: Prioritized Actions
```bash
# Fix broken links first (critical)
logseq-validate-links validate --create-missing

# Then address orphaned pages (high priority)
# Review list from connection analysis and add links

# Finally, improve poorly connected pages (medium priority)
# Use synthesis to enhance content and connections
```

## Use Cases

1. **Before Publishing**: Ensure all references are valid
2. **After Major Edits**: Verify no links were broken during restructuring
3. **Content Planning**: Identify which concepts need dedicated pages
4. **Quality Assurance**: Regular health checks of knowledge base integrity
5. **Automated Validation**: Integration with CI/CD for continuous validation
6. **Knowledge Graph Health**: Use connection analysis to maintain a well-connected wiki
7. **Content Discovery**: Find isolated content that needs integration

## Fallback Strategy for Tool Availability Issues

If `logseq-validate-links` is not installed or not accessible:

### Manual Installation
```bash
cd ~/Documents/personal-wiki
uv install -e .
```

### Manual Link Validation
If the tool still doesn't work, perform manual validation using grep:

```bash
# Find all wiki links
cd ~/Documents/personal-wiki
grep -rho '\[\[.*\]\]' logseq/pages/ logseq/journals/ | sort -u > all_links.txt

# Find all existing pages
find logseq/pages -name "*.md" -exec basename {} .md \; | sort > all_pages.txt

# Compare to find broken links (requires manual review)
comm -23 all_links.txt all_pages.txt
```

### Read-Only Analysis Mode
If file modifications aren't possible:
1. Generate a report of broken links in markdown format
2. Provide stub page templates in code blocks
3. List exact file paths for manual creation
4. Prioritize links by frequency of reference