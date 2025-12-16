# Markdown Confluence Examples

## Example 1: New Project Publishing

### Step 1: Create Project Structure

```
my-project/
├── .markdown-confluence.json
├── README.md
├── overview/
│   ├── introduction.md
│   └── architecture.md
└── guides/
    ├── getting-started.md
    └── troubleshooting.md
```

### Step 2: Create Config File

`.markdown-confluence.json`:
```json
{
  "confluence": {
    "base_url": "https://betfanatics.atlassian.net",
    "parent_id": "1394901392",
    "username": "tyler.stapler@betfanatics.com"
  },
  "publish": {
    "folder_to_publish": ".",
    "frontmatter_from_document_start": true,
    "resolve_relative_links": true,
    "respect_link_dependencies": true
  }
}
```

### Step 3: Add Frontmatter to Files

`README.md`:
```markdown
---
connie-title: "My Project Documentation"
---

# My Project

Welcome to my project documentation.

See [Introduction](./overview/introduction.md) for details.
```

### Step 4: Dry Run

```bash
CONFLUENCE_BASE_URL="https://betfanatics.atlassian.net" \
ATLASSIAN_USER_NAME="tyler.stapler@betfanatics.com" \
/Users/tylerstapler/Documents/personal-wiki/tools/markdown_confluence/.venv/bin/markdown-confluence \
publish . --config .markdown-confluence.json --dry-run --verbose
```

### Step 5: Publish

```bash
CONFLUENCE_BASE_URL="https://betfanatics.atlassian.net" \
ATLASSIAN_USER_NAME="tyler.stapler@betfanatics.com" \
/Users/tylerstapler/Documents/personal-wiki/tools/markdown_confluence/.venv/bin/markdown-confluence \
publish . --config .markdown-confluence.json --verbose
```

After publishing, frontmatter is updated with page IDs:
```markdown
---
connie-title: "My Project Documentation"
connie-page-id: '2307522893'
connie-parent-id: '1394901392'
---
```

---

## Example 2: Crawl Existing Confluence Content

### Download Single Page

```bash
CONFLUENCE_BASE_URL="https://betfanatics.atlassian.net" \
ATLASSIAN_USER_NAME="tyler.stapler@betfanatics.com" \
/Users/tylerstapler/Documents/personal-wiki/tools/markdown_confluence/.venv/bin/markdown-confluence \
crawl page 1070956670 --output /tmp/crawled_page --verbose
```

### Download by URL

```bash
CONFLUENCE_BASE_URL="https://betfanatics.atlassian.net" \
ATLASSIAN_USER_NAME="tyler.stapler@betfanatics.com" \
/Users/tylerstapler/Documents/personal-wiki/tools/markdown_confluence/.venv/bin/markdown-confluence \
crawl page "https://betfanatics.atlassian.net/wiki/spaces/ENG/pages/1070956670/My+Page" \
--output /tmp/crawled_page --verbose
```

### Download Page Tree

```bash
CONFLUENCE_BASE_URL="https://betfanatics.atlassian.net" \
ATLASSIAN_USER_NAME="tyler.stapler@betfanatics.com" \
/Users/tylerstapler/Documents/personal-wiki/tools/markdown_confluence/.venv/bin/markdown-confluence \
crawl page-tree 1070956670 --output /tmp/crawled_tree --max-depth 2 --verbose
```

---

## Example 3: Selective Publishing

### Publish Only Specific Files

```bash
/Users/tylerstapler/Documents/personal-wiki/tools/markdown_confluence/.venv/bin/markdown-confluence \
publish . --config .markdown-confluence.json \
--pattern "guides/**/*.md" --verbose
```

### Exclude Drafts

```bash
/Users/tylerstapler/Documents/personal-wiki/tools/markdown_confluence/.venv/bin/markdown-confluence \
publish . --config .markdown-confluence.json \
--exclude "**/drafts/**" --exclude "**/archive/**" --verbose
```

---

## Example 4: Force Update and Troubleshooting

### Force Update Unchanged Pages

```bash
/Users/tylerstapler/Documents/personal-wiki/tools/markdown_confluence/.venv/bin/markdown-confluence \
publish . --config .markdown-confluence.json --force --verbose
```

### Stop on First Error

```bash
/Users/tylerstapler/Documents/personal-wiki/tools/markdown_confluence/.venv/bin/markdown-confluence \
publish . --config .markdown-confluence.json --fail-fast --verbose
```

### Handle Archived Pages

```bash
/Users/tylerstapler/Documents/personal-wiki/tools/markdown_confluence/.venv/bin/markdown-confluence \
publish . --config .markdown-confluence.json --delete-archived --verbose
```

---

## Example 5: Moving Pages Between Parents

### Change Parent via Frontmatter

Before:
```markdown
---
connie-page-id: '123456'
connie-parent-id: '111111'
---
```

After (change parent ID):
```markdown
---
connie-page-id: '123456'
connie-parent-id: '222222'
---
```

Then publish - the tool automatically detects parent change and moves the page.

---

## Example 6: Force Hierarchy from Directory Structure

### Ignore Frontmatter Parents, Use Directories

```bash
/Users/tylerstapler/Documents/personal-wiki/tools/markdown_confluence/.venv/bin/markdown-confluence \
publish . --config .markdown-confluence.json \
--force-hierarchy --update-frontmatter --verbose
```

This:
1. Ignores `connie-parent-id` in frontmatter
2. Uses directory structure to determine hierarchy
3. Updates frontmatter with corrected parent IDs

---

## Example 7: Compare Page Versions

### Fetch and Compare Versions

```bash
CONFLUENCE_BASE_URL="https://betfanatics.atlassian.net" \
ATLASSIAN_USER_NAME="tyler.stapler@betfanatics.com" \
/Users/tylerstapler/Documents/personal-wiki/tools/markdown_confluence/.venv/bin/markdown-confluence \
crawl page-versions 2322038952 --compare 11,12 --output ./version_comparison --verbose
```

---

## Example 8: Real Project Configuration

From `project_plans/shared-dictionary-compression/.markdown-confluence.json`:

```json
{
  "confluence": {
    "base_url": "https://betfanatics.atlassian.net",
    "parent_id": "1394901392",
    "username": "tyler.stapler@betfanatics.com"
  },
  "publish": {
    "folder_to_publish": ".",
    "frontmatter_from_document_start": true,
    "skip_metadata": false,
    "use_file_path_as_title": false,
    "prepend_file_path_to_title": false,
    "resolve_relative_links": true,
    "respect_link_dependencies": true
  }
}
```

Published markdown example:
```markdown
---
connie-page-id: '2307522893'
connie-parent-id: '1394901392'
---

# Project Proposal: Pages API Optimization

Content with wikilinks like [[Related Page]] and
relative links like [Architecture](./docs/architecture.md)
are automatically resolved to Confluence page links.
```

---

## Example 9: Publish Single File

```bash
CONFLUENCE_BASE_URL="https://betfanatics.atlassian.net" \
ATLASSIAN_USER_NAME="tyler.stapler@betfanatics.com" \
/Users/tylerstapler/Documents/personal-wiki/tools/markdown_confluence/.venv/bin/markdown-confluence \
publish ONE_PAGER.md --verbose
```

---

## Example 10: Debugging Failed Publish

### Step 1: Run with Diagnostic Mode

```bash
/Users/tylerstapler/Documents/personal-wiki/tools/markdown_confluence/.venv/bin/markdown-confluence \
publish . --config .markdown-confluence.json --diagnostic --fail-fast --verbose
```

### Step 2: Fix Corrupted Parent (if needed)

```bash
cd /Users/tylerstapler/Documents/personal-wiki/tools/markdown_confluence
uv run python debug_tools/fix_page_format.py \
  --config /path/to/.markdown-confluence.json \
  --page-id PARENT_PAGE_ID
```

### Step 3: Retry Publish

```bash
/Users/tylerstapler/Documents/personal-wiki/tools/markdown_confluence/.venv/bin/markdown-confluence \
publish . --config .markdown-confluence.json --force --verbose
```
