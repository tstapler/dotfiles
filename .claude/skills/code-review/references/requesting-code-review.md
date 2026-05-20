---
name: requesting-code-review
description: Use when completing tasks, implementing major features, or before merging to verify work meets requirements — dispatches code-reviewer subagent with a structured diff summary to review implementation against plan or requirements before proceeding.
---

# Requesting Code Review

Dispatch code-reviewer subagent to catch issues before they cascade.

**Core principle:** Review early, review often. One finding before merge is worth ten findings after.

## When to Request Review

**Mandatory:**
- After each task in subagent-driven development
- After completing major feature
- Before merge to main

**Optional but valuable:**
- When stuck (fresh perspective)
- Before refactoring (baseline check)
- After fixing complex bug

## How to Request

**1. Generate a diff summary first:**

```bash
git log --oneline -5
git diff HEAD~1 --stat
```

Synthesize a 3-sentence summary: *"This change modifies N files. It [main change]. Key affected areas: [list]."*

Research finding: a structured diff summary injected at the start of the reviewer's context measurably improves accuracy over letting the reviewer discover the context on its own.

**2. Get git SHAs:**
```bash
BASE_SHA=$(git rev-parse HEAD~1)  # or origin/main for full branch
HEAD_SHA=$(git rev-parse HEAD)
```

**3. Dispatch code-reviewer subagent:**

Use Agent tool with `subagent_type: "code-reviewer"`, filling these placeholders:
- `{DIFF_SUMMARY}` — from step 1 above
- `{WHAT_WAS_IMPLEMENTED}` — what you just built
- `{PLAN_OR_REQUIREMENTS}` — what it should do (link or paste relevant plan section)
- `{BASE_SHA}` — starting commit
- `{HEAD_SHA}` — ending commit
- `{DESCRIPTION}` — brief one-line summary

**Prompt template:**
```
CONTEXT: {DIFF_SUMMARY}

Review the changes from {BASE_SHA} to {HEAD_SHA}.

What was implemented: {WHAT_WAS_IMPLEMENTED}
Requirements/plan: {PLAN_OR_REQUIREMENTS}
Summary: {DESCRIPTION}

Focus on:
- Correctness relative to requirements
- Security issues (auth, input handling, data exposure)
- API compatibility (public interface changes)
- Test coverage on new paths
- Anything that would block or delay merge

Use severity labels: [BLOCKER] / [CRITICAL] / [MAJOR] / [NIT]
Include code snippet fix suggestions for BLOCKER/CRITICAL findings.
```

**4. Act on feedback by severity:**

| Label | Action |
|-------|--------|
| `[BLOCKER]` | Fix immediately. Do not proceed to next task. |
| `[CRITICAL]` | Fix before declaring this task complete. |
| `[MAJOR]` | Fix if time allows; otherwise create a tracked follow-up. |
| `[NIT]` | Note it; fix at your discretion. |

## Example

```
[Just completed Task 2: Add verification function]

Step 1 — Diff summary:
"This change adds 2 new functions in conversation-index.ts.
It adds verifyIndex() and repairIndex() for detecting and fixing
4 issue types in the conversation index. Affected: conversation-index.ts, tests/."

BASE_SHA=$(git log --oneline | grep "Task 1" | head -1 | awk '{print $1}')
HEAD_SHA=$(git rev-parse HEAD)

[Dispatch code-reviewer subagent]
  DIFF_SUMMARY: [above]
  WHAT_WAS_IMPLEMENTED: Verification and repair functions for conversation index
  PLAN_OR_REQUIREMENTS: Task 2 from docs/plans/deployment-plan.md
  BASE_SHA: a7981ec
  HEAD_SHA: 3df7661
  DESCRIPTION: Added verifyIndex() and repairIndex() with 4 issue types

[Subagent returns]:
  [CRITICAL] conversations/index.ts:88 — Missing null check before getValue() call.
    Fix: `if (result?.getValue()) { ... }`
  [MAJOR] conversations/index.ts:120 — repairIndex() has no test coverage.
  [NIT] — Magic number (100) for reporting interval; extract as constant.
  Assessment: Fix CRITICAL before proceeding.

[Fix CRITICAL]
[Continue to Task 3]
```

## Full Review → Ship Cycle

After requesting a review and fixing all findings, use these commands in order:

1. `/quality:reflect-and-fix` — after fixing any BLOCKER/CRITICAL: make the bug class impossible to reintroduce
2. `/quality:test-planner` — if review found MAJOR test coverage gaps: plan and implement missing tests
3. `/code:fix-loop` — auto-fix any remaining build/test/lint failures
4. `/code:is-it-ready` — final shipping gate: 7-reviewer swarm produces a GO / HOLD / FIX-THEN-SHIP verdict

Do not create a PR until `/code:is-it-ready` returns 🚀.

## Integration with Workflows

**Subagent-Driven Development:**
- Review after EACH task
- Catch issues before they compound
- Fix before moving to next task

**Executing Plans:**
- Review after each batch (3 tasks)
- Get feedback, apply, continue

**Ad-Hoc Development:**
- Review before merge
- Review when stuck

## Red Flags

**Never:**
- Skip review because "it's simple" — simple changes have the highest rate of unreviewed bugs
- Ignore BLOCKER issues
- Proceed with unfixed CRITICAL issues
- Argue with valid technical feedback

**If reviewer wrong:**
- Push back with technical reasoning
- Show code/tests that prove it works
- Request clarification on the specific claim
