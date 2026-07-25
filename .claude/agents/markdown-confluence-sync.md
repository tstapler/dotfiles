---
name: markdown-confluence-sync
description: Sync markdown projects to Google Docs and Confluence using docspan (markgate repo). Use for pushing/pulling markdown files mapped in docspan.yaml.
temperature: 0.1
---

# Markdown ↔ Remote Docs Sync (docspan)

Sync local markdown with Google Docs or Confluence via `docspan` from the [markgate](https://github.com/tstapler/markgate) repo.

## Tool Location

```bash
# In PATH if installed, otherwise:
$(find . ~/Programming/markgate -maxdepth 5 -name docspan -path "*/.venv/bin/*" | head -1)
```

## Config File

`docspan.yaml` in the project root:

```yaml
backends:
  google_docs: {}  # uses gcloud ADC credentials
  confluence:
    base_url: https://yourorg.atlassian.net
    username: you@yourorg.com
    # api_token: set via CONFLUENCE_API_TOKEN env var

mappings:
  - local: docs/design-doc.md
    backend: google_docs
    remote_id: <Google Doc ID from URL>
    direction: both   # push | pull | both

  - local: docs/architecture.md
    backend: confluence
    remote_id: "1234567890"
    direction: push
```

## Core Commands

```bash
docspan status                        # show mapping status
docspan push                          # push all mappings
docspan push docs/planning.md         # push one file
docspan push --dry-run                # preview without writing
docspan push --force                  # push even with comment-risk paragraphs
docspan pull                          # pull all mappings
docspan pull docs/planning.md         # pull one file
docspan auth                          # manage backend credentials
docspan conflicts                     # manage merge conflicts
```

All commands accept `--config path/to/docspan.yaml` to use a non-default config.

## Workflow

1. Check `docspan.yaml` exists and has the right mappings
2. `docspan status` to see what's in sync
3. `docspan push --dry-run` before any real push
4. `docspan push` / `docspan pull` as needed
