---
description: Capture instincts from this session into MEMORY.md and optionally into
  Logseq wiki
prompt: "# Extract Session Learnings\n\nThis command captures what was learned in\
  \ this session and writes durable instincts to the appropriate memory layer. Run\
  \ at the end of any session where something worth keeping was discovered.\n\n##\
  \ Memory Layers\n\n| Layer | File | Scope | What Goes Here |\n|---|---|---|---|\n\
  | Global | `~/.claude/MEMORY.md` | All projects, all time | Tool preferences, workflow\
  \ patterns, anti-patterns, universal instincts |\n| Project | `~/.claude/projects/.../memory/MEMORY.md`\
  \ | This project only | Project-specific conventions, file locations, gotchas |\n\
  | Wiki | `logseq/journals/<today>.md` | Chronological | Session narrative, decisions\
  \ made, concepts worth wikifying |\n\n## Step 1: Extract Learnings\n\nAsk the user:\
  \ **\"What are the 3–7 most useful things you learned or confirmed in this session?\"\
  **\n\nIf the user says \"figure it out from context\", review the conversation and\
  \ identify:\n- Decisions made (and why)\n- Patterns confirmed or refuted\n- Tools/commands\
  \ that worked well or poorly\n- Architectural choices and their rationale\n- Anti-patterns\
  \ encountered\n- Anything surprising or non-obvious\n\n## Step 2: Classify Each\
  \ Learning\n\nFor each learning, classify it:\n\n- **Global instinct** → applies\
  \ regardless of project (e.g., \"always check X before doing Y\")\n- **Project instinct**\
  \ → specific to this repo/context (e.g., \"in this repo, migrations live in X\"\
  )\n- **Wiki candidate** → a concept worth a Zettelkasten note (e.g., a named pattern,\
  \ framework, or decision)\n\n## Step 3: Write Global Instincts\n\nAppend to `~/.claude/MEMORY.md`:\n\
  \n```markdown\n## <Category or Topic>\n\n- **<Instinct title>**: <1–2 sentence description\
  \ of what was learned and why it matters>\n```\n\n**MEMORY.md rules:**\n- Keep entries\
  \ under 200 lines total — if approaching limit, move old sections to topic files\
  \ in `~/.claude/projects/`\n- Use present tense, active voice\n- Every entry should\
  \ answer: \"what should I do differently next time?\"\n- Do NOT add session-specific\
  \ context (current task details, temp state)\n\n## Step 4: Write Project Instincts\n\
  \nIf project-specific learnings exist, append to the project memory file.\n\nFind\
  \ the project memory path: `~/.claude/projects/<project-slug>/memory/MEMORY.md`\n\
  \nFor the personal-wiki project: `~/.claude/projects/-Users-tylerstapler-Documents-personal-wiki/memory/MEMORY.md`\n\
  \n## Step 5: Logseq Journal Entry (Optional)\n\nAsk: **\"Add a session summary to\
  \ today's Logseq journal? (y/n)\"**\n\n**Locating the Logseq library**: Default\
  \ path is `~/Documents/personal-wiki/logseq`. A shell function `wiki_path` (in `~/.shell/functions.sh`)\
  \ returns the wiki root; the logseq subdirectory is `$(wiki_path)/logseq`. Today's\
  \ journal is at `$(wiki_path)/logseq/journals/$(date +%Y_%m_%d).md`.\n\nIf yes,\
  \ append to the journal file:\n\n```markdown\n- Session: <brief 1-line description\
  \ of what was worked on>\n  - Key decisions: <bullet list>\n  - Artifacts created:\
  \ <files written, if any>\n  - Learnings: [[Needs Synthesis]] if complex enough\
  \ to deserve a zettel\n```\n\n## Step 6: Surface Wiki Candidates\n\nAsk: **\"Any\
  \ concepts from this session worth turning into a permanent Zettelkasten note?\"\
  **\n\nIf yes, for each concept:\n- Check if `logseq/pages/<Concept Name>.md` already\
  \ exists\n- If missing, create a stub with `[[Needs Synthesis]]` tag\n- Use `/knowledge:create_zettle`\
  \ or `/knowledge:synthesize-knowledge` in a fresh session to flesh it out\n\n##\
  \ Output\n\nAfter running, report:\n- How many global instincts were written\n-\
  \ How many project instincts were written\n- Whether a journal entry was added\n\
  - Any wiki stubs created\n\nExample:\n```\n=== Session Learnings Captured ===\n\
  ✓ 3 global instincts → ~/.claude/MEMORY.md\n✓ 2 project instincts → project MEMORY.md\n\
  ✓ Journal entry → logseq/journals/2026_04_02.md\n○ 1 wiki candidate flagged → logseq/pages/MDD\
  \ Phase Gates.md (stub)\n```\n"
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

Ask the user: **"What are the 3–7 most useful things you learned or confirmed in this session?"**

If the user says "figure it out from context", review the conversation and identify:
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

Find the project memory path: `~/.claude/projects/<project-slug>/memory/MEMORY.md`

For the personal-wiki project: `~/.claude/projects/-Users-tylerstapler-Documents-personal-wiki/memory/MEMORY.md`

## Step 5: Logseq Journal Entry (Optional)

Ask: **"Add a session summary to today's Logseq journal? (y/n)"**

**Locating the Logseq library**: Default path is `~/Documents/personal-wiki/logseq`. A shell function `wiki_path` (in `~/.shell/functions.sh`) returns the wiki root; the logseq subdirectory is `$(wiki_path)/logseq`. Today's journal is at `$(wiki_path)/logseq/journals/$(date +%Y_%m_%d).md`.

If yes, append to the journal file:

```markdown
- Session: <brief 1-line description of what was worked on>
  - Key decisions: <bullet list>
  - Artifacts created: <files written, if any>
  - Learnings: [[Needs Synthesis]] if complex enough to deserve a zettel
```

## Step 6: Surface Wiki Candidates

Ask: **"Any concepts from this session worth turning into a permanent Zettelkasten note?"**

If yes, for each concept:
- Check if `logseq/pages/<Concept Name>.md` already exists
- If missing, create a stub with `[[Needs Synthesis]]` tag
- Use `/knowledge:create_zettle` or `/knowledge:synthesize-knowledge` in a fresh session to flesh it out

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
