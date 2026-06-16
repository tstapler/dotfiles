# dotfiles/plugins

Claude Code plugins managed and installed by `llm-sync`. Each plugin lives in its own subdirectory and is auto-discovered by llm-sync without any manual registration.

## Current Plugins

| Plugin | Version | What it does |
|--------|---------|--------------|
| `prompt-injection-defender` | 0.1.0 | PostToolUse hook — scans every tool output (Read, WebFetch, Bash, Grep, Task, mcp__*) for prompt injection patterns. Warns Claude without blocking. Adapted from [lasso-security/claude-hooks](https://github.com/lasso-security/claude-hooks). |
| `sdd` | 0.1.0 | Stapler-Driven Development workflow. 7 numbered phase commands + skills. Enforces spec-before-code. Run `/sdd:status` to find your current phase. |
| `git-stacked-prs` | 0.1.0 | Stacked PR workflow using git-machete. Evaluate → Plan → Execute → Ship. Requires `brew install git-machete`. |

## Plugin Structure

```
plugins/
└── my-plugin/
    ├── .claude-plugin/
    │   └── plugin.json          # Required manifest
    ├── hooks/
    │   ├── hooks.json           # Hook event registrations
    │   └── my-hook.py           # Hook script(s)
    ├── commands/
    │   └── my-command.md        # Slash command definitions
    └── skills/
        └── my-skill/
            └── SKILL.md         # Skill definition
```

### `plugin.json` (required)

Minimum viable manifest:

```json
{
  "name": "my-plugin",
  "description": "What this plugin does",
  "version": "0.1.0",
  "author": {
    "name": "Tyler Stapler"
  }
}
```

### `hooks/hooks.json`

Top-level keys must be Claude Code event types (`PostToolUse`, `PreToolUse`, `Stop`, etc.) — **no outer `"hooks"` wrapper**.

```json
{
  "PostToolUse": [
    {
      "matcher": "Read",
      "hooks": [
        {
          "type": "command",
          "command": "uv run \"$HOME/dotfiles/plugins/my-plugin/hooks/my-hook.py\"",
          "timeout": 5
        }
      ]
    }
  ]
}
```

**Hook script paths**: Use `$HOME/dotfiles/plugins/<name>/hooks/<script>` (absolute). Do not use `$CLAUDE_PROJECT_DIR` — that is project-relative and will be wrong when the hook fires in other projects.

**Python hooks with dependencies**: Use `uv run` with PEP 723 inline metadata at the top of the script:

```python
# /// script
# requires-python = ">=3.8"
# dependencies = ["pyyaml"]
# ///
```

### `commands/`

Markdown files become slash commands namespaced under the plugin name. `commands/do-thing.md` → `/my-plugin:do-thing`.

Subdirectories are included: `commands/sub/thing.md` → `/my-plugin:sub/thing`.

### `skills/`

Each subdirectory containing a `SKILL.md` becomes a skill. The directory name is the skill name.

## Installation

llm-sync auto-discovers plugins at `~/dotfiles/plugins/` — no path argument needed:

```bash
# Install only plugins (hooks, commands, skills)
uv run stapler-scripts/llm-sync/main.py --plugins-only

# Preview without writing
uv run stapler-scripts/llm-sync/main.py --plugins-only --dry-run

# Full sync (agents + MCP + plugins)
uv run stapler-scripts/llm-sync/main.py
```

### What gets installed where

| Plugin asset | Installed to |
|---|---|
| Hooks | Merged into `~/.claude/settings.json` under `.hooks.<EventType>` |
| Commands | `~/.claude/commands/<plugin-name>/<command>.md` |
| Skills | `~/.claude/skills/<skill-name>/SKILL.md` |

Hooks are deduplicated by command string — reinstalling is safe and idempotent.

## Adding a New Plugin

1. Create `plugins/<name>/` directory
2. Add `.claude-plugin/plugin.json` manifest
3. Add hooks, commands, or skills as needed
4. Run `uv run stapler-scripts/llm-sync/main.py --plugins-only --dry-run` to preview
5. Run without `--dry-run` to install

## Hook Script Notes

- **PostToolUse `"block"` decision**: In PostToolUse context, outputting `{"decision": "block", "reason": "..."}` does **not** prevent tool execution (the tool already ran). It injects the `reason` string into Claude's context as a warning. This is the correct pattern for scan-and-warn hooks.
- **Exit codes**: Exit 0 always — non-zero exits are treated as errors and may suppress the hook output.
- **Timeout**: Keep hook scripts fast. Default timeout is 5 seconds. Pattern-scanning hooks should complete in < 500ms.
