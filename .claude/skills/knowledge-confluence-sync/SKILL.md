---
name: knowledge-confluence-sync
description: Publish markdown files to Confluence, crawl Confluence pages to local markdown, sync bidirectionally, validate links, and manage page hierarchy. Use when publishing documentation, downloading Confluence content, checking sync status, resolving conflicts, managing comments, or troubleshooting Confluence page issues.
---

# Markdown Confluence Sync

Manage the bidirectional flow between local markdown files and Confluence pages using the `markdown-confluence` CLI.

## Tool Binary

```
/Users/tylerstapler/Documents/personal-wiki/tools/markdown_confluence/.venv/bin/markdown-confluence
```

All commands below use this absolute path. Alias as `MC` in examples for brevity.

## Authentication

Three environment variables are required for every operation:

```bash
export CONFLUENCE_BASE_URL="https://betfanatics.atlassian.net"
export ATLASSIAN_USER_NAME="tyler.stapler@betfanatics.com"
# ATLASSIAN_API_TOKEN must be set (from keychain or secrets manager)
# Create at: https://id.atlassian.net/manage-profile/security/api-tokens
```

Verify setup:

```bash
CONFLUENCE_BASE_URL="https://betfanatics.atlassian.net" \
ATLASSIAN_USER_NAME="tyler.stapler@betfanatics.com" \
/Users/tylerstapler/Documents/personal-wiki/tools/markdown_confluence/.venv/bin/markdown-confluence \
status --env
```

## Command Map

| Command | Purpose |
|---------|---------|
| `publish` | Upload markdown to Confluence |
| `crawl page` | Download a single page |
| `crawl page-tree` | Download page and all descendants |
| `crawl space` | Download entire space |
| `sync status` | Check sync status of files |
| `sync pull` | Pull remote changes to local |
| `sync resolve` | Interactively resolve conflicts |
| `handle-deleted` | Report/delete/archive removed pages |
| `validate-links` | Check for broken links |
| `cache` | Clear/inspect content cache |
| `comments fetch` | Fetch page comments |
| `comments add` | Add footer comment |
| `comments reply` | Reply to a comment |
| `migrate-editor` | Migrate legacy editor pages to ADF |
| `crawl page-versions` | Fetch/compare page version history |
| `crawl analyze-adf` | Analyze ADF document structure |
| `crawl compare` | Compare markdown with generated ADF |

## Workflow 1: Publish Markdown to Confluence

### Step 1: Create Config File

Create `.markdown-confluence.json` in your project root:

```json
{
  "confluence": {
    "base_url": "https://betfanatics.atlassian.net",
    "parent_id": "PARENT_PAGE_ID",
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

### Step 2: Add Frontmatter to Files

```markdown
---
connie-title: "Custom Page Title"
connie-parent-id: "789012"      # Override parent page (optional)
connie-publish: true             # Set false to skip
---

# Your Content Here
```

After first publish, `connie-page-id` is auto-injected for future updates.

### Step 3: Dry Run Then Publish

```bash
# Always dry-run first
CONFLUENCE_BASE_URL="https://betfanatics.atlassian.net" \
ATLASSIAN_USER_NAME="tyler.stapler@betfanatics.com" \
/Users/tylerstapler/Documents/personal-wiki/tools/markdown_confluence/.venv/bin/markdown-confluence \
publish . --config .markdown-confluence.json --dry-run --verbose

# Actual publish
/Users/tylerstapler/Documents/personal-wiki/tools/markdown_confluence/.venv/bin/markdown-confluence \
publish . --config .markdown-confluence.json --verbose
```

### One-Off Single File Publish

Publish a single file without a config file using CLI flags:

```bash
/Users/tylerstapler/Documents/personal-wiki/tools/markdown_confluence/.venv/bin/markdown-confluence \
publish ONE_PAGER.md --parent-id "1394901392" --verbose
```

Or update an existing page:

```bash
/Users/tylerstapler/Documents/personal-wiki/tools/markdown_confluence/.venv/bin/markdown-confluence \
publish updated_doc.md --page-id "2307522893" --verbose
```

### Key Publish Options

| Option | Effect |
|--------|--------|
| `--dry-run` | Preview without publishing |
| `--force` | Force update unchanged pages |
| `--fail-fast` | Stop on first error |
| `--delete-archived` | Delete archived pages (default: on) |
| `--force-hierarchy` | Use directory structure, ignore frontmatter parents |
| `--update-frontmatter` | Update frontmatter parent IDs (requires `--force-hierarchy`) |
| `--pattern "**/*.md"` | Filter files to publish |
| `--exclude "**/drafts/**"` | Exclude file patterns |
| `--private` | Restrict page to current user only |

## Workflow 2: Crawl Confluence Pages

### Download Single Page

```bash
CONFLUENCE_BASE_URL="https://betfanatics.atlassian.net" \
ATLASSIAN_USER_NAME="tyler.stapler@betfanatics.com" \
/Users/tylerstapler/Documents/personal-wiki/tools/markdown_confluence/.venv/bin/markdown-confluence \
crawl page 1070956670 --output /tmp/crawled_page --verbose
```

Accepts page IDs or full URLs:

```bash
/Users/tylerstapler/Documents/personal-wiki/tools/markdown_confluence/.venv/bin/markdown-confluence \
crawl page "https://betfanatics.atlassian.net/wiki/spaces/ENG/pages/1070956670/My+Page" \
--output /tmp/crawled_page --verbose
```

### Download Page Tree

```bash
/Users/tylerstapler/Documents/personal-wiki/tools/markdown_confluence/.venv/bin/markdown-confluence \
crawl page-tree 1070956670 --output /tmp/crawled_tree --max-depth 3 --verbose
```

### Download Entire Space

```bash
/Users/tylerstapler/Documents/personal-wiki/tools/markdown_confluence/.venv/bin/markdown-confluence \
crawl space MYSPACE --output /tmp/crawled_space --verbose
```

### Output Structure

Crawled pages are saved as structured directories with:
- `metadata.json` - Page metadata (title, space, version, status)
- `content.adf.json` - ADF format content
- `content.storage.html` - Storage format HTML
- `index.json` - Index of all crawled pages (space/tree crawls)

## Workflow 3: Sync and Conflict Resolution

### Check Status

```bash
/Users/tylerstapler/Documents/personal-wiki/tools/markdown_confluence/.venv/bin/markdown-confluence \
sync status . --recursive
```

Shows per-file status: up-to-date, local changes, remote changes, conflicted, not tracked.

### Pull Remote Changes

```bash
/Users/tylerstapler/Documents/personal-wiki/tools/markdown_confluence/.venv/bin/markdown-confluence \
sync pull . --recursive

# Auto-resolve conflicts
sync pull . --recursive --auto-resolve --prefer-remote
```

### Resolve Conflicts Interactively

```bash
/Users/tylerstapler/Documents/personal-wiki/tools/markdown_confluence/.venv/bin/markdown-confluence \
sync resolve docs/page.md
```

Prompts to choose: keep local, take remote, or cancel.

## Frontmatter Fields

| Field | Purpose |
|-------|---------|
| `connie-title` | Custom page title (overrides filename) |
| `connie-page-id` | Existing page ID (auto-set after first publish) |
| `connie-parent-id` | Parent page ID (sets/moves hierarchy) |
| `connie-publish` | `true`/`false` to enable/disable publishing |
| `connie-skip-link-resolution` | `true` to exclude from link graph |

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| 400 Bad Request | Corrupted parent page format | Run `fix_page_format.py` debug tool |
| Duplicate title | Title already exists in space | Add unique `connie-title` in frontmatter |
| Page not found | Invalid page ID | Tool auto-creates new page |
| Archived page blocking | Archived page at same title | Use `--delete-archived` flag |
| Version not incrementing | No content change detected | Use `--force` flag |
| Auth failure | Missing/invalid API token | Check `status --env` output |

### Debug Tools

Located at `/Users/tylerstapler/Documents/personal-wiki/tools/markdown_confluence/debug_tools/`:

```bash
# Fix corrupted parent page
cd /Users/tylerstapler/Documents/personal-wiki/tools/markdown_confluence
uv run python debug_tools/fix_page_format.py \
  --config=/path/to/.markdown-confluence.json \
  --page-id=PARENT_PAGE_ID
```

## Features

- Mermaid diagrams: auto-rendered to images and uploaded as attachments
- Wikilinks: `[[Page Name]]` and `[[Page Name|Display Text]]` resolved to Confluence links
- Relative links: `[Doc B](./doc_b.md)` converted to Confluence page links
- Directory hierarchy: maps to Confluence page hierarchy with `--force-hierarchy`
- Content hashing: skips unchanged pages for efficient updates
- Asset handling: images auto-uploaded, paths converted to attachment references

## Progressive Context

- Full CLI option reference: see `reference.md` in this skill directory
- Worked examples: see `examples.md` in this skill directory
