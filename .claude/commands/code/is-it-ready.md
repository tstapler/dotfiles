---
description: Shipping readiness gate — parallel swarm across plan compliance, architecture,
  code quality, tests, security, product/UX, and operational readiness. Produces a
  GO / HOLD / FIX-THEN-SHIP verdict.
prompt: "# Is It Ready? — Shipping Readiness Review\n\nRun a parallel swarm of specialized\
  \ reviewers against the current changes to produce a single, evidence-backed shipping\
  \ decision.\n\n**Scope**: `${1:-current git changes}`\n\n---\n\n## Step 0 — PR\
  \ Validation\n\n```bash\ngh pr list --head $(git branch --show-current) --json number,title,state\n\
  ```\n\nIf a PR exists, check CI and inline comments before continuing. For failing\
  \ CI: `gh run view <RUN_ID> --log-failed`. For comments: `gh api repos/{owner}/{repo}/pulls/{PR_NUMBER}/comments\
  \ --paginate | jq '.[] | {id, user: .user.login, path, body: .body[:150]}'`.\n\
  Fix bugs, decline style preferences (with reply), push fixes. Record: PR#, failing\
  \ checks, unresolved comment count, review decision.\n\n---\n\n## Step 1 — Gather\
  \ Context (this thread only)\n\nRun these once and keep the results in memory —\
  \ do NOT pass raw diffs to agents; pre-filter for each agent's focus:\n\n```bash\n\
  git diff HEAD --stat && git diff HEAD --name-only\n```\n\nAlso read: existing plan\
  \ in `project_plans/` or `docs/tasks/`, any `validation.md`. Note language and\
  \ framework.\n\nBuild a **compact change manifest** (≤150 words): list changed files,\
  \ one-line summary of what each does, which files relate to which review dimension.\
  \ This is what agents receive instead of raw diffs.\n\n---\n\n## Step 2 — Launch\
  \ 7 Parallel Reviewers\n\nSend all 7 in a **single message**. Each agent:\n- Gets:\
  \ (a) compact change manifest, (b) diff sections relevant to its dimension,\
  \ (c) strict output format\n- Uses `subagent_type: general-purpose` and `model:\
  \ haiku`\n- May freely read files and search the codebase to verify findings —\
  \ but return only what is needed to act on the problems found — nothing more. Use\
  \ this format:\n\n```\nRATING:\
  \ 🟢/🟡/🔴\nBLOCKING: [file:line — one sentence each, or \"none\"]\nNON-BLOCKING:\
  \ [one sentence each, or \"none\"]\n```\n\n---\n\n### Agent 1 — Plan Compliance\n\
  \nVerify implementation matches the plan. Check: every requirement has code, no\
  \ unasked-for features, acceptance criteria traceable to tests.\n\nRate 🟢 all\
  \ done / 🟡 minor gaps / 🔴 significant requirements missing.\n\n---\n\n### Agent\
  \ 2 — Architecture & Design\n\nCheck: SOLID violations, layer boundary crossings,\
  \ new tight coupling, anti-patterns, inconsistency with existing conventions.\n\n\
  Rate 🟢 sound / 🟡 minor issues / 🔴 causes future pain.\n\n---\n\n### Agent 3\
  \ — Code Quality\n\nCheck: naming clarity, function size, DRY violations, swallowed\
  \ errors, magic values, misleading comments.\n\nRate 🟢 clean / 🟡 some issues\
  \ / 🔴 hard to maintain.\n\n---\n\n### Agent 4 — Test Quality\n\nCheck: behavior\
  \ coverage vs. coverage theater, missing unhappy paths, test isolation, plan-to-test\
  \ traceability.\n\nRate 🟢 high confidence / 🟡 coverage gaps / 🔴 won't catch\
  \ real bugs.\n\n---\n\n### Agent 5 — Security\n\nCheck: injection vectors, missing\
  \ auth on new paths, PII in logs, new CVE-bearing deps, weak crypto, unverified\
  \ external fetches.\n\nRate 🟢 no new risks / 🟡 low-severity / 🔴 exploitable.\n\
  \n---\n\n### Agent 6 — Product & UX\n\nCheck: all user flows complete, empty/error/loading\
  \ states handled, error messages actionable, accessibility basics, solves original\
  \ user problem.\n\nRate 🟢 ready / 🟡 rough edges / 🔴 confusing or broken.\n\n\
  ---\n\n### Agent 7 — Operational Readiness\n\nCheck: no silent catch blocks, new\
  \ failure modes have logging, backward compatibility, no N+1 or unbounded loops,\
  \ graceful degradation. (For internal/non-prod tools: SLO dimension is 🟡 informational\
  \ only, not blocking.)\n\nRate 🟢 production-ready / 🟡 gaps / 🔴 ships blind.\n\
  \n---\n\n## Step 3 — Synthesize\n\nAfter all 7 return, produce this report:\n\n\
  ```markdown\n## Is It Ready? — Shipping Gate Report\n\n**Branch**: <name>  **PR**:\
  \ <#N or none>  **CI**: <pass/fail>  **Date**: <today>\n\n| Dimension | Status\
  \ | Blocking | Notes |\n|---|---|---|---|\n| CI / PR | 🟢/🟡/🔴 | ... | ... |\n\
  | Plan | 🟢/🟡/🔴 | ... | ... |\n| Architecture | 🟢/🟡/🔴 | ... | ... |\n| Code\
  \ Quality | 🟢/🟡/🔴 | ... | ... |\n| Tests | 🟢/🟡/🔴 | ... | ... |\n| Security\
  \ | 🟢/🟡/🔴 | ... | ... |\n| Product/UX | 🟢/🟡/🔴 | ... | ... |\n| Ops | 🟢/🟡/🔴\
  \ | ... | ... |\n\n## Verdict: [🚀 SHIP IT / ⚠️ FIX THEN SHIP / 🛑 HOLD]\n\n###\
  \ Blocking Issues\n1. [Dimension] file:line — issue\n\n### Non-Blocking\n1. [Dimension]\
  \ — suggestion\n\n### Next Action\n[One sentence]\n```\n\n---\n\n## Step 4 — Fix\
  \ Loop\n\nIf ⚠️ FIX THEN SHIP: auto-fix blocking issues, then re-run only the\
  \ affected reviewer agents. Max 3 iterations.\n\n**Auto-fix** (no asking): code\
  \ quality, test gaps, silent error handling, CI formatting failures, PR comment\
  \ replies.\n**Pause for human**: Security 🔴, SLO targets (product decision), systemic\
  \ architecture redesign, HOLD with multiple 🔴.\n\n| Dimension | Fix via |\n|---|---|\n\
  | CI failures | `gh run view <ID> --log-failed` → fix → push |\n| Code / Tests\
  \ / Ops | Direct edit — targeted file only |\n| PR comments | Inline fix or `gh\
  \ api ... -X POST -f body=...` decline reply |\n\nTerminate when: all 🟢 → 🚀,\
  \ no progress two rounds → report as needs-human, Security/SLO 🔴 → ask human.\n\
  \n---\n\n## Verdict Criteria\n\n| Verdict | Condition |\n|---|---|\n| 🚀 SHIP IT\
  \ | All 🟢 or only 🟡 with no blocking issues |\n| ⚠️ FIX THEN SHIP | 🟡 with\
  \ fixable blockers — triggers Step 4 |\n| 🛑 HOLD | Any 🔴 — pause for human |\n\
  \nSecurity 🔴 or SLO 🔴 on a new user-facing feature → always HOLD.\n"
---

# Is It Ready? — Shipping Readiness Review

Token-efficient parallel swarm: 7 focused reviewers dispatch with pre-filtered context and return a structured 3-line verdict (rating + blocking + non-blocking). Synthesizes into a single shipping decision.

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

Run these once and keep the results in memory — do NOT pass raw diffs to agents; pre-filter for each agent's focus:

```bash
git diff HEAD --stat && git diff HEAD --name-only
```

Also read: existing plan in `project_plans/` or `docs/tasks/`, any `validation.md`. Note language and framework.

Build a **compact change manifest** (≤150 words): list changed files, one-line summary of what each does, which files relate to which review dimension. This is what agents receive instead of raw diffs.

---

## Step 2 — Launch 7 Parallel Reviewers

Send all 7 in a **single message**. Each agent:
- Gets: (a) compact change manifest, (b) diff sections relevant to its dimension, (c) strict output format
- Uses `subagent_type: general-purpose` and `model: haiku`
- May freely read files and search the codebase to verify findings
- Return only what is needed to act on the problems found — nothing more. Use this format:

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

Rate 🟢 sound / 🟡 minor issues / 🔴 causes future pain.

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

Rate 🟢 no new risks / 🟡 low-severity / 🔴 exploitable.

---

### Agent 6 — Product & UX

Check: all user flows complete, empty/error/loading states handled, error messages actionable, accessibility basics, solves original user problem.

Rate 🟢 ready / 🟡 rough edges / 🔴 confusing or broken.

---

### Agent 7 — Operational Readiness

Check: no silent catch blocks, new failure modes have logging, backward compatibility, no N+1 or unbounded loops, graceful degradation. (For internal/non-prod tools: SLO dimension is 🟡 informational only, not blocking.)

Rate 🟢 production-ready / 🟡 gaps / 🔴 ships blind.

---

## Step 3 — Synthesize

After all 7 return, produce this report:

```markdown
## Is It Ready? — Shipping Gate Report

**Branch**: <name>  **PR**: <#N or none>  **CI**: <pass/fail>  **Date**: <today>

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

### Next Action
[One sentence]
```

---

## Step 4 — Fix Loop

If ⚠️ FIX THEN SHIP: auto-fix blocking issues, then re-run only the affected reviewer agents. Max 3 iterations.

**Auto-fix** (no asking): code quality, test gaps, silent error handling, CI formatting failures, PR comment replies.  
**Pause for human**: Security 🔴, SLO targets (product decision), systemic architecture redesign, HOLD with multiple 🔴.

| Dimension | Fix via |
|---|---|
| CI failures | `gh run view <ID> --log-failed` → fix → push |
| Code / Tests / Ops | Direct edit — targeted file only |
| PR comments | Inline fix or `gh api ... -X POST -f body=...` decline reply |

Terminate when: all 🟢 → 🚀, no progress two rounds → report as needs-human, Security/SLO 🔴 → ask human.

---

## Verdict Criteria

| Verdict | Condition |
|---|---|
| 🚀 SHIP IT | All 🟢 or only 🟡 with no blocking issues |
| ⚠️ FIX THEN SHIP | 🟡 with fixable blockers — triggers Step 4 |
| 🛑 HOLD | Any 🔴 — pause for human |

Security 🔴 or SLO 🔴 on a new user-facing feature → always HOLD.
