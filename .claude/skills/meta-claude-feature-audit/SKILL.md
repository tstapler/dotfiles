---
name: meta-claude-feature-audit
description: Audit our whole skills library against the current Claude Code docs and changelog to find built-in commands (/goal, /loop, /batch, /code-review, /verify, ...), skill frontmatter fields, and platform features that shipped after the skills were written. Use when asked to "see what new Claude Code features our skills should use", after a Claude Code upgrade, or periodically (monthly). For evaluating ONE technique or blog post, use meta-claude-technique-evaluator instead.
---

# Claude Code Feature Audit

Library-wide gap analysis: current docs vs. what our skills use. Produces a ranked list of skill edits, then applies the approved ones.

## Phase 1 — Snapshot the docs

```bash
~/.claude/skills/meta-claude-feature-audit/scripts/fetch-docs.sh   # prints the docs dir (a fresh mktemp -d); pass it to scan.py below
claude --version   # record it; flag features newer than the installed version
```

Downloads commands, skills, goal, hooks, sub-agents, workflows, scheduled-tasks, and the CHANGELOG to a fresh temp dir (path printed; pass a dir arg to override). Docs index for anything else: `https://code.claude.com/docs/llms.txt`.

## Phase 2 — Mechanical scan

```bash
python3 -I ~/.claude/skills/meta-claude-feature-audit/scripts/scan.py ~/.claude/skills <docs_dir>
```

Reports: frontmatter keys not in the docs (silently ignored), documented keys we never use, skills without a `description`, which built-ins skills reference, and skills with hand-rolled loop language. Valid keys and command names are parsed from the docs, so the report tracks them.

## Phase 3 — Read the deltas

Read, don't skim, only what the scan flags:
- `goal.md`, plus the `/goal` row in `commands.md`: condition-writing rules, `-p` support, requirements (hooks must be enabled).
- `skills.md` "Frontmatter reference": `context: fork`, `agent`, `disallowed-tools`, `paths`, `hooks`, `effort`, `model`, `arguments`.
- `commands.md` rows marked **Skill** or **Workflow** (bundled; may supersede our custom skills).
- `CHANGELOG.md`: `grep -iE 'skill|/goal|slash|command|hook|workflow' CHANGELOG.md | head -80`, newest versions first. Version-gate every recommendation (e.g. `/goal` check-ins need v2.1.234+).

## Phase 4 — Classify each finding

| Class | Test | Action |
|---|---|---|
| **Replace** | A bundled skill/command does what ours does (`/code-review`, `/simplify`, `/verify`, `/skill-doctor`, `/insights`, `/autofix-pr`) | Diff capability; deprecate ours, or reduce it to what the built-in lacks (our conventions, internal tooling) |
| **Adopt** | Our skill hand-rolls what a built-in or field does (loop/termination → `/goal`; subagent spawning → `context: fork`; autonomous skill that may call `AskUserQuestion` → `disallowed-tools`) | Edit the skill to use it |
| **Fix** | Frontmatter key not in the docs, missing `description` | Move extras under `metadata:`; rename `tools:` → `allowed-tools:` |
| **Document** | Built-in is useful but no skill needs changing | Mention in the relevant skill's chaining table only if it changes a decision |
| **Skip** | Interactive-only, cosmetic, or account-gated (`/theme`, `/stickers`, `/voice`) | Ignore |

Before calling something "Adopt", open the skill and confirm it really has the problem. A keyword hit is a lead, not a finding.

## Phase 5 — Report, then apply

1. Present findings as a table: skill, class, change, version gate, evidence (`path:line` or doc URL).
2. Apply only after the user approves, one commit per class (Fix / Adopt / Replace). Stage specific files, never `git add -A`.
3. Re-run Phase 2 and show the before/after counts.
4. Run `/skill-doctor` (needs v2.1.252+ and feature-flag fetching; say so if unavailable) to check context cost didn't grow.

## Gotchas

- `/goal`'s evaluator only sees what Claude surfaced in the transcript, so conditions must name a check whose output appears there ("`make ready` exits 0"). Don't point a skill at `/goal` when success needs an unobserved file or external state.
- `/goal` is unavailable when `disableAllHooks` is true or `allowManagedHooksOnly` is set. Skills that must work there need a fallback (`lean-agent-loop` Option C, the manual loop).
- UNVERIFIED: the docs describe `/goal` only as a user-typed command, so assume a skill can't set one. Phrase adoption as "run under `/goal <condition>`" guidance.
- Only commands marked **Skill** in `commands.md` are bundled skills; the rest are built-in commands, not skills.
