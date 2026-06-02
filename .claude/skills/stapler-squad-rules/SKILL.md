---
name: stapler-squad-rules
description: Use when you need to add a new rule to the stapler-squad project (a persistent guard, convention, or anti-pattern to avoid). This skill writes a new file to .claude/rules/ with the correct format and optionally updates CLAUDE.md's reference index.
---

# Add a Stapler Squad Rule

Rules in `stapler-squad` live at `.claude/rules/*.md` and are automatically loaded by Claude Code for every session in this project. They encode hard-won lessons, required conventions, and anti-patterns that have caused real bugs or failures.

## When to Add a Rule

Add a rule when:
- A mistake was made (or nearly made) that a written constraint would have caught
- A non-obvious convention must be followed every time (e.g., always pass a specific flag)
- A "wrong" and "right" pattern exists and the wrong one is easy to accidentally reach for

Do NOT add a rule for:
- Things already documented in ADRs or code comments
- General best practices that aren't stapler-squad-specific
- Anything already covered by an existing rule

## Rule File Format

Create a new file at `.claude/rules/<kebab-case-name>.md`:

```markdown
# <Short Title>

<One-sentence imperative statement of the rule.>

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

### Optional: glob scope

If the rule only applies when editing specific files, add frontmatter:

```markdown
---
globs:
  - "web-app/**/*.ts"
  - "web-app/**/*.tsx"
---
```

Rules without globs apply to every session.

## Steps

1. Identify the rule: wrong pattern, right pattern, why it matters
2. Write the file at `.claude/rules/<name>.md` using the format above
3. If the rule is significant enough to surface in `CLAUDE.md`, add a row to the **Reference Documents Index** table there

## Existing Rules Index

| File | Covers |
|---|---|
| `css-architecture.md` | vanilla-extract for new CSS; never use undefined CSS vars |
| `feature-registry.md` | Update `docs/registry/` for every new RPC or UI feature |
| `feature-testing-registry.md` | OmnibarAction union + DetectorRegistry registration checklist |
| `session-creation-registry.md` | 7 touchpoints required for every new session creation mode |
| `gh-pr-merge-repo-flag.md` | Always pass `--repo` to `gh pr merge` to avoid worktree conflicts |
