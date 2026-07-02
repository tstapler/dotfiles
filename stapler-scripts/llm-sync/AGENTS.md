# LLM Sync Agent

This project syncs LLM agents, skills, and commands from Claude to Gemini (legacy), Antigravity, and OpenCode.

## Running the Project

Use `uv` to run the project. This ensures dependencies are managed correctly.

```bash
uv run main.py --help
```

## Features

- **Namespacing:** Preserves directory structures for agents, skills, and commands (e.g., `git/commit`).
- **Tool Mapping:** Automatically maps Claude tool names to Gemini/OpenCode/Antigravity equivalents.
- **Metadata Overrides:** Supports overriding default values (like model, temperature, mode) via YAML frontmatter.
- **Recursive Directory Creation:** Ensures nested structures are synced correctly.
- **Custom Paths:** Use `--source-dir`, `--gemini-dir`, `--antigravity-dir`, or `--opencode-dir` to sync to local project folders.
- **Plugin Installer:** Installs plugins globally or locally into both Claude (`.claude/`) and Antigravity (`.agents/` or `~/.gemini/config/plugins/`).
- **MCP Server Sync:** Syncs Model Context Protocol configs to both Claude (`~/.claude.json`) and Antigravity (`~/.gemini/antigravity-cli/mcp_config.json`).

## Configuration References

### Claude Code
- **Skills:** https://docs.anthropic.com/en/docs/claude-code/skills
- **Location:** `.claude/skills/<name>/SKILL.md`, `.claude/commands/<name>.md`

### OpenCode
- **Agents:** https://opencode.ai/docs/agents/
- **Location:** `~/.config/opencode/agents/<name>.md`

### Gemini CLI (Legacy)
- **Configuration:** https://github.com/google-gemini/gemini-cli/blob/main/docs/reference/configuration.md
- **Location:** `.gemini/agents/*.md`, `.gemini/skills/*/SKILL.md`, `.gemini/commands/*.toml`

### Antigravity
- **Customizations Root:** `~/.gemini/config` (global) or `.agents` (workspace)
- **Skills:** `~/.gemini/config/skills/<name>/SKILL.md` (Note: commands sync as skills here)
- **Agents:** `~/.gemini/config/agents/<name>.md`
- **Plugins:** `~/.gemini/config/plugins/<name>/` (containing `plugin.json`, `skills/`, `hooks.json`)
- **MCP Config:** `~/.gemini/antigravity-cli/mcp_config.json`
