# Claude Code Commands & Skills Reference
Sources: https://code.claude.com/docs/en/skills, https://code.claude.com/docs/en/slash-commands
Downloaded: 2026-06-21

---

## Frontmatter fields (complete reference)

| Field | Description |
|-------|-------------|
| `name` | Display name in skill listings. Does NOT change the invoke command (except plugin-root SKILL.md). |
| `description` | What the skill does. Claude auto-invokes based on this. Combined with `when_to_use`, truncated at 1,536 chars. **Put the key use case first.** |
| `when_to_use` | Additional trigger phrases/examples. Appended to `description`, counts toward 1,536-char cap. |
| `argument-hint` | Shown during autocomplete. e.g. `[issue-number]` or `[filename] [format]` |
| `arguments` | Named positional args for `$name` substitution. Space-separated or YAML list. Maps names to positions. |
| `disable-model-invocation` | `true` = user-only trigger. Hides from Claude's context entirely; also prevents preloading into subagents. |
| `user-invocable` | `false` = hide from `/` menu (Claude can still auto-invoke). **NOT the same as `disable-model-invocation`.** |
| `allowed-tools` | ⚠️ **Pre-approves without per-use prompts ONLY. Does NOT restrict other tools.** Comma or space separated. Example: `Bash(git add *) Bash(git commit *)` |
| `disallowed-tools` | **Actually restricts** — removes tools from available pool while skill active. Clears on next user message. |
| `model` | Overrides model for this skill's turn only. Accepts same values as `/model` or `inherit`. |
| `effort` | `low` / `medium` / `high` / `xhigh` / `max`. Overrides session effort for this skill. |
| `context` | `fork` = run in isolated subagent. Skill content becomes the subagent prompt. No access to conversation history. |
| `agent` | Which agent type when `context: fork`. Built-ins: `Explore`, `Plan`, `general-purpose`. Or any custom agent from `.claude/agents/`. |
| `hooks` | Hooks scoped to this skill's lifecycle. |
| `paths` | Glob patterns — skill only auto-activates when Claude works with matching files. e.g. `"src/api/**/*.ts"` |
| `shell` | `bash` (default) or `powershell` for `!`command`` blocks. |

---

## String substitutions

| Variable | Description |
|----------|-------------|
| `$ARGUMENTS` | All args as typed. If not in content, appended as `ARGUMENTS: <value>` automatically. |
| `$ARGUMENTS[0]` | First positional arg (0-based). |
| `$N` | Shorthand: `$0` = first, `$1` = second (legacy syntax — prefer `$ARGUMENTS[N]`). |
| `$name` | Named arg declared via `arguments` frontmatter. |
| `${CLAUDE_SESSION_ID}` | Current session ID. Useful for log files, session-specific artifacts. |
| `${CLAUDE_EFFORT}` | Current effort level: `low` / `medium` / `high` / `xhigh` / `max`. Ultracode reports as `xhigh`. |
| `${CLAUDE_SKILL_DIR}` | Directory containing the SKILL.md. For referencing bundled scripts. |

Escape a literal `$`: write `\$1.00`.

---

## Shell preprocessing with `!`command``

Runs a shell command **before** Claude sees the skill — output replaces the placeholder inline:

```markdown
## Current git state
!`git diff HEAD --stat`

## Requirements
!`cat project_plans/my-project/requirements.md`
```

Multi-line variant (fenced block opened with ` ```! `):
````
```!
git status --short
node --version
```
````

- Executes once at invocation time, not during the conversation
- `!` must appear at start of line or after whitespace
- Can be disabled globally with `"disableSkillShellExecution": true` in settings
- Include `ultrathink` anywhere in content to trigger deep reasoning for that skill run

---

## `context: fork` + `agent: Explore`

```yaml
---
name: deep-research
description: Research a topic thoroughly
context: fork
agent: Explore
---

Research $ARGUMENTS thoroughly:
1. Find relevant files using Glob and Grep
2. Read and analyze the code
3. Summarize findings with specific file references
```

- Skill content becomes the subagent prompt
- `Explore` agent skips CLAUDE.md and git status — smaller, faster context
- No access to conversation history (truly isolated)

---

## Key behavioral notes

- **`user-invocable: true`** — officially supported, controls `/` menu visibility. Claude can still auto-invoke.
- **`disable-model-invocation: true`** — removes skill from Claude's context entirely; user-only.
- **`allowed-tools`** — pre-approves (no permission prompts), does NOT restrict. Other tools still callable with prompts.
- **`disallowed-tools`** — actually removes tools from available pool for that skill invocation.
- Skill content enters conversation as a single message and **stays for the rest of the session**.
- After `/compact`, the most recent invocation of each skill is re-attached (first 5,000 tokens each, 25,000 token shared budget).

---

## .claude directory structure

| File | Scope | Committed | What it does |
|------|-------|-----------|--------------|
| `CLAUDE.md` | Project + global | ✓ | Instructions loaded every session |
| `rules/*.md` | Project + global | ✓ | Topic-scoped instructions, optionally path-gated via `paths:` frontmatter |
| `settings.json` | Project + global | ✓ | Permissions, hooks, env vars, model defaults |
| `settings.local.json` | Project only | ✗ | Personal overrides (gitignored) |
| `.mcp.json` | Project only | ✓ | Team-shared MCP servers |
| `skills/<name>/SKILL.md` | Project + global | ✓ | Reusable prompts invoked with `/name` or auto-invoked |
| `commands/*.md` | Project + global | ✓ | Single-file prompts; same mechanism as skills |
| `output-styles/*.md` | Project + global | ✓ | Custom system-prompt sections |
| `agents/*.md` | Project + global | ✓ | Subagent definitions with their own prompt and tools |
| `workflows/*.js` | Project + global | ✓ | Dynamic workflow scripts; each file becomes a `/<name>` command |
| `agent-memory/<name>/` | Project + global | ✓ | Persistent memory for named subagents |

Note: `commands/*.md` and `skills/<name>/SKILL.md` are equivalent. Skills take precedence on name collision.
