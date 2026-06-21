---
name: docs-local-cache
description: >
  Fetch official documentation for any library or tool, cache it locally in a versioned store, and
  search it offline. Prefers arabold/docs-mcp-server (MCP with SQLite + vector search) when
  installed; falls back to llms.txt fetch or website-downloader for lightweight caching. Use
  instead of context7 or live web search when you need authoritative, offline, version-pinned docs.
  Invoke when asked to "look up docs for X", "cache docs for X", "search local docs", "add docs
  for X", or "update docs cache for X".
---

# Local Documentation Cache

Authoritative docs, offline and version-pinned. No SaaS dependency.

## Approach Selection

Choose based on what's installed:

| Scenario | Approach |
|---|---|
| `arabold/docs-mcp-server` configured as MCP | [Option A](#option-a--docs-mcp-server-recommended) — full vector search |
| DocsetMCP configured, Zeal/Dash installed | [Option B](#option-b--docsetmcp) — curated docsets |
| Neither installed | [Option C](#option-c--manual-cache) — procedural fetch + ripgrep |

Check what's available:

```bash
# Check if docs-mcp-server scraper CLI is reachable
npx @arabold/docs-mcp-server@latest --version 2>/dev/null && echo "available" || echo "not installed"

# Check if Zeal is installed (Linux)
which zeal 2>/dev/null || echo "zeal not installed"
```

---

## Option A — docs-mcp-server (Recommended)

**`arabold/docs-mcp-server`** is an open-source local documentation server with version-aware
scraping, SQLite storage, and vector search — a self-hosted drop-in for context7.

### One-time MCP Setup

Add to `~/.claude/settings.json` under `mcpServers`:

```json
{
  "mcpServers": {
    "docs": {
      "command": "npx",
      "args": ["-y", "@arabold/docs-mcp-server@latest"],
      "env": {
        "DOCS_MCP_STORAGE_DIR": "~/.local/share/docs-mcp-server"
      }
    }
  }
}
```

For vector search (semantic, not just keyword), set one of:
```json
"env": {
  "DOCS_MCP_STORAGE_DIR": "~/.local/share/docs-mcp-server",
  "OPENAI_API_KEY": "<key>",
  "OPENAI_EMBEDDING_MODEL": "text-embedding-3-small"
}
```
Or use a local embedding model via Ollama (`OLLAMA_HOST`, `OLLAMA_EMBEDDING_MODEL`).

### Scraping docs for a library

```bash
# Scrape from a URL
npx @arabold/docs-mcp-server@latest scrape <library-name> <docs-url> --version <version>

# Examples
npx @arabold/docs-mcp-server@latest scrape pydantic https://docs.pydantic.dev/latest/ --version 2.7
npx @arabold/docs-mcp-server@latest scrape anthropic https://docs.anthropic.com --version 2025
npx @arabold/docs-mcp-server@latest scrape react https://react.dev --version 19

# From GitHub (reads docs/ and README)
npx @arabold/docs-mcp-server@latest scrape mylib https://github.com/<owner>/<repo> --version latest

# From npm package (extracts bundled docs)
npx @arabold/docs-mcp-server@latest scrape zod npm:zod --version 3.23
```

### Searching (via MCP tools, when server is running)

The server exposes MCP tools: `search_docs`, `list_libraries`, `get_library_info`.

```
search_docs(library="pydantic", query="validator decorator", version="2.7")
list_libraries()
```

### Web UI

```bash
# Launch the web UI to browse cached docs
npx @arabold/docs-mcp-server@latest --port 6280
# then open http://localhost:6280
```

### Keeping docs fresh

```bash
# Re-scrape a library (updates existing cache)
npx @arabold/docs-mcp-server@latest scrape pydantic https://docs.pydantic.dev/latest/ --version 2.7

# List what's in the store
npx @arabold/docs-mcp-server@latest list
```

---

## Option B — DocsetMCP

**`codybrom/DocsetMCP`** serves locally-installed Dash/Zeal docsets over MCP. 165+ curated
libraries, 40+ cheatsheets. Entirely offline after download.

### Setup

```bash
# Install Zeal (Linux)
sudo pacman -S zeal          # Arch/Manjaro
# or
sudo apt install zeal        # Debian/Ubuntu

# Then download docsets within Zeal (GUI: Tools → Docsets)

# Add DocsetMCP to ~/.claude/settings.json
uvx docsetmcp
```

```json
{
  "mcpServers": {
    "docsets": {
      "command": "uvx",
      "args": ["docsetmcp"]
    }
  }
}
```

### Usage

DocsetMCP exposes `search_docset` and `list_docsets` MCP tools:

```
search_docset(library="Python", query="list comprehension")
list_docsets()
```

**Limitation**: Covers curated libraries only. For unlisted libraries, fall back to Option A or C.

Additional docsets: <https://zealusercontributions.vercel.app>

---

## Option C — Manual Cache (Procedural Fallback)

When neither MCP server is installed, use a structured file cache at `~/.claude/docs/cache/`.

### Cache layout

```
~/.claude/docs/cache/
  index.json                  # manifest: library → {version, path, url, fetched_at}
  <library>/
    <version>/
      _meta.json              # source URL, fetch date, fetch method
      llms.txt                # if available (preferred)
      llms-full.txt           # if available (complete docs)
      *.md / *.html / *.txt   # downloaded pages
```

### Step 1: Check cache

```bash
ls ~/.claude/docs/cache/<library>/ 2>/dev/null || echo "not cached"
cat ~/.claude/docs/cache/index.json 2>/dev/null | python3 -m json.tool
```

### Step 2: Check for llms.txt

The `llms.txt` standard (<https://llmstxt.org>) — a concise, LLM-optimized doc summary many
projects now publish at their docs root.

Use `mcp__read-website-fast__read_website` to fetch:
- `<docs-url>/llms.txt` — summary + links
- `<docs-url>/llms-full.txt` — complete docs in one file

**Check this first** — if it exists, it's often sufficient and tiny.

**Known llms.txt adopters** (mid-2025): Anthropic, FastAPI, Pydantic, Svelte, Astro, Vite, FastHTML, LangChain, and hundreds more indexed at <https://llmstxt.org/directory>.

### Step 3: Fetch docs (priority order)

| Priority | Method | When |
|---|---|---|
| 1 | `mcp__read-website-fast__read_website` on `/llms.txt` | Always try first |
| 2 | `mcp__read-website-fast__read_website` on specific pages | For targeted queries |
| 3 | `mcp__website-downloader__download_page` | Preserve HTML structure |
| 4 | `mcp__website-downloader__download_website` | Full offline copy (slow) |
| 5 | `git clone --depth=1 <repo>` + copy `docs/` | Docs in GitHub repo |

### Step 4: Write metadata

```bash
mkdir -p ~/.claude/docs/cache/<library>/<version>

python3 - <<'EOF'
import json, os

meta = {
    "library": "<library>",
    "version": "<version>",
    "source_url": "<docs-url>",
    "fetch_method": "llms.txt",
    "fetched_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}

path = os.path.expanduser("~/.claude/docs/cache/<library>/<version>/_meta.json")
with open(path, "w") as f:
    json.dump(meta, f, indent=2)

# Update index
index_path = os.path.expanduser("~/.claude/docs/cache/index.json")
index = {}
if os.path.exists(index_path):
    with open(index_path) as f:
        index = json.load(f)

index["<library>"] = {
    "version": "<version>",
    "path": "~/.claude/docs/cache/<library>/<version>",
    "url": "<docs-url>",
    "fetched_at": meta["fetched_at"]
}

with open(index_path, "w") as f:
    json.dump(index, f, indent=2, sort_keys=True)
print("cache updated")
EOF
```

### Step 5: Search

```bash
# Search within a library
rg "search term" ~/.claude/docs/cache/<library>/ --type txt --type md -C 3

# Search all cached docs
rg "search term" ~/.claude/docs/cache/ -l

# Case-insensitive, show filenames
rg -i "configuration" ~/.claude/docs/cache/<library>/ -l
```

Use `Read` tool to read specific matched files.

---

## Alternatives Comparison

| Tool | Type | Offline | Versioned | Semantic search | LLM-optimized |
|---|---|---|---|---|---|
| **docs-mcp-server** (arabold) | Local MCP server | Yes (after scrape) | Yes | Yes (with embeddings) | Yes |
| **DocsetMCP** (codybrom) | Local MCP server | Yes | Per docset | No | No |
| **devdocs.io** (self-hosted) | Web app | Yes | Per docset | No | No |
| **Zeal** | Desktop app | Yes | Per docset | No | No |
| **llms.txt** | Fetch standard | After fetch | Manual | N/A | Yes |
| **git-mcp** (idosal) | Remote MCP | No (cloud) | No | No | No |
| **context7** | SaaS MCP | No (SaaS) | Managed | Yes | Yes |
| **This skill, Option C** | Procedural + rg | Yes | Yes | No | Via llms.txt |

### devdocs.io self-hosted

```bash
# Self-host devdocs (Ruby + Docker)
docker run -p 9292:9292 ghcr.io/freecodecamp/devdocs:latest

# API access
curl http://localhost:9292/docs/<library>/<version>/entries.json
```

200+ libraries, keyword search, no semantic search.

---

## Decision Tree

```
Need docs for <library>?
│
├── docs-mcp-server installed?
│   └── Yes → npx scrape if not yet cached → search_docs via MCP
│
├── DocsetMCP + Zeal installed, library in docsets?
│   └── Yes → search_docset via MCP
│
├── Check ~/.claude/docs/cache/<library>/?
│   └── Cached → rg search it
│
├── Check <docs-url>/llms.txt or /llms-full.txt?
│   └── Exists → fetch + cache, done
│
├── Small set of important pages needed?
│   └── Yes → download_page each, cache, done
│
├── Need comprehensive offline access?
│   └── Yes → download_website (depth 2–3), cache, done
│
└── Docs in GitHub repo?
    └── Yes → git clone --depth=1, copy docs/, cache, done
```

## Setup Recommendation

For a permanent local docs solution, install `arabold/docs-mcp-server` as an MCP server (Option A).
Then scrape libraries as you encounter them. The first time you need `pydantic` docs, run:

```bash
npx @arabold/docs-mcp-server@latest scrape pydantic https://docs.pydantic.dev/latest/ --version 2
```

It becomes instantly available to all future Claude Code sessions via `search_docs` MCP tool.

## Execution Rules

- **Always check cache / installed MCP before fetching** — avoid redundant downloads
- **Prefer llms.txt** when no MCP server is installed — smallest, highest signal
- **Record `_meta.json`** for every manual cache entry — staleness detection needs it
- **Update `index.json`** after every manual fetch
- **Use `rg` not `grep`** for searching the file cache — faster, respects `.gitignore`
- **Read cached files with `Read` tool** not `cat`
- **Version strings**: use semver (e.g., `3.11`) or `latest`; never dates as versions
- **Don't cache entire internet** — download only what you'll realistically search
- **Refresh on version bump** or when docs seem stale vs. observed behavior
