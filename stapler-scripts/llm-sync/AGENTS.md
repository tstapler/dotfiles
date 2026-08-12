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
  - **`$ARGUMENTS` limitation:** Antigravity skills are auto-triggered by relevance,
    not explicitly invoked with positional arguments the way Claude commands
    (`/command args...`) are — there's no `{{args}}`-equivalent substitution target
    (confirmed against antigravity.google/docs/skills). A Claude command whose
    content uses `$ARGUMENTS` still syncs, but the token is inert once Antigravity
    auto-triggers the skill. `build_antigravity_skill_content()` in
    `src/targets/gemini.py` detects this, prints a sync-time warning, and prepends
    an HTML-comment annotation to the written `SKILL.md` so the limitation is
    visible on disk too, not just at sync time.
- **Agents:** `~/.gemini/config/agents/<name>.md`
- **Plugins:** `~/.gemini/config/plugins/<name>/` (containing `plugin.json`, `skills/`, `hooks.json`)
- **MCP Config:** `~/.gemini/antigravity-cli/mcp_config.json`

## Adding a new MCP server

MCP servers are sourced from `src/sources/mcp_config.py` (`McpConfigSource`), which
merges a config.d-style layered set of sources and hands the result to every target
(Claude's `~/.claude.json`, Antigravity's `mcp_config.json`, etc.) in one pass. Merge
order (later wins on a name collision) is: global file, global config.d fragments
(sorted by filename), local file, local config.d fragments (sorted by filename).

| Source | Tracked | Use for |
|--------|---------|---------|
| `.config/mcp/mcp-servers.json` (repo root) | yes | Servers every machine should get — checked in, universal |
| `.config/mcp/mcp-servers.d/*.json` (repo root) | yes | Additional tracked fragments layered on top, e.g. contributed by a separate overlay repo (like `ndotfiles`) without editing the file above |
| `~/.config/mcp/mcp-servers.local.json` | **no** (gitignored) | Machine-specific servers — secrets, tools only some machines have installed |
| `~/.config/mcp/mcp-servers.local.d/*.json` | **no** (gitignored) | Additional machine-local fragments, same reasoning as the tracked config.d directory above |

The config.d directories exist so a second repo can contribute servers by adding its
own file instead of editing a file another repo owns — the same "dedicated directory,
file-by-file symlinks" pattern used elsewhere for cross-repo config (e.g. consolette's
`conf.d`), rather than one repo owning a whole-directory symlink another repo can't
add files into. `ndotfiles` uses this for a work-specific set of MCP servers
(`.config/mcp/mcp-servers.d/50-work.json`) so they're tracked and survive this
tool's full-replace write to `~/.claude.json`/`mcp_config.json`, instead of only
existing as whatever `claude mcp add` happened to write on one machine.

All sources use the same schema, keyed by server name under `mcpServers`:

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
- Underscore-prefixed keys (e.g. `_fork`, `_requires`) are ignored by the loader — use them as inline documentation for the entry (provenance, prerequisites, why it might fail on some machines).
- Any other key (e.g. Claude Code's `enabled`, `zone`, or a display `name` distinct from the server's key) is passed through as-is to `~/.claude.json` rather than dropped — the loader doesn't need to model every target-specific field to round-trip it.
- A server that depends on something not every machine has (an app, an env var, a binary on PATH) doesn't need special-casing — it just fails to start on machines without the dependency, the same way `brave-search` above silently needs `BRAVE_API_KEY`. Put it in the global file/config.d if most machines should still attempt it; put it in the local file/config.d if it's truly one-machine-only.

After editing any of the files above, propagate with:

```bash
make llm-sync
# or: uv run --directory stapler-scripts/llm-sync main.py --force
```
