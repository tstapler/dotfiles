# Claude Project Instructions

## Important Reminders

- Do what has been asked; nothing more, nothing less
- Be resourceful before asking: read the file, search the code, check the docs — come back with answers, not questions. Only escalate to the user when something is genuinely undocumented, ambiguous, or requires a decision only they can make.
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

Use the serena MCP server for complex multi-file structural edits when available.

## Engineering Discipline

- **No fix without root cause.** Before changing code to make a symptom go away, state the root-cause hypothesis ("this fails because X") and confirm it. Symptom fixes without a root-cause statement are not done.
- **No completion claim without proof.** Don't say a task is done until the relevant check/test/build has actually been run and its output shown. Green first, then "done."
- **Self-review before handing off.** Before presenting a non-trivial doc, plan, or diff as finished, re-read it adversarially once yourself (does every claim hold up, do the cross-references actually exist) rather than shipping the first draft.
- **Git hygiene in shared repos.** Never `git add -A` / `git add .` in a repo you don't exclusively own — it can sweep up the user's own uncommitted work. Stage only the specific files you touched, and check `git status` first if anything looks entangled with pending changes that aren't yours.
- **Draft PRs by default.** When opening a PR the user hasn't reviewed yet, open it as a draft (`gh pr create --draft`) so reviewers aren't notified prematurely; mark it ready only once the user gives the go-ahead.

## Repo Placement

- New clones go under `~/code/<host>/<owner>/<repo>` (e.g. `~/code/github.com/tstapler/dotfiles`)
- Use `tyclone <url>` (defined in `~/dotfiles/.shell/functions.sh`) to clone into that layout automatically; `repo_dir <url>` prints the resulting path without cloning
- Existing repos outside this layout (e.g. `~/dotfiles` itself) are left in place — this convention only applies going forward, not as a retroactive migration

---

## Stapler-Driven Development (SDD) Workflow

For non-trivial features, use `/sdd:full` (or the `sdd` agent) to run the complete 7-phase workflow end to end — ideate → research → plan → validate → implement → verify → ship — with parallel agents at each phase and a fresh session before implementation. For a task that fits in one context window, use `/sdd:quick`; for a bug fix, `/sdd:fix-bug`. Check progress with `/sdd:status`; individual phases (`/sdd:1-ideate` … `/sdd:7-ship`, `/sdd:adr`) are also invocable standalone. Artifacts land in `project_plans/<project>/`. Full docs: `.claude/skills/sdd/skills/`.

---

@~/.claude/RTK.md
@~/.claude/CLAUDE.local.md
