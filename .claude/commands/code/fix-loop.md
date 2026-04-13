---
title: Fix Loop
description: Run parallel minimal-context checks across all failure dimensions, fix everything found, and repeat until all pass or max iterations reached.
arguments: [max_iterations]
---

# Fix Loop — Parallel Check → Fix → Repeat

Run checks across all failure dimensions simultaneously using minimal-context agents, fix every failure found, then re-verify. Loop until everything passes or `$1` iterations are exhausted (default: 5).

**Max iterations**: `${1:-5}`

---

## When to Use

- After implementing a feature — run until green before opening a PR
- When `quality:does-it-work` reports failures you want auto-resolved
- When you have a large test suite with scattered failures across modules
- Faster than running fixes manually: parallel agents, minimal context per agent, automatic re-verification

**Not a replacement for** `code:is-it-ready` — that does architectural review. This does build/test/lint repair.

---

## Step 0 — Project Inventory

Before launching agents, establish ground truth:

```bash
# 1. Identify project type(s)
ls -1 pyproject.toml package.json build.gradle build.gradle.kts go.mod Cargo.toml 2>/dev/null

# 2. Identify changed files (limit blast radius)
git diff HEAD --name-only 2>/dev/null || git status --short

# 3. Run ALL checks once to capture the full failure set
# Python:     pytest 2>&1 | tail -50; ruff check .; mypy .
# Java:       ./gradlew check 2>&1 | tail -100
# JS/TS:      npm test 2>&1 | tail -50; npm run lint 2>&1 | tail -50
# Go:         go test ./... 2>&1 | tail -50; golangci-lint run 2>&1 | tail -50
# Rust:       cargo test 2>&1 | tail -50; cargo clippy 2>&1 | tail -50
```

Record:
- Project type and test/lint commands used
- Total failure count by category (build errors, test failures, lint violations, type errors)
- Estimated complexity (simple = trivial fixes, complex = logic bugs)

If **zero failures**, output "✅ Already green — nothing to fix." and stop.

---

## Step 1 — Parallel Scan (Minimal Context)

Launch one agent per failure category, **simultaneously in a single message**. Each agent receives ONLY its category's raw output — no full codebase, no unrelated context.

Keep each agent's input focused: pipe raw tool output, trim to relevant lines, pass only the files implicated.

---

### Scanner A — Build / Compilation
**subagent_type**: `general-purpose`

Input: raw compiler/build output (max 200 lines). Changed files list.

Identify:
- Every file:line with a compile error or build failure
- Root cause (missing import, type mismatch, undefined symbol, etc.)
- Dependencies between errors (fixing one may resolve others)

Output structured list:
```
BUILD_ERROR | file:line | root_cause | fix_strategy | dependency_on:[other error IDs or "none"]
```

---

### Scanner B — Test Failures
**subagent_type**: `general-purpose`

Input: raw test runner output (max 300 lines, trimmed to failing test names + stack traces). Do NOT include passing tests.

Identify:
- Each failing test: name, file:line of assertion failure, error type
- Group by root cause (same bug causing multiple failures = one group)
- Classify: logic bug | missing setup | broken fixture | flaky/timing | wrong assertion

Output structured list:
```
TEST_FAILURE | test_name | file:line | root_cause | group_id | classification
```

---

### Scanner C — Lint / Style
**subagent_type**: `general-purpose`

Input: raw linter output (max 200 lines). Linter name/version.

Identify:
- Each violation: file:line, rule name, description
- Which are auto-fixable (e.g., `ruff --fix`, `spotlessApply`, `eslint --fix`) vs. require manual edits
- Group violations by rule type to batch fixes

Output structured list:
```
LINT | file:line | rule | auto_fixable:[yes/no] | group:[rule_group]
```

---

### Scanner D — Type Checking
**subagent_type**: `general-purpose`

Input: raw type checker output (mypy, tsc, etc.) max 200 lines.

Identify:
- Each type error: file:line, error code, description
- Whether fix is: add annotation | change signature | fix wrong type | add cast | import missing type
- Dependencies between errors

Output structured list:
```
TYPE_ERROR | file:line | error_code | fix_type | dependency_on:[other IDs or "none"]
```

---

## Step 2 — Triage and Fix Planning

After all scanners return, consolidate:

1. **Auto-fixable lint** → run auto-fix commands immediately (no agent needed):
   - `ruff check --fix .` / `black .`
   - `./gradlew spotlessApply`
   - `eslint --fix src/`
   - `gofmt -w .`

2. **Group remaining failures** by independence:
   - Failures in different files/modules = independent → can fix in parallel
   - Failures in same file or with dependencies = sequential

3. **Create fix task list** using TodoWrite with:
   - Group ID, failure type, files affected, estimated complexity
   - Dependencies noted

---

## Step 3 — Parallel Fix Agents

Launch fix agents simultaneously for independent failure groups. Each agent receives:
- **Only** the failures in its group (structured output from scanners)
- **Only** the relevant source files (read them, not the whole codebase)
- **Context**: project type, test command to verify the fix

**Agent sizing**:
- 1–3 simple lint/type fixes → direct Edit tool call (no agent)
- Logic bug in a single test → `general-purpose` agent
- Multiple interrelated test failures (same module) → `general-purpose` agent
- Complex refactor needed → `code-refactoring` agent

**Fix agent prompt template** (customize per group):
```
Fix these specific failures in [project_type] codebase.

FAILURES:
[structured failure list for this group]

RELEVANT FILES:
[content of only the implicated files]

CONSTRAINTS:
- Fix ONLY what is listed. Do not refactor unrelated code.
- After editing, state which failures are resolved and which remain.
- Do not run the full test suite — just explain what you changed and why.
```

---

## Step 4 — Re-Verify

After all fix agents complete:

```bash
# Re-run all checks (same commands as Step 0)
# Capture: new failure count, newly green categories, newly introduced failures
```

**If new failures introduced** by fixes: add them to the failure list and note which fix agent caused them.

---

## Step 5 — Loop Decision

```
iteration_count += 1

if all_checks_pass:
    → EXIT with success report

elif iteration_count >= max_iterations:
    → EXIT with partial report (what's fixed, what remains, why it's stuck)

elif no_progress (same failures as last iteration):
    → EXIT with stuck report — mark remaining failures as "needs human"

else:
    → Go back to Step 1 with updated failure set
```

---

## Exit Report

```markdown
## Fix Loop — Final Report

**Iterations**: N / ${1:-5}
**Outcome**: ✅ All green / ⚠️ Partial / 🛑 Stuck

### Fixed
| Category     | Count | Method         |
|--------------|-------|----------------|
| Build errors |     N | Agent / Direct |
| Test failures|     N | Agent / Direct |
| Lint issues  |     N | Auto-fix       |
| Type errors  |     N | Agent / Direct |

### Remaining (if any)
| Category | Failure | File:line | Why Stuck |
|----------|---------|-----------|-----------|
| ...      | ...     | ...       | ...       |

### Recommended Next Action
[Single clearest unblocking step, or "ready for /code:is-it-ready"]
```

---

## Loop Termination Rules

| Condition | Action |
|-----------|--------|
| All checks pass | Exit immediately with ✅ |
| Max iterations reached | Exit with partial report |
| No progress (identical failures two iterations in a row) | Exit with "stuck" report — do not keep spinning |
| A fix introduces a regression in a previously-passing area | Note the regression, revert the offending fix, mark as "needs human" |
| Same failure appears 3 times in a row | Mark as "needs human" and remove from loop |

---

## Related Commands

- `/quality:does-it-work` — one-shot check without fixing
- `/code:is-it-ready` — full architectural + quality review (run after fix-loop passes)
- `/fix-failures` — similar but single-pass; use fix-loop for complex multi-pass scenarios
- `/quality:test-planner` — write tests before implementing (upstream of this)
