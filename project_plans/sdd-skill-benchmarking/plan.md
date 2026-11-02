# Skill benchmarking and efficiency plan

Goal: make changes to SDD and its neighbouring skills measurable before and after, then use that to cut cost and wall-clock without lowering outcomes.

Evidence lives in `research/` (one file per study) and `baseline-phase-report-2026-11-01.txt`. Claims below marked **(agent)** come from a research agent's reading of transcripts and were not re-derived here; **(measured)** came from `phase_cost_report.py` run on 195 sessions.

## What we know

| Finding | Source |
|---|---|
| Fitted cost is dominated by cache traffic (read + write about 91%), not output. The lever is fewer turns and smaller context per turn. | measured, rates fitted to billed `cost-state`, about ±5% median per `sonnet-5-5` session |
| `sdd:*` is 43–52% of cost in these sessions. The range is the two labelling bounds (strict windows vs carry-forward). Neither is exact. | measured |
| Only research parallelizes (2.7). Plan, validate and verify run at about 1.0. Phase 5 workers reach 3-7 concurrent but average about 1.9 overlap (15 of 20 sessions between 1.0 and 2.5). | measured |
| Phase 5 serialization in the one session read closely was reasoned: a cross-epic data dependency the plan's wave grouping missed (Story 4.2.1 needs 3.2.1). The fix is better dependency graphs, not "parallelize more". | `research/` transcript read, one session |
| Triad review: the repair step is 46% of cost, rounds 3-5 do not converge, the exit rule is "all legs green" not "no blockers". | agent: `research/skill-pm-triad-review.md` |
| `github:pr-ship`: the orchestrator runs at a median 113k context and does worker tasks itself; merge conflicts are checked last. | agent: `research/skill-github-pr-ship.md` |
| `code:review`: reviewers spawn their own subagents (7 forks = $6.76 of $11.6 in one run); the lead's prompts carry no diff. The skeptic pass is cheap (about 4%) and works. | agent: `research/skill-code-review-and-extract-learnings.md` |
| `golang-development`, `backlog:*` command files and `extract-learnings` are not cost targets as skill text. Cost is session startup context (about 70k tokens) and build/test output. | agent: `research/skill-backlog-and-golang-development.md` |

## Measurement rules (before any A/B)

1. Cost per skill = from its invocation to the end of its own agents, reported separately from work that inherited its label. Label totals are a ranking, not a cost.
2. Primary metric is cost per success; success rate and step adherence are guardrails (a skill must not win by skipping steps).
3. Report fitted dollars with the fit error, and tokens by bucket. Keep a no-cache-discount sensitivity check; interleave arms in random order; pin the model; run arms in the same time window; keep a canary task.
4. Defects caught later is the value the extra review rounds buy; score it, or cost cuts will look free.

## Benchmark tasks (from the studies)

| Skill | Fixture | Deterministic check |
|---|---|---|
| `pm:triad-review` | plan with 12 seeded gaps; clean plan vs plan with 2 blockers; digest fidelity | gap recall; rounds to exit; handback JSON keywords |
| `code:review` | frozen diff with 6 seeded defects + 2 decoys; two-round regression test | recall, precision, cost, agent count |
| `github:pr-ship` | lint-only CI trap; conflicting PR with silent CI; slow CI with a late bot comment (needs stub `gh`) | merge-ready reached, rounds, orchestrator context |
| `extract-learnings` | frozen transcript + memory snapshot; null-yield and seeded-secret transcripts | must-save / must-not-save patterns |
| `sdd:5-implement` | one small frozen project with a plan whose dependency graph is known | tests pass, wall-clock, peak concurrency |
| `golang-development` | seeded-antipattern Go module, with-skill / slim / no-skill arms | `go vet`, `go test -race`, `staticcheck`, `goleak` |

## Changes to test, in order

Ordered by expected saving per cost of testing. Savings are agents' estimates, not measurements.

1. **Triad review**: blocker-scoped, diff-bounded repair; exit when no lens reports a blocker; at most 2 repairs; skip repair at Complexity 2. (agent estimate: 40-55% combined)
2. **`code:review`**: forbid subagents inside reviewers; write the diff to a file once; re-review only the fix commit.
3. **`github:pr-ship`**: run the gate loop in a fresh subagent; check merge conflicts at entry; derive local lint commands from `.github/workflows`; stop waking the orchestrator on agent notifications.
4. **SDD planning**: make the plan's dependency graph story-level and have `4-validate` check cross-epic data dependencies; then dispatch Phase 5 per epic along that graph.
5. **SDD-wide** (from `research/agent-cost-quality-techniques.md`): model/effort routing via `.claude/agents/` definitions; complexity gate with agent caps; shrink `6-verify` (427 lines) and run deterministic checks before LLM reviewers; file handoff with 3-line returns.
6. **Outside skill text**: slim the spawn prefix for headless backlog sessions; add a build/test output summarizer.

## Build order (cost classes, not human time)

| Step | Output | Class | Blocker |
|---|---|---|---|
| 0 | `phase_cost_report.py` with fitted rates (done) | done | none |
| 1 | Own-window mode: per invocation, Skill call to last descendant agent end | small, no model spend | none |
| 2 | `run_ab.py`: `claude -p --output-format json`, N runs per arm over two git refs of the skills dir, fresh worktree + temp HOME, random order, cost cap, paired bootstrap CI | medium build; each smoke run costs real money | decision: spend cap per experiment |
| 3 | Triad fixture + first A/B (change 1) | small build, medium run cost | none |
| 4 | `code:review` fixture + A/B (change 2) | small build, medium run cost | none |
| 5 | `pr-ship` stub-`gh` fixtures | medium build | none |
| 6 | Phase 5 golden project | large build, large run cost | pick the project |

Open: whether `claude plugin eval` is enabled for this account and whether the SDD suite's cross-references load under its isolation (`research/benchmarking-methods.md`).
