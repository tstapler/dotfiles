# Claude Code Memory & CLAUDE.md Reference
Source: https://code.claude.com/docs/en/memory
Downloaded: 2026-06-21

---

## Two memory systems

| | CLAUDE.md files | Auto memory |
|---|---|---|
| **Who writes it** | You | Claude |
| **What it contains** | Instructions and rules | Learnings and patterns |
| **Scope** | Project, user, or org | Per repository, shared across worktrees |
| **Loaded into** | Every session | Every session (first 200 lines or 25KB) |
| **Use for** | Coding standards, workflows, project architecture | Build commands, debugging insights, preferences |

CLAUDE.md is context (not enforced config). Hooks enforce; CLAUDE.md guides.

---

## File import with `@` syntax

```
See @README for project overview and @package.json for available npm commands.

# Additional Instructions
- git workflow @docs/git-instructions.md
```

- Both relative and absolute paths work
- Relative paths resolve from the file containing the import (not `$PWD`)
- Recursive imports supported, max depth 4 hops
- Import parsing **skips Markdown code spans and fenced code blocks**
- To mention a path without importing: wrap in backticks — `` `@README` `` stays literal

---

## CLAUDE.md load order (broadest → most specific)

| Scope | Location | Shared with |
|---|---|---|
| **Managed policy** | `/etc/claude-code/CLAUDE.md` (Linux) | All users on machine |
| **User** | `~/.claude/CLAUDE.md` | Just you, all projects |
| **Project** | `./CLAUDE.md` or `./.claude/CLAUDE.md` | Team via source control |
| **Local** | `./CLAUDE.local.md` | Just you, this project (gitignore!) |

Files in parent directories load at launch. Files in subdirectories load on demand when Claude reads files there. Project instructions appear in context *after* user instructions (closer to working dir = read last = higher priority).

---

## HTML comments are stripped from CLAUDE.md context

```markdown
<!-- maintainer notes here — costs zero tokens -->
Regular content here costs tokens.
```

Block-level HTML comments (`<!-- ... -->`) are stripped before injecting into Claude's context.
Comments **inside code blocks** are preserved.
When you Read the file directly, comments are visible.

---

## `.claude/rules/` — path-scoped instructions

```
your-project/
├── .claude/
│   ├── CLAUDE.md
│   └── rules/
│       ├── code-style.md    # always loaded
│       ├── testing.md       # always loaded
│       └── api-design.md    # scoped to src/api/**
```

Rules with `paths:` frontmatter only load when Claude works with matching files:

```markdown
---
paths:
  - "src/api/**/*.ts"
  - "lib/**/*.ts"
---
# API Rules
- All endpoints must include input validation
```

Rules **without** a `paths` field load at launch unconditionally. Rules load before project-level CLAUDE.md (project CLAUDE.md has higher priority). User-level rules (`~/.claude/rules/`) load before project rules.

---

## Auto memory

- Location: `~/.claude/projects/<project>/memory/`
- `MEMORY.md` = index, first 200 lines or 25KB loaded every session
- Topic files (`debugging.md`, etc.) loaded on demand, not at startup
- Toggle: `/memory` → auto memory toggle, or `"autoMemoryEnabled": false` in settings

---

## How CLAUDE.md survives compaction

After `/compact`, project-root CLAUDE.md is re-read from disk and re-injected.
Nested CLAUDE.md files in subdirectories are **not** re-injected — they reload next time Claude reads a file in that subdirectory.

---

## Exclude CLAUDE.md files in monorepos

```json
{
  "claudeMdExcludes": [
    "**/other-team/CLAUDE.md",
    "/home/user/monorepo/other-team/.claude/rules/**"
  ]
}
```

---

## AGENTS.md interop

```markdown
@AGENTS.md
## Claude Code
Use plan mode for changes under `src/billing/`.
```

Or symlink: `ln -s AGENTS.md CLAUDE.md`
