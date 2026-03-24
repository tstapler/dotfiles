---
title: Get Wikipedia Image for Topic
description: Fetch the Wikipedia thumbnail image for any topic and save it as a local asset in the Logseq wiki. Returns the markdown image reference to embed in a page.
arguments: [topic, subfolder]
tools: Bash, Read, Write, Edit, Glob, mcp__fetch__fetch
model: haiku
---

## Prerequisites

Install required Homebrew dependencies before use:

```bash
brew install libavif   # AVIF encoder/decoder (avifenc, avifdec)
```

`libavif` provides `avifenc` for converting downloaded JPEG/PNG images to AVIF format (~50% smaller than JPEG, supported in Logseq via Electron 28+).

# Get Wikipedia Image

Download a Wikipedia thumbnail for `$ARGUMENTS` and save it locally in the Logseq assets folder.

## Arguments

- **topic** (required): The topic name, e.g. "Oregon Grape" or "Sword Fern". Used both as the Wikipedia article title and to derive the local filename.
- **subfolder** (optional): Subdirectory under `logseq/assets/` to save into, e.g. `plants`. Defaults to `images`.

## Workflow

### Step 1 — Locate the wiki root

Look for the personal wiki at `~/Documents/personal-wiki`. Confirm it exists:

```bash
ls ~/Documents/personal-wiki/logseq/assets/ 2>/dev/null && echo "found" || echo "not found"
```

If not found, ask the user where their wiki is.

### Step 2 — Call the Wikipedia Summary API

Use `mcp__fetch__fetch` to call:

```
https://en.wikipedia.org/api/rest_v1/page/summary/{URL_ENCODED_TOPIC}
```

Replace spaces with underscores in the topic name, e.g. `Oregon_Grape`.

Extract from the JSON response:
- `thumbnail.source` — the pre-rendered thumbnail URL (standard 330px, safe to use)
- `title` — the canonical Wikipedia title (use for the image alt text)
- If `thumbnail` is missing, the article may have no image; report this to the user.

### Step 3 — Derive local filename

Convert the topic to a kebab-case slug:
- Lowercase all characters
- Replace spaces and underscores with hyphens
- Remove apostrophes and special characters

Examples:
- "Oregon Grape" → `oregon-grape`
- "False Solomon's Seal" → `false-solomons-seal`
- "Western Red Cedar" → `western-red-cedar`

Append the file extension from the thumbnail URL (`.jpg`, `.JPG`, `.png`, etc.).

Full asset path: `~/Documents/personal-wiki/logseq/assets/{subfolder}/{slug}{ext}`

### Step 4 — Download with curl

```bash
mkdir -p ~/Documents/personal-wiki/logseq/assets/{subfolder}

curl -L \
  --silent \
  --show-error \
  -H 'User-Agent: personal-wiki-image-downloader/1.0 (https://github.com/tylerstapler/personal-wiki; logseq-wiki)' \
  --retry 3 \
  --retry-delay 5 \
  -o "~/Documents/personal-wiki/logseq/assets/{subfolder}/{slug}{ext}" \
  "{thumbnail_url}"
```

**Wikimedia bot policy compliance** (https://w.wiki/4wJS):
- Use the thumbnail URL from the API (it returns standard 330px — a compliant size)
- Do NOT construct your own thumbnail URLs; guessed filenames will fail
- Identify the bot properly via User-Agent
- If you get a 429, wait for the `Retry-After` header value before retrying
- Do not download more than 2 files concurrently

### Step 5 — Return the result

Report back:
1. The local file path
2. The markdown embed syntax to paste into a Logseq page:

```markdown
![{Topic Name}](../assets/{subfolder}/{slug}{ext})
```

If the page being edited is not in `logseq/pages/`, adjust the relative path accordingly.

## Bulk Downloads

For downloading images for many topics at once, use the existing script:

```bash
uv run ~/Documents/personal-wiki/scripts/download-plant-images.py
```

To add new entries, append to the `PLANT_MAP` list in that file:
```python
("PageName.md", "Wikipedia_Article_Title", "local-slug"),
```

## Error Handling

| Error | Action |
|-------|--------|
| 404 from summary API | Topic not found on Wikipedia — try alternate title or spelling |
| `thumbnail` missing in response | No image on this Wikipedia article — report to user |
| 429 on download | Wait `Retry-After` seconds, then retry |
| File already exists | Skip download, return existing path |
