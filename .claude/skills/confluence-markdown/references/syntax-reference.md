# Confluence Markdown Syntax Reference

## Frontmatter

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

## Headings

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

## Table of Contents

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

## Links

### Internal Links (to other Confluence pages)
```markdown
[[Page Title]]               # Link to another page in wiki
[[Custom Text|Page Title]]   # Link with custom text
```

**Note**: The markdown-confluence tool will resolve these to Confluence page links.

### External Links
```markdown
[Link Text](https://example.com)
[Google](https://google.com)
```

### Relative Links (within project)
```markdown
[Other Doc](./other-doc.md)
[Sibling Doc](../sibling/doc.md)
```

**Note**: Relative links are resolved during sync. The target file must also be published to Confluence.

## Images

```markdown
![Alt Text](./images/diagram.png)
![Screenshot](../assets/screenshot.png)
![External](https://example.com/image.png)
```

**Best Practices**:
- Store images in `images/` or `assets/` subdirectory
- Use relative paths
- External URLs work but images won't be uploaded to Confluence

## Code Blocks

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

## Tables

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

## Lists

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

## Emphasis

```markdown
**Bold text**
*Italic text*
***Bold and italic***
~~Strikethrough~~
`Inline code`
```

## Blockquotes

```markdown
> This is a blockquote.
> It can span multiple lines.

> **Note**: Use blockquotes for callouts or important notes.
```

## Horizontal Rules

```markdown
---
```

Use `---` on its own line for a horizontal divider.
