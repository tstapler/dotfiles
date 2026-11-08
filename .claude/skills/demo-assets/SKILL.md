---
name: demo-assets
description: "Capture and share demo assets on a GitHub PR: terminal-recording GIFs (vhs) and PNG screenshots, including browser screenshots of web pages (Playwright). Use for 'screenshots for the PR', 'demo gif', 'attach images/gifs to a PR', 'show the UI change'. Hosts files on a throwaway orphan branch deleted after merge"
allowed-tools: Bash(vhs:*) Bash(ffmpeg:*) Bash(git:*) Bash(gh:*) Bash(npx:*) Bash(node:*)
---

# Demo assets (GIFs and screenshots) for a PR comment

Use when a PR needs visual evidence: a CLI/TUI flow (GIF) or a UI change (PNG). Posting is outward-facing:
draft the comment, get the user's approval before `gh pr comment`, and label it agent-authored if it goes out
under the user's login.

**Rule: never commit assets into the PR branch.** They live only on the `qa-assets/pr-<N>` branch (step 2).

## 1a. Record a terminal GIF

```sh
brew install vhs            # pulls ttyd; runs headless
vhs demo.tape               # tape: Output demo.gif / demo.mp4
```

- Open the tape with a title card (PR number, scenarios shown) so the clip is self-describing.
- vhs drops frames at large sizes. Use `Set Framerate 12` and about 1500x860; a 1700x950 render of a 70s run came out 15s.
- Keep the GIF under ~5 MB: trim waits with `Sleep` and shorten timeouts via env overrides. Ship the MP4 too.
- Check it: `ffmpeg -ss 25 -i demo.mp4 -frames:v 1 f.png`, then look at a few frames. Don't claim it's legible unseen.

## 1b. Capture PNG screenshots

1. **List every page, tab and state the PR changes first** (including empty, error and loading states). One
   image per state; tick each off before moving on.
2. Run the app locally, preferably against synthetic/fixture data.
3. Capture with Playwright (chromium) into `/tmp/<name>/`:

```js
// shots.js — run: npx playwright install chromium && node shots.js
const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1500, height: 1000 } });
  const shots = [['capacity', 'http://localhost:3000/capacity', '[data-testid=chart]']];
  for (const [name, url, ready] of shots) {
    await page.goto(url);
    await page.waitForSelector(ready);                 // wait for content, not a fixed sleep
    await page.addStyleTag({ content: '*,*::before,*::after{animation:none!important;transition:none!important}' });
    await page.screenshot({ path: `/tmp/pr-assets/${name}.png` });  // viewport only; fullPage only if needed
  }
  await browser.close();
})();
```

- **Naming:** kebab-case, `<page>[-<tab-or-state>].png`, e.g. `capacity.png`, `capacity-empty.png`. Names become
  URLs; no spaces or uppercase.
- **Size:** viewport screenshots, not full-page, unless the page's point is its length. If installed, shrink
  with `oxipng -o2 *.png` or `pngquant --force --ext .png 256 *.png`.
- **Look at every image** (Read the PNG) before publishing. Don't claim it's right unseen.
- **Sensitive data:** inspect each image for real hostnames, account IDs, emails, tokens, customer names or
  internal URLs in the address bar, tabs or content. Prefer fixture data; otherwise re-capture or crop. In a
  public repo anyone can see these files.

## 2. Host on a throwaway orphan branch

An orphan branch shares no history with the PR, so the PR diff and the default branch are untouched.

```sh
git worktree add --orphan -b qa-assets/pr-<N> /tmp/qa-assets-<N>   # git >= 2.42
cp /tmp/pr-assets/*.png demo.gif demo.mp4 /tmp/qa-assets-<N>/      # whichever you have
git -C /tmp/qa-assets-<N> add .
git -C /tmp/qa-assets-<N> commit -m "qa assets for PR <N> (delete after merge)"
git -C /tmp/qa-assets-<N> push origin qa-assets/pr-<N>
git worktree remove /tmp/qa-assets-<N>
```

Embed:

```md
<!-- public repo -->
![demo](https://raw.githubusercontent.com/<owner>/<repo>/qa-assets/pr-<N>/capacity.png)
<!-- private repo: raw.githubusercontent URLs need a token; use the repo-relative raw URL and check it renders -->
![demo](https://github.com/<owner>/<repo>/raw/qa-assets/pr-<N>/capacity.png)
```

For a GitHub Enterprise Server host, use `https://<host>/<owner>/<repo>/raw/...` (there is no
`raw.githubusercontent.com`).

## 3. Comment template

```md
**Screenshots (agent-captured for this PR, not the author's own words)**

| Page | Image |
|---|---|
| Capacity, default | ![capacity](<raw-url>/capacity.png) |
| Capacity, empty state | ![capacity-empty](<raw-url>/capacity-empty.png) |

Demo: ![demo](<raw-url>/demo.gif)
```

Post it, then open the PR and confirm every image renders inline. If not, fall back to drag-and-drop upload in
the comment box and delete the branch.

## 4. Clean up after merge

```sh
git push origin --delete qa-assets/pr-<N>
```

## Caveats

- **Clones fetch it.** A default `git clone`/`git fetch` downloads every branch, so the blobs ride along for
  everyone until the branch is deleted and the server garbage-collects. It is not checked out by default.
  `--single-branch` clones skip it. Delete promptly.
- Anyone with read access sees the files, and in a public repo anyone does. Don't capture secrets or tokens.
- Branch protection or push rules matching `qa-assets/*` can block the push.
- The private-repo and GHES embed URLs are untested here; the render check is mandatory.
- Simplest alternative that leaves nothing in the repo: drag the files into the PR comment box by hand.
