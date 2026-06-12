---
name: lean-agent-loop
description: Run any iterative analysis-and-fix workflow using minimal-context sub-agents that write full results to temp files and return only short structured summaries. Prevents context poisoning while looping until a condition is met. Use when a skill needs "run until clean", "repeat until all findings fixed", or "check → fix → verify" cycles at scale.
---

# Lean Agent Loop

Run iterative workflows context-efficiently: each agent knows ONE thing, does ONE thing, and reports back in a tiny structured summary. Full raw output lives in `/tmp/` and is only read when the coordinator needs to drill in.

---

## The Ralph Wiggum Principle

A lean agent is like a first-grader with a flashcard: it gets exactly one question and one context block. It does not know it is part of a loop. It does not accumulate prior rounds. It returns a tiny structured answer and stops.

**Before** (bloated agent prompt):
> "Here's the entire diff, here are the last three review passes, here are the prior findings, here is the current failing log, here is the test output, here are the codebase conventions — now tell me what to fix."

**After** (Ralph Wiggum):
> "Run `go test ./internal/...` and save full output to `/tmp/scan-go-test.txt`. Return only: `{status: pass|fail, failures: [{file, line, message}]}` — nothing else."

The coordinator accumulates knowledge across rounds; the agents are stateless.

---

## The Two-Layer Output Pattern

Every lean agent produces two things:

| Layer | Where | What |
|---|---|---|
| Full output | `/tmp/scan-<category>-<run>.txt` | Raw command output, full logs, verbatim error text |
| Structured summary | Returned to coordinator | JSON or tight markdown — findings only, ≤ 20 lines |

The coordinator reads only summaries each round. It reads the full file only when it needs the exact error text to write a fix. This keeps the coordinator context lean across N iterations.

**Naming convention for temp files:**
```
/tmp/lean-<skill>-<category>-$(date +%s).txt
# Examples:
/tmp/lean-review-lint.txt
/tmp/lean-ci-test-unit.txt
/tmp/lean-ci-test-integration.txt
/tmp/lean-review-types.txt
```

---

## Loop Primitives

### Option A — `/goal` (recommended for hands-free loops)

```
/goal all build, test, and lint checks pass with exit code 0, or stop after 5 iterations
```

Sets a persistent condition that a Haiku evaluator checks after every turn. When true, the goal clears automatically. When max iterations hit or Claude gets stuck, it stops and reports. No per-turn prompting required.

Use `/goal` when:
- The success condition is a single boolean check (exit code, zero failures)
- You want fully autonomous repair with no intermediate checkpoints
- You trust the evaluator to judge completion correctly

### Option B — `/loop <interval> <command>` (timed repeat)

```
/loop 2m /fix-failures
```

Fires the inner command on a fixed cadence. Use for polling external state (CI runs, deploys) or for workflows where you want a delay between iterations.

### Option C — Manual while loop via Agent tool (step-level control)

Use when:
- You need to inspect intermediate summaries and decide whether to continue
- Different agent prompts are needed each iteration (e.g. harder-mode review on round 2+)
- You want to break on specific conditions not expressible as a `/goal` predicate

```
iteration 1:
  Launch agents in parallel (see below) → collect summaries
  If all summaries show zero findings → DONE
  Else apply fixes → iteration 2

iteration 2:
  Re-launch same agents → collect summaries
  ... (repeat up to N)
```

---

## Wiring Lean Agents in Parallel

Launch one agent per category **in a single message** (parallel = same turn). Each agent:
1. Runs its single check command
2. Writes full output to its designated temp file
3. Returns a tiny structured summary

**Agent prompt template:**
```
Run: <exact command>
Save full output to: /tmp/lean-<skill>-<category>.txt
Return ONLY this JSON (no explanation):
{
  "category": "<category>",
  "status": "pass" | "fail" | "error",
  "count": <number of findings>,
  "findings": [
    {"file": "<path>", "line": <n>, "message": "<one-line description>"}
  ]
}
Max 10 findings. Truncate with {"truncated": true} if more exist.
```

**Coordinator reads the summaries, not the files.** Only drill into a temp file when you need exact error text to write the fix.

---

## Worked Example: Code Review Fix Cycle

```
GOAL: all code review findings resolved, or stop after 4 rounds

--- Round 1 (parallel agent launch) ---

Agent A: Run `golangci-lint run ./...`
  → /tmp/lean-review-lint.txt
  → {status: fail, count: 3, findings: [...]}

Agent B: Run `go test ./... 2>&1`
  → /tmp/lean-review-test.txt
  → {status: fail, count: 1, findings: [...]}

Agent C: Run `go vet ./...`
  → /tmp/lean-review-vet.txt
  → {status: pass, count: 0, findings: []}

Coordinator: 4 total findings across 2 categories.
Read /tmp/lean-review-lint.txt lines 1-40 to get exact messages.
Apply fixes.

--- Round 2 (re-launch same agents) ---
Agent A: {status: pass, count: 0}
Agent B: {status: pass, count: 0}
Agent C: {status: pass, count: 0}

Coordinator: all green → DONE.
```

---

## Context Budget

| Approach | Per-round coordinator tokens |
|---|---|
| Feed full output to coordinator | O(output_size × rounds) — grows unbounded |
| Lean agent pattern | O(20 lines × agent_count) — constant |

For a 5-round loop with 4 agents producing 500-line outputs each, the lean pattern saves ~40k tokens per session.

---

## Existing Command: `code:fix-loop`

The `/code:fix-loop` command is a pre-built implementation of this pattern for **build/test/lint repair**. Use it directly when your loop condition is "all build, test, and lint checks pass":

```
/code:fix-loop          # default 5 iterations
/code:fix-loop 10       # up to 10 iterations
```

Build a custom loop (this skill) when:
- Your check categories differ from build/test/lint (e.g. code review findings, security scan, type coverage)
- You need different agent prompts per iteration (e.g. escalating strictness)
- You need to branch on intermediate results

---

## When to Invoke This Skill from Other Skills

Reference this skill when your workflow has any of these patterns:

| Pattern | How lean-agent-loop helps |
|---|---|
| "Run X, fix findings, re-run until clean" | Drive the loop; agents run X with minimal context |
| "Multiple independent checks that could all fail" | Parallel lean agents — one per check category |
| "Review → fix → verify → repeat" | Each iteration: parallel scan, coordinator reads summaries, applies fixes |
| "CI is red, loop until green" | Wrap CI check in lean agent; loop via `/goal` |
| "Debug until root cause found" | Each iteration surfaces one layer; full output in temp file |
| "Multi-dimensional quality gate" | One agent per dimension (PM/UX/Engineering, or Testing/Architecture/Security); each returns structured rating; loop until all dimensions pass |

### The unanchored re-review principle

When running multiple iterations of a quality gate, **each iteration's agents must be fresh with no memory of prior rounds**. This is not a limitation — it's the point. An agent that remembers what it found last round will anchor on those findings and may either miss new gaps or rubber-stamp fixed ones. A fresh agent gives an unanchored second opinion: it either confirms the fix resolved the issue (by not finding it) or surfaces it again independently, proving the fix was insufficient.

The coordinator tracks what was found and fixed across rounds. The agents do not.

**Not needed when:**
- A one-shot check with < 3 failure cases (just run it inline)
- The fix is already known (no discovery needed, no loop)
- The check is trivial (< 10s, no meaningful output to parse)

---

## Anti-Patterns

- **Feeding prior-round findings into the next agent prompt** — the agent doesn't need history; the coordinator tracks state
- **Reading full temp files every round** — only read when you need exact text to write a fix
- **One mega-agent that runs all checks** — defeats parallelism and bloats the agent's context
- **No temp file** — if a scan produces 500 lines and you feed it all to the coordinator, you've negated the savings
- **Infinite loop without a max-iterations guard** — always set a ceiling; `/goal` and `/code:fix-loop` both enforce one
