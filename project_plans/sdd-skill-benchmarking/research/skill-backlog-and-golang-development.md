# Skill cost study: backlog:status/review/ship and golang-development

Data: transcripts in ~/.claude/projects, loaded with phase_cost_report.load_session, as of 2026-11-01.
Session ids are 8-char prefixes; dates are approximate (derived from epoch). VERIFIED = counted or read in a transcript or file. INFERRED = reasoned, not measured.
Baseline: baseline-phase-report-2026-11-01.txt. A prefix match on attributionSkill found 331/108/299/5 sessions for status/review/ship/golang-development, against 112/61/75/9 in the baseline. Counts here are mine; the baseline used a different filter and I did not reconcile them.
Dollar figures come from the baseline: status 70.17 / 2621 turns = $0.027 per turn; golang-development 80.09 / 1637 = $0.049 per turn.

## Key finding: the label is the whole session, not the command

Both skill types are tiny prompts that trigger a long, unrelated session. The cost comes from that session.

- VERIFIED: the backlog:* commands are not in dotfiles. stapler-squad generates them per item (`session/backlog_commands.go:89` in ~/.stapler-squad/repos/github.com/tstapler/stapler-squad). status.md is 131 bytes: "Call get_backlog_item ... Format as numbered checklist". review.md is 1.3 KB and ship.md is 2.1 KB.
- VERIFIED: the label is inherited by every later turn. In backlog:status, 3513 turns carry their own attribution; 5431 turns carry the label in total.
- VERIFIED: status is the first action of an autonomous worker session. The kickoff prompt is the whole backlog item (3.5-4.7 KB), and the median pre-status turns is 1. Session 6dad1c0a (~Oct 10) went from status to a full Kotlin feature with 75 Bash calls and 21 gradlew runs.
- So the "$70 for status" is feature-implementation cost. Optimizing status.md cannot move it.
- The same holds for review and ship: median first-labelled-turn context is 112k and 64k tokens, which is the prior session carried along.

## 1. backlog:status (331 sessions in my filter; baseline 112 sessions, $70)

(a) Per-run (labelled turns, subagents included):

| stat | turns | cache-read Mtok | active min | output k |
|---|---|---|---|---|
| p25 | 2 | 0.1 | 0.1 | 0.5 |
| p50 | 7 | 0.6 | 1.7 | 2.0 |
| p75 | 23 | 2.6 | 9.5 | 10.7 |
| p90 | 43 | 5.3 | 19.1 | 25.2 |
| max | 198 | 32.5 (b551804a, ~Oct 13) | 111 | 75 |

Totals: 640 Mtok cache-read. The top 10% of sessions hold 48% of it. Whole-session cache-read is 2,599 Mtok, so the label covers about a quarter of what these sessions spend.
The pure command run (e.g. af6f15af ~Nov 1, 46c68913 ~Oct 10) is 1 MCP call plus 1 git command, about 0.6 Mtok. At p50 this is the whole labelled cost.

(b) Waste patterns:
1. VERIFIED: fixed startup prefix re-read every turn. First-turn context is p50 69.7k, p25 62k, p90 86k tokens (all 331 sessions). Prefix x turns = 424 of 640 Mtok, 66% of labelled cache reads. What the prefix holds (system prompt, the ~270-entry skill listing, MCP tool names, CLAUDE.md at 13 KB + 3.8 KB) is INFERRED. It has not been measured per component.
2. VERIFIED: large Bash output. Bash results are 111-290k chars per expensive run; 83fccec2 (~Oct 25) had 238k chars from 118 Bash calls (`cargo` 42, `go build` 26). Build/test output goes straight into context.
3. VERIFIED: repeat get_backlog_item. 43390a93 (~Oct 16) called it 4 times, 18k chars; 83fccec2 4 times, 29k chars. The item is already in the kickoff prompt. Small.
4. VERIFIED: extra ToolSearch hop to load deferred ssq tools (`select:mcp__stapler-squad__...`) in 76 of 331 sessions. One extra turn at about 100k context each. Small.
5. INFERRED, low confidence: 701 "silent_turn_reminder" attachments across 201 sessions ("say what you're doing"). They are attachments, not separate turns, so likely little cost; I did not measure the added output.
6. VERIFIED: context grows over the run (6dad1c0a: 63k at start, 344k at max). Late turns cost 5x early turns; no compaction seen.

(c) Ranked candidates:

| # | change | proving metric | quality risk |
|---|---|---|---|
| 1 | Slim the worker-session startup prefix: drop unused skills/plugins/MCP from headless backlog sessions (stapler-squad spawn flags or settings) | first-turn ctx tokens (now p50 70k); label cache-read Mtok per equal task | Medium: agent loses skills it would auto-invoke (sdd:6-verify, golang-*) |
| 2 | Wrap build/test output: a script that prints the last 30 lines and failures only, named in the worker prompt or a hook | Bash result chars per session (now 110-290k) | Low-medium: may hide a useful warning |
| 3 | Preload ssq MCP tools instead of ToolSearch; tell status.md the item is already in the prompt | turns before first real action | Low |
| 4 | Edit status.md | none: 131 bytes | n/a, not worth it |

(d) Benchmark task: a fixture repo with a synthetic backlog item (a 3-line known change plus 3 acceptance criteria) and a stub ssq MCP server. Run the worker kickoff. Deterministic checks: (i) `go test` passes in the fixture, (ii) first-turn context tokens <= threshold, (iii) total Bash result chars <= threshold, (iv) report_progress called 3 times with the right criteria_index.

## 2. backlog:review (108 sessions; baseline 61, $15.87) and backlog:ship (299; baseline 75, $10.56)

(a) Per-run:

| skill | turns p50 / p90 / max | cache-read Mtok p50 / p90 | active min p50 / p90 | first-turn ctx p50 | prefix share of label cache-read |
|---|---|---|---|---|---|
| review | 5 / 22 / 57 | 0.5 / 3.2 | 1.3 / 13.5 | 112k | 89% |
| ship | 1 / 4 / 68 | 0.1 / 0.4 | 0.0 / 0.4 | 64k | 91% |

Totals: review 128 Mtok, ship 96 Mtok; the top 10% of ship sessions hold 70% of it.

(b) Waste patterns:
1. VERIFIED: the typical run is trivial. 0ec1d882 (review, ~Oct 28) was ToolSearch plus one `request_review`; e803e1de (ship) was 1 turn. The cost is the carried context (89-91% of label cache-read).
2. VERIFIED: a few runs are real work. f62e80c9 review (~Oct 16; 57 turns, 18 subagents) ran a full idiom/architecture review (sdd:6-verify) after request_review. 4e442d95 ship (~Oct 15; 68 turns, 42 min) was CI polling driven by user prompts ("Check the Bazel CI jobs", `gh pr checks 425`).
3. VERIFIED: ToolSearch to load `request_review` or `report_pr_created` in 43/108 review and 54/299 ship sessions. Extra turn at 100k+ context.
4. VERIFIED (file read): ship.md step 2 runs `/backlog/review` from inside ship when review looped. That is a second round-trip over the full context.
5. INFERRED: `gh pr checks` polling by a Sonnet agent on a 150k+ context is deterministic work. A script plus `schedule_wake` would do it, as the commands already advise.

(c) Ranked candidates:

| # | change | proving metric | risk |
|---|---|---|---|
| 1 | Preload the ssq tools so no ToolSearch turn | turns per review/ship | none |
| 2 | CI-wait: one script returning pass/fail/pending; agent uses schedule_wake instead of polling turns | turns and active min on 4e442d95-style runs | Low |
| 3 | PR creation and PR-body writing in a cheaper-model subagent (Haiku) given the summary; main context never re-read | cache-read Mtok per ship | Medium: PR body quality |

(d) Benchmark task: replay `/backlog/ship` on a fixture repo with a pre-made branch and a stub gh. Deterministic checks: `report_pr_created` called once with the right pr_number, PR body contains the `## Summary / ## What Changed / ## Test plan` headings, turns <= N.

## 3. golang-development (5 sessions by attribution; baseline 9 sessions, $80, 1637 turns)

(a) Per-run:

| session (date) | main turns | subagent turns | cache-read Mtok | active min | Skill invoked (share of session) |
|---|---|---|---|---|---|
| 117ebd00 (~Oct 10) | 148 | 0 | 37.9 | 68 | ~16% in |
| 0ac487a7 (~Oct 19) | 145 | 93 (3 files) | 33.8 | 181 | ~5% in (merge-train session: 605 Bash, 46 Agent) |
| f35758f3 (~Oct 26) | 26 | 0 | 6.2 | 13 | ~79% in |
| 64ade807 | 36 | 0 | 5.0 | 14 | ~36% in |
| 7f4a0505 | 23 | 0 | 3.0 | 13 | ~12% in |

Total 85.9 Mtok; the whole sessions total 347 Mtok. Median run is 36 turns, 6.2 Mtok. (Invocation share is from message-line counts, approximate.)
Size: SKILL.md is 209 lines / 14.6 KB (about 3.6k tokens). Its 3 reference files add 555 lines / 17.6 KB. There are 43 `golang-*` skills; related ones are 7-21 KB each.

(b) Waste patterns:
1. VERIFIED: the skill is not a cost driver. 3.6k tokens x 378 main turns = about 1.4 Mtok, 1.6% of the label's 85.9 Mtok (upper bound; counts every labelled main turn). The $80 is the Go work that followed, not the skill text.
2. VERIFIED: references are never read. 0 Reads of golang-development/references/* in all 5 sessions. They cost nothing unless opened, so no waste, but their value is unproven (small sample).
3. VERIFIED: the real spend in the big runs is Bash output. 0ac487a7 had 867k chars of Bash results, 81 `go test`, 37 `go build`, 25 `go vet`, 28 `git fetch`, 26 `git merge`. 117ebd00 had 293k chars from 134 Bash calls (22 `go test`, 14 `make`). A script could drive that merge/CI loop.
4. VERIFIED: f35758f3 read 1.38M chars through Read (screenshots, TSX), far more context than the skill ever adds.
5. INFERRED: invoked late in 1 of 5 sessions (f35758f3), so it cannot have shaped earlier code there.
6. INFERRED: overlap with the dedicated skills it links (`golang-error-handling`, `golang-naming`, `golang-testing`) means a double-load when both fire. Not observed in these 5 sessions.

(c) Ranked candidates:

| # | change | proving metric | quality risk |
|---|---|---|---|
| 1 | Leave the skill body alone; fix Bash-output flooding in Go sessions (a `go test`/`go vet` summarizer wrapper) | Bash result chars per session (0ac487a7: 867k) | Low-medium |
| 2 | Trim SKILL.md to checklist plus anti-patterns (about 110 lines), rest to references | skill tokens loaded (3.6k -> about 2k); vet/lint pass rate on the benchmark task | Medium: weaker idiom guidance |
| 3 | Dedupe against golang-concurrency/safety/code-style | description triggers per session | Medium |

Saving from #2 is at most about 0.6 Mtok (about 0.7% of the label), so it is not worth a benchmark on its own.

(d) Benchmark task: a fixture Go module seeded with anti-patterns (primitive-obsession IDs, a leaking goroutine, a naked bool param, a mutable global). The task is "add feature X with tests". Deterministic checks: `go vet` and `go test -race` pass, `staticcheck` clean, grep confirms a typed ID is used, no `interface{}` in the new API, goroutine test passes under `goleak`. Run with-skill, slim-skill and no-skill arms.

## Verdict (cost x frequency)

- backlog:status: the command is not worth optimizing (131 bytes, one MCP call; median run 0.6 Mtok). The attributed $70 is autonomous feature work. The one real target is the startup prefix (66% of labelled cache-read), which is a stapler-squad spawn setting, not a skill edit. Priority: medium, as a spawn-config experiment.
- backlog:review / backlog:ship: low priority. Median runs are 1-5 turns. The tail is review sub-work and CI polling. Do the easy fixes (preload tools, CI-wait script); the replay task suffices.
- golang-development: not worth optimizing the skill. It is 1.6% of its label's cache reads and the references go unread. The money is in Go build/test/merge output; a Bash-output wrapper also helps status.
- Caveat on the baseline: phase_cost_report inherits the label to all later turns, so these rows are per-session-type cost, not skill cost. Own-turn counts (inherited=False) are a better measure of what a skill itself spent.
