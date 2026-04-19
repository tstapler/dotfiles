---
name: blog-pipeline
description: Scan ~/Documents/personal-wiki (Logseq pages and journals) for blog post candidates, manage a content pipeline backlog, and move ideas through stages from candidate to published post on the personal-website Hugo blog.
---

# Blog Pipeline

Scan the personal Logseq wiki for content worth turning into blog posts, track ideas through a pipeline, and coordinate with the personal-website Hugo blog.

---

## When to Use

- User asks to "find blog post ideas" or "scan the wiki for posts"
- User wants to review what's in the blog post backlog
- User wants to move a post idea forward (outline → draft → publish)
- User asks what blog posts are in progress

---

## Pipeline Stages

| Stage | Emoji | Meaning |
|---|---|---|
| Candidate | 💡 | Identified from wiki scan, not yet committed |
| Outlined | 📋 | Has a plan.md in project_plans/blog-pipeline/<slug>/ |
| Drafting | ✍️ | Draft exists in personal-website content/blog/ (draft=true) |
| Review | 👀 | Draft complete, needs polish/proofread |
| Published | ✅ | Live on site (draft=false, pushed to master) |

---

## Tracking Location

All pipeline state lives in the **personal-website repo**:

```
/home/tstapler/Programming/personal-website/project_plans/blog-pipeline/
├── candidates.md          ← master backlog (all stages)
└── <post-slug>/
    ├── plan.md            ← created when post moves to Outlined
    └── validation.md      ← optional: outline review notes
```

Always read `candidates.md` first before any pipeline operation.

---

## Workflow: Scan Wiki for Candidates

Run when the user asks to find new blog post ideas.

### Step 1 — Scan for candidates

Search these locations in `~/Documents/personal-wiki/logseq/`:

**Pages** (`pages/*.md`): Look for files with:
- Multiple headers (structured content, not a stub)
- A complete arc: problem or context → analysis or exploration → insight or resolution
- Personal experience or opinion, not just link dumps
- Minimum ~300 words of original prose
- Technical depth relevant to: homelab, software development, AI tools, networking, infrastructure, personal productivity

**Journals** (`journals/*.md`): Look for entries with:
- A narrative that resolves (not just daily notes)
- A lesson learned or something that surprised the user
- Content that would read as a story, not a log

### Step 2 — Score each candidate

For each candidate, quickly assess:

```
TITLE: <page title or journal entry subject>
SOURCE: pages/<filename>.md OR journals/<date>.md
HOOK: one sentence — what's the interesting angle?
EFFORT: Low / Medium / High (how much writing work to turn this into a post?)
OVERLAP: Does a similar post already exist in content/blog/?
```

Disqualify if:
- It's a stub (< 200 words, no structure)
- It's a meeting/Slack export with no synthesis
- The personal-website blog already has a similar post

### Step 3 — Append to candidates.md

For each qualified candidate not already in the backlog, append an entry:

```markdown
## <Post Title>

**Stage**: 💡 Candidate
**Source**: ~/Documents/personal-wiki/logseq/pages/<filename>.md
**Hook**: <one sentence pitch>
**Effort**: Low / Medium / High
**Added**: YYYY-MM-DD
```

Report a summary to the user: N new candidates found, M already existed.

---

## Workflow: Advance a Post

When the user picks a post to work on:

### 💡 → 📋 Outlined

1. Run `/plan:mdd-start` with the post idea to generate `requirements.md`
2. Create `project_plans/blog-pipeline/<slug>/plan.md` with:
   - Target audience
   - Post structure (H2 sections with one-line descriptions)
   - Key points to hit
   - Tone notes (match existing blog voice: casual, first-person, story-driven)
3. Update `candidates.md` stage to `📋 Outlined`

### 📋 → ✍️ Drafting

1. Create `content/blog/<slug>/index.md` with Hugo frontmatter (`draft = true`)
2. Write post following the plan
3. Update `candidates.md` stage to `✍️ Drafting`

### ✍️ → 👀 Review

1. Check post against blog style (see Writing Standards below)
2. Verify all links resolve (`{{< ref >}}` targets exist)
3. Update `candidates.md` stage to `👀 Review`

### 👀 → ✅ Published

1. Set `draft = false` in frontmatter
2. Commit and push to master
3. Update `candidates.md` stage to `✅ Published` with publish date

---

## Workflow: Review Backlog

When the user asks "what's in the pipeline":

1. Read `candidates.md`
2. Group by stage and report a table
3. Flag any post that's been in the same stage for > 30 days (calculate from Added date)

---

## Writing Standards (Personal Blog Voice)

Match the tone of existing posts in `content/blog/`:

- **First person**, casual register — "I found", "I noticed", not passive voice
- **Start with a concrete problem** — not definitions, not background
- **Tell what happened** — narrative over exposition
- **Short sections** — H2s every 200-300 words
- **Show the thing** — tables, command output, screenshots referenced where useful
- **Honest about tradeoffs** — don't oversell the solution
- **End with a takeaway** — one or two sentences, not a bulleted summary

---

## Hugo Frontmatter Template

```toml
+++
title = ""
description = ""  # under 160 chars, SEO-focused
summary = ""      # 2-3 sentence teaser for post listings
categories = [""]
tags = [""]
date = "YYYY-MM-DD"
draft = true
+++
```

---

## Files to Check

| Purpose | Path |
|---|---|
| Pipeline backlog | `/home/tstapler/Programming/personal-website/project_plans/blog-pipeline/candidates.md` |
| Wiki pages | `~/Documents/personal-wiki/logseq/pages/` |
| Wiki journals | `~/Documents/personal-wiki/logseq/journals/` |
| Published posts | `/home/tstapler/Programming/personal-website/content/blog/` |
