---
description: Check a design doc's markdown for constructs that render wrong, drop silently, or need a manual fixup when the doc is published/synced to its actual target (Confluence via markdown-confluence, or Google Docs/Confluence via docspan) — verified by lookup against that tool's current documented behavior, not guessed. One check in the design-doc-review pipeline — run standalone or via design-doc-review:review.
---

# design-doc-review:publish-compat

Publish-target check only — this skill does not evaluate prose quality (`design-doc-review:readability`), topic coverage (`design-doc-review:outline`), or whether content should be a diagram/table (`design-doc-review:visuals`). It answers: **will this markdown still say what it says once it lands where it's actually going to be read?**

Most design docs in this repo's workflow are written in markdown but reviewed on Confluence or Google Docs after a sync step. A construct that's perfectly fine GitHub-flavored markdown can silently lose content (dropped section, broken link, image that never uploads) or render as noise (raw code fence, unrendered HTML) on the far side — and nobody notices until a reviewer is looking at the published copy, not the source the author tested.

**Target**: {{args}} — a file path, or a doc already in context.

## Step 1 — Determine the actual publish target

Do not assume. Check, in order, and stop at the first match:

1. **Frontmatter** — `connie-page-id` / `connie-last-sync-timestamp` / `connie-last-remote-version` keys (per the `confluence-markdown` skill) → target is **Confluence via `markdown-confluence`**.
2. **A `docspan.yaml` mapping** in the repo that lists this file → target is **Confluence or Google Docs via docspan** (`markdown-doc-sync` skill/agent); read the mapping entry to see which of the two.
3. **A `.confluence-config.json`** in the same directory or an ancestor → target is **Confluence via `markdown-confluence`**.
4. **An explicit statement in the doc** ("this doc will be published to Confluence/Google Docs", a Confluence/Google Docs URL already in the doc's header) → use that.
5. **None of the above** → target is plain markdown (GitHub/GitLab rendering or read in-editor). Report `status: "pass"`, `count: 0`, and one line stating no publish target was detected, so the coordinator doesn't mistake silence for "checked and clean." Do not run Step 2 against guesses.

## Step 2 — Verify constructs against the *current* tool behavior, not memory

This check's whole value is that it verifies rather than guesses — a hardcoded "known limitations" list goes stale the moment the sync tool is updated. For the target identified in Step 1:

- **Confluence via `markdown-confluence`**: re-read the `confluence-markdown` skill (`.claude/skills/confluence-markdown/SKILL.md`) and `knowledge-confluence-sync` skill/reference for the current supported-language list, frontmatter rules, and documented gotchas — these are the checked-in source of truth for this specific tool and are cheaper and more current than a web search.
- **Google Docs / Confluence via docspan**: no cached reference lives in this repo. Use `WebSearch` / the `markdown-doc-sync` skill / the markgate repo's own docs (if reachable) for docspan's current markdown-conversion limitations before flagging anything. If lookup is genuinely unavailable this run, fall back to the backend-agnostic candidate list below but **label every finding from that fallback as unverified** — don't present a guess with the same confidence as a looked-up fact (per CLAUDE.md's evidence rule).
- Cite what you checked in the finding's `note` (skill file path, or the URL you looked up) — a finding without a source the reader can check is exactly the defect CLAUDE.md's evidence rules exist to prevent, and doubly so for a check whose entire premise is "don't guess."

## Checklist — candidate constructs to verify per target

Not every item applies to every target; verify each against Step 2's source before flagging, don't flag mechanically off this list alone.

- [ ] **Content before the single H1, or multiple H1s** — Confluence's H1 becomes the page title and is stripped from the body; content placed before it, or a second H1, is silently dropped or duplicated. This is a **data-loss** bug, not cosmetic.
- [ ] **Absolute local image/file paths** — documented to silently fail to upload (per `confluence-markdown`); only relative paths from the doc's own directory are reliable.
- [ ] **Fenced code block language tag outside the target's supported set** — `markdown-confluence` documents an explicit list (python, javascript, typescript, java, go, rust, bash, shell, sql, yaml, json, xml, html, css, markdown as of the last read of that skill — re-verify, don't trust this parenthetical). A tag outside it (`kotlin`, `hcl`, `graphql`, `proto`, `mermaid`, ...) commonly falls back to unhighlighted or garbled text.
- [ ] **Diagram fences (mermaid, d2, plantuml, ...)** — verify whether the target renders the fence natively, needs a macro, or needs the diagram pre-rendered to an image and embedded instead; don't assume parity with how it renders in this session's artifact/markdown preview.
- [ ] **GitHub-flavored extras**: task-list checkboxes (`- [ ]`), footnotes (`[^1]`), `<details>/<summary>` collapsibles, strikethrough, definition lists, raw inline HTML — verify each renders as intended rather than as literal text or vanishing.
- [ ] **Internal cross-references**: markdown-relative links (`[text](./other.md)`) vs. the target's own linking convention (Confluence wiki-links `[[Page Title]]`, or a docspan-specific reference syntax) — a relative link that isn't translated at sync time is a dead link on the published copy even though it resolves fine in the source repo.
- [ ] **In-doc anchor links** (`[jump](#some-heading)`) — verify the target preserves GitHub-style heading-slug anchors; some converters regenerate anchors differently, silently breaking a TOC or "see below" link.
- [ ] **Complex tables** — merged cells, multi-line cell content, or a list nested inside a cell; verify the target's table support handles these rather than flattening or truncating them.
- [ ] **`[TOC]` / auto-TOC placement** — must be a standalone paragraph, not inside a list or code block, or it's emitted literally instead of expanding.
- [ ] **Frontmatter collisions** — hand-authored YAML keys that collide with the sync tool's auto-managed keys (`connie-*` for `markdown-confluence`, whatever docspan's own mapping keys are) get silently overwritten on next sync.

## Severity

| Severity | Meaning |
|---|---|
| `blocking` | Silent data loss or a broken link/reference on the published copy — content before the H1, an absolute image path, a dropped cross-reference, a frontmatter-key collision that overwrites sync metadata. |
| `notable` | Renders visibly wrong but the content survives — unsupported code-block language, an unrendered diagram fence, a mis-rendered collapsible/footnote, a flattened complex table. |
| `minor` | Cosmetic mismatch a reader would notice but not lose information over — anchor slug drift, TOC placement quirk. |

## Output

Write full analysis (quotes, line refs, the lookup source consulted per finding) to `/tmp/lean-design-doc-review-publish-compat-<ts>.md`.

Return only this structured summary:

```json
{
  "category": "publish-compat",
  "status": "pass" | "fail",
  "target": "confluence-markdown-confluence" | "docspan-confluence" | "docspan-google-docs" | "none-detected",
  "count": <number of blocking+notable findings>,
  "findings": [
    {"section": "§2.1", "construct": "mermaid fence", "severity": "notable", "verified": true, "source": "path or URL checked", "note": "one line: what breaks + the fix direction"}
  ]
}
```

`status: "pass"` if `target` is `"none-detected"`, or if there are zero `blocking` findings once verified. Set `"verified": false` only for the labeled-unverified fallback case in Step 2 — never omit the field.

## When invoked standalone (not via the coordinator)

Print findings as a table (Construct | Severity | Verified? | Source | Note) and state the detected target up front. Ask before editing — most fixes here (re-ordering content around the H1, swapping a code-fence language tag, converting a diagram to an image) are mechanical and safe to apply once confirmed, but a broken cross-reference or a table restructure may need the author's judgment on where content should actually land.

## False-positive guardrails — do NOT flag

- **No detected publish target.** Don't invent a target to have something to check; a doc that only ever gets read as markdown in-repo has nothing to verify against.
- **Constructs the target's own documentation explicitly supports.** Re-verify against Step 2's source before flagging — don't carry over a limitation from a different tool (e.g. a Confluence-specific gotcha doesn't automatically apply to a docspan/Google-Docs target).
- **Double-flagging table shape.** `design-doc-review:visuals` owns whether a table's *shape* (2D-ness, malformed single-row/column) is right; this check owns only whether the target's renderer can *represent* a well-formed table's shape (merged cells, nested content). Don't re-flag the same table for both.
