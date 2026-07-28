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
- **A constraint on *how* reviewers run is not a reason to skip review.** Independent, unanchored perspectives are the value; running them concurrently is only an optimization. If parallel or background execution is unavailable, run the same lenses **serially** — same prompts, same rounds — and say which mode ran. If the blocker is *permission* rather than capability, ask for it in one sentence; do not report the work as unreviewed. See the `lean-agent-loop` skill's degraded-mode tiers.
- **Git hygiene in shared repos.** Never `git add -A` / `git add .` in a repo you don't exclusively own — it can sweep up the user's own uncommitted work. Stage only the specific files you touched, and check `git status` first if anything looks entangled with pending changes that aren't yours.
- **Draft PRs by default.** When opening a PR the user hasn't reviewed yet, open it as a draft (`gh pr create --draft`) so reviewers aren't notified prematurely; mark it ready only once the user gives the go-ahead.

## Evidence and Claims

Do not overclaim. Every factual statement — in chat, code comments, commit messages, PR bodies, docs, or notes — carries a source the reader can check, **and a hyperlink or path wherever one exists**: a PR/issue URL, `repo/path/file.ext:42`, a doc or dashboard URL, or the exact command and its output. Naming a source without a link pushes verification back onto the reader.

- **Run it, don't read it.** Before asserting that code, a query, or a config does something, execute it and show the output. Reading it is a hypothesis; running it is evidence. And run the *real* invocation: a tool exercised without the flag that loads its config has not tested the config — mine had a fatal syntax error and I'd "run it" a dozen times.
- **Read a mutation back before claiming it happened.** An API that accepts a write and silently ignores it is indistinguishable from success at the call site: a `PUT ... {enabled:true}` returned 200 and left the value `false`; a message-styling override was applied but absent from the response. "No error" is not confirmation — re-read the state you changed.
- **Link code references, don't just name them.** When you reference a specific file, function, or line, include a browsable link to it — `https://github.com/<org>/<repo>/blob/<sha>/<path>#L42` (ranges: `#L42-L58`). A bare `path/file.ext:42` makes the reader clone the repo and guess the branch. Prefer a commit SHA over a branch name so the line number can't rot; get both in one call with `gh api "repos/<org>/<repo>/contents/<path>?ref=<ref>" --jq '.html_url, .sha'`. Keep the `path:line` text alongside the link when the line is the point — `[file.ext:42](https://…#L42)` is copy-pasteable *and* clickable.
- **Recount every number.** Panel counts, file counts, "N of M", "all X pass" — derive them with a command, never from memory or estimate.
- **Rationales need citations too.** An explanation of *why* something is done ("split this way to stay under the limit") is as falsifiable as a fact, and is a common place to invent one.
- **Consistent-with is not because-of.** For causal claims, say which one the evidence supports. If the data needed to establish causation is gone (log retention, an expired window), say so explicitly.
- **Scope a replacement claim.** Retiring a wrong explanation doesn't license a loose new one — state which symptom the new evidence actually covers.
- **Label confidence:** VERIFIED (source opened / command run — cite it) vs INFERRED / UNVERIFIED. Never relay another tool's or agent's synthesis as established fact without opening the primary source.
- **When you can't cite it, name the gap** rather than smoothing it into the narrative. The tidier story is the one to go re-check.

### Proportionality

The rigor above is constant. How much of it belongs **inside the artifact** is not — scale that to the change's consequence. Verbose justification on a small change reads as noise to a reviewer, and it ages badly: build numbers, timelines, and log excerpts are stale within a week.

- **Comments explain the code, not the investigation.** If a comment is longer than the code it annotates, cut it. Keep only the *why* a future reader needs in order not to re-litigate the value; the evidence trail belongs elsewhere.
- **Put the detail where it is cheap to skip.** Diff → smallest. PR body → a few sentences. Reproduction steps, dead ends, stale-able specifics → a PR comment or your notes, which a reviewer can ignore.
- **Scale structure to the diff.** A one-line or mechanical change gets a sentence or two, not a multi-heading template. Add a section only when a reviewer would otherwise have to ask for it.
- **The test:** would a reviewer of *this* change have asked for this paragraph? If not, delete it. Being right is not a licence to be long.

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
