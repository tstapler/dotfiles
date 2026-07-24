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

## Adding a new MCP server

MCP servers are sourced from `src/sources/mcp_config.py` (`McpConfigSource`), which
merges two files and hands the result to every target (Claude's `~/.claude.json`,
Antigravity's `mcp_config.json`, etc.) in one pass:

| File | Tracked | Use for |
|------|---------|---------|
| `.config/mcp/mcp-servers.json` (repo root) | yes | Servers every machine should get — checked in, universal |
| `~/.config/mcp/mcp-servers.local.json` | **no** (gitignored) | Machine-specific servers — secrets, tools only some machines have installed |

Both use the same schema, keyed by server name under `mcpServers`:

```json
{
  "mcpServers": {
    "some-server": {
      "command": "npx",
      "args": ["-y", "@some/mcp-package"],
      "env": { "SOME_API_KEY": "${SOME_API_KEY}" }
    }
  }
}
```

- stdio transport: `command` + `args` + `env`. HTTP transport: `type: "http"` + `url` instead.
- `disabled: true` turns an entry off without deleting it.
- Any other key (e.g. `_fork`, `_requires`) is ignored by the loader — use it as inline documentation for the entry (provenance, prerequisites, why it might fail on some machines).
- A server that depends on something not every machine has (an app, an env var, a binary on PATH) doesn't need special-casing — it just fails to start on machines without the dependency, the same way `brave-search` above silently needs `BRAVE_API_KEY`. Put it in the global file if most machines should still attempt it; put it in the local file if it's truly one-machine-only.

After editing either file, propagate with:

```bash
make llm-sync
# or: uv run --directory stapler-scripts/llm-sync main.py --force
```
