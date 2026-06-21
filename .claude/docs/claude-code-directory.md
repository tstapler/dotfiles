# Claude Code .claude Directory Reference
Source: https://code.claude.com/docs/en/claude-directory
Downloaded: 2026-06-21

---

## Full file reference

| File | Scope | Commit | What it does |
|------|-------|--------|--------------|
| `CLAUDE.md` | Project + global | ✓ | Instructions loaded every session |
| `rules/*.md` | Project + global | ✓ | Topic-scoped instructions, optionally path-gated |
| `settings.json` | Project + global | ✓ | Permissions, hooks, env vars, model defaults |
| `settings.local.json` | Project only | ✗ | Personal overrides, gitignored |
| `.mcp.json` | Project only | ✓ | Team-shared MCP servers |
| `.worktreeinclude` | Project only | ✓ | Gitignored files to copy into new worktrees |
| `skills/<name>/SKILL.md` | Project + global | ✓ | Reusable prompts invoked with `/name` or auto-invoked |
| `commands/*.md` | Project + global | ✓ | Single-file prompts; same mechanism as skills |
| `output-styles/*.md` | Project + global | ✓ | Custom system-prompt sections |
| `agents/*.md` | Project + global | ✓ | Subagent definitions with their own prompt and tools |
| `workflows/*.js` | Project + global | ✓ | Dynamic workflow scripts; each `/<name>` command |
| `agent-memory/<name>/` | Project + global | ✓ | Persistent memory for named subagents |
| `~/.claude.json` | Global only | ✗ | App state, OAuth, UI toggles, personal MCP servers |
| `projects/<project>/memory/` | Global only | ✗ | Auto memory: Claude's notes to itself |
| `keybindings.json` | Global only | ✗ | Custom keyboard shortcuts |
| `themes/*.json` | Global only | ✗ | Custom color themes |

---

## Where to put each type of customization

| You want to | Edit | Reference |
|-------------|------|-----------|
| Persistent project instructions | `CLAUDE.md` | Memory |
| Allow or block specific tool calls | `settings.json` permissions or hooks | Permissions |
| Run a script before/after tool calls | `settings.json` hooks | Hooks |
| Set env vars for the session | `settings.json` env | Settings |
| Personal overrides out of git | `settings.local.json` | Settings |
| Invoke a prompt with `/name` | `skills/<name>/SKILL.md` or `commands/<name>.md` | Skills |
| Specialized subagent with own tools | `agents/*.md` | Subagents |
| Orchestrate many subagents via script | `workflows/*.js` | Dynamic workflows |
| Custom system-prompt sections | `output-styles/*.md` | Output styles |
| Path-scoped conditional rules | `.claude/rules/*.md` with `paths:` frontmatter | Memory#rules |
| Connect external tools | `.mcp.json` | MCP |

---

## Application data Claude writes (auto-cleaned after 30 days by default)

| Path under `~/.claude/` | Contents |
|--------------------------|----------|
| `projects/<project>/<session>.jsonl` | Full conversation transcript |
| `projects/<project>/<session>/tool-results/` | Large tool outputs spilled to disk |
| `file-history/<session>/` | Pre-edit snapshots for checkpoint restore |
| `plans/` | Plan files from plan mode |
| `tasks/` | Per-session task lists from task tools |
| `shell-snapshots/` | Captured shell environment |

Kept indefinitely (not auto-cleaned):
- `history.jsonl` — every prompt you've typed
- `stats-cache.json` — token/cost counts for `/usage`
