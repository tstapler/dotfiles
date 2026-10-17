---
description: Capture instincts from this session into MEMORY.md and optionally into Logseq wiki
---

# Extract Session Learnings

This command captures what was learned in this session and writes durable instincts to the appropriate memory layer. Run at the end of any session where something worth keeping was discovered.

## Memory Layers

| Layer | File | Scope | What Goes Here |
|---|---|---|---|
| Global | `~/.claude/MEMORY.md` | All projects, all time | Tool preferences, workflow patterns, anti-patterns, universal instincts |
| Project | `~/.claude/projects/.../memory/MEMORY.md` | This project only | Project-specific conventions, file locations, gotchas |
| Wiki | `logseq/journals/<today>.md` | Chronological | Session narrative, decisions made, concepts worth wikifying |

## Step 1: Extract Learnings

**Default to deriving them from context; do not ask.** Only ask the user "What are the 3–7 most useful things you learned or confirmed in this session?" when the invocation is interactive *and* the conversation holds too little to go on. When called from another workflow (e.g. `/sdd:7-ship` step 7) or by an autonomous agent, never block on this question.

Review the conversation and identify:
- Decisions made (and why)
- Patterns confirmed or refuted
- Tools/commands that worked well or poorly
- Architectural choices and their rationale
- Anti-patterns encountered
- Anything surprising or non-obvious

## Step 2: Classify Each Learning

For each learning, classify it:

- **Global instinct** → applies regardless of project (e.g., "always check X before doing Y")
- **Project instinct** → specific to this repo/context (e.g., "in this repo, migrations live in X")
- **Wiki candidate** → a concept worth a Zettelkasten note (e.g., a named pattern, framework, or decision)

## Step 3: Write Global Instincts

Append to `~/.claude/MEMORY.md`:

```markdown
## <Category or Topic>

- **<Instinct title>**: <1–2 sentence description of what was learned and why it matters>
```

**MEMORY.md rules:**
- Keep entries under 200 lines total — if approaching limit, move old sections to topic files in `~/.claude/projects/`
- Use present tense, active voice
- Every entry should answer: "what should I do differently next time?"
- Do NOT add session-specific context (current task details, temp state)

## Step 4: Write Project Instincts

If project-specific learnings exist, append to the project memory file.

Use the current project's memory directory (the one named in the session's auto-memory instructions, `~/.claude/projects/<project-slug>/memory/`), not a hard-coded slug.

Write one file per fact, with frontmatter, then add a one-line pointer to that directory's `MEMORY.md` index (index lines only, never content):

```markdown
---
name: <short-kebab-case-slug>
description: <one-line summary used to decide relevance>
metadata:
  type: project | feedback | reference | user
---

<the fact; for feedback/project add **Why:** and **How to apply:** lines>
```

Before writing, check for an existing file covering the same fact and update it instead of duplicating. Skip anything the repo already records (code, git history, CLAUDE.md).

## Step 5: Logseq Journal Entry (Optional)

Add the journal entry by default when the wiki repo exists; ask "Add a session summary to today's Logseq journal? (y/n)" only in an interactive run with no clear signal. Skip silently if `$(wiki_path)/logseq/journals` is missing.

**Locating the Logseq library**: Default path is `~/Documents/personal-wiki/logseq`. A shell function `wiki_path` (in `~/.shell/functions.sh`) returns the wiki root; the logseq subdirectory is `$(wiki_path)/logseq`. Today's journal is at `$(wiki_path)/logseq/journals/$(date +%Y_%m_%d).md`.

If yes, append to the journal file:

```markdown
- Session: <brief 1-line description of what was worked on>
  - Key decisions: <bullet list>
  - Artifacts created: <files written, if any>
  - Learnings: [[Needs Synthesis]] if complex enough to deserve a zettel
```

## Step 6: Surface Wiki Candidates

Decide from context which concepts deserve a permanent note (ask only in an interactive run). For each one chosen:
- Check if `logseq/pages/<Concept Name>.md` already exists
- If missing, create a stub with `[[Needs Synthesis]]` tag
- Use `/knowledge:create_zettle` or `/knowledge:synthesize-knowledge` in a fresh session to flesh it out

## Unattended runs

When invoked from another workflow, finish all steps without prompting, make the classification decisions yourself, and report in the Output format below. Stop for the user only on a genuinely blocking ambiguity (e.g. the memory directory cannot be determined).

## Output

After running, report:
- How many global instincts were written
- How many project instincts were written
- Whether a journal entry was added
- Any wiki stubs created

Example:
```
=== Session Learnings Captured ===
✓ 3 global instincts → ~/.claude/MEMORY.md
✓ 2 project instincts → project MEMORY.md
✓ Journal entry → logseq/journals/2026_04_02.md
○ 1 wiki candidate flagged → logseq/pages/MDD Phase Gates.md (stub)
```

