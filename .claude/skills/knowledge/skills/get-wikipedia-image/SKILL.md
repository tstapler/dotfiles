---
description: Fetch the Wikipedia thumbnail image for any topic and save it as a local
  asset in the Logseq wiki. Returns the markdown image reference to embed in a page.
prompt: "## Prerequisites\n\nInstall required Homebrew dependencies before use:\n\n\
  ```bash\nbrew install libavif   # AVIF encoder/decoder (avifenc, avifdec)\n```\n\
  \n`libavif` provides `avifenc` for converting downloaded JPEG/PNG images to AVIF\
  \ format (~50% smaller than JPEG, supported in Logseq via Electron 28+).\n\n# Get\
  \ Wikipedia Image\n\nDownload a Wikipedia thumbnail for `{{args}}` and save it locally\
  \ in the Logseq assets folder.\n\n## Arguments\n\n- **topic** (required): The topic\
  \ name, e.g. \"Oregon Grape\" or \"Sword Fern\". Used both as the Wikipedia article\
  \ title and to derive the local filename.\n- **subfolder** (optional): Subdirectory\
  \ under `logseq/assets/` to save into, e.g. `plants`. Defaults to `images`.\n\n\
  ## Workflow\n\n### Step 1 — Locate the wiki root\n\nLook for the personal wiki at\
  \ `~/Documents/personal-wiki`. Confirm it exists:\n\n```bash\nls ~/Documents/personal-wiki/logseq/assets/\
  \ 2>/dev/null && echo \"found\" || echo \"not found\"\n```\n\nIf not found, ask\
  \ the user where their wiki is.\n\n### Step 2 — Call the Wikipedia Summary API\n\
  \nUse `mcp__fetch__fetch` to call:\n\n```\nhttps://en.wikipedia.org/api/rest_v1/page/summary/{URL_ENCODED_TOPIC}\n\
  ```\n\nReplace spaces with underscores in the topic name, e.g. `Oregon_Grape`.\n\
  \nExtract from the JSON response:\n- `thumbnail.source` — the pre-rendered thumbnail\
  \ URL (standard 330px, safe to use)\n- `title` — the canonical Wikipedia title (use\
  \ for the image alt text)\n- If `thumbnail` is missing, the article may have no\
  \ image; report this to the user.\n\n### Step 3 — Derive local filename\n\nConvert\
  \ the topic to a kebab-case slug:\n- Lowercase all characters\n- Replace spaces\
  \ and underscores with hyphens\n- Remove apostrophes and special characters\n\n\
  Examples:\n- \"Oregon Grape\" → `oregon-grape`\n- \"False Solomon's Seal\" → `false-solomons-seal`\n\
  - \"Western Red Cedar\" → `western-red-cedar`\n\nAppend the file extension from\
  \ the thumbnail URL (`.jpg`, `.JPG`, `.png`, etc.).\n\nFull asset path: `~/Documents/personal-wiki/logseq/assets/{subfolder}/{slug}{ext}`\n\
  \n### Step 4 — Download with curl\n\n```bash\nmkdir -p ~/Documents/personal-wiki/logseq/assets/{subfolder}\n\
  \ncurl -L \\\n  --silent \\\n  --show-error \\\n  -H 'User-Agent: personal-wiki-image-downloader/1.0\
  \ (https://github.com/tylerstapler/personal-wiki; logseq-wiki)' \\\n  --retry 3\
  \ \\\n  --retry-delay 5 \\\n  -o \"~/Documents/personal-wiki/logseq/assets/{subfolder}/{slug}{ext}\"\
  \ \\\n  \"{thumbnail_url}\"\n```\n\n**Wikimedia bot policy compliance** (https://w.wiki/4wJS):\n\
  - Use the thumbnail URL from the API (it returns standard 330px — a compliant size)\n\
  - Do NOT construct your own thumbnail URLs; guessed filenames will fail\n- Identify\
  \ the bot properly via User-Agent\n- If you get a 429, wait for the `Retry-After`\
  \ header value before retrying\n- Do not download more than 2 files concurrently\n\
  \n### Step 5 — Return the result\n\nReport back:\n1. The local file path\n2. The\
  \ markdown embed syntax to paste into a Logseq page:\n\n```markdown\n![{Topic Name}](../assets/{subfolder}/{slug}{ext})\n\
  ```\n\nIf the page being edited is not in `logseq/pages/`, adjust the relative path\
  \ accordingly.\n\n## Bulk Downloads\n\nFor downloading images for many topics at\
  \ once, use the existing script:\n\n```bash\nuv run ~/Documents/personal-wiki/scripts/download-plant-images.py\n\
  ```\n\nTo add new entries, append to the `PLANT_MAP` list in that file:\n```python\n\
  (\"PageName.md\", \"Wikipedia_Article_Title\", \"local-slug\"),\n```\n\n## Error\
  \ Handling\n\n| Error | Action |\n|-------|--------|\n| 404 from summary API | Topic\
  \ not found on Wikipedia — try alternate title or spelling |\n| `thumbnail` missing\
  \ in response | No image on this Wikipedia article — report to user |\n| 429 on\
  \ download | Wait `Retry-After` seconds, then retry |\n| File already exists | Skip\
  \ download, return existing path |\n"
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
