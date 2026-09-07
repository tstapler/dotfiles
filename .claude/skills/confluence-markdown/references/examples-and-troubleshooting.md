# Full Examples and Troubleshooting

## Best Practices (Detailed)

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
