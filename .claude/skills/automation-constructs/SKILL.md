---
name: automation-constructs
description: Reference for which construct to build when the user asks to automate, remember, or make reusable something — a skill, subagent, hook, rule, CLAUDE.md entry, shell alias, stapler-squad workflow, backlog item, approval rule, or scheduled job. Use whenever a request has the shape "set this up so I/you can do X easily/automatically/every time/from now on" and it's not obvious which mechanism fits.
---

# Automation Constructs

Tyler's toolchain has ~15 distinct ways to make something reusable or automatic, spanning Claude Code itself, his dotfiles, and stapler-squad. Picking the wrong one either does nothing (a skill that never gets invoked) or costs more than it should (a hook where a rule would do, an always-loaded CLAUDE.md line for something rarely needed). Check this table before building.

## Decision table

| User wants... | Build |
|---|---|
| A named, reusable procedure Claude follows when asked (by description-match or explicit `/name`) | **Skill** |
| A specialized persona with its own tool access / model, invoked via the Agent tool | **Subagent** |
| Something enforced on *every* matching tool call, with no LLM judgment involved | **Hook** |
| A guardrail that only needs to load when Claude touches specific file paths | **Rule** (`.claude/rules/*.md`) |
| A standing fact/preference that should apply to every session in one repo | **Project `CLAUDE.md`** |
| A standing fact/preference that should apply to every session, everywhere | **Global `~/.claude/CLAUDE.md`** |
| A terminal shortcut the user types themselves, outside Claude | **Shell alias/function** (dotfiles) |
| A reusable stapler-squad session preset (fixed prompt+dir+model), run via `@slug` or on a schedule | **stapler-squad workflow** |
| A piece of implementation work to triage and drive through the SDD pipeline | **stapler-squad backlog item** |
| An auto-allow/deny/escalate policy for a class of tool calls inside stapler-squad | **stapler-squad approval rule** |
| A prompt that fires once or repeatedly, but only needs to live as long as this session | **`CronCreate`** |
| A durable recurring (or one-shot future) agent, independent of any open session | **`/schedule`** |
| A self-paced recurring check-in inside one long-running session | **`/loop` + `ScheduleWakeup`** |
| A new external tool/data source Claude should be able to call | **MCP server** |
| Several related skills/commands grouped under one `namespace:` prefix | **Plugin** |

Facts the user asks you to remember (not procedures) go to the **auto-memory system**, not any of these — see the memory instructions in your system prompt.

## Constructs in Claude Code

### Skill
- **What**: reusable instructions loaded on demand — either auto-triggered when the task matches its `description`, or explicitly via `/name`. Cheap: the description is always in context, the body loads only when invoked.
- **Where**: `<dir>/.claude/skills/<name>/SKILL.md`, frontmatter `name:` + `description:`. Global (applies everywhere): `~/dotfiles/.claude/skills/` (symlinked to `~/.claude/skills/`). Project-scoped: `<repo>/.claude/skills/`.
- **Use for**: a "how to do X" procedure, a checklist, a reference — anything that would otherwise need re-explaining each session. See `skill-creator`/`skill-development` for authoring conventions.
- **Don't** put content here that's only relevant to one narrow file pattern and needs zero invocation logic — that's a Rule instead.

### Subagent
- **What**: a named persona with its own system prompt, tool allowlist, and optional model override, invoked via the Agent tool (`subagent_type: "<name>"`).
- **Where**: `<dir>/.claude/agents/<name>.md`, frontmatter `name`, `description`, `tools`.
- **Use for**: a recurring task *type* that benefits from restricted tools, a specific model, or a different persona (e.g. `java-test-debugger`, `pr-reviewer`) — not a one-off task, which is just a plain Agent call with `subagent_type: "general-purpose"` or a fork.

### Hook
- **What**: a shell command the harness runs automatically on an event (`PreToolUse`, `PostToolUse`, `SessionStart`, etc.), matched by regex against the tool name. Runs deterministically — no LLM in the loop, so it can't be talked out of firing.
- **Where**: `hooks` key in `~/.claude/settings.json` (global) or a project's `.claude/settings.json`. Configure via the `update-config` skill; see `hook-development` for authoring one.
- **Use for**: something that must happen every time regardless of what the model decides — e.g. this repo's `ssq-hooks check` (every tool call) and `rtk-rewrite.sh` (every Bash call, transparently rewrites to the token-saving `rtk` proxy).
- **Don't** use a hook for something that needs judgment about *when* it applies — that's what a Skill or CLAUDE.md instruction is for.

### Rule
- **What**: a guardrail scoped to a glob (`globs: [...]` frontmatter) that auto-loads only when Claude touches a matching path — unlike a skill, it needs no explicit invocation; unlike CLAUDE.md, it isn't always in context.
- **Where**: `<repo>/.claude/rules/<name>.md`.
- **Use for**: a narrow, path-scoped code convention that a skill would be overkill for and CLAUDE.md would be too expensive for. Examples in this codebase: `stapler-squad/.claude/rules/instance-lock-free-reads.md` (scoped to `session/instance*.go`), `norawghrequest.md` (GitHub HTTP client convention).

### CLAUDE.md
- **What**: always-loaded instructions — every token here is in every session's context regardless of relevance, so it costs more than any other construct per line.
- **Where**: project root (`<repo>/CLAUDE.md`, checked in, team-visible) or global (`~/.claude/CLAUDE.md`, `~/.claude/CLAUDE.local.md`, `~/.claude/RTK.md` — personal, all `@`-imported from the global file).
- **Use for**: orientation (repo map, how pieces fit together) and standing rules that genuinely apply to *every* session in that scope. If it only matters for a subset of paths or tasks, it belongs in a Rule or Skill instead — see this repo's own note on why `.claude/rules/*.md` and skills replaced the old always-loaded `.claude/rules/*.md` blanket files.

### Plugin
- **What**: a namespace bundling multiple skills/commands/agents under one `plugin:skill` prefix (e.g. the `knowledge` plugin → `knowledge:maintain`, `knowledge:synthesize-knowledge`).
- **Where**: `<dir>/.claude-plugin/plugin.json` (`{"name": "<namespace>"}`) alongside a `skills/` (and optionally `commands/`, `agents/`) directory.
- **Use for**: grouping many related skills once there are enough of them that a shared prefix aids discovery — not worth it for one or two skills.

### Scheduling — three different lifetimes
- **`CronCreate`**: fires a prompt on a cron schedule, but only while *this* session exists — nothing is written to disk, gone when the session ends, recurring jobs auto-expire after 7 days anyway. Use for a short-lived recurring check tied to the current work.
- **`/schedule`**: durable cron-based cloud agent ("routine"), independent of any open session — survives session end. Use for anything that should keep running unattended long-term.
- **`/loop` + `ScheduleWakeup`**: a single long-lived session re-invokes itself at a self-chosen pace. Use for "keep checking on this until it's done," not a fixed schedule.

## Constructs outside Claude Code

### Shell alias / function
- **What**: a literal `alias` or shell function the user runs themselves in a terminal — Claude never sees or drives it.
- **Where**: `~/dotfiles/.shell/aliases.sh` (simple `alias x=y`) or `~/dotfiles/.shell/functions.sh` (anything needing arguments/logic, e.g. `tyclone`, `wiki_path`). Symlinked onto `PATH`/shell rc via cfgcaddy.
- **Use for**: a manual shortcut the user wants to type. If Claude is the one who should run it repeatedly, it doesn't need an alias at all — just remember the command (or build one of the constructs above).

### stapler-squad workflow
- **What**: a saved preset (`create_workflow`) for spawning a new agent session with a fixed `command`/`input_template`, `target_directory`, `model`, `agent_type`, and session mode (`directory`/`new_worktree`/`existing_worktree`/`one_off`/`new_project`). Triggered by `run_workflow`, by typing `@<slug>` in the omnibar, or on `cron_expression` if `cron_enabled`.
- **Use for**: "let me kick off a fresh session that does X" as a one-liner, repeatably — e.g. the `topic-synthesis` workflow (`@topic-synthesis <topic>` → new session in the wiki repo running the `topic-synthesis` skill). Manage with `list_workflows`/`update_workflow`/`delete_workflow`.
- **Don't** use this for something that should run inside the *current* session — it always spawns a new one.

### stapler-squad backlog item
- **What**: a tracked, triaged unit of implementation work (`create_backlog_item`) that flows through triage → priority/category assignment → (optionally) an SDD-driven session.
- **Use for**: "someone should build/fix this" — a one-shot deliverable, not a repeatable trigger.

### stapler-squad approval rule
- **What**: a policy (`upsert_approval_rule`) that auto-allows, auto-denies, or escalates a class of tool calls (by tool name, Bash program/subcommand/flags, or file pattern) across stapler-squad-managed sessions.
- **Use for**: governance ("always let sessions run `git status` without asking," "never let sessions run `rm -rf`") — not task automation.

### MCP server
- **What**: an external tool/data integration added to Claude's toolset.
- **Where**: `.config/mcp/mcp-servers.json`, synced to other LLM CLIs by `stapler-scripts/llm-sync` — see its `AGENTS.md` for adding one.
- **Use for**: giving Claude a new *capability* (an API, a database, a service) — not for automating a workflow Claude can already do with existing tools.

## Worked example

Request: "Research topic X and write it into my wiki" needed to be repeatable on demand, from any context, without a chat session already open.
1. **Skill** (`topic-synthesis`) — the actual research → atomic-page → journal-log procedure, invocable by Claude in any session.
2. **stapler-squad workflow** (`topic-synthesis`, slug `@topic-synthesis`) — a one-line trigger that spawns a fresh session in the wiki repo and runs the skill, so the user doesn't need an existing Claude Code session open to use it.

The skill holds the *how*; the workflow holds the *how to invoke it from anywhere*. Neither alone would satisfy "so that I can use it."
