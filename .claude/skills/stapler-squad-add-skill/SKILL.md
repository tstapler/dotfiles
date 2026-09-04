---
name: stapler-squad-add-skill
description: Use when you need to add a new persistent guard, convention, or anti-pattern check to the stapler-squad project. This skill scaffolds a new project skill at .claude/skills/<slug>/SKILL.md with the correct frontmatter and optionally updates CLAUDE.md's reference index.
---

# Add a Stapler Squad Skill

AI-authorship code-review checklists, conventions, and anti-pattern guards for
`stapler-squad` live at `.claude/skills/<slug>/SKILL.md`, not at
`.claude/rules/*.md` — that directory was retired in 2026-08 because a
`.claude/rules/*.md` file's entire content loaded into context every time
something referenced it, while a skill's full body only loads when actually
invoked via the Skill tool (the skill list itself shows just a one-line
description the rest of the time). See CLAUDE.md's "Documentation Placement"
section for the full policy.

## When to Add a Skill

Add one when:
- A mistake was made (or nearly made) that a written constraint would have caught
- A non-obvious convention must be followed every time (e.g., always pass a specific flag)
- A "wrong" and "right" pattern exists and the wrong one is easy to accidentally reach for

Do NOT add one for:
- Things already documented in ADRs or code comments
- General best practices that aren't stapler-squad-specific
- Anything already covered by an existing skill

## Skill File Format

Create a new file at `.claude/skills/<kebab-case-slug>/SKILL.md`:

```markdown
---
name: <kebab-case-slug>
description: Use when <the situation that should trigger loading this skill>.
---

# <Short Title>

<One-sentence imperative statement of the rule.>

## When to Use This Skill

- <situation 1>
- <situation 2>

**Wrong:**
```<lang>
<bad example>
```

**Right:**
```<lang>
<good example>
```

## Why

<Explain the root cause: what breaks, why, when. Be specific — reference error messages, file paths, or mechanisms if known.>
```

`name` in the frontmatter must match the directory slug. `description` is the
only thing shown in the skill list before it's invoked, so make it specific
enough that it's obvious when to reach for it.

## Steps

1. Identify the rule: wrong pattern, right pattern, why it matters
2. Write the file at `.claude/skills/<slug>/SKILL.md` using the format above
3. If the rule is significant enough to surface in `CLAUDE.md`, add a row to the **Reference Documents Index** table there, pointing at the skill by name (not a file path — skills aren't looked up by path)

## Existing Skills Index

| Skill | Covers |
|---|---|
| `interface-pollution-checklist` | Java/Spring-shaped leaky abstractions in LLM-generated Go (speculative interfaces, forwarding wrappers, etc.) |
| `primitive-obsession-checklist` | Same-typed parameter piles in Go function signatures |
| `e2e-test-conventions` | Feature annotation, locators, no `waitForTimeout` for Playwright specs |
| `prefer-go-git-over-subshells` | Prefer `go-git` over shelling out to the `git` CLI |
| `fix-flaky-tests-dont-defer` | Root-cause flaky tests instead of re-excusing them as "known pre-existing" |

This index can drift — `ls .claude/skills/` in the stapler-squad repo is the source of truth.
