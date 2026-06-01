---
name: code-review
description: Use when receiving code review feedback (especially if unclear or technically questionable), when completing tasks or major features requiring review before proceeding, or before making any completion/success claims. Covers four practices — receiving feedback with technical rigor, requesting reviews via code-reviewer subagent, verification gates requiring evidence before claims, and security/API-compat awareness. Essential for subagent-driven development, pull requests, and preventing false completion claims.
---

# Code Review

Guide proper code review practices emphasizing technical rigor, evidence-based claims, and verification over performative responses.

## Overview

Code review requires four distinct practices:

1. **Receiving feedback** — Technical evaluation over performative agreement
2. **Requesting reviews** — Systematic review via code-reviewer subagent
3. **Verification gates** — Evidence before any completion claims
4. **Security & compatibility awareness** — Recognize when a change warrants security or API compat review

Each practice has specific triggers and protocols detailed in reference files.

## Core Principle

**Technical correctness over social comfort.** Verify before implementing. Ask before assuming. Evidence before claims.

**Fix everything you see — pre-existing or not.** When a review surfaces an issue, fix it regardless of whether the current diff introduced it. "Not my change" is not a reason to leave broken code in place. Every finding gets fixed before the PR merges.

## When to Use This Skill

### Receiving Feedback
Trigger when:
- Receiving code review comments from any source
- Feedback seems unclear or technically questionable
- Multiple review items need prioritization
- External reviewer lacks full context
- Suggestion conflicts with existing decisions

**Reference:** `references/code-review-reception.md`

### Requesting Review
Trigger when:
- Completing tasks in subagent-driven development (after EACH task)
- Finishing major features or refactors
- Before merging to main branch
- Stuck and need fresh perspective
- After fixing complex bugs

**Reference:** `references/requesting-code-review.md`

### Verification Gates
Trigger when:
- About to claim tests pass, build succeeds, or work is complete
- Before committing, pushing, or creating PRs
- Moving to next task
- Any statement suggesting success/completion
- Expressing satisfaction with work

**Reference:** `references/verification-before-completion.md`

### Security, Performance & Compatibility Flags
Trigger when:
- Diff touches auth, input handling, secrets, data exposure, cryptography, or logging → security review
- Diff changes public method signatures, shared schemas, DTOs, or event payloads → API compat check
- Diff touches concurrent/async code, shared mutable state, or locks → concurrency check
- Diff adds nested loops over unbounded collections, synchronous remote calls in hot paths, or removes pagination → performance check

Escalate security to `/security-review`. Performance and compat are covered inside `/code:review` (Code Quality + Architecture agents).

## Quick Decision Tree

```
SITUATION?
│
├─ Received feedback
│  ├─ Unclear items? → STOP, ask for clarification first
│  ├─ From human partner? → Understand, then implement
│  └─ From external reviewer? → Verify technically before implementing
│
├─ Completed work
│  ├─ Touches auth/secrets/data? → Flag for security review
│  ├─ Changes public API/schema? → Flag for compat check
│  ├─ Major feature/task? → Request code-reviewer subagent review
│  └─ Before merge? → Request code-reviewer subagent review
│
└─ About to claim status
   ├─ Have fresh verification? → State claim WITH evidence
   └─ No fresh verification? → RUN verification command first
```

## Receiving Feedback Protocol

### Response Pattern
READ → UNDERSTAND → VERIFY → EVALUATE → RESPOND → IMPLEMENT

### Key Rules
- ❌ No performative agreement: "You're absolutely right!", "Great point!", "Thanks for [anything]"
- ❌ No implementation before verification
- ✅ Restate requirement, ask questions, push back with technical reasoning, or just start working
- ✅ If unclear: STOP and ask for clarification on ALL unclear items first
- ✅ YAGNI check: grep for usage before implementing suggested "proper" features

### Severity Label Handling
When a code reviewer uses severity labels, handle them as follows:
- `[BLOCKER]` — Fix immediately, do not proceed to next task until resolved
- `[CRITICAL]` — Fix in the current PR/task before declaring complete
- `[MAJOR]` — Acknowledge, fix if time allows, otherwise track as follow-up
- `[NIT]` — Author's discretion; no obligation to fix

### Source Handling
- **Human partner:** Trusted — implement after understanding, no performative agreement
- **External reviewers:** Verify technically correct, check for breakage, push back if wrong

**Full protocol:** `references/code-review-reception.md`

## Requesting Review Protocol

### When to Request
- After each task in subagent-driven development
- After major feature completion
- Before merge to main

### Process
1. Get git SHAs: `BASE_SHA=$(git rev-parse HEAD~1)` and `HEAD_SHA=$(git rev-parse HEAD)`
2. Dispatch code-reviewer subagent via Agent tool with: WHAT_WAS_IMPLEMENTED, PLAN_OR_REQUIREMENTS, BASE_SHA, HEAD_SHA, DESCRIPTION
3. Act on feedback using severity labels: fix BLOCKER/CRITICAL immediately, track MAJOR, note NIT

**Full protocol:** `references/requesting-code-review.md`

## Verification Gates Protocol

### The Iron Law
**NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE**

### Gate Function
IDENTIFY command → RUN full command → READ output → VERIFY confirms claim → THEN claim

Skip any step = lying, not verifying

### Requirements
- Tests pass: Test output shows 0 failures
- Build succeeds: Build command exit 0
- Bug fixed: Test original symptom passes
- Requirements met: Line-by-line checklist verified

### Red Flags — STOP
Using "should"/"probably"/"seems to", expressing satisfaction before verification, committing without verification, trusting agent reports, ANY wording implying success without running verification

**Full protocol:** `references/verification-before-completion.md`

## Integration with Workflows

- **Subagent-Driven:** Review after EACH task, verify before moving to next
- **Pull Requests:** Verify tests pass, request code-reviewer review before merge
- **General:** Apply verification gates before any status claims, push back on invalid feedback

## Bottom Line

1. Technical rigor over social performance — No performative agreement
2. Fix everything you see — pre-existing issues are not exempt; if you see it, fix it
3. Systematic review processes — Use code-reviewer subagent
4. Evidence before claims — Verification gates always
5. Security and compat flags — Escalate proactively when diff touches high-risk areas

Verify. Question. Then implement. Evidence. Then claim.

---

## Review Pipeline

`code-review` is the diagnostic center. These skills chain around it:

**Before review:**
| Skill/Command | When |
|---|---|
| `/quality:does-it-work` | Sanity-check build/test/lint before requesting a full review |
| `/quality:find-test-smells` | Deeper test analysis before review if test quality is a known concern |

**After fixing findings:**
| Skill/Command | When |
|---|---|
| `/quality:reflect-and-fix` | After fixing BLOCKER/CRITICAL: make recurrence structurally impossible (shift-left) |
| `/quality:test-planner` | Review found test coverage MAJOR gaps → plan and implement the missing tests |
| `/code:fix-loop` | Auto-fix loop for remaining build/test/lint failures |

**Final gate:**
| Skill/Command | When |
|---|---|
| `/code:is-it-ready` | After all findings fixed: 7-reviewer shipping swarm → GO/HOLD/FIX-THEN-SHIP verdict |

**For deeper analysis of specific findings:**
| Skill | When |
|-------|------|
| `code-debugging` | Investigate failures discovered during verification gates |
| `code-root-cause-analysis` | Trace recurring bugs found in review to their historical origin |
| `security-review` | Diff touches auth, input handling, secrets, data exposure, or cryptography |
| `code-architecture-best-practices` | Evaluate structural decisions (layering, SOLID) in the reviewed code |
| `/quality:architecture-review` | Architecture agent flags systemic design issues needing deep analysis |
| `/quality:find-refactor-candidates` | Code Quality agent flags many MAJOR refactoring needs |
| `github-pr` | Create or manage the pull request after review gates pass |
