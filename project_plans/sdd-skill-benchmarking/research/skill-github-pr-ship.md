# github:pr-ship — cost and speed analysis (2026-11-01)

Skill: `.claude/skills/github/skills/pr-ship/SKILL.md` (415 lines) + `references/headless-settings.md`.
Method: python/mmap scan of `~/.claude/projects/*/*.jsonl`; windowed each real invocation (`/github:pr-ship` slash
command or `Skill` tool_use) from the invoke event to the next human message; summed cache-read of main + subagents
spawned inside the window. Scripts: scratchpad `psr_runs.py`, `sweep.py`, `cat.py`, `wake.py`, `polls.py`.
Labels: VERIFIED = I read the transcript/ran the count; INFERRED = reasoned from verified facts.

## 0. The baseline over-counts this skill (VERIFIED, read first)

- `phase_cost_report.py` labels every later turn with the last `Skill` seen (`last_skill` is never cleared). 251 sessions
  carry pr-ship labels = 6,024 Mtok cache-read. The 291 real invocation windows in them hold **1,198 Mtok (20%)**.
- Example: session `3967ab3e` invokes pr-ship once at event 2746; the window is 5 turns, but 8,446 later turns
  (3,383 Mtok, mostly unrelated orchestration) are labelled pr-ship. Same shape in `f1d0ad89`, `9e3cf2b3`.
- INFERRED: the real fitted cost is roughly one fifth of $1,195 (token share, not re-priced). Fix the labeller (clear
  `last_skill` on the next real human turn) before using this skill's number to rank work. The skill is still among
  the larger ones: median invocation 9 turns / 1.3 Mtok, but p75 3.7 Mtok and top 30 runs = 58% of window cost.

Window totals (291 invocations, 210 with >=5 turns): main thread 818 Mtok (68%), subagents 380 Mtok (32%).
Subagent split: review+skeptic agents 159 (169 agents), fix agents 113, haiku pollers 105 (183 agents).

## (a) Per-run table

Active min = main-thread event gaps capped at 5 min; sub = subagents spawned in window (their turns in brackets).
Cache-read Mtok = main + subagents.

| Session | Turns (main) | Cache-read Mtok | Active min (wall) | Subagents | Outcome |
|---|---|---|---|---|---|
| 4350803b (stapler-mcp PR45) | 73 (+350 sub) | 20.2 + 57.4 = 77.6 | 37 (67) | 6 | Ready after 2nd push (CI clippy fail); 3 re-entries more, 0.7-5 Mtok each |
| eed933c9 (steam-controls PR1) | 62 (+204) | 45.1 + 32.3 = 77.4 | 46 (61) | 5 | Ready to Merge; CI workflow was in wrong dir, fixed |
| c9b7d70e (stapler-squad PR1059) | 109 (+150) | 26.7 + 17.0 = 43.7 | 41 (63) | 7 | NOT ready at window end: CI silent, PR CONFLICTING; conflict resolved 40 min later |
| 95bae92c (kibitzer PR125) typical | 13 (+7) | 1.6 + 0.3 = 1.9 | 5 (5) | 1 | CI clippy fail fixed, CI green, left draft |
| f62e80c9 (typical, PR433) | 9 (+5) | 1.7 + 0.2 = 1.9 | 6 (6) | 1 | Merged origin/main, CI pending at window end |

Main-thread context per turn: 278k (4350803b), 729k (eed933c9, invoked inside a huge SDD session), 246k, 128k, 192k.
Across all windows: median 113k, p90 278k; 35 runs start above 200k and account for 319 of the 818 main Mtok.

## (b) Top 5 waste patterns

1. **Orchestrator runs in a bloated inherited context (biggest, ~25-45% of window cost).** VERIFIED: eed933c9 main turns
   read 662k-767k tokens each (45 of its 77 Mtok for 62 turns). Capping every main turn at 60k would remove 558 of 1,198
   Mtok (47%) — an upper bound, since a fresh agent also grows. INFERRED realistic saving 25-35%. The skill says
   "orchestrator only" but is run in the caller's session (sdd:7-ship, implement-top-issue) and does real work inline:
   4350803b main thread debugged an npm e2e flake, edited files, ran full `cargo test`, grep spot checks (turns 1492-1590, 1801-1857).
2. **Waking the full-context orchestrator to acknowledge background agents (~8% of window, 11.6% of main).** VERIFIED
   (wake.py): 479 text-only main turns directly after agent completion events cost 95 Mtok; each completion arrives twice
   (`<task-notification>` and "Another Claude session sent a message" carrying a subagent hand-back), 268 of those turns (52
   Mtok) are the duplicate. c9b7d70e turns 3395-3484: six consecutive "still waiting on X" turns while 4 reviewers ran.
   eed933c9 05:03-05:22: four `ScheduleWakeup` "is the fix agent done?" cycles at ~740k context each, though the
   completion notification would have resumed it anyway (the wakeups reported "found nothing actionable").
3. **Gate 4 learns about lint/format failures only after pushing (~10% of runs' cost; 1 extra push + wait + fix cycle).**
   VERIFIED: Gate 1 uses `cargo build/test`, `go build`, `tsc`; CI also ran `cargo fmt --check` and
   `cargo clippy --all-targets -D warnings`. 4350803b failed CI on fmt+flaky e2e at first look and again on clippy after
   Gate 2 (turns 1448-1500, 1917-2011; ~8 min and ~7 Mtok per cycle); 95bae92c failed on `clippy --all-targets`
   (agent said "my local clippy ran without --all-targets"). Fleet: 58 of 291 windows pulled `--log-failed`; 26 of
   those mention lint/format output, 11 lint-only (regex count, INFERRED category).
4. **Conflict check is Gate 5 (last), but a CONFLICTING PR gets no `pull_request` check runs, so Gate 4 stalls and the
   agent debugs the wrong thing (~30% of c9b7d70e).** VERIFIED: c9b7d70e 18:42:56 `gh pr view` printed
   `mergeStateStatus DIRTY, mergeable CONFLICTING, statusCheckRollup []`; the agent then spent 18:43-19:10 (26 turns, 8.0
   Mtok, plus a 20-min local `make ci`, 3 manual workflow_dispatch runs, close/reopen, a 98-min haiku poll) concluding
   "webhook delivery isn't firing", and only resolved the conflict at 19:22. INFERRED causal link (GitHub documents that
   conflicting PRs skip pull_request workflows). Fleet: 26 windows hit "no checks reported"; 9 of them also saw
   CONFLICTING/DIRTY in a tool result.
5. **Pollers: premature exits and spin loops (~9% of window, but on haiku so lower $ share).** VERIFIED (polls.py):
   183 poller agents; 35 (19%) finished in <1 min and 19 in <=3 turns. c9b7d70e's poller exited in 4 turns because
   `gh pr checks` returned "no checks reported" (exit 1): the dispatched prompt omitted the skill's 5-minute guard
   (only 8 of 183 prompts contain it). 9 pollers ran >=30 turns and consumed 41 of 105 Mtok — e.g. a2c00e68 wrote a
   script and then called `Monitor`/`Read` ~every 3 s for 91 turns instead of one `sleep`-based wait.

Also VERIFIED but smaller: (i) fix agents take one monolithic prompt of 10-25 KB and 150-225 turns (4350803b: 225
turns, 44 Mtok, 34 min for 13 findings; eed933c9: 150 turns, 22 min); (ii) the orchestrator re-verifies afterwards
(full test suite + greps) in all three top runs and found nothing wrong in any (4350803b 17:45, eed933c9 05:24,
c9b7d70e 18:37-18:41, ~15 turns/7 Mtok in c9b7d70e); (iii) the "re-run /code:review until clean" loop never ran a
second reviewer round in any of 48 runs that used reviewers (max 8 review/skeptic agents) — the instruction is dead
text; (iv) eed933c9 re-ran Gate 1b "already verified in Phase 6, re-confirming now". Counter-evidence (keep): Gate 2
found real defects in the top runs (silent action drop in `assign()`, unsynchronized `i.Backend` write, audit-log gap).

## (c) Ranked candidate SKILL.md changes

| # | Change | Proof metric | Risk |
|---|---|---|---|
| 1 | Run the gate loop in a fresh `general-purpose` subagent (prompt: PR#, repo path, state-file path, verbatim untrusted clause), never inline in the caller. Callers (sdd:7-ship, implement-top-issue) get a verdict only. Add "if own context >150k at entry, delegate". | main cache-read per turn at entry (target <70k median); total Mtok/run on the 35 big-context starts (-30%) | Lose conversational steering mid-run; hold/escalation must come back as a verdict field. Mitigate: Hold section already in state file |
| 2 | Move the conflict check to Entry (`mergeable`/`mergeStateStatus` before Gate 1); if CONFLICTING resolve first, and if "no checks reported" >2 min after a push with CONFLICTING, go to Gate 5, never debug webhooks/dispatch workflows. Keep Gate 5 as a re-check after CI. | Runs with "no checks reported" that also reach manual workflow_dispatch/close-reopen: now ~9 of 291 -> 0; turns between push and first check run | Early merge of base can invalidate Gate 1-2 results (rerun cheap Gate 1 only); small |
| 3 | Gate 1 derives local commands from `.github/workflows/*.yml` run steps (fmt, clippy `--all-targets`, golangci, eslint, etc.), runs those instead of the stack table; one command per CI job, skip deploy/matrix duplicates. | Fraction of runs with a lint-only CI failure after first push (~4% of windows lint-only, ~9% any lint mention) -> <1%; pushes per run | Longer Gate 1 locally; wrong job picked if workflow uses secrets/services — fall back to the table |
| 4 | Do not wake for subagent completion: dispatch reviewers/fixers with `run_in_background` and tell the orchestrator to end the turn with no text, ignore the second "hand-back" notification, and never use `ScheduleWakeup` to check a running agent. | Main text-only turns after notifications (479 -> <120); wakeups-per-run (38 total, 10 in eed933c9) -> 0 | A genuinely crashed agent goes unnoticed until its notification; keep a 60-min wakeup as dead-man switch |
| 5 | Replace the haiku poller with one blocking Bash (`timeout 590 bash -c 'until <cond>; do sleep 60; done'`, loop re-issued up to the 90-min cap) with the "no checks reported = pending for 5 min" guard embedded in the snippet; keep the agent only for unattended runs. | Poller turns (1,824 -> ~300), premature exits (19% -> ~0), Mtok on polling (105 -> <25) | Bash call max timeout is 10 min, so up to 9 main turns per 90-min wait at the large context; if #1 is adopted those are cheap |
| 6 | Verify after a fix agent once, narrowly: `git log`, the build+test that failed, and the agent's own reported test output; drop independent spot-check greps. Delete "Re-run /code:review until clean"; replace with one targeted re-review only if a BLOCKER/CRITICAL was fixed. | Orchestrator turns after fix agent (~12-15 -> ~4); zero change in post-merge defect rate | Misses a fix agent that lies about a security fix; keep targeted re-review for BLOCKER |
| 7 | Gate 1b: skip if the HEAD tree matches a SHA recorded as verified by sdd:6 / a previous run (state file records `verified-sha`); Gate 2: skip when review already ran on this diff (sdd:6 / a prior iteration) unless the diff changed since. | Gate 1/2 turns on re-entries (e.g. 4350803b re-entries cost 0.7-5 Mtok each); Gate 2 agents per PR | Stale verification if base moved; key the skip on `git diff` hash against base, not just HEAD |
| 8 | Split fix work: one fix agent per file group (parallel, <=3 findings each, prompts <4 KB), instead of one agent with 13 findings and a 10-25 KB prompt. | Fix-agent wall-clock (34 min -> ~10) and turns per finding (17 -> <8) | Merge conflicts between fixers; same-file findings must stay together |

Order of expected value: 1 > 4 > 2 > 5 > 3 > 6 > 8 > 7 (2 and 3 matter most for merge-ready rate, not cost).

## (d) Benchmark task ideas (deterministic pass checks)

All run in a throwaway GitHub repo created per trial (or `act` + a local bare remote for the no-network variant);
record turns, cache-read Mtok, active minutes, pushes via `phase_cost_report.py` on the transcript.

1. **Lint-only-CI trap.** Fixture Rust (or Go) repo, PR whose code compiles and tests pass but violates `cargo fmt` and
   a clippy `--all-targets` lint; CI workflow runs exactly those commands. Pass: final head's required checks all
   `success` AND exactly 1 push by the skill (extra pushes = fail on efficiency axis) AND state file all five gates
   `[x]`. Tests changes 3 and 7 (and gate ordering).
2. **Conflicting-PR with silent CI.** Same fixture, base branch advanced so the PR is CONFLICTING and its
   `pull_request` workflow does not trigger. Pass: skill resolves the conflict (merge commit, no markers) and
   `gh pr checks` reaches success; efficiency check: zero `workflow_dispatch`, close/reopen, or `make ci`-style
   substitute runs, and conflict resolution happens before the first CI wait. Tests change 2.
3. **Slow-CI wait cost.** PR whose CI is a single job `sleep 420 && exit 0` plus one reviewer-bot comment arriving at
   minute 3 (injected by the harness). Pass: ready report printed with a head SHA matching `--match-head-commit`,
   the late comment is detected (new_since_count > 0 path) and resolved, main-thread turns during the wait <= 6, poller
   (if any) never exits before the job completes. Tests changes 1, 4, 5 and the staleness re-check that VERIFIED
   exists in the skill.
