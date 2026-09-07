# Confluence Markdown Writing

Write Confluence-compatible markdown for publishing via markdown-confluence tool. Covers syntax, frontmatter, directory structure, and Confluence-specific features.

## When to Use This Skill

Use when:
- Creating new markdown files for Confluence publishing
- Documenting projects that will be synced to Confluence
- Need syntax reference for Confluence markdown features
- Setting up project structure for Confluence sync

## Confluence Markdown Syntax — Quick Guide

Every synced file has YAML frontmatter (auto-generated on first publish; don't hand-edit `connie-*` fields). Use exactly **one H1** — it becomes the page title and is stripped from the body — then start content at H2. Add `[TOC]` on its own line for an auto-updating table of contents. Standard GFM otherwise: headings, tables, ordered/unordered/task lists, code fences (python/javascript/typescript/java/go/rust/bash/sql/yaml/json/xml/html/css/markdown), emphasis, blockquotes, `---` horizontal rules, and images (relative paths, `images/`/`assets/` subdirectory, <2MB).

Links come in three forms: `[[Page Title]]` / `[[Custom Text|Page Title]]` for other Confluence pages (must also be published), `[text](https://...)` for external URLs, and `[text](./relative.md)` for project-internal docs (resolved during sync — the target must be published too).

Full syntax with examples for every element above: [Syntax Reference](references/syntax-reference.md).

---

## Directory Structure

### Project Layout for Confluence Sync

```
project-name/
├── .confluence-config.json      # Sync configuration
├── README.md                    # Main project page (parent)
├── architecture.md              # Child page
├── requirements.md              # Child page
├── vendors/
│   ├── vendor-a.md             # Child page under vendors/
│   └── vendor-b.md             # Child page under vendors/
└── images/
    ├── diagram.png
    └── screenshot.png
```

### Configuration File

`.confluence-config.json`:
```json
{
  "confluenceBaseUrl": "https://yourorg.atlassian.net",
  "parentPageId": "1234567890",
  "spaceKey": "~accountid",
  "pageTitle": "Project Name",
  "syncEnabled": true,
  "excludePatterns": [
    ".confluence-config.json",
    ".git",
    "*.pyc",
    "__pycache__"
  ]
}
```

**Fields**:
- `parentPageId`: ID of the Confluence page that will be the parent
- `spaceKey`: Confluence space key (e.g., `~630044b443e43992b9a3e6f2` for personal space)
- `pageTitle`: Title for the root page created from README.md

---

## Publishing Workflow

### 1. Create Project Structure

```bash
mkdir my-project
cd my-project

# Create .confluence-config.json
cat > .confluence-config.json <<EOF
{
  "confluenceBaseUrl": "https://betfanatics.atlassian.net",
  "parentPageId": "1394901392",
  "spaceKey": "~630044b443e63992b9a3e6f2"
}
EOF
```

### 2. Write Markdown Files

Create `README.md` with empty frontmatter (`---\n---`), one H1, `[TOC]`, and H2 sections — see [Syntax Reference](references/syntax-reference.md) for the full element list, or [Examples](references/examples-and-troubleshooting.md) for two complete worked pages.

### 3. Publish to Confluence

```bash
# Set environment variables
export CONFLUENCE_BASE_URL="https://betfanatics.atlassian.net"
export ATLASSIAN_USER_NAME="tyler.stapler@betfanatics.com"
export CONFLUENCE_PARENT_ID="1394901392"

# Publish
markdown-confluence publish README.md --verbose
```

### 4. Sync Updates

After making changes:
```bash
markdown-confluence publish README.md --verbose
```

The tool automatically:
- Detects existing page via `connie-page-id` in frontmatter
- Updates the page instead of creating a new one
- Maintains page hierarchy

---

## Best Practices (Summary)

- **One H1 per file**, content starts at H2, don't hand-edit `connie-*` frontmatter fields
- **Relative links only** — absolute paths break after sync; link targets must also be published
- **Images in `images/`/`assets/`**, relative paths, kept under 2MB
- **Directory structure mirrors page hierarchy** — set `parentPageId` in config, avoid a flat layout for large projects

Full do/don't lists per category, plus troubleshooting (duplicate page titles, missing TOC, failed image uploads, broken links after sync), are in [Examples and Troubleshooting](references/examples-and-troubleshooting.md).

---

## Related Skills

| Skill | When to apply |
|-------|--------------|
| `knowledge-confluence-sync` | Publish, crawl, and manage Confluence pages programmatically |
| `knowledge-synthesis` | Create Zettelkasten notes for Logseq from the same knowledge sources |
| `mermaid-diagrams` | Author diagrams to embed in Confluence pages as code blocks |

## Tool Location

**Binary**: `/Users/tylerstapler/Documents/personal-wiki/tools/markdown_confluence/.venv/bin/markdown-confluence`

**Source**: `/Users/tylerstapler/Documents/personal-wiki/tools/markdown_confluence/`

## Common Commands

```bash
# Publish single file
markdown-confluence publish <file.md> --verbose

# Publish with parent page
CONFLUENCE_PARENT_ID="123456" markdown-confluence publish <file.md>

# Crawl Confluence page to markdown
markdown-confluence crawl page <page-id> --output <dir>

# Check sync status
markdown-confluence status

# Validate links
markdown-confluence validate-links
```

## References

- [Syntax Reference](references/syntax-reference.md) — full markdown syntax with examples (frontmatter, headings, TOC, links, images, code blocks, tables, lists, emphasis)
- [Examples and Troubleshooting](references/examples-and-troubleshooting.md) — detailed do/don't lists, troubleshooting, and two full worked example pages
