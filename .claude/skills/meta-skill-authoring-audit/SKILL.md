---
name: meta-skill-authoring-audit
description: Audit existing Claude Code skills/agents/commands for authoring-quality problems — oversized SKILL.md files that should use progressive disclosure, weak/generic descriptions, dangling symlinks, and plugin-vs-namespace-vs-flat-skill structure. Use when reviewing the skills library for quality, deciding whether a skill should be split or restructured, or asked "which skills need work" or "is this skill too big." Complements `skill:create` (new-skill guidance) and `meta-skill-effectiveness-audit` (usage/token-cost audit) — this is the structural/authoring-convention audit.
---

# Skill Authoring Audit

Run the deterministic pass first, then apply judgment to what it can't check.

## Deterministic Pass — Run First

`stapler-scripts/lint-claude-kb` (`make lint-skills`; tested by `make test-lint-skills` against
synthetic fixtures, not the live repo) catches the mechanical half of this, all sourced from
[Anthropic's Skill authoring guidance](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices):
- `invalid-skill-location`: a bare `<name>.md` sitting directly under `.claude/skills/` instead of
  `<name>/SKILL.md`. **This is the single highest-value check** — Claude Code's own spec is
  unambiguous ("Create Skills as directories with SKILL.md files"), and a flat file in this shape
  is never discovered or triggered, no matter how well-formed its frontmatter is. It looks like a
  working skill, reads like one, and simply never fires. Found 75 instances in this repo on first
  run (68 genuinely non-functional, 7 harmless dead duplicates of an already-working directory).
- frontmatter `name:`/dirname drift, missing `description:`
- `name:` over 64 chars, outside lowercase/digits/hyphens, or `description:` over 1,024 chars or
  containing a paired XML-like tag (`<example>...</example>`, not a bare `<placeholder>` — this
  repo uses `<project>`-style angle brackets constantly as a plain-English variable convention,
  which isn't what that rule is about) — **Skill-only**: agent definitions legitimately use a
  longer, XML-example-laden description format and are exempt from this by design
- dangling skill cross-references (a backtick `` `skill-name` `` mention that doesn't resolve)
- `oversized-no-split`: a top-level `SKILL.md` over 500 lines with no `references/`/`scripts/`/`assets/`
  subdirectory (error), 300–500 lines (warn) — keep `SKILL.md` under 500 lines, split via
  progressive disclosure once it doesn't fit
- `nested-references`: a subdirectory inside `references/` — Anthropic's guidance is to keep
  references one level deep from `SKILL.md` so Claude always reads complete files
- `windows-path`: a backslash-style file path in the body — always use forward slashes
- `dangling-symlink`: a symlink under `.claude/{skills,agents,commands}` whose target doesn't resolve

Everything below is what that script *can't* check — it needs judgment.

## Progressive Disclosure — Judging the Split, Not Just the Size

Anthropic's 3-tier model: **Discovery** (name + description, always loaded — this is what makes a
skill findable) → **Activation** (`SKILL.md` body, loaded once triggered) → **Execution**
(`references/`/`scripts/`/`assets/`, loaded on demand). A skill that's 550 lines all inline pays the
full Activation-tier token cost on every trigger for content most invocations never need.

When the linter flags a file, check:
- Is there genuinely separable reference material (a long table, code examples for a secondary
  language, a rarely-needed edge case) that could move to `references/` without hurting the primary
  read-through? → split it.
- Or is it one continuous decision flow with no natural cut point? → a long-but-cohesive skill is
  fine; don't split for the line count alone.

Local examples of a good split: `golang-design-patterns` (277-line `SKILL.md` +
`references/{hexagonal,clean,ddd}-architecture.md` for the deep content) and `golang-documentation`
(238 lines + `references/` + `assets/templates/`). Both keep the frequently-needed decision logic in
`SKILL.md` and push worked examples to `references/`.

## Description Quality (Discovery Tier)

The description is the *only* thing loaded before a skill triggers — a generic one means the skill
silently never fires, regardless of how good its body is.

| Weak | Strong |
|---|---|
| "Best practices for X" | "Use when doing Y, deciding between A and B, or asked 'should I split this into Z'" |
| States what the skill contains | States *when* to reach for it — trigger conditions, not a table of contents |

Anthropic's own guidance: descriptions should be "a little pushy" about triggers, since Claude
under-triggers skills by default. A skill with a vague description is a weak skill even if its body
content is excellent — it just never gets read.

## Symlinks: One Legitimate Pattern, Watch Only For Genuine Breakage

`.claude/commands/<ns>/<x>.md → ../../skills/<ns>/skills/<x>/SKILL.md` is a deliberate bridge (106
of them in this repo, verified all resolving) so a namespaced skill is simultaneously invocable as
`/ns:sub` — healthy by design, not something to clean up. Don't flag this pattern itself; the
linter's `dangling-symlink` check already covers the failure mode that actually matters — a target
that moved/got renamed and the symlink wasn't updated. (Exactly what would have happened to a
symlink pointed at `go-depguard-architecture` after that skill was renamed to
`golang-depguard-architecture` earlier this session, had one existed.)

## Plugin vs. Namespace vs. Flat Skill

Three distinct structures that look similar at a glance — know which one a given situation calls for:

| Structure | Shape | When |
|---|---|---|
| Flat top-level skill | `.claude/skills/<name>/SKILL.md` | One self-contained skill, no sub-skills |
| Namespaced family | `.claude/skills/<ns>/skills/<sub>/SKILL.md` + a near-empty `.claude/skills/<ns>/.claude-plugin/plugin.json` (often just `{"name": "<ns>"}`) | 2+ related skills invoked as `/ns:sub`, sharing a namespace but not meant for distribution outside this repo |
| Real plugin | `plugins/<name>/.claude-plugin/plugin.json` with full metadata (description, version, author, sometimes `upstream`) at repo root | A skill/hook bundle meant to be distributable/shareable on its own — e.g. `plugins/ponytail`, `plugins/git-stacked-prs` |

**Open question this audit surfaces but doesn't auto-resolve:** `.claude-plugin/marketplace.json`'s
`plugins` array is currently empty while `plugins/ponytail` and `plugins/git-stacked-prs` exist with
full distributable metadata. Whether they belong there depends on how this repo's plugin system is
actually meant to be consumed (marketplace install vs. the direct hook-path wiring already present in
`settings.json`) — a judgment call for the repo owner, not something to script around.

A namespaced family with only one sub-skill is a signal the namespace was premature — collapse it
back to a flat top-level skill.

## Related Skills

| Skill | When to reach for it |
|---|---|
| `skill:create` | Creating a *new* skill with progressive disclosure from the start |
| `meta-skill-effectiveness-audit` | Usage/token-cost/behavioral audit from session transcripts — complements this structural audit |
| `meta-cross-reference` | Add/maintain cross-reference callouts between skills |
| `code-hotspot-analysis` | Same "churn × complexity" lens, applied to code instead of skill authoring |
