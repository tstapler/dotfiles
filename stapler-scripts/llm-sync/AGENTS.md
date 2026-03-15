# LLM Sync Agent

This project syncs LLM agents, skills, and commands from Claude to Gemini and OpenCode.

## Running the Project

Use `uv` to run the project. This ensures dependencies are managed correctly.

```bash
uv run main.py --help
```

## Features

- **Namespacing:** Preserves directory structures for agents, skills, and commands (e.g., `git/commit`).
- **Tool Mapping:** Automatically maps Claude tool names to Gemini/OpenCode equivalents.
- **Metadata Overrides:** Supports overriding default values (like model, temperature, mode) via YAML frontmatter.
- **Recursive Directory Creation:** Ensures nested structures are synced correctly.
- **Custom Paths:** Use `--source-dir`, `--gemini-dir`, or `--opencode-dir` to sync to local project folders.
