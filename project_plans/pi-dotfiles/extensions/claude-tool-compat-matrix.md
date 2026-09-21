# Claude Tool Compatibility Matrix (Pi)

Maps every Claude-specific tool name referenced by this repo's synced
`.claude/skills/**/SKILL.md` corpus to its status under the Pi coding agent
(https://pi.dev). Built for Epic 5.3 (`project_plans/pi-dotfiles/implementation/plan.md`,
Stories 5.3.1-5.3.2) so a future coding agent syncing a new skill to Pi
doesn't assume parity that doesn't exist. Corresponds to validation rows
`SM-7`/`SM-7 (error)` (`project_plans/pi-dotfiles/implementation/validation.md`).

**Method**: `find .claude/skills -iname SKILL.md -print0 | xargs -0 grep -lE '\b<name>\b'`,
run 2026-09-21 against 398 `SKILL.md` files. Counts below are the number of
`SKILL.md` files containing at least one occurrence of the exact word, not
total occurrences.

**Status values**:
- `native` — Pi has an equivalent built in; no extension needed.
- `shimmed via pi-claude-compat` — a first-party Tyler-owned extension aliases
  the Claude name onto a native or extension-provided capability. **Not yet
  built** (Epic 3.4, `plugins/pi-claude-compat/pi/index.ts` does not exist on
  disk as of this writing) — noted per-row as "planned, not yet shimmed."
- `extension-provided` — requires a third-party Pi extension; noted per-row
  whether that extension is forked/approved in this plan's scope or merely a
  named research candidate.
- `unsupported` — no native equivalent and no extension planned in this
  plan's scope.
- `unknown — needs verification` — could not be confirmed from this repo's
  own verified research or from Pi's docs; not guessed.

## Basis for Pi's native tool set

This repo has not independently re-verified Pi's full native tool list
against `pi.dev` docs during this task (no web access was used here beyond
what earlier phases already verified). The claims below are grounded in two
already-VERIFIED sources already in this repo:

- `project_plans/pi-dotfiles/full-featured-profile-research.md` (lines 18-44):
  "Pi already has core read/write/edit/bash and file discovery tools,
  instructions and skills, prompt templates, model/provider switching,
  session persistence, branching, compaction, themes, keybindings, package
  filtering, and an extension API," and separately: "The existing skills
  materially use Claude tool names, especially `AskUserQuestion`, `WebSearch`,
  `WebFetch`, task tools, and `Agent`. We therefore need either a selective
  compatibility extension or a deliberate source translation layer."
- `project_plans/pi-dotfiles/requirements.md:114`: "Pi deliberately omits
  native MCP, subagents, permission popups, plan mode, and background bash;
  parity may require evaluating or building extensions rather than copying
  Claude configuration."

Where a row's status isn't directly supported by one of those two sources or
by an in-scope plan.md epic, it is marked `unknown — needs verification`
rather than inferred.

## Matrix

| Tool name | Found in corpus | Pi status | Basis |
|---|---|---|---|
| `AskUserQuestion` | 41 files | `shimmed via pi-claude-compat` — planned, not yet shimmed | Pi has a native ask-user primitive; Task 3.4.1a (plan.md:550) plans registering `AskUserQuestion` as an alias for it. `plugins/pi-claude-compat/` does not exist yet. |
| `Grep` | 64 files | `shimmed via pi-claude-compat` — planned, not yet shimmed | research.md:20-21 confirms Pi has native "file discovery tools"; Task 3.4.1b (plan.md:553) plans a `Grep` casing alias over the native equivalent. Not yet built. |
| `Glob` | 54 files | `shimmed via pi-claude-compat` — planned, not yet shimmed | Same as `Grep` — Task 3.4.1b. Not yet built. |
| `LS` | 0 files (searched, none found in current corpus) | `shimmed via pi-claude-compat` — planned, not yet shimmed | Included because it's part of the plan's required grep set (plan.md:722) and Task 3.4.1b explicitly plans an `LS` alias, even though no current `SKILL.md` uses the exact word `LS`. Not yet built. |
| `Agent` | 105 files | `extension-provided` — not yet forked/approved, and its `pi-claude-compat` facade is also not yet built | requirements.md:114: Pi "deliberately omits native ... subagents." `gotgenes/pi-subagents` (Tier 1, `full-featured-profile-research.md:56-90`) is the candidate, tracked in Epic 3.2 with disposition `candidate` (`extension-audit.md:17`) — not yet forked/approved per Task 3.2.1's precondition. research.md:139 additionally plans `Agent` "as a compatibility facade over the selected subagent package" via `pi-claude-compat` (Epic 3.4) — also not yet built. Two dependent gaps, neither closed today. |
| `TaskCreate` | 3 files | `unsupported` — no extension scheduled in this plan's scope | research.md:165-177 (Tier 3) names `juicesharp/rpiv-mono`'s `rpiv-todo` package as the closest candidate for Claude `TaskCreate`/`TaskUpdate` compatibility, but no epic in `plan.md` forks or schedules it — Tier 3 is out of scope except where Epic 3.4's compat shim explicitly covers it (it doesn't cover task tools; see plan.md:722's required-name list, which omits task-store aliasing from Epic 3.4's own scope at plan.md:537-554). |
| `WebSearch` | 14 files | `unsupported` — no extension scheduled in this plan's scope | research.md:199-207 (Tier 3) names `nicobailon/pi-web-access` as the non-browser search/content-extraction candidate, but no epic in this plan forks or approves it. Not covered by Epic 3.4's compat shim (scoped to `AskUserQuestion`/`Grep`/`Glob`/`LS`/`Agent` only, plan.md:537-554). |
| `WebFetch` | 30 files | `unsupported` — no extension scheduled in this plan's scope | Same basis as `WebSearch` — `nicobailon/pi-web-access` is the named Tier 3 candidate; not forked/scheduled in this plan. |
| `Read` | 166 files | `native` | research.md:20-21: Pi already has "core read/write/edit/bash" tools. Exact tool-name casing on Pi's side is not verified here, but the capability gap list (research.md:24-38) does not list read/write/edit/bash as a gap, so no compat shim is planned or needed. |
| `Write` | 173 files | `native` | Same basis as `Read`. |
| `Edit` | 71 files | `native` | Same basis as `Read`. |
| `Bash` | 64 files | `native` (synchronous only) | research.md:20-21 confirms native bash. Caveat: requirements.md:114 states Pi "deliberately omits ... background bash" — background/interactive execution is a separate Tier 3 gap (research.md:226-241, `99percentpeople/pi-background-tasks` candidate), not forked or scheduled in this plan. Ordinary synchronous `Bash` calls are native; long-running/background bash is `unsupported` in this plan's scope. |
| `TodoWrite` | 7 files | `unknown — needs verification` | Distinct from `TaskCreate`/`TaskUpdate`. research.md's closest lead is the Tier 3 `rpiv-todo` package (line 171), evaluated there only in the context of `TaskCreate`/`TaskUpdate`, not `TodoWrite` specifically. No verified statement in this repo confirms or denies a native Pi equivalent for session-scoped todo tracking. Not guessed. |
| `MultiEdit` | 3 files | `native` (functional equivalent, not name-for-name) | Legacy Claude Code tool for the same multi-file text substitution Pi's native edit/bash tools already cover (research.md:20-21). Not called out as a gap in research.md's gap list (lines 24-38), so no dedicated shim is planned. |
| `SlashCommand` | 2 files | `unknown — needs verification` | Pi has "prompt templates" natively (research.md:21), but whether Pi exposes a tool-callable mechanism to invoke one programmatically from within another tool call (the `SlashCommand` tool's actual behavior in Claude Code) is not confirmed by any source in this repo. Not guessed. |

## Tier 4 — explicitly deferred (session/workflow utilities)

Per `plan.md`'s "Explicitly deferred" section (plan.md:27): Tier 4
session/workflow-utility parity is deliberately deferred to a follow-up SDD
project, not delivered by this plan. These rows are recorded here so the gap
is tracked, not silently absent from the matrix.

| Category | Pi status | Basis |
|---|---|---|
| Session search/handoff | `deferred` — follow-up candidate named, not evaluated or forked | `full-featured-profile-research.md:245-255` (Tier 4) names `thurstonsand/pi-sessions` (review anchor `8f2f3d444cc65255bfc61dbb6173e69c21eb5e2c`) as the candidate a follow-up project would evaluate. |
| Async compaction | `deferred` — follow-up candidate named, not evaluated or forked | `full-featured-profile-research.md:257-265` (Tier 4) names `almogdepaz/pi-async-compaction` (review anchor `5b9a70b678f23b7250f66b97789cb2777061cf3c`) as the candidate a follow-up project would evaluate. |

## Workflow category: global/project instructions

Not a tool name found by the grep — recorded separately per Story 5.3.2
(plan.md:735-751), since "global and project instructions" parity is named
explicitly in requirements.md's In-Scope list and needed its own row rather
than being silently covered by the glossary alone.

| Category | Pi status | Basis |
|---|---|---|
| Global/project instructions | **Project-level: `native`.** **Global-level: closed via symlink (this epic, Task 5.3.2a).** | Project-level: Pi natively loads project instructions by walking up from the current directory looking for `AGENTS.md` or `CLAUDE.md` (`AGENTS.override.md` takes precedence per-directory) — VERIFIED against `pi.dev/docs/latest/quickstart` and `github.com/earendil-works/pi/blob/main/AGENTS.md` (plan.md:21). This repo's project-level `CLAUDE.md` files (e.g. `/home/tstapler/CLAUDE.md`) already exist, so Pi already reads them with no dotfiles change. Global-level: `~/.claude/CLAUDE.md`'s equivalent is `~/.pi/agent/AGENTS.md`; `.cfgcaddy.yml` now has a `dest: .pi/agent/AGENTS.md` entry (Task 5.3.2a) mirroring the existing `.claude/CLAUDE.md` entry's `src`, giving `~/.pi/agent/AGENTS.md` the same tracked content Claude already reads globally. |
