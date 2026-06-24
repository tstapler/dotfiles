---
description: Report what's consuming your Claude Code context window — token estimates,
  loaded files, MCP servers
prompt: '# Context Budget Audit


  Context is a finite budget. This command reports what''s consuming it and surfaces
  opportunities to trim.


  ## Step 0: Locate Key Paths


  The Logseq wiki is at `~/Documents/personal-wiki/logseq` by default. A shell function
  `logseq_path` (defined in `~/.shell/functions.sh`) returns the path, respecting
  the `$LOGSEQ_PATH` env var override if set. The wiki root (one level up) is returned
  by `wiki_path`.


  ```bash

  # If the shell function is available:

  source ~/.shell/functions.sh && logseq_path   # → ~/Documents/personal-wiki/logseq

  source ~/.shell/functions.sh && wiki_path     # → ~/Documents/personal-wiki

  ```


  Default fallbacks if shell functions unavailable:

  - **Logseq library**: `~/Documents/personal-wiki/logseq`

  - **Wiki root**: `~/Documents/personal-wiki`

  - **Today''s journal**: `$(wiki_path)/logseq/journals/$(date +%Y_%m_%d).md`


  ## Step 1: Measure Always-Loaded Files


  Use word count to estimate tokens (1 token ≈ 0.75 words, so words × 1.33 ≈ tokens):


  ```bash

  wc -w ~/.claude/CLAUDE.md ~/.claude/skills-index.md ~/.claude/STAPLER.md 2>/dev/null

  wc -w ~/.claude/projects/*/memory/MEMORY.md 2>/dev/null | tail -5

  ```


  Also check the project-local CLAUDE.md if in a project:

  ```bash

  wc -w CLAUDE.md 2>/dev/null

  ```


  ## Step 2: Count Skills


  ```bash

  ls ~/.claude/skills/ | wc -l

  ls ~/.claude/commands/ -R | grep "\.md$" | wc -l

  ```


  ## Step 3: Check MCP Servers


  Read `~/.claude/settings.json` or `~/.claude/claude_desktop_config.json` (whichever
  exists) and count configured MCP servers.


  ## Step 4: Build Report


  Output a formatted table:


  ```

  === Context Budget Report ===


  Always-Loaded Files

  ───────────────────

  ~/.claude/CLAUDE.md          ~XXX tokens

  ~/.claude/skills-index.md    ~XXX tokens

  ~/.claude/STAPLER.md         ~XXX tokens  (if present)

  MEMORY.md (global)           ~XXX tokens

  MEMORY.md (project)          ~XXX tokens  (if present)

  Project CLAUDE.md            ~XXX tokens  (if in project)

  ───────────────────

  Subtotal (always loaded):    ~XXXX tokens


  Registered Resources

  ────────────────────

  Skills available:            XX files

  Commands available:          XX files

  MCP servers:                 XX configured


  Total context overhead:      ~XXXX tokens

  Estimated % of 200k budget:  X.X%


  === Recommendations ===

  [Generated based on findings]

  ```


  ## Step 5: Generate Recommendations


  Apply these rules to generate recommendations:


  - **If CLAUDE.md > 3000 tokens**: "Consider using `@`-references to external files
  instead of inline content. Run `/meta:refine-claude-md` to compress."

  - **If skills-index.md > 4000 tokens**: "skills-index.md is large. Consider splitting
  into domain-specific index files loaded conditionally."

  - **If STAPLER.md > 5000 tokens**: "STAPLER.md is large. Consider a 1-page summary
  version for always-loaded context."

  - **If MEMORY.md > 2000 tokens**: "MEMORY.md is approaching the 200-line limit.
  Archive older entries to a dated topic file."

  - **If total > 20,000 tokens**: "Always-loaded context exceeds 10% of a 200k window.
  This will consistently crowd out working context."

  - **If total < 8,000 tokens**: "Context overhead is healthy. No action needed."


  ## Output Format


  Use this structure:

  1. The metrics table (always)

  2. A brief "what''s largest" callout

  3. Numbered recommendations (only if issues found)

  4. A one-line summary verdict: healthy / watch / trim needed

  '
---

# Context Budget Audit

Context is a finite budget. This command reports what's consuming it and surfaces opportunities to trim.

## Step 0: Locate Key Paths

The Logseq wiki is at `~/Documents/personal-wiki/logseq` by default. A shell function `logseq_path` (defined in `~/.shell/functions.sh`) returns the path, respecting the `$LOGSEQ_PATH` env var override if set. The wiki root (one level up) is returned by `wiki_path`.

```bash
# If the shell function is available:
source ~/.shell/functions.sh && logseq_path   # → ~/Documents/personal-wiki/logseq
source ~/.shell/functions.sh && wiki_path     # → ~/Documents/personal-wiki
```

Default fallbacks if shell functions unavailable:
- **Logseq library**: `~/Documents/personal-wiki/logseq`
- **Wiki root**: `~/Documents/personal-wiki`
- **Today's journal**: `$(wiki_path)/logseq/journals/$(date +%Y_%m_%d).md`

## Step 1: Measure Always-Loaded Files

Use word count to estimate tokens (1 token ≈ 0.75 words, so words × 1.33 ≈ tokens):

```bash
wc -w ~/.claude/CLAUDE.md ~/.claude/skills-index.md ~/.claude/STAPLER.md 2>/dev/null
wc -w ~/.claude/projects/*/memory/MEMORY.md 2>/dev/null | tail -5
```

Also check the project-local CLAUDE.md if in a project:
```bash
wc -w CLAUDE.md 2>/dev/null
```

## Step 2: Count Skills

```bash
ls ~/.claude/skills/ | wc -l
ls ~/.claude/commands/ -R | grep "\.md$" | wc -l
```

## Step 3: Check MCP Servers

Read `~/.claude/settings.json` or `~/.claude/claude_desktop_config.json` (whichever exists) and count configured MCP servers.

## Step 4: Build Report

Output a formatted table:

```
=== Context Budget Report ===

Always-Loaded Files
───────────────────
~/.claude/CLAUDE.md          ~XXX tokens
~/.claude/skills-index.md    ~XXX tokens
~/.claude/STAPLER.md         ~XXX tokens  (if present)
MEMORY.md (global)           ~XXX tokens
MEMORY.md (project)          ~XXX tokens  (if present)
Project CLAUDE.md            ~XXX tokens  (if in project)
───────────────────
Subtotal (always loaded):    ~XXXX tokens

Registered Resources
────────────────────
Skills available:            XX files
Commands available:          XX files
MCP servers:                 XX configured

Total context overhead:      ~XXXX tokens
Estimated % of 200k budget:  X.X%

=== Recommendations ===
[Generated based on findings]
```

## Step 5: Generate Recommendations

Apply these rules to generate recommendations:

- **If CLAUDE.md > 3000 tokens**: "Consider using `@`-references to external files instead of inline content. Run `/meta:refine-claude-md` to compress."
- **If skills-index.md > 4000 tokens**: "skills-index.md is large. Consider splitting into domain-specific index files loaded conditionally."
- **If STAPLER.md > 5000 tokens**: "STAPLER.md is large. Consider a 1-page summary version for always-loaded context."
- **If MEMORY.md > 2000 tokens**: "MEMORY.md is approaching the 200-line limit. Archive older entries to a dated topic file."
- **If total > 20,000 tokens**: "Always-loaded context exceeds 10% of a 200k window. This will consistently crowd out working context."
- **If total < 8,000 tokens**: "Context overhead is healthy. No action needed."

## Output Format

Use this structure:
1. The metrics table (always)
2. A brief "what's largest" callout
3. Numbered recommendations (only if issues found)
4. A one-line summary verdict: healthy / watch / trim needed
