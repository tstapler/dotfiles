---
name: hooker
description: Design, write, and manage Claude Code hooks. Scans conversation history to identify what hooks you need, applies layered analysis to classify controls by severity, and generates performant hookify-compatible rule files with correct deduplication strategies.
---

# Hooker — Claude Code Hook Designer

Design, write, and manage Claude Code hooks with history-driven pattern detection and layered control analysis.

## When to Use

- You want to know what hooks you *should* have based on past session behavior
- Writing a new hook and want the correct event type, matcher, async flag, and dedup strategy
- An existing hook is firing too slowly, blocking Claude, or firing twice
- You want to understand what control layer a behavior belongs to before writing anything

## Don't Use For

- General settings.json changes → `update-config` skill
- Debugging why a hook is erroring (check stderr output in the JSONL) → `code-debugging` skill
- Syncing hooks across platforms — hookify rules are intentionally local (`*.local.md`) and cannot sync to Gemini/OpenCode

---

## Commands

| Command | What It Does |
|---------|-------------|
| `/hooker` | Full workflow: scan history → layered analysis → generate hook files |
| `/hooker:scan` | History scan only — returns a findings table, no files written |
| `/hooker:write <description>` | Write one specific hook from a plain-language description |
| `/hooker:dedup <hook-file>` | Retrofit deduplication onto an existing hook script |

---

## Core Workflow (Full `/hooker` Run)

### Phase 1 — History Scan

Determine the current project's conversation directory:

```
Project slug = working directory path with / replaced by - (e.g. /home/user/dotfiles → -home-user-dotfiles)
History path = ~/.claude/projects/<slug>/*.jsonl
```

For each JSONL file, parse these event types:

**Signal extraction targets:**

| Signal | JSONL pattern | Severity |
|--------|--------------|----------|
| Explicit user correction | `type:"user"` message text contains: *no, don't, wait, undo, wrong, revert, stop* | High |
| Tool retry loop | Same `tool_use.name` + near-identical `input` appearing 2+ times in sequence | High |
| Hook already firing | `type:"attachment", attachment.type:"hook_success"` — notes what already exists | Info |
| Bash danger patterns | `tool_use.name:"Bash"`, `input.command` matches `rm -rf|chmod 777|curl.*\|.*sh|eval|exec` | High |
| Sensitive file touch | `tool_use.name:"Write"/"Edit"`, `input.file_path` matches `\.env|credentials|secrets|\.pem` | High |
| Same file edited repeatedly | Same `file_path` appearing in 3+ Edit/Write calls in one session | Medium |
| Stop then continue | `type:"user"` text contains *actually|wait|one more* after an assistant `end_turn` | Medium |
| Unapproved tool denied | Permission denial events | Medium |

Build a **findings table** from all sessions (last 30 days):

```
Pattern | Frequency | Example | Suggested Layer | Candidate Hook
```

For full scanning implementation: see `references/history-scanning.md`

---

### Phase 2 — Layered Analysis

Classify each finding into one of four control layers. Each layer maps to different event types and default actions:

| Layer | Control Type | Primary Events | Default Action |
|-------|-------------|----------------|----------------|
| **L1 Protection** | Block dangerous operations before they happen | `PreToolUse` | `block` |
| **L2 Quality** | Warn on standards violations after writes | `PostToolUse` | `warn` |
| **L3 Workflow** | Enforce checklists and completion criteria | `Stop` | `block` |
| **L4 Intelligence** | Inject context and capture session state | `UserPromptSubmit`, `Stop` | `warn` |

For full layer definitions and decision trees: see `references/layered-analysis.md`

**Layer assignment rules:**
- High severity + happens before damage is done → L1
- High severity + detected after the fact → L2
- Relates to "Claude stopped but shouldn't have" → L3
- Relates to repetitive context injection or session memory → L4
- When in doubt: warn before block; L2 before L1

---

### Phase 3 — Hook Design

For each candidate hook, determine:

**1. Event type** (from layer assignment above)

**2. Matcher/if fields** (always use both when possible — they're evaluated before spawning a process):
```yaml
# In settings.json hook entry:
matcher: "Bash"          # tool name exact match — cheapest filter
if: "bash"               # hookify event alias
```

**3. Async vs sync:**
- `async: true` if the hook does not need to block Claude (notifications, logging, memory writes)
- Sync (default) only if the hook must block/redirect (protection, blocking quality gates)

**4. Dedup strategy** (assign one of three):

| Strategy | When | Implementation |
|----------|------|----------------|
| **None needed** | Config-level dedup handles it (same command in one settings file) | Nothing to do |
| **Time-window** | Bug-level double-firing (CWD=~ issue, dual plugin loading) | File lock + epoch check in script |
| **Semantic hash** | Prevent redundant work on equivalent inputs | SHA256 of relevant input fields → state file |

For complete dedup implementation patterns: see `references/hook-patterns.md`

**5. Output format** — always generate hookify-compatible files:

```
~/.claude/hookify.{kebab-name}.local.md
```

This integrates with hookify's `/hookify:list` and `/hookify:configure` commands.

---

### Phase 4 — Generate Hook Files

Write one `.claude/hookify.{name}.local.md` per hook using this structure:

```markdown
---
name: {kebab-case-name}
enabled: true
event: {bash|file|stop|prompt}
action: {warn|block}
pattern: {python-regex}     # simple format — OR use conditions below
conditions:                  # advanced format
  - field: {command|file_path|new_text|content}
    operator: {regex_match|contains|equals|not_contains|starts_with|ends_with}
    pattern: {value}
---

{Human-readable message shown when rule triggers. Markdown supported.}

**Why this rule exists**: {one sentence from the history scan finding}
**Dedup strategy**: {None|Time-window N seconds|Semantic hash on field}
**Layer**: {L1 Protection|L2 Quality|L3 Workflow|L4 Intelligence}
```

For hooks requiring external scripts (complex logic, async operations, dedup state files):

```markdown
---
name: {name}
enabled: true
event: bash
action: warn
conditions:
  - field: command
    operator: regex_match
    pattern: {pattern}
---

{Message body}
```

Plus a companion script at `~/.claude/hooks/{name}.sh` or `.py`.

For script templates with dedup built in: see `references/hook-patterns.md`

---

## `/hooker:scan` — Scan Only

Run Phase 1 only. Output the findings table to the conversation — no files written. Use when you want to understand what patterns exist before committing to hook design.

---

## `/hooker:write <description>` — Single Hook

Skip history scan. Take the plain-language description and:

1. Identify the layer (ask if ambiguous)
2. Determine event type, matcher, async flag, dedup strategy
3. Write the hookify rule file
4. If the logic needs a script, write that too

Example: `/hooker:write block bash commands that pipe curl output to sh`

---

## `/hooker:dedup <hook-file>` — Retrofit Dedup

Read an existing hook script or rule file. Identify which of the three dedup problems applies. Add the appropriate strategy without changing the hook's logic.

---

## Quality Checklist (Apply to Every Generated Hook)

- [ ] Uses `matcher`/`if` field to avoid unnecessary subprocess spawns
- [ ] Async flag matches whether Claude needs to wait for the result
- [ ] Dedup strategy chosen and documented in the rule body
- [ ] Action is `warn` before escalating to `block` unless the risk is clear
- [ ] Pattern uses Python regex syntax (hookify's rule engine compiles with `re`)
- [ ] File is named `hookify.{kebab-name}.local.md` (gitignored by default)
- [ ] Message body explains the why, not just the what

## References (Load On Demand)

- `references/hook-patterns.md` — UV script templates, dedup implementations, `matcher`/`if` field reference
- `references/layered-analysis.md` — Full layer definitions, decision tree, example rules per layer
- `references/history-scanning.md` — JSONL schema, signal extraction logic, scoring heuristics
