---
description: Shipping readiness gate — parallel swarm across plan compliance, architecture,
  code quality, tests, security, product/UX, and operational readiness. Produces a
  GO / HOLD / FIX-THEN-SHIP verdict with a mandatory auto-fix loop.
prompt: |
  # Is It Ready? — Shipping Readiness Review

  Run a parallel swarm of 7 specialized reviewers against the current changes to produce a single, evidence-backed shipping decision. **After any non-🚀 verdict, auto-fix ALL blocking issues using parallel subagents WITHOUT asking the user. Loop until 🚀 or a hard stop.**

  **Scope**: `${1:-current git changes}`

  ---

  ## Step 0 — PR Validation

  ```bash
  gh pr list --head $(git branch --show-current) --json number,title,state
  ```

  If a PR exists, check CI and inline comments before continuing. For failing CI: `gh run view <RUN_ID> --log-failed`. For comments: `gh api repos/{owner}/{repo}/pulls/{PR_NUMBER}/comments --paginate | jq '.[] | {id, user: .user.login, path, body: .body[:150]}'`.

  Fix bugs, decline style preferences (with reply), push fixes. Record: PR#, failing checks, unresolved comment count, review decision.

  ---

  ## Step 1 — Gather Context (this thread only)

  ```bash
  git diff HEAD --stat && git diff HEAD --name-only
  ```

  Also read: existing plan in `project_plans/` or `docs/tasks/`, any `validation.md`. Note language and framework.

  Build a **compact change manifest** (≤150 words): list changed files, one-line summary of what each does, which files relate to which review dimension. Agents receive this manifest + their relevant diff slice — never raw full diffs.

  ---

  ## Step 2 — Launch 7 Parallel Reviewers

  **Dispatch ALL 7 agents in a SINGLE tool invocation block (one message).** This is what enables true parallelism — staggering across messages defeats the purpose. Each agent:
  - Gets: (a) compact change manifest, (b) diff sections relevant to its dimension only, (c) strict output format below
  - Uses `subagent_type: general-purpose` and `model: haiku`
  - May freely read files and search the codebase — but return ONLY what is needed to act on problems found

  Required output format (3 lines only):
  ```
  RATING: 🟢/🟡/🔴
  BLOCKING: [file:line — one sentence each, or "none"]
  NON-BLOCKING: [one sentence each, or "none"]
  ```

  ### Agent 1 — Plan Compliance
  Verify implementation matches the plan. Check: every requirement has code, no unasked-for features, acceptance criteria traceable to tests.
  Rate 🟢 all done / 🟡 minor gaps / 🔴 significant requirements missing.

  ### Agent 2 — Architecture & Design
  Check: SOLID violations, layer boundary crossings, new tight coupling, anti-patterns, inconsistency with existing conventions.
  Rate 🟢 sound / 🟡 minor issues / 🔴 causes future pain OR requires systemic redesign.

  ### Agent 3 — Code Quality
  Check: naming clarity, function size, DRY violations, swallowed errors, magic values, misleading comments.
  Rate 🟢 clean / 🟡 some issues / 🔴 hard to maintain.

  ### Agent 4 — Test Quality
  Check: behavior coverage vs. coverage theater, missing unhappy paths, test isolation, plan-to-test traceability.
  Rate 🟢 high confidence / 🟡 coverage gaps / 🔴 won't catch real bugs.

  ### Agent 5 — Security
  Check: injection vectors, missing auth on new paths, PII in logs, new CVE-bearing deps, weak crypto, unverified external fetches.
  Rate 🟢 no new risks / 🟡 low-severity / 🔴 exploitable vulnerability present.

  ### Agent 6 — Product & UX
  Check: all user flows complete, empty/error/loading states handled, error messages actionable, accessibility basics, solves original user problem.
  Rate 🟢 ready / 🟡 rough edges / 🔴 confusing or broken.

  ### Agent 7 — Operational Readiness
  Check: no silent catch blocks, new failure modes have logging, backward compatibility, no N+1 or unbounded loops, graceful degradation. (For internal/non-prod tools: SLO dimension is 🟡 informational only, not blocking.)
  Rate 🟢 production-ready / 🟡 gaps / 🔴 ships blind.

  ---

  ## Step 2.5 — Wait for CI to Complete

  **Never issue 🚀 SHIP IT while any CI run is in-progress or queued.** After launching the 7 reviewers (they run concurrently while CI runs), poll until all CI runs reach `completed`:

  ```bash
  gh run list --branch $(git branch --show-current) --limit 5 --json databaseId,status,conclusion,name
  ```

  Repeat every 60 seconds until no run has `status` of `in_progress` or `queued`. Then:
  - All conclusions `success` → CI 🟢, proceed to Step 3
  - Any conclusion `failure` or `cancelled` → CI 🔴, fetch logs before Step 3:
    ```bash
    gh run view <RUN_ID> --log-failed
    ```

  If CI is still running when all 7 reviewers have returned, wait for CI before synthesizing — do not skip this gate.

  ---

  ## Step 3 — Synthesize

  After all 7 reviewers return **and CI has completed**, produce this report. Include an "Auto-Fixed This Iteration" section listing any issues already resolved in the current fix cycle so the user can track progress.

  ```markdown
  ## Is It Ready? — Shipping Gate Report

  **Branch**: <name>  **PR**: <#N or none>  **CI**: <pass/fail>  **Date**: <today>  **Iteration**: <N of 5>

  | Dimension | Status | Blocking | Notes |
  |---|---|---|---|
  | CI / PR | 🟢/🟡/🔴 | ... | ... |
  | Plan | 🟢/🟡/🔴 | ... | ... |
  | Architecture | 🟢/🟡/🔴 | ... | ... |
  | Code Quality | 🟢/🟡/🔴 | ... | ... |
  | Tests | 🟢/🟡/🔴 | ... | ... |
  | Security | 🟢/🟡/🔴 | ... | ... |
  | Product/UX | 🟢/🟡/🔴 | ... | ... |
  | Ops | 🟢/🟡/🔴 | ... | ... |

  ## Verdict: [🚀 SHIP IT / ⚠️ FIX THEN SHIP / 🛑 HOLD]

  ### Blocking Issues
  1. [Dimension] file:line — issue

  ### Non-Blocking
  1. [Dimension] — suggestion

  ### Auto-Fixed This Iteration
  - [Dimension] file:line — what was fixed

  ### Next Action
  [One sentence]
  ```

  ---

  ## Step 4 — Fix Loop (MANDATORY — NEVER ASK THE USER)

  **NEVER ask before fixing. NEVER pause for confirmation. Fix everything auto-fixable immediately.**

  After every verdict that is not 🚀 SHIP IT, fix all auto-fixable blocking issues in parallel subagents, then re-run ONLY the affected reviewer agents (not all 7). Re-synthesize. Repeat until 🚀 or hard stop.

  ### Auto-fix without asking (run fixes as parallel subagents where independent):
  - Code quality: naming, magic values, function size, DRY
  - Test gaps: missing unhappy paths, weak assertions, isolation issues
  - Silent error handling, swallowed exceptions
  - CI lint/format/build failures
  - PR inline comment responses (fix bugs, decline style with reply)
  - CSS/style convention violations
  - Fallback value inconsistencies
  - Ops issues: missing logging, N+1 queries, unbounded loops

  ### Hard stop — only these two conditions pause for human:
  1. **Security 🔴** — exploitable vulnerability present
  2. **Architecture 🔴** — systemic redesign required (not just refactoring)

  Everything else is auto-fixable. When in doubt, fix it.

  ### Loop mechanics:
  ```
  while verdict != 🚀 SHIP IT:
    1. Group blocking issues by dimension
    2. Launch fix subagents in parallel (one per independent issue or group)
    3. Run tests to confirm fixes didn't break anything
    4. git add + commit + push
    5. Re-run ONLY the reviewer agents whose dimension had blocking issues (parallel, fresh context each)
    6. Re-synthesize verdict (Step 3) — note what was auto-fixed
    7. If blocking issues unchanged after a round → escalate to human
    8. Max 5 iterations before escalating
  ```

  | Dimension | Fix via |
  |---|---|
  | CI failures | `gh run view <ID> --log-failed` → fix inline → push |
  | Code / Tests / Ops | Direct Edit — targeted file only, then verify with test run |
  | PR comments | Inline fix or decline reply via `gh api` |
  | Architecture (non-systemic) | Targeted refactor subagent with full file context |

  ---

  ## Verdict Criteria

  | Verdict | Condition |
  |---|---|
  | 🚀 SHIP IT | All 🟢 or only 🟡 with no blocking issues |
  | ⚠️ FIX THEN SHIP | Any fixable blockers — triggers Step 4 immediately |
  | 🛑 HOLD | Security 🔴 or Architecture 🔴 requiring systemic redesign |

  Security 🔴 or SLO 🔴 on a new user-facing feature → always HOLD.
---

# Is It Ready? — Shipping Readiness Review

Token-efficient parallel swarm: 7 focused reviewers dispatch with pre-filtered context and return a structured 3-line verdict. Synthesizes into a single shipping decision. **After any non-🚀 verdict, auto-fix ALL blocking issues using parallel subagents WITHOUT asking the user. Loop until 🚀 or a hard stop.**

**Scope**: `${1:-current git changes}`

---

## Step 0 — PR Validation

```bash
gh pr list --head $(git branch --show-current) --json number,title,state
```

If a PR exists, check CI and inline comments before continuing. For failing CI: `gh run view <RUN_ID> --log-failed`. For comments: `gh api repos/{owner}/{repo}/pulls/{PR_NUMBER}/comments --paginate | jq '.[] | {id, user: .user.login, path, body: .body[:150]}'`.

Fix bugs, decline style preferences (with reply), push fixes. Record: PR#, failing checks, unresolved comment count, review decision.

---

## Step 1 — Gather Context (this thread only)

```bash
git diff HEAD --stat && git diff HEAD --name-only
```

Also read: existing plan in `project_plans/` or `docs/tasks/`, any `validation.md`. Note language and framework.

Build a **compact change manifest** (≤150 words): list changed files, one-line summary of what each does, which files relate to which review dimension. Agents receive this manifest + their relevant diff slice — never raw full diffs.

---

## Step 2 — Launch 7 Parallel Reviewers

**Dispatch ALL 7 agents in a SINGLE tool invocation block (one message).** This is what enables true parallelism — staggering across messages defeats the purpose. Each agent:
- Gets: (a) compact change manifest, (b) diff sections relevant to its dimension only, (c) strict output format below
- Uses `subagent_type: general-purpose` and `model: haiku`
- May freely read files and search the codebase — but return ONLY what is needed to act on problems found

Required output format (3 lines only):
```
RATING: 🟢/🟡/🔴
BLOCKING: [file:line — one sentence each, or "none"]
NON-BLOCKING: [one sentence each, or "none"]
```

---

### Agent 1 — Plan Compliance

Verify implementation matches the plan. Check: every requirement has code, no unasked-for features, acceptance criteria traceable to tests.

Rate 🟢 all done / 🟡 minor gaps / 🔴 significant requirements missing.

---

### Agent 2 — Architecture & Design

Check: SOLID violations, layer boundary crossings, new tight coupling, anti-patterns, inconsistency with existing conventions.

Rate 🟢 sound / 🟡 minor issues / 🔴 causes future pain OR requires systemic redesign.

---

### Agent 3 — Code Quality

Check: naming clarity, function size, DRY violations, swallowed errors, magic values, misleading comments.

Rate 🟢 clean / 🟡 some issues / 🔴 hard to maintain.

---

### Agent 4 — Test Quality

Check: behavior coverage vs. coverage theater, missing unhappy paths, test isolation, plan-to-test traceability.

Rate 🟢 high confidence / 🟡 coverage gaps / 🔴 won't catch real bugs.

---

### Agent 5 — Security

Check: injection vectors, missing auth on new paths, PII in logs, new CVE-bearing deps, weak crypto, unverified external fetches.

Rate 🟢 no new risks / 🟡 low-severity / 🔴 exploitable vulnerability present.

---

### Agent 6 — Product & UX

Check: all user flows complete, empty/error/loading states handled, error messages actionable, accessibility basics, solves original user problem.

Rate 🟢 ready / 🟡 rough edges / 🔴 confusing or broken.

---

### Agent 7 — Operational Readiness

Check: no silent catch blocks, new failure modes have logging, backward compatibility, no N+1 or unbounded loops, graceful degradation. (For internal/non-prod tools: SLO dimension is 🟡 informational only, not blocking.)

Rate 🟢 production-ready / 🟡 gaps / 🔴 ships blind.

---

## Step 2.5 — Wait for CI to Complete

**Never issue 🚀 SHIP IT while any CI run is in-progress or queued.** After launching the 7 reviewers (they run concurrently while CI runs), poll until all CI runs reach `completed`:

```bash
gh run list --branch $(git branch --show-current) --limit 5 --json databaseId,status,conclusion,name
```

Repeat every 60 seconds until no run has `status` of `in_progress` or `queued`. Then:
- All conclusions `success` → CI 🟢, proceed to Step 3
- Any conclusion `failure` or `cancelled` → CI 🔴, fetch logs before Step 3:
  ```bash
  gh run view <RUN_ID> --log-failed
  ```

If CI is still running when all 7 reviewers have returned, wait for CI before synthesizing — do not skip this gate.

---

## Step 3 — Synthesize

After all 7 reviewers return **and CI has completed**, produce this report. Include an "Auto-Fixed This Iteration" section listing any issues resolved in the current fix cycle so the user can track progress.

```markdown
## Is It Ready? — Shipping Gate Report

**Branch**: <name>  **PR**: <#N or none>  **CI**: <pass/fail>  **Date**: <today>  **Iteration**: <N of 5>

| Dimension | Status | Blocking | Notes |
|---|---|---|---|
| CI / PR | 🟢/🟡/🔴 | ... | ... |
| Plan | 🟢/🟡/🔴 | ... | ... |
| Architecture | 🟢/🟡/🔴 | ... | ... |
| Code Quality | 🟢/🟡/🔴 | ... | ... |
| Tests | 🟢/🟡/🔴 | ... | ... |
| Security | 🟢/🟡/🔴 | ... | ... |
| Product/UX | 🟢/🟡/🔴 | ... | ... |
| Ops | 🟢/🟡/🔴 | ... | ... |

## Verdict: [🚀 SHIP IT / ⚠️ FIX THEN SHIP / 🛑 HOLD]

### Blocking Issues
1. [Dimension] file:line — issue

### Non-Blocking
1. [Dimension] — suggestion

### Auto-Fixed This Iteration
- [Dimension] file:line — what was fixed

### Next Action
[One sentence]
```

---

## Step 4 — Fix Loop (MANDATORY — NEVER ASK THE USER)

**NEVER ask before fixing. NEVER pause for confirmation. Fix everything auto-fixable immediately.**

After every verdict that is not 🚀 SHIP IT, fix all auto-fixable blocking issues in parallel subagents, then re-run ONLY the affected reviewer agents (not all 7). Re-synthesize. Repeat until 🚀 or hard stop.

### Auto-fix without asking (run fixes as parallel subagents where independent):
- Code quality: naming, magic values, function size, DRY
- Test gaps: missing unhappy paths, weak assertions, isolation issues
- Silent error handling, swallowed exceptions
- CI lint/format/build failures
- PR inline comment responses (fix bugs, decline style with reply)
- CSS/style convention violations
- Fallback value inconsistencies
- Ops issues: missing logging, N+1 queries, unbounded loops

### Hard stop — only these two conditions pause for human:
1. **Security 🔴** — exploitable vulnerability present
2. **Architecture 🔴** — systemic redesign required (not just refactoring)

Everything else is auto-fixable. When in doubt, fix it.

### Loop mechanics

```
while verdict != 🚀 SHIP IT:
  1. Group blocking issues by dimension
  2. Launch fix subagents in parallel (one per independent issue or group)
  3. Run tests to confirm fixes didn't break anything
  4. git add + commit + push
  5. Re-run ONLY the reviewer agents whose dimension had blocking issues (parallel, fresh context each)
  6. Re-synthesize verdict (Step 3) — note what was auto-fixed
  7. If blocking issues unchanged after a round → escalate to human
  8. Max 5 iterations before escalating
```

| Dimension | Fix via |
|---|---|
| CI failures | `gh run view <ID> --log-failed` → fix inline → push |
| Code / Tests / Ops | Direct Edit — targeted file only, then verify with test run |
| PR comments | Inline fix or decline reply via `gh api` |
| Architecture (non-systemic) | Targeted refactor subagent with full file context |

---

## Verdict Criteria

| Verdict | Condition |
|---|---|
| 🚀 SHIP IT | All 🟢 or only 🟡 with no blocking issues |
| ⚠️ FIX THEN SHIP | Any fixable blockers — triggers Step 4 immediately |
| 🛑 HOLD | Security 🔴 or Architecture 🔴 requiring systemic redesign |

Security 🔴 or SLO 🔴 on a new user-facing feature → always HOLD.
