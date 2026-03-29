# Claude Project Instructions

## Important Reminders

- Do what has been asked; nothing more, nothing less
- Always use Read/Grep/Glob/Edit/Write tools for file operations — never use Bash for cat, grep, find, sed, or ls
- NEVER create files unless absolutely necessary
- ALWAYS prefer editing existing files to creating new ones
- NEVER proactively create documentation (*.md) unless explicitly requested
- Use the SUCCESS framework for communication style
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

## Code Editing

- Prefer `Edit` / `Write` tools for file changes
- Use the serena MCP server for complex multi-file structural edits when available

---

## Spec-Driven Development Workflow

For non-trivial features, follow these phases in order. Each produces an artifact the next phase requires. See `project_plans/README.md` for directory conventions.

### Directory Structure

Artifacts live under `project_plans/<project>/` — or `project_plans/<project>/<feature>/` for multi-feature projects:

```
project_plans/<project>/
├── README.md            # navigation + status
├── requirements.md      # spec (ideation output)
├── research/            # research output (one file per dimension)
├── implementation/
│   ├── plan.md          # planning output
│   └── validation.md    # test coverage map (before any code)
└── <feature>/           # repeat structure for each feature/phase
    ├── requirements.md
    ├── research/
    └── implementation/
```

### Phase Gates

| Phase | Skill/Command | Input | Output |
|-------|--------------|-------|--------|
| Ideation | `AskUserQuestion` interview | User's idea | `requirements.md` |
| Research | `/research-workflow` | `requirements.md` | `research/*.md` (parallel: stack, features, architecture, pitfalls) |
| Planning | `/plan:feature` or `/handy:plan` | `requirements.md` + `research/` | `implementation/plan.md` |
| Validation | `/quality:test-planner` | `plan.md` | `implementation/validation.md` |
| Implementation | `/code:implement` | `plan.md` + `validation.md` | Code + passing tests |
| QA | `/quality:does-it-work`, `/code:review` | Implementation | Sign-off or fix plans |

### Rules

- **Fresh session before implementation** — planning context degrades implementation quality
- **Never skip phases** — each artifact is the required input for the next
- **Research in parallel** — spawn agents for: stack, features, architecture, pitfalls dimensions
- **Validation before code** — `validation.md` maps test coverage to requirements before writing a line

---

@~/.claude/skills-index.md
