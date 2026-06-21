# Claude Project Instructions

## Important Reminders

- Do what has been asked; nothing more, nothing less
- Always use Read/Grep/Glob/Edit/Write tools for file operations — never use Bash for cat, grep, find, sed, or ls
- NEVER create files unless absolutely necessary
- ALWAYS prefer editing existing files to creating new ones
- NEVER proactively create documentation (*.md) unless explicitly requested
- Use the SUCCESS framework for communication style
- Never start responses with preamble ("I'll", "Let me", "Sure,", "I'd be happy to") — answer directly
- Only push the specific branch you're working on

## Tool Priority (CRITICAL)

Always prefer dedicated tools over Bash for these operations:

| Operation | Use This | NOT This |
|-----------|----------|----------|
| Read files | `Read` | `cat`, `head`, `tail`, `sed` |
| Edit files | `Edit` / `Write` | `sed`, `awk`, echo redirect |
| Find files | `Glob` | `find`, `ls` |
| Search text | `Grep` | `grep`, `rg` |
| Search code (structural) | `ast-grep` (`sg`) via Bash | `grep` for code patterns |
| Web search | `WebSearch` | — |
| Read a URL (clean text) | `mcp__read-website-fast__read_website` — save to `/tmp` if page is large | `WebFetch`, `curl` |
| Download page to disk | `mcp__website-downloader__download_page` | `curl`, wget |
| Download site to disk | `mcp__website-downloader__download_website` | wget |

Reserve `Bash` exclusively for: git operations, running tests/commands, and system operations with no dedicated tool.

**Missing tools**: If a required CLI tool is not installed, use `WebSearch` to find the correct Homebrew formula, then install it with `brew install <formula>`. Use the `homebrew` skill for guidance.

## Codebase Exploration (context-efficient)

Before reading code, orient with cheap tools first — do not read entire files or directories blindly:

1. `Glob` to find files by pattern (`src/**/*.ts`, `**/*service*.go`)
2. `sg --pattern '<pattern>' --lang <lang>` for **structural** searches — function signatures, type definitions, interface declarations, call sites. Prefer `sg` over `Grep` for anything that depends on code syntax. See `/code-ast-grep` for pattern syntax.
3. `Grep` for text patterns in configs, docs, or non-code files
4. `Read` with `offset`/`limit` to read targeted line ranges — not whole files

Orient yourself before acting. Avoid reading a file in full unless the entire file is relevant.

## Code Editing

- Prefer `Edit` / `Write` tools for file changes
- Use the serena MCP server for complex multi-file structural edits when available


---

## Manifest-Driven Development (MDD) Workflow

For non-trivial features, follow these phases in order. Each produces an artifact the next phase requires. Directory conventions: `@docs/plans/README.md`.

### Two Artifact Layers

MDD uses two stores. **Do not confuse them:**

| Layer | Location | Phases | Contents |
|---|---|---|---|
| **Spec** | `docs/plans/<project>/` | 1–4 (pre-code) | requirements.md, research/, plan.md, validation.md |
| **ADRs** | `docs/adr/` in target repo | 3 (planning) | ADR-NNN-*.md |
| **Execution** | `docs/tasks/{feature}.md` in target repo | 5–6 (in-code) | Implementation Plan, bug tracking |

`/plan:feature` bridges them — it reads `docs/plans/` and writes `docs/tasks/`.

### Phase Gates

| Phase | Command | Input | Output | Location |
|---|---|---|---|---|---|
| **1. Ideation** | `/plan:mdd-start` | User's idea | `requirements.md` | `docs/plans/<project>/` |
| **2. Research** | `/research-workflow` | `requirements.md` | `research/*.md` | `docs/plans/<project>/research/` |
| **3. Planning** | `/plan:feature` or `/handy:plan` | requirements + research | `plan.md` + ADRs (via `/plan:adr`) | `docs/plans/<project>/implementation/` + `docs/adr/` (target repo) |
| **4. Validation** | `/quality:test-planner` | `plan.md` | `validation.md` | `docs/plans/<project>/implementation/` |
| **5. Implementation** | `/code:implement` | plan + validation | Code + tests | Target repo |
| **6. QA** | `/quality:does-it-work`, `/code:review` | Implementation | Sign-off | Target repo |

### Rules

- **Fresh session before Phase 5** — planning context degrades implementation quality
- **Never skip phases** — each artifact is the required input for the next
- **Research in parallel** — spawn agents for: stack, features, architecture, pitfalls
- **Validation before code** — `validation.md` maps test coverage to requirements before writing a line
- **Session hygiene** — run `/knowledge:extract-learnings` at session end to capture instincts
- **Context health** — run `/meta:context-audit` to check token budget

---

@~/.claude/RTK.md
