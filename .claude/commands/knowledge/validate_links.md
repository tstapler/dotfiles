---
title: Validate Links
description: Validates all [[wiki links]] and #[[tag links]] in the Logseq repository to ensure they point to existing pages
---

# Validate Links Command

Validates all [[wiki links]] and #[[tag links]] in the Logseq repository to ensure they point to existing pages.

## Usage

```bash
# Basic validation - shows broken links only
python validate_links.py validate

# Validation with detailed output
python validate_links.py validate --show-valid

# Create stub pages for missing links
python validate_links.py validate --create-missing

# Quick check for missing links only
python validate_links.py missing

# Show wiki statistics and analysis
python validate_links.py stats
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
python validate_links.py validate
if [ $? -eq 1 ]; then
    echo "❌ Commit blocked: Broken links found"
    echo "Run 'python validate_links.py validate --create-missing' to fix"
    exit 1
fi
```

### CI/CD Integration
```yaml
# GitHub Actions example
- name: Validate Wiki Links
  run: |
    cd wiki
    python validate_links.py validate
```

### Daily Health Check
```bash
# Add to cron or scheduled task
python validate_links.py stats > wiki_health_report.txt
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

## Use Cases

1. **Before Publishing**: Ensure all references are valid
2. **After Major Edits**: Verify no links were broken during restructuring
3. **Content Planning**: Identify which concepts need dedicated pages
4. **Quality Assurance**: Regular health checks of knowledge base integrity
5. **Automated Validation**: Integration with CI/CD for continuous validation