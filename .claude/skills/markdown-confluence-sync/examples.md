# Markdown Confluence Examples

## Tool Binary (used in all examples)

```
/Users/tylerstapler/Documents/personal-wiki/tools/markdown_confluence/.venv/bin/markdown-confluence
```

All examples assume environment variables are set:

```bash
export CONFLUENCE_BASE_URL="https://betfanatics.atlassian.net"
export ATLASSIAN_USER_NAME="tyler.stapler@betfanatics.com"
```

---

## Example 1: New Project Setup and Publish

### Project Structure

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

### Config File

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

### Frontmatter

```markdown
---
connie-title: "My Project Documentation"
---

# My Project

See [Introduction](./overview/introduction.md) for details.
```

### Dry Run, Then Publish

```bash
/Users/tylerstapler/Documents/personal-wiki/tools/markdown_confluence/.venv/bin/markdown-confluence \
publish . --config .markdown-confluence.json --dry-run --verbose

/Users/tylerstapler/Documents/personal-wiki/tools/markdown_confluence/.venv/bin/markdown-confluence \
publish . --config .markdown-confluence.json --verbose
```

After publishing, frontmatter is auto-updated with IDs:
```markdown
---
connie-title: "My Project Documentation"
connie-page-id: '2307522893'
connie-parent-id: '1394901392'
---
```

---

## Example 2: Crawl Existing Confluence Content

### Single Page by ID

```bash
/Users/tylerstapler/Documents/personal-wiki/tools/markdown_confluence/.venv/bin/markdown-confluence \
crawl page 1070956670 --output /tmp/crawled_page --verbose
```

### Single Page by URL

```bash
/Users/tylerstapler/Documents/personal-wiki/tools/markdown_confluence/.venv/bin/markdown-confluence \
crawl page "https://betfanatics.atlassian.net/wiki/spaces/ENG/pages/1070956670/My+Page" \
--output /tmp/crawled_page --verbose
```

### Page Tree with Depth Limit

```bash
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

## Example 4: One-Off Single File Publish

No config file needed; use CLI flags directly:

```bash
# Create under a parent page
/Users/tylerstapler/Documents/personal-wiki/tools/markdown_confluence/.venv/bin/markdown-confluence \
publish ONE_PAGER.md --parent-id "1394901392" --verbose

# Update an existing page by ID
/Users/tylerstapler/Documents/personal-wiki/tools/markdown_confluence/.venv/bin/markdown-confluence \
publish updated_doc.md --page-id "2307522893" --verbose
```

---

## Example 5: Force Update and Troubleshooting

```bash
# Force update unchanged pages
/Users/tylerstapler/Documents/personal-wiki/tools/markdown_confluence/.venv/bin/markdown-confluence \
publish . --config .markdown-confluence.json --force --verbose

# Stop on first error for debugging
/Users/tylerstapler/Documents/personal-wiki/tools/markdown_confluence/.venv/bin/markdown-confluence \
publish . --config .markdown-confluence.json --fail-fast --verbose

# Enable diagnostic mode for detailed error info
/Users/tylerstapler/Documents/personal-wiki/tools/markdown_confluence/.venv/bin/markdown-confluence \
publish . --config .markdown-confluence.json --diagnostic --fail-fast --verbose
```

---

## Example 6: Directory Hierarchy as Page Hierarchy

Force the directory structure to drive Confluence page hierarchy:

```bash
/Users/tylerstapler/Documents/personal-wiki/tools/markdown_confluence/.venv/bin/markdown-confluence \
publish . --config .markdown-confluence.json \
--force-hierarchy --update-frontmatter --verbose
```

This ignores `connie-parent-id` in frontmatter, uses directory nesting instead, and updates frontmatter with the corrected parent IDs.

---

## Example 7: Move Page to New Parent

Change `connie-parent-id` in frontmatter:

```markdown
---
connie-page-id: '123456'
connie-parent-id: '222222'    # Changed from '111111'
---
```

Then publish; the tool detects the parent change and moves the page.

---

## Example 8: Sync Workflow

```bash
# Check what's changed
/Users/tylerstapler/Documents/personal-wiki/tools/markdown_confluence/.venv/bin/markdown-confluence \
sync status . --recursive

# Pull remote changes
/Users/tylerstapler/Documents/personal-wiki/tools/markdown_confluence/.venv/bin/markdown-confluence \
sync pull . --recursive

# Auto-resolve conflicts preferring remote
/Users/tylerstapler/Documents/personal-wiki/tools/markdown_confluence/.venv/bin/markdown-confluence \
sync pull . --recursive --auto-resolve --prefer-remote

# Resolve a specific conflict interactively
/Users/tylerstapler/Documents/personal-wiki/tools/markdown_confluence/.venv/bin/markdown-confluence \
sync resolve docs/page.md
```

---

## Example 9: Compare Page Versions

```bash
/Users/tylerstapler/Documents/personal-wiki/tools/markdown_confluence/.venv/bin/markdown-confluence \
crawl page-versions 2322038952 --compare 11,12 --output /tmp/version_comparison --verbose
```

---

## Example 10: Fix Corrupted Parent Page

```bash
cd /Users/tylerstapler/Documents/personal-wiki/tools/markdown_confluence
uv run python debug_tools/fix_page_format.py \
  --config=/path/to/.markdown-confluence.json \
  --page-id=PARENT_PAGE_ID

# Then retry publish with force
/Users/tylerstapler/Documents/personal-wiki/tools/markdown_confluence/.venv/bin/markdown-confluence \
publish . --config .markdown-confluence.json --force --verbose
```

---

## Example 11: Comments

```bash
# Fetch all comments
/Users/tylerstapler/Documents/personal-wiki/tools/markdown_confluence/.venv/bin/markdown-confluence \
comments fetch 1070956670

# Add a footer comment
/Users/tylerstapler/Documents/personal-wiki/tools/markdown_confluence/.venv/bin/markdown-confluence \
comments add 1070956670 --message "Updated documentation per review feedback"

# Export comments to markdown
/Users/tylerstapler/Documents/personal-wiki/tools/markdown_confluence/.venv/bin/markdown-confluence \
comments export 1070956670 --output /tmp/comments.md --format markdown
```

---

## Example 12: Migrate Legacy Editor Pages

```bash
# Check editor type (dry run)
/Users/tylerstapler/Documents/personal-wiki/tools/markdown_confluence/.venv/bin/markdown-confluence \
migrate-editor 2132017153 --dry-run

# Migrate multiple pages
/Users/tylerstapler/Documents/personal-wiki/tools/markdown_confluence/.venv/bin/markdown-confluence \
migrate-editor 2132017153 1848115341
```

---

## Example 13: Restrict Page Access

```bash
# Make page private (only visible to you)
/Users/tylerstapler/Documents/personal-wiki/tools/markdown_confluence/.venv/bin/markdown-confluence \
publish private_doc.md --config .markdown-confluence.json --private --verbose

# Restrict to specific group
/Users/tylerstapler/Documents/personal-wiki/tools/markdown_confluence/.venv/bin/markdown-confluence \
publish internal_doc.md --config .markdown-confluence.json \
--restrict-read "group:platform-team" --restrict-update "group:platform-team" --verbose
```
