# Benchmarking skill changes (before/after) with statistical honesty

Date: 2026-11-01. Claude Code under test locally: 2.1.316.
Labels: **VERIFIED** = I opened the source (or ran the command) this session. **UNVERIFIED** = secondary source, search snippet, or my inference. Anything marked INFERRED is my reasoning, not a citation.

## 0. Bottom line

1. Anthropic now ships first-party tooling for exactly this: `claude plugin eval` (paired with-plugin vs no-plugin arms, 3 runs per case by default, graders, JSON, CI exit codes). It is the right substrate for *"does the skill help vs nothing"*. It is a poor fit for *"did my edit to the skill help vs the old version"* and for token-bucket accounting (see 1.2).
2. For *old-version vs new-version* of a skill, build a thin harness around `claude -p --output-format json` that runs both arms on the same frozen task snapshots, then does a **paired, task-clustered bootstrap**. The statistics are cheap; the real cost is task design and running N x K x 2 sessions.
3. The honest sample size is large. My simulation (section 2.5) says 20 tasks x 5 runs only detects a ~15-20 point success-rate change reliably. Token/cost deltas are far easier to detect than success deltas, which is both useful and a Goodhart trap.
4. Biggest validity threats: prompt-cache warmth skew, model/infra drift between arms, order effects, grader noise, and tasks that leaked into the skill text.

## 1. Anthropic tooling and guidance

### 1.1 Official guidance

- **Skill best practices, "Build evaluations first"** (VERIFIED, https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices): run Claude on representative tasks without the skill, establish a baseline, write minimal instructions, iterate against the baseline. Checklist: "At least three evaluations created", tested with Haiku, Sonnet, Opus. It states: "There is not currently a built-in way to run these evaluations" (that note is older than `plugin eval`; treat as stale).
- **Claude Code skills doc** (VERIFIED, https://code.claude.com/docs/en/skills.md): "run each one in a fresh session with the skill available and again with it turned off". A fresh session matters "because leftover context from authoring the skill will mask gaps". Turning off a personal/project skill for the baseline: `skillOverrides` set to `"off"`. Plugin skills: use `claude plugin eval`. `/skill-doctor` (v2.1.252+) reports per-skill context cost and usage; prints text under `-p`.
- **Demystifying evals for AI agents** (VERIFIED, https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents): pass@k = at least one success in k tries; pass^k = all k succeed; combine code-based, model-based, human graders (prefer deterministic); each trial starts from a clean environment (shared state such as git history leaks across trials and inflates scores); read transcripts; test both should-trigger and should-not-trigger cases; calibrate LLM judges against humans and give them an "Unknown" option; saturated evals stop showing gains but still work as regression tests.
- **Description token budget** (VERIFIED, skills.md above): combined `description` + `when_to_use` truncated at 1,536 chars in the listing; once loaded a skill stays in context across turns; after compaction the most recent invocation of each skill is re-attached up to 5,000 tokens each within a 25,000-token shared budget. Relevant because a "tighter SKILL.md" change has measurable recurring token effects.

### 1.2 `claude plugin eval` (VERIFIED, https://code.claude.com/docs/en/plugin-evals.md)

Requires Claude Code >= v2.1.269 (my local 2.1.316 qualifies). Facts, all from that page:

- Layout: `evals/<case>/prompt.md` (frontmatter + prompt) or `case.yaml`, plus `graders/*.md`. `plugin eval init` scaffolds; `init --bare <name>` for CI.
- Each run: fresh isolated `claude -p` child with temp HOME, temp cwd, temp Claude config; only the plugin under test is loaded; user settings, CLAUDE.md, MCP, other plugins, memory, other skills are absent; Artifact tool off; eval directory hidden from the agent.
- Default 3 runs per case per arm (`runs` 1-50; `--runs`). Two arms by default: WITH plugin and W/OUT; reports `Δ` = with minus without. `--ablation none` runs one arm (halves cost). Score = fraction of graders passed per run, mean over runs; case passes at `--threshold` (default 1.0).
- Graders (six types): `regex`, `tool_used`, `tool_order`, `file_exists` (free), `llm` (judge votes, passes at 2 of 3), `baseline` (judge compares to a reference transcript). No custom-code graders. `tool_used: Skill` graders are auto-excluded from scoring in two-arm runs (reported as "plugin-fired indicator").
- Case limits: `max_turns` default 10 (cap 200), `timeout_seconds` default 300 (cap 3600), `model`, `allowed_tools`, `append_system_prompt`, `env` (only `EVAL_*`). `context.scaffold_script` (bash, 120 s, needs `--scaffold`) builds fixture files or a git repo; `context.history_file` resumes a `.jsonl` transcript; `add_dirs` read-only.
- CI options: `--json path`, `--threshold`, `--model` (docs: "Pin it in CI so a model rollout isn't mistaken for a plugin regression"), `--judge-model`, `--max-cost-usd`, `--trust-plugin`, `-j` 1-8, `--keep-temp`. Exit 0 pass; 1 below threshold/load error/API error; 2 partial (cost ceiling or auth); 130/143 interrupted. "The with-minus-without delta is reported but never changes the exit code."
- Tool grants: runs never prompt; Bash/Write/Edit/WebFetch need `--allow-tools`; granting Bash forces the OS sandbox (Linux needs `bubblewrap` and `socat`).
- JSON (`aggregate-result.json`, `schemaVersion: 1`): `aggregates.overallScore`, `casesPassed/casesTotal`, `meanDelta`, `cases[].aggregates.score|delta`, `cases[].arms.with[].error`, `costUsd`, `durationSeconds`, `claudeVersion`, `partial`.
- Availability risk: troubleshooting lists "plugin eval is currently in early access" and "currently unavailable ... Anthropic has switched the command off server-side". So it can be gated off remotely. Do not make it the only path.

**Fit for this repo, my assessment (INFERRED):**

| Need | `plugin eval` | Gap |
|---|---|---|
| "Skill vs no skill" delta | Yes, native | Plugin packaging required (skills-directory plugin may work: `name@skills-dir`, per target table) |
| "Old SKILL.md vs new SKILL.md" | Indirect: run twice against two checkouts/git refs and diff two `aggregate-result.json` | No paired stats across runs; no built-in CI on the difference |
| Token buckets (input/cache read/cache write/output), turns, subagent count | Only `costUsd`, `durationSeconds` aggregated | Need our own capture (1.3) |
| SDD-scale tasks (multi-phase, subagents, many files) | `max_turns` <= 200, `timeout_seconds` <= 3600; `Agent` tool is in the read-only grantable set | Isolation hides `~/.claude` skills/agents the SDD suite cross-references; they must ship in the plugin |
| Work in a real repo snapshot | `scaffold_script` can `git clone` / checkout a fixed commit (needs `--scaffold`; sandbox network limits apply, INFERRED) | Cloning private repos inside the sandbox is unproven |

### 1.3 `claude -p` headless as the measurement primitive

- **`--output-format json`** (VERIFIED by running v2.1.316 locally, plus https://code.claude.com/docs/en/headless.md): the result object has keys `usage`, `modelUsage`, `total_cost_usd`, `num_turns`, `duration_ms`, `duration_api_ms`, `permission_denials`, `subagent_stats`, `session_id`, `stop_reason`, `terminal_reason`, `is_error`, `subtype`. `usage` carries `input_tokens`, `cache_creation_input_tokens`, `cache_read_input_tokens`, `output_tokens`, and a `cache_creation` split into 5m/1h. `modelUsage[model]` has per-model tokens and `costUSD`, `costBasis: "list"`. Docs: cost is a "client-side estimate" that "can differ from your actual bill".
- **`--output-format stream-json --verbose`**: newline-delimited events; subagent messages carry `parent_tool_use_id` (null for main thread) so subagent count and per-subagent tokens are recoverable; `system/init` reports `plugins`, `plugin_errors`, `mcp_servers`, `mcp_server_errors` (use to fail the run if the intended skill/plugin did not load) (VERIFIED, headless.md). `permission_denied` events and `permission_denials` in the result.
- **Flags** (VERIFIED, https://code.claude.com/docs/en/cli-reference): `--max-turns` (print mode; "Exits with an error when the limit is reached"), `--max-budget-usd` (print mode; subagent spend counts; can overshoot), `--no-session-persistence`, `--model`, `--permission-mode` (`default|acceptEdits|plan|auto|dontAsk|bypassPermissions`), `--plugin-dir`, `--setting-sources user,project,local`, `--settings`, `--strict-mcp-config`, `--disable-slash-commands`, `--worktree/-w`, `--exclude-dynamic-system-prompt-sections` (moves per-user context such as the auto-memory location out of the system prompt for better cache reuse across machines).
- **`--bare`** (VERIFIED, headless.md): skips hooks, skills, commands, subagents, plugins, MCP, auto memory, CLAUDE.md; "recommended mode for scripted and SDK calls" and "will become the default for `-p` in a future release". It never reads OAuth/keychain, so it needs `ANTHROPIC_API_KEY`. Also drops system reminders (including the skill list) and background tasks. Implication: a `--bare` arm is a "no ambient config" arm; load the skill under test explicitly via `--plugin-dir` or `--add-dir` (skills in `--add-dir/.claude/skills` still load). The default non-bare `-p` loads everything from `~/.claude` and the project, which is exactly the contamination you want to control.
- `-p` supports `/skill-name` in the prompt string (expanded before run) (VERIFIED, headless.md). This is how to invoke `/sdd:quick` headless.
- Since v2.1.302 a `-p` run starts in Manual permission mode when nothing sets one (VERIFIED, headless.md): unlisted tools needing approval are denied. Use `--permission-mode acceptEdits` plus `--allowedTools`, or `dontAsk` for strictly locked runs; `bypassPermissions` only inside a throwaway container/worktree.
- **Isolation options:** (a) `plugin eval`'s own temp-HOME model; (b) `HOME=$(mktemp -d)` plus copied minimal `~/.claude` (INFERRED; the repo memory notes a `pi` HOME-sandbox convention but that is a different tool); (c) `git worktree` per run (see `--worktree`), which isolates files but not `~/.claude`.

### 1.4 skill-creator (VERIFIED, https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md)

- Paired runs launched in the same turn (with-skill vs baseline; for improving an existing skill the baseline is `old_skill` via `cp -r <skill> <workspace>/skill-snapshot/`). Workspace `iteration-N/eval-K/{with_skill,old_skill}/outputs`, `timing.json` (`total_tokens`, `duration_ms`), `grading.json` (fields `text`, `passed`, `evidence`), `benchmark.json` with mean +/- stddev and delta via `scripts.aggregate_benchmark`.
- Caveat I extracted from the page: no fixed repetition count is specified; each eval appears to get one run per configuration, so the "stddev" is across evals, not across repeats. Treat it as a viewer and workflow, not as statistics.
- Description optimizer: 20 queries (about half should-trigger, half near-miss negatives), 60/40 train/held-out split, 3 runs per query, up to 5 iterations, best description chosen by **test** score. This is the only official train/test discipline I found.
- Old-skill-as-baseline plus snapshot is the pattern to copy for before/after.

## 2. Statistics for noisy agents

### 2.1 Treat it as an experiment (Anthropic, "Adding Error Bars to Evals")

VERIFIED by reading the PDF text (arXiv 2411.00640, https://arxiv.org/abs/2411.00640). Its five recommendations: (1) SE of the mean via CLT; (2) clustered SEs when questions come in related groups (real-world adjustment "up to 3X"); (3) reduce variance by resampling answers; (4) compare two models by inference on **question-level paired differences**; (5) power analysis. Formulas seen: `CI95 = mean +/- 1.96 x SE`; paired `SE_{A-B} = sqrt( (1/(n(n-1))) * sum_i (d_i - dbar)^2 )` with `d_i = s_{A,i} - s_{B,i}`. Paired analysis helps because tasks share difficulty; the unpaired variance is `(Var(sA)+Var(sB))/n`.

Mapping to skills: the "question" is a **task**; the K repeats of a task are resamples of the same cluster. The unit of analysis is the task, never the individual run. Averaging K runs per task into `s_i`, then taking `d_i = s_new,i - s_old,i`, is the correct paired design. Treating N x K runs as independent overstates n and understates the SE.

### 2.2 Recommended analysis (INFERRED from 2.1 plus standard practice)

- Per task and arm: mean over K runs of each metric. Delta per task `d_i`.
- Report mean delta, **paired bootstrap 95% CI over tasks** (resample tasks with replacement, recompute mean d; `scipy.stats.bootstrap(..., paired=True, method="BCa")`, default 9999 resamples, VERIFIED: https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.bootstrap.html). Also report the CLT paired SE as a cross-check. With N below about 15 tasks, bootstrap CIs are optimistic (INFERRED); show the per-task delta dot plot beside the CI.
- Decision rule fixed *before* running: "ship if the 95% CI for success delta excludes < -X and cost delta CI excludes > +Y", not "the mean went down".
- Binary success with few tasks: also show the discordant-pair table (tasks where new won vs old won). A sign test on discordant tasks is robust but weak (INFERRED).
- Use different statistics for different metrics: success (proportion, bounded), tokens/cost/duration (right-skewed; use log-ratio per task, `log(new/old)`, then bootstrap, INFERRED), turns (count).
- Multiple comparisons: with 8 metrics, one will look significant by chance. Pre-declare 1 primary metric (e.g. success rate, or cost per success) and treat the rest as secondary (INFERRED).

### 2.3 pass@k vs pass^k vs mean success

- pass@k: P(at least one of k succeeds); pass^k: P(all k succeed) (VERIFIED, Anthropic demystifying-evals above). pass^k came from tau-bench (VERIFIED abstract, https://arxiv.org/abs/2406.12045): the abstract reports that even strong function-calling agents "succeed on <50% of tasks" and are "quite inconsistent (pass^8 <25% in retail)". The abstract fetched did not give the formula; the standard unbiased estimator is `C(c,k)/C(n,k)` for pass^k where `c` successes in `n` trials (UNVERIFIED here, from tau-bench's definition as I recall it).
- For skills, **pass^k is the right headline for workflow skills** (a human wants it to work every time; a skill is a reliability tool). pass@k is right only if a human retries on failure. Always also report the plain mean success rate, because pass^k at k=5 on 5 runs has very high variance (it is one number per task, 0/1 at k=n).
- Inspect has built-in reducers `mean`, `median`, `mode`, `max`, `at_least_{n}`, `pass_at_{k}`, `pass_k_{k}` for epochs (VERIFIED, https://inspect.aisi.org.uk/options.html; definitions not shown on that page).

### 2.4 Cost-per-success

- Define `cost_per_success = sum(cost over all runs) / (number of successful runs)` per arm, and report it alongside success. A change that cuts tokens by 30% but halves success is a regression the raw token chart hides (INFERRED; AgencyBench-style `score / (attempts x tokens)` is cited in the repo's own audit skill, UNVERIFIED by me).
- Bootstrap this ratio at task level (ratio estimators are biased with small N; use the bootstrap, not the delta method).
- Include failed runs' cost. Excluding them rewards skills that fail fast and cheap.

### 2.5 Power (my simulation; code was run, not cited)

Setup: N tasks, K runs, task success probability `p_i ~ Beta(2,2)`, new arm adds `delta` (clipped to the 0-1 range); analysis = paired z-test on per-task mean differences at alpha=0.05. 2,000 sims per cell. Script: `/tmp/claude-1000/-home-tstapler-dotfiles/70365390-dd85-4ee2-bc86-16f37456c1fe/scratchpad/pw.py`.

| N tasks x K runs | delta 0.05 | 0.10 | 0.15 | 0.20 |
|---|---|---|---|---|
| 10 x 3 | 0.12 | 0.18 | 0.29 | 0.45 |
| 10 x 5 | 0.12 | 0.24 | 0.42 | 0.64 |
| 20 x 3 | 0.11 | 0.25 | 0.48 | 0.68 |
| 20 x 5 | 0.15 | 0.38 | 0.67 | 0.89 |
| 30 x 5 | 0.17 | 0.49 | 0.83 | 0.97 |

Reading it: more tasks beats more repeats (10x5 < 20x3 at equal run count). Detecting a 10-point success change at 80% power needs far more than 30 x 5. Therefore: use success as a **guardrail** (detect large regressions), and use cost/duration/turns (continuous, lower relative noise) as the **primary** efficiency metric. Caveat: my Beta(2,2) difficulty model is an assumption; real task difficulty will be bimodal (many 0% or 100% tasks), which lowers power further because saturated tasks contribute zero paired variance.
Anthropic's paper has its own power formula (section 5 of arXiv 2411.00640, formula seen but not re-derived here).

## 3. Existing frameworks, fit for a CLI-driven skills repo

| Framework | What I verified | Fit |
|---|---|---|
| **`claude plugin eval`** | Section 1.2 | Best first choice for with/without; native skill awareness, isolation, CI exit codes. Weak: custom stats, token buckets, version-A-vs-B |
| **skill-creator** | 1.4 | Good interactive loop and viewer; not CI-grade stats |
| **promptfoo** | (https://www.promptfoo.dev/docs/providers/claude-agent-sdk/, https://www.promptfoo.dev/docs/usage/command-line/) Provider `anthropic:claude-agent-sdk` / alias `anthropic:claude-code`; `working_dir` and `copy_working_dir` (fresh copy per step; those calls are never cached); `skills`/`setting_sources`/`plugins`; `skill-used` assertion; `metadata.toolCalls`; `trace-span-count` can cap turns; `max_budget_usd`; `--repeat <n>`, `--no-cache`, `-j`, output `json/junit.xml/html`; exit code 100 on any test failure | Good declarative harness with YAML, caching on by default (must disable for benchmarking), no paired/CI statistics. Reasonable if you want a diffable config; extra Node dependency |
| **Inspect AI** (UK AISI) | (https://inspect.aisi.org.uk/, /options.html, /agent-bridge.html) task = dataset + solver + scorer; `--epochs` with reducers incl. `pass_at_k`, `pass_k_k`; `--token-limit`, `--time-limit`, `--limit`; sandboxes (Docker, K8s, Modal, Proxmox, Vagrant); `inspect view` log viewer; runs external agents like Claude Code via `sandbox_agent_bridge` (a proxy that relays the agent's API calls to the eval's model provider) | Strongest eval *framework* (epochs, logs, scorer ecosystem). Overhead: Docker sandbox plus the bridge reroutes API calls, so cache/token accounting is Inspect's, not Claude Code's own; the agent-bridge page did not document a ready Claude Code agent. Overkill for v1 |
| **Terminal-Bench / Harbor** | (https://www.tbench.ai/docs) runs in Harbor; Claude Code selectable with `-a claude-code -m anthropic/<model>`; sandboxes via Modal etc.; task format/scoring not on the page I fetched (UNVERIFIED) | Pattern to copy: per-task container + test script as grader. Infra heavy |
| **SWE-bench / Verified** | (https://www.swebench.com/SWE-bench/guides/evaluation/) JSONL predictions (`instance_id`, `model_patch`), containerized Docker eval, "resolved" = required tests pass, cache by `run_id`+`instance_id`. Verified-subset specifics (500 samples, 93 annotators, 1,699 annotated, issues: underspecified statements, over-specific tests) come from a search snippet only, because openai.com returned 403: UNVERIFIED | Pattern to copy: frozen repo at base commit, hidden tests as grader, instance IDs. Cautionary lesson: benchmark validity depends on task/test quality, not just volume |
| **Braintrust** | (https://docs.braintrust.dev/evaluate/run-evaluations) experiments are "immutable snapshots", compare experiments, CI/CD run for regressions. Page lacked trial/baseline details (UNVERIFIED) | Hosted SaaS; unnecessary for a personal repo |
| **LangSmith** | (https://docs.langchain.com/langsmith/evaluation-concepts) datasets, experiments, pairwise evaluation, few-shot judge prompts, pytest/Vitest integration, dataset-version pinning for CI. Repetitions not covered on page | Same: SaaS, little benefit here |
| **OpenAI evals** | (https://github.com/openai/evals) registry in Git-LFS with YAML; "not accepting evals with custom code"; points users to the OpenAI Dashboard | Not relevant to Claude Code |
| **METR** | (https://metr.org/blog/2025-03-19-measuring-ai-ability-to-complete-long-tasks/) 95% CIs by hierarchical bootstrap over task families, tasks, attempts; page says it is partly outdated and does not state runs per task | Methodology reference: bootstrap at multiple levels, which is what 2.2 does with task as the cluster |

**Recommendation:** v1 = hand-rolled Python harness over `claude -p` (stdlib + `scipy`), plus `claude plugin eval` where the with/without question applies. Keep Inspect AI as the upgrade path if tasks move into containers.

## 4. Building a golden task set from your own sessions

Sources already on disk: `~/.claude/projects/<slug>/*.jsonl` transcripts (parsed by `.claude/skills/meta-skill-effectiveness-audit/scripts/skill_usage_report.py` and `stapler-scripts/session-compare`).

**What the existing tools give you (VERIFIED by reading SKILL.md files in this repo):**
- `meta-skill-effectiveness-audit`: walks transcripts in file order; a `Skill` call, `Agent`/`Task` call, or `<command-name>` tag opens a bucket; attributes `output_tokens + cache_creation_input_tokens` of subsequent assistant turns (deduped by message id) to it; explicitly excludes cache-read; flags large `unattributed`/`agent:unknown` buckets as untrustworthy. Its own docs admit "No published methodology exists yet for per-skill token-cost attribution".
- `session-compare`: two sessions, four token buckets, estimated cost, turns, files touched.
- Limitation for benchmarking: both are **observational** (uncontrolled task, repo state, and model). They find candidates; they cannot do A/B. Attribution by "open bucket" is heuristic when buckets interleave or subagents run in parallel (INFERRED).

**Recipe (INFERRED, design):**
1. *Select*: from the audit's `--json`, pick sessions where a target skill (e.g. `/sdd:quick`, `/sdd:fix-bug`) ran start to finish, ended in an accepted outcome (commit made, PR merged; check `git log` after the session timestamp), and the starting repo state is recoverable.
2. *Freeze*: record `repo`, `base_commit` (the commit at session start from the first `cwd`/`gitBranch` fields and `git log --before=<ts>`), and the verbatim first user prompt. Task = `(repo@commit, prompt)`. Store as `tasks/<id>/task.yaml`. Build the workspace per run with `git worktree add --detach <tmp> <commit>` (fresh per run; no shared state, as demanded by the Anthropic isolation guidance in 1.1).
3. *Define the verifier before running anything*: prefer executable checks (tests pass, file exists, `make ready` clean, the artifact has required sections). SWE-bench's pattern: hidden tests as the grader. For planning-type tasks (SDD phases 1-4), use structural checks (required files/sections present, cross-references resolve) plus a rubric judge.
4. *Strip leaked answers*: the transcript's eventual diff must not be reachable from the frozen commit (base commit predates it) and not in the skill text. Exclude tasks whose fix you later pasted into a skill as an example (contamination, section 6).
5. *Balance*: include should-trigger and should-NOT-trigger prompts (Anthropic: one-sided evals optimize one-sidedly), and a few easy tasks (guards against regressions) plus hard ones (headroom). Keep 3-5 tasks per distinct skill path.
6. *Split*: dev set (iterate on) vs held-out set (touch only at ship decisions), mirroring skill-creator's 60/40 split with selection by test score (VERIFIED, 1.4).
7. *Size*: start at 8-12 tasks; grow toward 20-30 as power demands (section 2.5). Quality over quantity: SWE-bench Verified exists because noisy tasks/tests made the original benchmark unreliable (UNVERIFIED primary).
8. *Public and private*: transcripts contain private data. Keep tasks and runs in a git-ignored dir or a private repo (matches the repo's "resume skills private fork" memory).

**Replay vs fresh-run:** do not replay the recorded assistant turns; replay only the *first prompt* against the frozen repo and let each arm run fresh. `plugin eval`'s `context.history_file` resumes a transcript with the case prompt as the next turn (VERIFIED), useful only to test a mid-session behavior; for a single-arm path target it defaults to one arm unless `--ablation with-without` (VERIFIED).

### 4.1 Graders and judge calibration

- Deterministic first (tests, regex over output files, tool_order such as "ran tests before claiming done"). `plugin eval` itself advises: grade long outputs with `regex` over file content and keep `llm` graders for short outputs with explicit PASS/FAIL conditions; if the skill fired but Δ is negative, suspect the judge before the plugin; re-run with `--judge-model sonnet` (VERIFIED, plugin-evals.md).
- LLM-as-judge risks: position, verbosity, self-enhancement bias; judges agree with humans over 80% of the time on MT-bench, about the human-human rate (VERIFIED abstract, https://arxiv.org/abs/2306.05685). Mitigations (INFERRED): judge in a fresh context that never saw the run's reasoning; randomize A/B order for pairwise; strip arm labels; pin the judge model and version separately from the agent model; give "Unknown" (Anthropic guidance).
- **Calibration set**: hand-label 20-30 outputs once (pass/fail with a one-line reason), run the judge 3x each, report agreement and flip rate. Do not trust the judge for gating until agreement >= your threshold (e.g. 85%) and flip rate is low (my thresholds, INFERRED). Re-calibrate when judge model or rubric changes.
- The repo's audit skill already says to use a fresh subagent for adherence reads rather than self-grading in the originating context (VERIFIED in-repo); same principle.
- `plugin eval`'s `llm` grader = 3 votes, passes at >= 2 (VERIFIED), i.e. a built-in noise reduction for judgments.

## 5. Metrics to capture, and gating

### 5.1 Per-run record (JSONL, one line per run)

| Group | Fields | Source (VERIFIED where stated) |
|---|---|---|
| Identity | task_id, arm, run_idx, skill_ref (git SHA of the skills dir), claude_version, model, judge_model, started_at, wall order index | harness |
| Tokens by bucket | input_tokens, cache_creation_input_tokens (split 5m/1h), cache_read_input_tokens, output_tokens, thinking_tokens | `usage`, `modelUsage` in result JSON (VERIFIED local run) |
| Cost | total_cost_usd (list-price estimate), plus own recomputation from buckets | result JSON; docs say client-side estimate |
| Time | duration_ms, duration_api_ms, ttft | result JSON |
| Turns / agents | num_turns, subagent count and per-subagent tokens | `num_turns`, `subagent_stats` (key exists, shape not inspected), `parent_tool_use_id` in stream-json |
| Outcome | success (verifier), terminal_reason / stop_reason, is_error, hit_max_turns, permission_denials | result JSON |
| Adherence | required-step checklist (e.g. SDD wrote `requirements.md` before research; `tool_order` test-before-claim) | transcript scan or `tool_order`-style assertions |
| Artifact quality | rubric score(s) from calibrated judge, deterministic structure checks | graders |

Report cache-read separately from "fresh" tokens: the audit skill already attributes only `output + cache_creation` (VERIFIED in-repo) because cache-read is reuse. For the primary efficiency metric use **cost** (it weights buckets the way the bill does) and show a fresh-token view next to it.

### 5.2 Manual vs CI

- **Manual (default):** run on demand when editing a skill: `bench run --skill sdd-quick --arms old,new`. Runs cost real money (the trivial "reply ok" call cost $0.0796 at list price in my test because of 19k cache-creation tokens, VERIFIED local run). A 10 tasks x 5 runs x 2 arms SDD suite is 100 sessions, each potentially dollars. Nightly CI on every PR is wasteful.
- **CI (later):** gate only on a cheap deterministic smoke subset (3-5 tasks, `runs: 3`), `--model` pinned, `--max-cost-usd` ceiling, nonzero exit on success-rate drop beyond a threshold; archive the JSON; exclude `partial: true` results from trends (plugin-evals.md guidance, VERIFIED). Running the full suite is a pre-ship manual step or a weekly scheduled job.
- Gate shape (INFERRED): block only when the paired CI for success delta lies entirely below -0.10, or the cost-per-success CI lies entirely above +25%; otherwise report and let a human decide. A strict point-estimate gate on a noisy benchmark produces flaky CI, which is its own failure mode.

## 6. Pitfalls

1. **Cache warmth skew (arms differ for non-skill reasons).** Prompt cache default TTL is 5 minutes (1-hour option); reads cost 0.1x base input (0.05x for Opus 5.5 and Sonnet 5.5); 5-min writes 1.25x, 1-hour writes 2x; hits require 100% identical prefix; tool-definition changes invalidate all levels; parallel requests cannot hit an entry before the first response starts (VERIFIED, https://platform.claude.com/docs/en/build-with-claude/prompt-caching). My local run showed 17,022 cache-read tokens plus 19,456 cache-creation tokens on a one-line prompt in a fresh session (VERIFIED), i.e. the shared system-prompt prefix is already warm from other recent sessions. Consequences (INFERRED): (a) the first run after a gap pays cache-creation, later runs get reads, so cost differs by position not by arm; (b) a skill edit changes the prefix only if the skill listing/description is in the cached prefix, otherwise the SKILL.md body is a cache-write in whichever turn it loads; (c) parallel arms contend for cache. Controls: interleave arms in randomized/ABBA order, discard or flag run 0 as warm-up, run both arms in the same time window, report `cache_read` share per arm, compare **cost computed from cold-equivalent pricing** as a sensitivity check (all non-output tokens at base input price) so cache luck cannot win the comparison.
2. **Order and time effects.** Anthropic saw pass rates "varying by time of day" anecdotally and advise running evals "at multiple times and on multiple days" (VERIFIED, https://www.anthropic.com/engineering/infrastructure-noise). Randomize run order; do not run all old-arm first.
3. **Infrastructure noise and resource limits.** Resource configuration alone moved Terminal-Bench 2.0 scores by up to 6 points (p<0.01); they suggest gaps under 3 points warrant skepticism (VERIFIED, same article). Fix CPU/RAM/timeouts identically across arms; treat `timeout`/`max_turns` hits as a separate "infra/limit" outcome, not as a skill failure silently. In `plugin eval`, hitting the turn cap is recorded as a run error and lowers the score (VERIFIED), so set `max_turns` generously.
4. **Model-version and serving drift.** Anthropic's own postmortem documents three Aug-Sep 2025 bugs (routing error affecting up to 16% of Sonnet 4 requests in the worst hour; TPU output corruption; XLA approximate top-k miscompilation), and says the issues looked like "random noise" and standard evals missed them (VERIFIED, https://www.anthropic.com/engineering/a-postmortem-of-three-recent-issues). Implications: pin `--model` to a full ID; record `claude_version` and model per run; run old and new arms **in the same window**; keep a never-changing control task or "canary" arm in every batch to detect drift; do not compare today's new-arm to last month's stored old-arm numbers unless the canary is flat. Also note `--fallback-model` can silently swap models (VERIFIED flag exists); do not set it in benchmark runs.
5. **Ambient configuration leakage.** Non-bare `-p` loads `~/.claude` hooks, skills, CLAUDE.md, memory and project `.mcp.json`, so the "no skill" arm may still have the skill via another path (VERIFIED, headless.md). Verify with `system/init` that the loaded skill/plugin set is exactly intended, and fail the run otherwise. Auto-memory writes across runs are shared state (disable via `--bare` or a temp HOME).
6. **Contamination / overfitting to the benchmark.** Tasks drawn from your own sessions may already be embedded in skill text or CLAUDE.md; the model may also have seen public repos. Keep a held-out set; do not tune the skill against the same tasks you gate on (skill-creator selects by test score for this reason, VERIFIED). Git history in the worktree can leak the answer (Anthropic example of a model reading git history from earlier trials, VERIFIED): use `--detach` at the base commit and strip refs/reflogs beyond it.
7. **Goodhart on token count.** If tokens/cost are the target, a skill can win by skipping verification, truncating research, or declining to run subagents. This is INFERRED but is exactly the failure mode the repo audit skill flags as "procedural compliance" (a cited paper claims gated review can drop reported success rates 27-78%; UNVERIFIED, arxiv.org/abs/2603.03116 cited in-repo, not opened by me). Always display tokens next to success and adherence; make success/adherence a hard guardrail and tokens the optimization target; never accept a token win with a success CI that includes meaningful regression.
8. **Judge noise masquerading as skill effect** (plugin-evals.md advice above). Calibrate and re-run the judge on a stored output set when the rubric changes.
9. **Non-independence.** Runs within a task share difficulty; use task as the cluster (2.1). Also runs sharing a cached prefix or rate-limit window are not fully independent (INFERRED).
10. **Cost blowups.** `--max-budget-usd` can be exceeded and counts subagent spend (VERIFIED); `plugin eval --max-cost-usd` only checks before each run starts. Set both a per-run and per-batch cap.
11. **Subscription vs API key.** `--bare` ignores OAuth, requires an API key (VERIFIED); `plugin eval`'s cost is a list-price estimate counted against plan usage or API bill (VERIFIED). Decide which billing path benchmarks use before building.
12. **Saturation.** If every task passes in both arms, the success metric is dead and only cost/duration discriminate (Anthropic: saturated evals still serve as regression tests).

## 7. Recommended harness design

### 7.1 Components

```
sdd-bench/                         (proposed location: stapler-scripts/skill-bench/, symlinked via .cfgcaddy.yml)
  tasks/<id>/task.yaml            repo, base_commit, prompt, allowed_tools, max_turns, timeout_s, verifier, tags, split(dev|heldout)
  tasks/<id>/verify.sh            deterministic grader; exit 0 = success; writes checks.json
  rubrics/<name>.md               LLM-judge rubrics (concrete PASS/FAIL conditions), calibration set in rubrics/<name>.calib.jsonl
  arms/<arm>.yaml                 skill_ref (git SHA or path snapshot), how loaded (--plugin-dir/--add-dir), flags
  bench                           CLI (Python, stdlib + scipy)
  runs/<batch_id>/runs.jsonl      one record per run (5.1 schema) + raw stream-json per run
  runs/<batch_id>/report.md       paired stats, per-task dot table
```

Runner per (task, arm, run), randomized ABBA order within a single time window:
1. `git worktree add --detach $TMP <base_commit>`; fresh `HOME=$(mktemp -d)` containing only a minimal config (settings with permissions, no memory) and the arm's skill snapshot (copy `.claude/skills/<skill>` from `skill_ref` via `git archive`).
2. `claude -p "<prompt>" --output-format stream-json --verbose --no-session-persistence --model <pinned full id> --max-turns N --max-budget-usd C --permission-mode acceptEdits --allowedTools ... --setting-sources project --strict-mcp-config --plugin-dir <arm skill plugin>` (use `--bare` + `ANTHROPIC_API_KEY` if you want zero ambient config and have an API key; otherwise temp HOME). Run under `timeout`.
3. Parse stream: assert `system/init` shows the expected skill/plugin and no `plugin_errors`; capture final `result` object (tokens, cost, turns, subagent_stats); count subagents via `parent_tool_use_id`.
4. Run `verify.sh` in the worktree; run rubric judge in a fresh `claude -p` (pinned judge model, no tools, sees only task + outputs, arms blinded).
5. Append the JSONL record; delete the worktree.

Analysis `bench report <batch>`: per task mean over K; paired deltas; paired BCa bootstrap CI over tasks for each metric; log-ratio for cost/tokens/duration; cost-per-success; pass^K and mean success; discordant-task table; cache-read share per arm; cold-equivalent cost sensitivity; canary arm drift check; verdict against pre-declared rule.

### 7.2 Commands (proposed)

```
bench task add --from-session <path.jsonl> --id sdd-quick-001   # extracts prompt, cwd, base commit; you write verify.sh
bench arm snapshot --skill sdd --ref HEAD~1 --name old           # frozen copy for the baseline arm
bench run   --tasks 'sdd-*' --arms old,new --runs 5 --concurrency 2 --max-cost-usd 40
bench report runs/<batch> [--metric cost --metric success] [--vs runs/<older_batch>]
bench calibrate-judge rubrics/plan-quality.md                    # agreement vs hand labels, flip rate
```
Also use `claude plugin eval . --runs 3 --ablation with-without --json out.json --model <id> --judge-model <id> --max-cost-usd N` for the cheap "does the skill beat nothing" smoke check on skills packaged as a plugin.

### 7.3 Metric hierarchy

- Guardrails (must not regress): success rate (and pass^K), adherence checklist, artifact rubric score.
- Primary optimization metric: cost per success (USD), with fresh-token view beside it.
- Diagnostics: tokens by bucket, wall-clock, turns, subagent count, cache-read share, max_turns/timeout hits.

### 7.4 Minimum viable first version (build order)

1. **v0 (smallest useful):** one `bench run` script that runs ONE task N times per arm via `claude -p --output-format json`, writes JSONL, and a 40-line report with per-metric mean and paired bootstrap CI. Arms are two git refs of the skills dir. Hand-written `verify.sh` for 3 tasks (one cheap tasks per skill path: a fix-bug, a quick, a planning phase). Randomized order, pinned model, `--max-cost-usd`. This already answers "did this SKILL.md edit change cost, duration, turns" credibly.
2. **v1:** add `--output-format stream-json` capture of subagent counts and `system/init` validation, ABBA scheduling, cold-equivalent cost sensitivity, and a canary task. Grow to 10 tasks, K=5. Add `bench task add --from-session` using the existing transcript parser.
3. **v2:** LLM-judge rubrics with calibration set; held-out split; pass^K reporting; `plugin eval` smoke wrapper; optional CI job on the small deterministic subset with exit code from CI-bound rule; archive JSON per run for trend charts excluding `partial` runs.
4. **Later (only if needed):** containerize tasks (Harbor/Inspect pattern) for stronger isolation; hosted dashboards (Braintrust/LangSmith) are not needed for one user.

### 7.5 Open questions I could not close

- Whether a skills-directory plugin (`name@skills-dir`) built from this repo's `.claude/skills/sdd/skills/` loads the cross-referenced agents/commands correctly under `plugin eval` isolation (docs say only the plugin under test loads). Needs a trial run.
- Whether `plugin eval` is currently enabled for this account (server-side gate documented; I did not run it, to avoid spend).
- Shape of `subagent_stats` in the result JSON (key present; contents not inspected).
- The exact pass^k estimator and Anthropic's power-analysis formula; read the primary text before implementing (tau-bench paper body; arXiv 2411.00640 section 5).
- Primary SWE-bench Verified numbers (openai.com returned 403 to my fetch).
