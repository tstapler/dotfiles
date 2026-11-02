# code:review and knowledge:extract-learnings: cost and benchmark research

Data: 43 sessions with `code:review` and 11 with `knowledge:extract-learnings` under `~/.claude/projects`. I re-derived per-turn labels with `phase_cost_report.py` (rates fitted on all 194 sessions). Times are UTC, 2026. Session ids are 8-char prefixes. Baseline: `baseline-phase-report-2026-11-01.txt` lines 13-14.
Scratch scripts are in `/tmp/claude-1000/-home-tstapler-dotfiles/70365390-dd85-4ee2-bc86-16f37456c1fe/scratchpad/crel/`.

## 0. Cross-cutting finding: the baseline mostly measures inherited labels, not the skills

The report labels a turn with its own `attributionSkill`, else the spawner's label, else the last skill seen. After the skill returns, all remaining work in the session inherits its label. That work is pr-ship CI polling, fix agents and later PR gates. VERIFIED by splitting turns on `Turn.inherited` (`crel/split.py`).

| skill | labeled $ (my fit) | own-attribution $ | inherited $ | note |
|---|---|---|---|---|
| code:review (43 sess) | 284.6 | 92.9 (33%) | 191.7 (67%) | mine covers more sessions than the baseline's 16 (cause not investigated), so use shares, not absolutes |
| extract-learnings (11 sess) | 91.1 | 8.6 main-thread (9%) | 82.5 | f1d0ad89 alone is $70.8 (78%): 1134 turns, 104 subagents, only 3 own turns |

Consequences:
- `par 0.5` for code:review is not reviewers idling. `agent_s / wall_s` divides by the active time of whole pr-ship sessions (VERIFIED, sec 1c).
- extract-learnings is about $0.8 per run, not $8 (10 own-label runs, $8.6 total). It is not a cost target. Any benchmark must score only own-attribution turns plus the review subagents.
- Recommended benchmark change: report `own$` and `inherited$` separately in `phase_cost_report.py` (not done; read-only task).

## 1. code:review

### 1a. Per-run table (top 10 of 43 by own-attribution cost)

| session | start (UTC) | own $ | labeled $ | own turns | own agents | Skill invocations |
|---|---|---|---|---|---|---|
| 4350803b | 09-11 16:47 | 13.8 | 29.2 | 274 | 11 (4 reviewers + 7 nested forks) | 1 |
| c86415dd | 09-30 08:27 | 12.1 | 31.1 | 201 | 13 | 3 (rounds) |
| eed933c9 | 09-12 04:52 | 8.2 | 30.0 | 90 | 8 | 1 |
| f3b50ede | 10-10 17:16 | 5.8 | 15.4 | 145 | 8 | 2 |
| c9b7d70e | 10-16 18:11 | 4.2 | 29.4 | 96 | 4 | 2 |
| c84db12c | 09-22 07:20 | 3.4 | 7.2 | 55 | 4 | 1 |
| db2db88b | 10-16 22:55 | 3.3 | 36.0 | 58 | 10 | 4 (rounds) |
| 2055c1cd | 10-16 04:18 | 3.2 | 8.5 | 38 | 4 | 2 |
| 2ad2a983 | 10-13 19:32 | 2.8 | 4.1 | 56 | 4 | 1 |
| 9e3cf2b3 | 10-05 07:51 | 2.7 | 4.1 | 55 | 2 | 1 |

Fleet: median own $1.19 per session, mean 3.9 own agents. Runs 4350803b and c86415dd were read closely. db2db88b was read for dispatch pattern only. eed933c9 was not read; its numbers come from the aggregate script only.

Per-agent cost, run 4350803b (`crel/pa.py`): main $2.22; code-refactoring $2.15 (39 turns); software-planner $1.94 (34); fork "Rust test code" $1.59; fork "dependency/access-control" $1.28; four more forks $0.59-0.97; security $0.35 (7 turns); testing $0.34 (5).
Run c86415dd, 3 rounds: 4 reviewers at $0.36-0.63 each in round 1, then 5 at $0.72-1.12 each on the larger PR #905 diff.

### 1b. Waste patterns

1. **Nested fan-out inside reviewers. VERIFIED, about 50% of review-agent cost in the worst run.** In 4350803b (16:52-17:02) the 4 dispatched reviewers spawned 7 `fork` agents (`Agent` tool calls inside the reviewers: security 5, testing 2). Forks cost $6.76 of the $11.6 reviewer total. Each fork pays a fresh 52k-token cache write (turn-1 usage of the "Review Rust test code" fork). Wall time was 10 minutes against 1-2 minutes in the flat runs (c86415dd round 1, 08:27:28 to 08:30:40). SKILL.md never says "do not spawn".
2. **Fixed per-agent startup tax. VERIFIED.** The first turn of every subagent carries about 80k tokens (c86415dd architecture reviewer: 22k cache read plus 59.5k cache write; 4350803b architecture reviewer: 23k plus 32k). Cache write is the priciest input bucket, so the 4-5 reviewers pay it 4-5 times on diffs as small as the 5-test-file PR in c86415dd round 1 ($0.36-0.63 per reviewer).
3. **No shared diff; every reviewer re-derives it. VERIFIED for presence, INFERRED for cost.** The lead's reviewer prompts are 1.4-3.5KB and contain a prose summary and file paths, never the diff (`ag.py` on c86415dd, 4350803b). Reviewers each run `git show`/`git diff` and `Read` the same files. In 4350803b, 18 of 25 review-ish agents ran git diff/show, and 17 of 46 distinct files were read by more than one agent (`plan.md` by 10). Estimate is 10-20% of reviewer tool turns, not measured.
4. **Wasted reads from wrong paths. VERIFIED, small.** c86415dd round 1 testing reviewer: first 3 `Read`s returned 164-char errors (path under the worktree, not `~/dotfiles`), then a `find` to recover. Lead prompts name `~/dotfiles` while cwd was a worktree.
5. **Re-review rounds repeat the full panel. VERIFIED.** c86415dd has 3 invocations (08:27, round 2 PR #905 around 17:00 with 5 reviewers at $0.72-1.12 each, round 3 `exportAntigravity` hook). db2db88b has 4 invocations. Round 2+ can be scoped to the fix commit (one run did this: "Re-review the review-fix commit", 3 turns).
6. **Reviewers run on the lead's model. VERIFIED.** All reviewer turns are `sonnet-5` or `sonnet-5-5`, the same as the lead (`insp2.py`); the `Agent(...)` blocks in SKILL.md set no `model`. Haiku appears only on CI-poll agents. No tiering.
7. **Dead steps and dimensions.** Step 4 (project-coordinator) was never run: no own-label agent has that type in 43 sessions. The Step 1 DB agent runs only on DB diffs (5 times, $1.83 total, cheap and correctly gated).
8. **Skeptic is cheap and earns its place. VERIFIED.** 6 dedicated skeptic agents across the 43 sessions cost $0.36-1.16 each ($4.0 total, about 4% of own spend). Two runs show inline skeptic reasoning, with no agent in at least c86415dd ("skeptic pass reasoning done inline", 08:30:40).

### 1c. Why parallelism is 0.5

- Reviewers ARE dispatched together. 4350803b: 4 `Agent` calls between 16:52:46 and 16:53:16. c86415dd: 08:27:28 to 08:28:02. Subagent start times in `insp2.py` output are within about 30s. They run in the background, and the parent waits with `TEXT "waiting on the other three"`. VERIFIED.
- The roughly 10s gap between launches suggests one `Agent` call per assistant message (INFERRED from timestamps). That gives about 30s of serial launch lag, small.
- `par = agent_seconds / session_active_seconds`. Session wall includes everything after review (CI polling, fix verification, `ScheduleWakeup` gaps: 08:34-08:38 in c86415dd), because those turns inherit the label. The metric is dominated by the main thread. The longest pole inside the review is the slowest (nested-fork) reviewer.

### 1d. Findings quality (n=2 runs read closely, so VERIFIED but thin)

- c86415dd round 1: 4 reviewers returned 7 kept items (1 CRITICAL, 6 MAJOR), 3 discarded inline. All 7 went to one fix agent (commit `745df33`). Two reviewers converged independently on the unguarded `copytree` finding.
- 4350803b: about 27 raw findings. The skeptic agent (17:03-17:10, 30 turns, $1.16) produced 13 real (fixed), 4 deferred, 10 discarded (37%). Fix agent dispatched 17:10:41.
- Overall: 48-100% of raw findings get fixed. The skill's "30-40% false positive reduction" claim matches the 37% here (a second source for it was not found).

### 1e. Ranked candidate changes

| # | change | proving metric | quality risk |
|---|---|---|---|
| 1 | Add "Do not spawn subagents; use Read/Grep/Bash only" to every reviewer prompt, and split by lens, not by file | agents/run (target 4-5), own $/run, wall of slowest reviewer; goal -30 to -50% on large diffs | Low-medium: large diffs lose per-file depth. Mitigate by giving each lens a file list |
| 2 | Lead writes `git diff` once to `/tmp/review-<sha>.diff` plus a changed-file list; reviewers Read that file instead of re-running git; prompts state the real cwd | tool turns per reviewer, count of duplicate `git diff/show` calls (18 of 25 in 4350803b) | Low |
| 3 | Delta-only re-review: round 2+ gets only the fix commit diff and only the dimensions that had findings | own $ of rounds 2+ (share of rounds 2+ in c86415dd and db2db88b not computed) | Low-medium: a regression elsewhere would be missed. The test suite covers most of that |
| 4 | Size gate: diffs under about 150 changed lines get one combined reviewer with all five checklists, others get the full panel | agents/run, recall on seeded benchmark vs panel | Medium: needs the benchmark to prove recall holds. Saves 3-4 startup taxes (about $0.3-0.5 each) |
| 5 | Model tiering: run Code Quality and Architecture checklists on a cheaper model, keep Security and Testing on the lead's model | catch-rate per lens on benchmark, $ per lens | Medium-high on architecture; the 2 reviewers with the highest turns are exactly these |
| 6 | Delete Step 4 (project-coordinator), or make it opt-in | none (never ran) | None |
| 7 | Keep the skeptic, but stop running it as a 30-turn ADR-reading agent when findings are fewer than 8 (inline instead, as in c86415dd) | tokens in skeptic, discard rate vs agent skeptic on the same findings | Low |

## 2. knowledge:extract-learnings

### 2a. Per-run table (own-attribution only; start UTC)

| session | start | own turns | own $ | pattern |
|---|---|---|---|---|
| 2055c1cd | 10-16 06:44 | 19 | ~1.5 | read global MEMORY.md and journal, 6 Edits to existing, 1 Write, wiki page edit |
| 05f798f4 | 10-20 03:39 | 15 | ~1.5 | checked existing memory first, 5 new Writes, extended 1 existing file |
| c84db12c | 09-22 07:40 | 13 | ~1.2 | 3 reads, 5 Edits of existing, 2 Writes |
| eed933c9 | 09-12 05:53 | 7 | ~1.3 | 2 reads, 5 Writes |
| 8f1af5b4 | 10-23 05:39 | 6 | ~0.3 | one Bash batch, then continued to ship |
| 48d00f1e | 10-24 23:15 | 7 | ~0.4 | 3 Writes |
| 9e3cf2b3 | 09-30 23:32 | 4 | ~0.6 | 5 Writes, 1 Edit, 1 read |
| 4350803b | 09-11 19:01 | 9 | 1.0 | 4 Writes |
| 3113016c, e5ab8b8e | 10-20, 10-24 | 4, 3 | 0.3, 0.05 | trivial |
| f1d0ad89 | 10-10 16:49 | 3 | 0.3 | the other 1131 turns and $70 are mis-attributed (sec 0) |

Fleet: 90 own turns, $8.6 for 10 real runs. Write/Edit counts come from a 30-tool-call window after the Skill call (`crel` inline script) and may include unrelated memory-path tool calls.

### 2b. What it reads and writes

- It does NOT re-read the transcript. It derives learnings from the live context (SKILL.md Step 1; sequences in 05f798f4 and 2055c1cd show only memory/journal reads and a `ls`). VERIFIED for those 2 runs plus the skill text. This means every turn pays the full conversation as cache read (the main-thread buckets are large), which is why one turn costs about $0.1.
- Writes: 2-6 files per run (project memory files, global `MEMORY.md`, journal, occasional wiki page).
- Duplicate check: 5 of 10 windows show an explicit read of existing memory (2055c1cd, 05f798f4 via Bash, c84db12c, eed933c9, 9e3cf2b3), and 2055c1cd, c84db12c, 05f798f4 edited or extended existing files ("Existing memory already covers the RPC-gate lessons, so I'll extend that file and add only what's new", 05f798f4 03:50:40). The other runs wrote straight to new files. Share of new-vs-duplicate content was NOT measured; that needs a diff of the memory dir before and after, which I did not run. INFERRED: at least half the runs risk duplicating.
- Variance: 8f1af5b4 spent its 6 turns on plan errata, a commit and a merge, and wrote "project learnings" inside a Bash batch. There is no consistent output format, so the Output counts in the skill (global/project/wiki) are rarely printed.

### 2c. Waste patterns

1. **Mis-attribution** (sec 0): about 91% of reported spend. VERIFIED.
2. **Many serial turns on a hot context.** 05f798f4 issued 5 separate `Write` turns plus one Bash batch (03:50:46 to 03:51:16). Each turn re-reads the whole session as cache. Batching all writes into 1-2 turns would cut about half of a roughly $1 run. INFERRED from per-turn cost ($0.095/turn mean).
3. **Dedup is optional in practice.** SKILL.md says "check for an existing file" only in Step 4. A run can write a new file without it. UNVERIFIED how often this produced duplicates.
4. **Can a cheap model do it? Not by default.** It needs the full context to judge what was surprising. A forked haiku agent inherits the same large context at fork cost (INFERRED). A haiku agent given a 1-3KB lead-written digest (decisions, surprises, files touched) would be cheap, but the digest has to be written by the lead, so the saving is about the same as batching writes.

### 2d. Ranked candidate changes

| # | change | proving metric | quality risk |
|---|---|---|---|
| 1 | Fix attribution in the report (own vs inherited) so the skill stops looking like a $88 cost | own$ per run (about $0.8 today) | None |
| 2 | Require: list memory dir and `MEMORY.md` index first, then write all files in one tool turn (parallel Write/Edit) | turns per run (target 8 or fewer from 15-25), duplicate-file rate on benchmark | Low |
| 3 | Add a "nothing worth saving" exit: if no learning passes the "what should I do differently" test, write nothing and say so | writes on a null transcript (target 0) | Low-medium: may drop marginal notes. Check on the benchmark |
| 4 | Dedup-first rule in Step 3 as well as Step 4 (global instincts currently append blindly) | duplicate rate against seeded existing memory | Low |
| 5 | Lead passes a short digest to a haiku subagent that does Steps 2-4 | $ per run, must/must-not pass rate | Medium: weaker judgment on "non-obvious". Run only after 2-4 are measured |

## 3. Benchmark task ideas

### code:review
- **CR-1 (seeded defects, Go or Java).** Freeze a repo as a `git bundle` plus a 150-250 line diff with 6 seeded defects: SQL built by string concatenation; list endpoint where an empty tenant filter returns all tenants (the lens the skill calls most commonly missed); new branch with no test; N+1 call in a loop; error-contract change that breaks a caller; a 7-line comment. Add 2 decoys the skeptic should discard (an intentional pattern documented in an ADR, and a style nit below confidence 75). Deterministic check: parse the report; a seeded defect counts as caught if a finding sits within +/-3 lines with severity at least MAJOR; a decoy fails if reported as BLOCKER or CRITICAL; score recall, precision, then own $ and agent count. Run N=3 per variant at a fixed model.
- **CR-2 (two-round).** Same repo, then a "fix commit" that fixes 4 of the 6 defects and introduces one regression. Check: round 2 must report the regression and must not re-report the 4 fixed defects, with a cost cap versus a full re-panel. This tests candidate 3 (delta re-review). For candidate 1, add a 600-line multi-module diff and assert the number of Agent spawns inside reviewers is 0, with recall unchanged.

### knowledge:extract-learnings
- **EL-1 (must/must-not save).** Freeze a truncated transcript (from 05f798f4 or 2055c1cd) plus a snapshot of the project memory dir that already contains 2 of the 5 lessons the session produced. Run in a sandboxed HOME. Must: at least 1 file or edit matching each of the 3 novel lessons (key phrase regexes, for example "stale local `main` ref" and "push-only Pages deploy"). Must not: a new file duplicating the 2 existing lessons (the existing file is edited instead); commit SHAs, PR numbers, `/tmp/...` paths or timestamps in saved text; more than 1 index line per new file; `MEMORY.md` over 200 lines; invalid frontmatter. Report writes, turns, own $.
- **EL-2 (null yield and secret).** (a) A routine transcript (rename plus tests green, nothing surprising): must write 0 files. (b) A transcript that contains a seeded API token and a private path: assert the token never appears in any written file. Together with EL-1 this bounds the quality side of candidates 3 and 5.
