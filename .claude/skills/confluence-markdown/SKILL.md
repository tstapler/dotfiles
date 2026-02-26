# Confluence Markdown Writing

Write Confluence-compatible markdown for publishing via markdown-confluence tool. Covers syntax, frontmatter, directory structure, and Confluence-specific features.

## When to Use This Skill

Use when:
- Creating new markdown files for Confluence publishing
- Documenting projects that will be synced to Confluence
- Need syntax reference for Confluence markdown features
- Setting up project structure for Confluence sync

## Confluence Markdown Syntax

### Frontmatter

Every Confluence-synced markdown file uses YAML frontmatter:

```yaml
---
connie-page-id: '1234567890'              # Confluence page ID (auto-assigned after first publish)
connie-last-sync-timestamp: '2026-02-20T...'  # Last sync time (auto-updated)
connie-last-remote-version: 2              # Confluence version number (auto-tracked)
---
```

**Important**:
- Frontmatter is auto-generated on first publish
- Don't manually edit `connie-*` fields unless you know what you're doing
- Empty frontmatter (`---\n---`) is fine for new files

### Headings

```markdown
# Page Title

## Section Heading (H2)

### Subsection (H3)

#### Sub-subsection (H4)
```

**Best Practices**:
- Use **only one H1** (`#`) - it becomes the Confluence page title
- The H1 will NOT appear in the body (automatically removed to prevent duplication)
- Start body content with H2 (`##`)

### Table of Contents

```markdown
[TOC]
```

**Features**:
- Place `[TOC]` on its own line where you want the table of contents
- Automatically generates Confluence TOC macro
- Shows all headings (H2-H6) in the document
- Auto-updates when headings change

**Example**:
```markdown
# Project Documentation

**Last Updated**: 2026-02-20

[TOC]

## Overview
Content here...

## Architecture
More content...
```

### Links

#### Internal Links (to other Confluence pages)
```markdown
[[Page Title]]               # Link to another page in wiki
[[Custom Text|Page Title]]   # Link with custom text
```

**Note**: The markdown-confluence tool will resolve these to Confluence page links.

#### External Links
```markdown
[Link Text](https://example.com)
[Google](https://google.com)
```

#### Relative Links (within project)
```markdown
[Other Doc](./other-doc.md)
[Sibling Doc](../sibling/doc.md)
```

**Note**: Relative links are resolved during sync. The target file must also be published to Confluence.

### Images

```markdown
![Alt Text](./images/diagram.png)
![Screenshot](../assets/screenshot.png)
![External](https://example.com/image.png)
```

**Best Practices**:
- Store images in `images/` or `assets/` subdirectory
- Use relative paths
- External URLs work but images won't be uploaded to Confluence

### Code Blocks

````markdown
```python
def hello():
    print("Hello, Confluence!")
```

```javascript
const greeting = "Hello, Confluence!";
console.log(greeting);
```
````

**Supported Languages**: python, javascript, typescript, java, go, rust, bash, shell, sql, yaml, json, xml, html, css, markdown

### Tables

```markdown
| Header 1 | Header 2 | Header 3 |
|----------|----------|----------|
| Cell 1   | Cell 2   | Cell 3   |
| Cell 4   | Cell 5   | Cell 6   |
```

**Alignment**:
```markdown
| Left | Center | Right |
|:-----|:------:|------:|
| L1   | C1     | R1    |
| L2   | C2     | R2    |
```

### Lists

**Unordered**:
```markdown
- Item 1
- Item 2
  - Nested item
  - Another nested
- Item 3
```

**Ordered**:
```markdown
1. First item
2. Second item
   1. Nested numbered
   2. Another nested
3. Third item
```

**Task Lists**:
```markdown
- [ ] Incomplete task
- [x] Completed task
- [ ] Another task
```

### Emphasis

```markdown
**Bold text**
*Italic text*
***Bold and italic***
~~Strikethrough~~
`Inline code`
```

### Blockquotes

```markdown
> This is a blockquote.
> It can span multiple lines.

> **Note**: Use blockquotes for callouts or important notes.
```

### Horizontal Rules

```markdown
---
```

Use `---` on its own line for a horizontal divider.

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

Create `README.md`:
```markdown
---
---

# My Project

[TOC]

## Overview
This is my project documentation.

## Architecture
Details about the architecture.
```

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

## Best Practices

### 1. Document Structure

✅ **Do**:
- Use one H1 for the page title
- Start body content with H2
- Add `[TOC]` after metadata for long documents
- Keep related docs in subdirectories
- Use descriptive filenames (becomes page title)

❌ **Don't**:
- Use multiple H1 headings (only first is used as title)
- Put content before the H1 (it will be lost)
- Manually edit `connie-*` frontmatter fields

### 2. Linking

✅ **Do**:
- Use relative links for project-internal docs
- Link to other published pages with `[[Page Title]]`
- Verify target files are also published

❌ **Don't**:
- Use absolute paths (won't work after sync)
- Link to unpublished files

### 3. Images

✅ **Do**:
- Store images in `images/` or `assets/` subdirectory
- Use relative paths from the markdown file
- Keep image files small (<2MB)

❌ **Don't**:
- Use absolute paths to local images
- Reference images outside the project

### 4. Page Hierarchy

✅ **Do**:
- Use directory structure to organize pages
- Set `parentPageId` in config for proper hierarchy
- Keep related docs together

❌ **Don't**:
- Create flat structure for large projects
- Forget to configure parent page

---

## Troubleshooting

### Page Title Appearing Twice

**Fixed** ✅ - The tool now automatically removes duplicate H1 headings that match the page title.

### TOC Not Appearing

- Verify `[TOC]` is on its own line
- Check that it's a paragraph, not inside a code block or list

### Images Not Uploading

- Verify image paths are relative
- Check that images are in the project directory
- Ensure file extensions are correct (.png, .jpg, .gif, .svg)

### Links Broken After Sync

- Verify target files are also published to Confluence
- Use relative links, not absolute paths
- Check that `[[Page Title]]` matches actual page title

---

## Examples

### Simple Project Page

```markdown
---
---

# Project Name

**Status**: Active
**Owner**: Tyler Stapler
**Last Updated**: 2026-02-20

[TOC]

## Overview

Brief description of the project.

## Architecture

![Architecture Diagram](./images/architecture.png)

Key components:
- Component A
- Component B
- Component C

## Getting Started

1. Clone the repository
2. Install dependencies
3. Run the application

```bash
npm install
npm start
```

## Related Documents

- [[API Documentation]]
- [[Deployment Guide]]
```

### Requirements Document

```markdown
---
---

# Requirements Document

**Project**: IDP Evaluation
**Date**: 2026-02-20

[TOC]

## Use Case 1: Developer Surveys

### Problem Statement
Description of the problem...

### Requirements

#### Must Have
- Requirement 1
- Requirement 2

#### Nice to Have
- Optional feature 1
- Optional feature 2

### Success Criteria
- Metric 1: Target value
- Metric 2: Target value

---

## Use Case 2: AI Monitoring

[Continue with next use case...]
```

---

## Related Skills

- `markdown-confluence-sync`: Publish, crawl, and manage Confluence pages
- `knowledge-synthesis`: Create Zettelkasten notes for Logseq

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
