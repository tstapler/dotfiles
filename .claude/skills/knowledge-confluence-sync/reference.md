# Markdown Confluence CLI Reference

Complete option reference for every CLI command.

## Tool Binary

```
/Users/tylerstapler/Documents/personal-wiki/tools/markdown_confluence/.venv/bin/markdown-confluence
```

## Global Options (All Commands)

| Option | Description |
|--------|-------------|
| `-v, --verbose` | Increase verbosity (`-v` for info, `-vv` for debug) |
| `--config TEXT` | Config file path (default: `.markdown-confluence.json`) |

---

## publish

```bash
markdown-confluence publish SOURCE [OPTIONS]
```

Publish a single markdown file or directory of files to Confluence.

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--dry-run` | flag | off | Preview without publishing |
| `--pattern TEXT` | string | - | Include glob pattern (e.g., `"**/*.md"`) |
| `--exclude TEXT` | string | - | Exclude glob pattern (e.g., `"**/drafts/**"`) |
| `--force` | flag | off | Force update even if content unchanged |
| `--fail-fast` | flag | off | Stop on first error |
| `--delete-archived/--no-delete-archived` | flag | on | Delete archived pages when detected |
| `--force-title-match` | flag | off | Duplicate detection by title only |
| `--event-driven/--no-event-driven` | flag | on | Use event-driven processing |
| `--diagnostic` | flag | off | Enable detailed error info |
| `--force-hierarchy` | flag | off | Use directory structure for hierarchy |
| `--update-frontmatter` | flag | off | Update frontmatter parent IDs (requires `--force-hierarchy`) |
| `--sync/--no-sync` | flag | on | Check remote changes before publishing |
| `--auto-resolve-conflicts` | flag | off | Auto-resolve detected conflicts |
| `--prefer-remote` | flag | off | Prefer remote changes when auto-resolving |
| `--private` | flag | off | Restrict page to current user only |
| `--restrict-read TEXT` | multi | - | Restrict read access (`user:accountId` or `group:name`) |
| `--restrict-update TEXT` | multi | - | Restrict update access (`user:accountId` or `group:name`) |
| `--page-id TEXT` | string | - | Confluence page ID to update (one-off mode) |
| `--parent-id TEXT` | string | - | Parent page ID for new pages (one-off mode) |
| `--base-url TEXT` | string | - | Confluence base URL (one-off mode) |
| `--username TEXT` | string | - | Atlassian username/email (one-off mode) |
| `--space-key TEXT` | string | - | Confluence space key (one-off mode) |

---

## crawl page

```bash
markdown-confluence crawl page PAGE_ID_OR_URL [OPTIONS]
```

Download a single Confluence page (by numeric ID or full URL).

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `-o, --output PATH` | path | **required** | Output directory for page archive |

---

## crawl page-tree

```bash
markdown-confluence crawl page-tree PAGE_ID_OR_URL [OPTIONS]
```

Recursively crawl a page and all its descendants.

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `-o, --output PATH` | path | **required** | Output directory for crawled pages |
| `--max-depth INTEGER` | int | unlimited | Maximum recursion depth |

---

## crawl space

```bash
markdown-confluence crawl space SPACE_KEY [OPTIONS]
```

Crawl all pages in a Confluence space.

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `-o, --output PATH` | path | **required** | Output directory for crawled pages |
| `--max-pages INTEGER` | int | all | Maximum number of pages to crawl |
| `--include-archived` | flag | off | Include archived pages |

---

## crawl page-versions

```bash
markdown-confluence crawl page-versions PAGE_ID_OR_URL [OPTIONS]
```

Fetch and compare page version history.

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `-v, --version INTEGER` | int | - | Specific version to fetch |
| `-c, --compare TEXT` | string | - | Compare two versions (format: `"v1,v2"`) |
| `-o, --output PATH` | path | - | Output directory for version data |

---

## crawl analyze-adf

```bash
markdown-confluence crawl analyze-adf ADF_FILE [OPTIONS]
```

Parse and analyze an ADF JSON document.

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `-o, --output PATH` | path | - | Output JSON report file |

---

## crawl compare

```bash
markdown-confluence crawl compare MARKDOWN_FILE [OPTIONS]
```

Compare markdown with generated ADF output.

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--adf-file PATH` | path | - | Compare with existing ADF file |
| `-o, --output PATH` | path | - | Output comparison report (JSON) |
| `-v, --verbose` | flag | off | Show detailed differences |

---

## sync status

```bash
markdown-confluence sync status PATH [OPTIONS]
```

Check sync status of markdown files.

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `-r, --recursive` | flag | off | Check subdirectories recursively |

Status values: Up to date, Local changes, Remote changes, Conflicted, Not tracked, Remote deleted.

---

## sync pull

```bash
markdown-confluence sync pull PATH [OPTIONS]
```

Pull remote changes from Confluence to local files.

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `-r, --recursive` | flag | off | Sync subdirectories recursively |
| `--auto-resolve` | flag | off | Auto-resolve conflicts |
| `--prefer-remote` | flag | off | Prefer remote changes when resolving |

---

## sync resolve

```bash
markdown-confluence sync resolve FILE_PATH
```

Interactively resolve a conflict for a specific file. Prompts for: keep local, take remote, or cancel.

---

## handle-deleted

```bash
markdown-confluence handle-deleted [OPTIONS]
```

Manage files that were deleted locally but still exist in Confluence.

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--action` | choice | `report` | Action: `report`, `delete`, or `archive` |

---

## validate-links

```bash
markdown-confluence validate-links [OPTIONS]
```

Validate links between markdown files and report broken links.

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--source PATH` | path | - | Source directory to validate |
| `--pattern TEXT` | string | - | File pattern to include |
| `--exclude TEXT` | string | - | File pattern to exclude |
| `--output PATH` | path | - | Output report file |
| `--check-existence` | flag | off | Verify linked pages exist in Confluence |
| `--fix` | flag | off | Attempt to fix broken links |

---

## cache

```bash
markdown-confluence cache [OPTIONS]
```

Manage the local content cache.

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--clear` | flag | off | Clear the cache |
| `--info` | flag | off | Show cache statistics |

---

## comments fetch

```bash
markdown-confluence comments fetch PAGE_ID_OR_URL [OPTIONS]
```

Fetch comments from a Confluence page.

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `-o, --output PATH` | path | - | Save comments to JSON file |
| `-t, --type` | choice | `all` | Type: `all`, `inline`, or `footer` |

---

## comments add

```bash
markdown-confluence comments add PAGE_ID_OR_URL [OPTIONS]
```

Add a footer comment to a page.

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `-m, --message TEXT` | string | **required** | Comment text |
| `-t, --type` | choice | `footer` | Comment type (only `footer` supported) |

---

## comments reply

```bash
markdown-confluence comments reply PAGE_ID_OR_URL PARENT_COMMENT_ID [OPTIONS]
```

Reply to an existing footer comment.

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `-m, --message TEXT` | string | **required** | Reply text |

---

## comments export

```bash
markdown-confluence comments export PAGE_ID_OR_URL [OPTIONS]
```

Export all comments to a file.

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `-o, --output PATH` | path | **required** | Output file |
| `-f, --format` | choice | `json` | Export format: `json` or `markdown` |

---

## migrate-editor

```bash
markdown-confluence migrate-editor PAGE_IDS... [OPTIONS]
```

Detect and migrate pages from legacy Confluence editor (v1) to new editor (v2/ADF).

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--dry-run` | flag | off | Detect editor type without migrating |

---

## status

```bash
markdown-confluence status [OPTIONS]
```

Show tool status information.

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--env` | flag | off | Show environment variable status |

---

## Configuration File Reference

### `.markdown-confluence.json`

```json
{
  "confluence": {
    "base_url": "https://betfanatics.atlassian.net",
    "parent_id": "1394901392",
    "username": "tyler.stapler@betfanatics.com",
    "space_key": "OPTIONAL_SPACE_KEY"
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

### Configuration Fields

| Field | Type | Description |
|-------|------|-------------|
| `base_url` | string | Confluence instance URL |
| `parent_id` | string | Root parent page ID for published content |
| `username` | string | Atlassian username (email) |
| `space_key` | string | Optional Confluence space key |
| `folder_to_publish` | string | Relative path to publish (default: `.`) |
| `frontmatter_from_document_start` | bool | Parse frontmatter from file start |
| `skip_metadata` | bool | Skip metadata panel in output |
| `use_file_path_as_title` | bool | Use file path as page title |
| `prepend_file_path_to_title` | bool | Prepend file path to title |
| `resolve_relative_links` | bool | Convert relative links to Confluence links |
| `respect_link_dependencies` | bool | Publish pages in dependency order |

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ATLASSIAN_API_TOKEN` | Yes | API token for authentication |
| `CONFLUENCE_BASE_URL` | No* | Overrides config `base_url` |
| `CONFLUENCE_PARENT_ID` | No* | Overrides config `parent_id` |
| `ATLASSIAN_USER_NAME` | No* | Overrides config `username` |
| `CONFLUENCE_SPACE_KEY` | No | Space key override |

*These override config file values when set.

---

## Frontmatter Complete Reference

```markdown
---
connie-title: "Custom Title"
connie-page-id: "123456"
connie-parent-id: "789012"
connie-parent-page-id: "789012"
connie-publish: true
connie-skip-link-resolution: false
---
```

---

## Link Resolution

The tool resolves three link types:

| Format | Example | Resolves To |
|--------|---------|-------------|
| Relative link | `[Doc B](./doc_b.md)` | Confluence page link |
| Wikilink | `[[Page Name]]` | Confluence page link |
| Titled wikilink | `[[Page Name\|Display Text]]` | Link with custom text |

When `respect_link_dependencies: true`, pages are published in dependency order (linked pages first).

---

## Debug Tools

Located at `/Users/tylerstapler/Documents/personal-wiki/tools/markdown_confluence/debug_tools/`:

| Tool | Purpose |
|------|---------|
| `download_confluence_pages.py` | Download pages for inspection |
| `fix_page_format.py` | Repair corrupted page formats |
| `compare_page_formats.py` | Compare storage vs ADF formats |
| `analyze_failing_page.py` | Diagnose publishing issues |
| `analyze_links.py` | Visualize link dependencies |

Usage:

```bash
cd /Users/tylerstapler/Documents/personal-wiki/tools/markdown_confluence
uv run python debug_tools/<tool>.py [OPTIONS]
```
