# Agent cost/quality techniques: evidence review for the SDD skill suite

Date: 2026-11-01. Scope: what primary sources and practitioners say about getting better results from coding agents for less money, and about speeding up multi-agent workflows.

Labels: **VERIFIED** = I opened the page and read the cited text. **UNVERIFIED** = seen only in a search-result summary or recalled; check before relying on it. **MARKETING** = vendor claim with no reproducible method. Claude Code docs cited are the current (Nov 2026) pages, so version-specific details (model names, multipliers) may change.

Local baseline (VERIFIED by grep of `/home/tstapler/dotfiles/.claude/skills/sdd/skills/*/SKILL.md`): 1,776 lines across 13 SKILL.md files; `6-verify` is 427 lines, `full` 187. The suite already has a complexity "calibration" step in phases 2-4 and already says "parallel Agent calls from the top-level thread, never `subagent_type: sdd`". `grep` finds **no `model:` frontmatter and no haiku/sonnet routing** anywhere in the suite. `effort: high` is set on phases 3, 4, 5.

---

## 1. When parallel/background subagents help vs. hurt

### What the evidence says

- **Anthropic's own multi-agent research system is the strongest pro-parallel result, but scoped to breadth-first research.** Opus 4 lead + Sonnet 4 subagents beat single-agent Opus 4 by 90.2% on Anthropic's *internal* research eval. Agents use ~4x the tokens of chat; multi-agent ~15x. Token usage alone explained 80% of BrowseComp variance. Parallel tool calling and parallel subagents cut research time "by up to 90%". VERIFIED: https://www.anthropic.com/engineering/multi-agent-research-system
  - Caveat (same page, VERIFIED): "most coding tasks involve fewer truly parallelizable tasks than research, and LLM agents are not yet great at coordinating and delegating to other agents in real time." They also say domains where all agents must share context or have many dependencies "are not a good fit".
  - Skeptic note: the 90.2% is an internal eval, no public benchmark, and "multi-agent works mainly because it spends enough tokens" is Anthropic's own framing. Parallelism buys speed and token budget, not a smarter model.
  - The same post says early failure modes were spawning 50 subagents for simple queries, duplicated work from vague delegation, and agents "distracting each other". Fixes were explicit effort-scaling rules in the prompt (1 agent / 3-10 calls for simple; 2-4 subagents for comparisons; 10+ for complex) and delegation briefs with objective, output format, tool guidance, task boundaries. VERIFIED.
  - Sync execution was a named bottleneck: the lead waits for each subagent batch; one slow subagent blocks everything. VERIFIED (same page).
- **Cognition, "Don't Build Multi-Agents" (June 2025)**: principles "share full traces, not just messages" and "actions carry implicit decisions; conflicting decisions carry bad results". Recommends single-threaded linear agents plus a context-compression step; says Claude Code's subagents were deliberately limited to answering questions, not writing code in parallel. VERIFIED: https://cognition.ai/blog/dont-build-multi-agents
  - Skeptic note: opinion piece, no measurements, written by a vendor selling a single-agent product, and dated (Claude Code now runs background subagents and worktree-isolated writers). Treat as a *failure-mode catalogue*, not a ruling.
- **Google Research / MIT, "Towards a Science of Scaling Agent Systems"** (180 configs, 5 architectures, 4 benchmarks, 3 model families): centralized multi-agent +80.9% on parallelizable Finance-Agent; **every multi-agent variant lost 39-70% on strictly sequential PlanCraft**; independent (no-orchestrator) agents amplified errors 17.2x vs 4.4x for centralized; coordination "tax" grows with tool count (16+ tools). Predictive model R^2=0.513, picks best architecture for 87% of unseen configs. VERIFIED (blog): https://research.google/blog/towards-a-science-of-scaling-agent-systems-when-and-why-agent-systems-work/ ; paper https://arxiv.org/abs/2512.08296 (abstract not independently opened, UNVERIFIED beyond the blog). Benchmarks are not coding benchmarks; transfer to SDD is by analogy.
- **MAST, "Why Do Multi-Agent LLM Systems Fail?"** (Berkeley): 14 failure modes in 3 groups (spec/design, inter-agent misalignment, verification/termination) over ~1.6k traces; claims failures are mostly system-design not model limits. UNVERIFIED (search summary only): https://arxiv.org/abs/2503.13657
- **Claude Code's own docs now say the same, bluntly.** "Handing the same task to a subagent doesn't make the answer any better. A fresh reviewer does help, because it hasn't seen your reasoning." Subagents cost tokens (each sends its own requests), can be *slower* (fresh context must re-gather what the conversation already had), and "by default it's the same model... You get parallelism or a fresh pair of eyes, but not a smarter answer." VERIFIED: https://code.claude.com/docs/en/best-practices (section "Know what subagents cost"). Costs doc: "The subagent's own requests still draw on your usage." VERIFIED: https://code.claude.com/docs/en/costs
- **Agentless** (UIUC): a fixed 3-phase pipeline (localize, repair, validate) with no agent autonomy hit 32.00% on SWE-bench Lite at $0.70/issue, topping open-source agents at the time (2024, old models). VERIFIED abstract: https://arxiv.org/abs/2407.01489. Lesson: structured deterministic phases can beat open-ended agent loops on cost; dated, so don't quote the number as current.

### Synthesis for SDD

| Situation | Parallel subagents? | Why |
|---|---|---|
| Research across independent dimensions (stack, pitfalls, build-vs-buy) | Yes | Breadth-first, read-only, no shared decisions. This is Anthropic's sweet spot. Phase 2 already does it. |
| Plan reviewers / pre-mortem / validation | Yes, read-only, independent perspectives | Fresh eyes is the documented benefit. Orchestrator (centralized) contains error amplification. |
| Implementation epics that share files or interfaces | Only with disjoint file ownership or worktree isolation, and an interface contract written first | Cognition's "implicit decisions" failure. Phase 5 already gates on "no shared file writes". |
| Strictly sequential reasoning (design a single coherent architecture, debug one failure) | No | -39 to -70% in the Google study (non-coding benchmark). |
| Verbose tool output (test runs, log scans, wide greps) | Yes, for context isolation, not speed | Documented use; return a summary only. |
| Trivial/clear task | No agents at all | Anthropic's effort-scaling rule; Claude Code best-practices say plan mode adds overhead for small scoped changes. |

Foreground vs background: Claude Code runs subagents in the background by default now (best-practices page, VERIFIED) and has a `background` frontmatter field, `maxTurns`, `isolation: worktree`, and `SendMessage` to resume a finished subagent with its history (VERIFIED: https://code.claude.com/docs/en/sub-agents). Speed gain comes from (a) a single message containing all independent Agent calls, (b) not blocking the main thread on results you do not need yet, (c) `maxTurns` caps so a stuck worker cannot stall a batch.

---

## 2. Context engineering

- **Smallest set of high-signal tokens**; context rot means more tokens degrade recall; "do the simplest thing that works". VERIFIED: https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
- **Just-in-time retrieval**: keep lightweight identifiers (paths, queries) and load on demand; Claude Code's hybrid (CLAUDE.md up front, glob/grep at runtime). Trade-off stated: slower than precomputed, needs good navigation heuristics. VERIFIED (same page).
- **Compaction** is the first lever; lightest form is *tool-result clearing*. Over-aggressive compaction loses subtle critical context. **Structured note-taking** (NOTES.md, TODO) for milestone-style work. **Sub-agents return 1-2k-token summaries.** VERIFIED (same page).
- **File-based handoff**: Anthropic's multi-agent post says have subagents write outputs to external storage and pass back lightweight references to avoid the "game of telephone" and token overhead of copying outputs through the lead. VERIFIED: multi-agent post, Appendix.
- **Progressive disclosure for skills** (3 levels: name+description always loaded; SKILL.md body on trigger; linked files on demand). Mutually exclusive contexts go in separate files to save tokens. Deterministic work should be a script, not tokens. VERIFIED: https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills
- **Claude Code skill mechanics that affect cost** (all VERIFIED at https://code.claude.com/docs/en/skills):
  - Rendered SKILL.md enters the conversation as one message and **stays in context on every later turn** ("every line is a recurring token cost"). It is not re-read; write standing instructions.
  - After compaction, only the first ~5,000 tokens of each invoked skill are re-attached, so **put critical rules at the top**.
  - `description` + `when_to_use` are truncated at 1,536 chars in the listing; `disable-model-invocation: true` removes the skill's description from context entirely (good for rarely-used phase skills you always call by slash command).
  - `context: fork` + `agent:` runs a skill as an isolated subagent that does not see conversation history; `` !`cmd` `` injects command output before the model sees the skill (preprocessing without tokens spent on exploration).
  - Per-skill `model:` and `effort:` apply for the rest of the turn.
- **Costs doc advice** (VERIFIED, https://code.claude.com/docs/en/costs): move workflow-specific instructions out of CLAUDE.md into skills; use hooks to pre-filter (e.g. grep errors from a 10k-line log); `/clear` between unrelated tasks; prefer CLI tools over MCP servers (MCP tool listings deferred by default now); lower effort for simple tasks.
- **Start a fresh session from a written spec**: Claude Code best-practices interview-then-`SPEC.md` pattern says start a fresh session to build from it "so the build begins with a clean context and a written definition of done". VERIFIED: best-practices page.
- **"After two failed corrections, /clear and re-prompt"** (best-practices, VERIFIED): a third correction adds to a context already holding two failed attempts.

---

## 3. Prompt caching mechanics and how skill/agent design breaks or keeps hits

### Pricing (VERIFIED, https://platform.claude.com/docs/en/build-with-claude/prompt-caching)
- Cache read: 0.1x base input generally; **0.05x for Opus 5.5 and Sonnet 5.5; 0.025x for Fable 5.1 and Mythos 5.1**. 1-hour TTL write costs 2x base input; 5-minute is the default. (The 1.25x 5-minute write multiplier is standard but I did not see it in the lines I read: UNVERIFIED.)
- Order is `tools` -> `system` -> `messages`; a change at one level invalidates it and everything after. Modifying tool definitions invalidates everything. Changing thinking params or `output_config.effort` invalidates message blocks (model-specific for tools/system).
- Lookback window is 20 blocks; put the breakpoint on the last block identical across requests; timestamps or per-request text before the breakpoint means a fresh write every time and no reads.
- Minimum cacheable prompt size applies (value varies by model; not captured here).

### Claude Code specifics (VERIFIED, https://code.claude.com/docs/en/prompt-caching)
- Layers: system prompt + tool defs, then project context (CLAUDE.md, memory), then conversation. Each model has its **own cache**: `/model` switch mid-session = full uncached re-read of history. Effort changes likewise on most models (not on Opus 5.5 / Sonnet 5.5 / Fable 5.1 per the doc's wording; re-check the exact sentence before depending on it).
- **Cache-safe**: invoking skills/commands (injected as user messages at the end), plugin skills/agents/hooks being loaded (appended, no invalidation), editing CLAUDE.md mid-session (not applied until `/clear`/`/compact`), permission-mode switches, `/rewind`.
- **Cache-breaking**: adding or removing MCP tool definitions that load upfront, denying a whole tool, model switch, effort change on some models, compaction (expected rebuild), new Claude Code version.
- A skill whose frontmatter names a different `model` is effectively a model switch for that turn: pays an uncached read of the whole conversation on that model, then again when it returns. VERIFIED (same page, "Invoking skills and commands").
- Cache lifetime: ~1 hour on a subscription, 5 minutes on API credits; first message after a longer gap re-reads everything. `experimental.cacheTtl: 5m|1h` is settable per subagent in frontmatter. VERIFIED: costs and sub-agents docs.
- Subagents have a separate context, so their first request has no warm conversation cache. They do share the identical system/tool prefix only if same model and config (I did not read the "Subagents and the cache" subsection in full: UNVERIFIED detail; read https://code.claude.com/docs/en/prompt-caching#subagents-and-the-cache before encoding a rule).

### Design implications for a skill suite
1. **Spawn N parallel workers from an identical, stable prompt prefix** (same agent type, same model, same shared preamble first, task-specific text last). Putting the varying task text first defeats prefix reuse across the parallel batch.
2. **Do not switch models mid-conversation in the main thread.** Route cheap work to *subagents* with `model: haiku`/`sonnet` (own cache anyway), not to main-thread `/model` toggles or per-skill `model:` in the lead thread.
3. **Warm-cache timing**: dispatch all parallel agents in one message; when a long wait (>5 min on API billing) is unavoidable, the next turn pays a full re-read, so batch work to finish within the TTL or set 1h TTL.
4. Keep timestamps, run IDs, and git status out of the stable prefix of shared agent prompts.
5. Compaction is a full-price request over the whole context; prefer ending a phase and starting a fresh session from file artifacts over compacting a huge one (the SDD "fresh session before implementation" design is directionally right).

---

## 4. Model routing and effort

- **Official guidance** (VERIFIED, best-practices + costs + sub-agents pages): default model handles most coding; Sonnet "costs less on routine work"; reserve Opus for architecture / multi-step reasoning; **Haiku for simple subagent jobs** (collect importing files, check doc links). Model resolution order for subagents: per-invocation `model` param > definition frontmatter > `CLAUDE_CODE_SUBAGENT_MODEL` > main model. Explore now inherits the main model (capped at Opus) rather than always Haiku (as of v2.1.198). Subagent `effort` frontmatter overrides session effort. VERIFIED: https://code.claude.com/docs/en/sub-agents
- **Workflows**: each workflow agent's model follows the same order; docs recommend asking for a smaller model on stages that do not need the strongest. VERIFIED: https://code.claude.com/docs/en/workflows#cost
- **Advisor tool**: a cheaper executor can consult a stronger model at key moments (before approach, when stuck, before declaring done). Only the intro was read: partial VERIFIED, https://code.claude.com/docs/en/advisor. Promising for "cheap worker, strong checkpoint" but I have no cost data.
- **Anthropic data point on model vs. tokens**: upgrading Sonnet 3.7 to Sonnet 4 gave a bigger gain than doubling the token budget. VERIFIED (multi-agent post). I.e. a better model can be cheaper than more samples.
- **Pricing gap** (VERIFIED, API pricing table in caching doc): Sonnet 4.5 $3/$15 per MTok, Haiku 4.5 $1/$5; the newest-generation prices were not captured. Output tokens (including thinking) cost several times input, so effort level matters: thinking is billed as output (costs doc, VERIFIED) and cannot be disabled on Opus 5.5/Sonnet 5.5/Fable.
- **Academic routing evidence**: FrugalGPT claims up to 98% cost savings at matched quality; RouteLLM reports ~2x-3.7x savings at ~95% of GPT-4 quality depending on benchmark; an agent-workflow adaptation reportedly got only 31-44%. All UNVERIFIED (search summaries): https://arxiv.org/abs/2305.05176 , https://arxiv.org/abs/2406.18665 . Takeaway: headline numbers are single-turn chat benchmarks on old model pairs; expect far less in agent loops.
- **Evidence gap**: I found no public, controlled measurement of Haiku-vs-Sonnet-vs-Opus per SDLC phase for coding agents. Any routing table for SDD is a hypothesis to be measured (that is what the parent benchmarking project is for).

Reasonable hypotheses to test (not facts): Haiku for file-gathering, link/lint checks, summarizing test output, status; Sonnet for research dimensions, implementation workers on well-specified tasks, idiom reviews; Opus (or high effort) for plan synthesis, adversarial review, architecture review, and root-cause debugging.

---

## 5. Spec-driven development and plan-then-execute

- **Anthropic**: Claude Code best practices recommend explore -> plan -> code -> commit, with plan mode, and explicitly say planning adds overhead so small, clearly scoped changes should skip it; and "give Claude a way to verify its work". Interview -> `SPEC.md` -> fresh session. VERIFIED: https://code.claude.com/docs/en/best-practices (the "skip planning for small changes" claim is from a search summary of this page: UNVERIFIED wording, VERIFIED page exists).
- **Birgitta Bockeler on martinfowler.com** (the best independent evaluation of Kiro, spec-kit, Tessl): Kiro turned a small bug into 4 user stories with 16 acceptance criteria, "a sledgehammer to crack a nut"; spec-kit produced "a LOT of markdown files" that were repetitive and "tedious to review... I'd rather review code"; the agent often **did not follow the spec anyway** ("false sense of control"), e.g. regenerated existing classes; skeptical that heavy up-front design beats small iterative steps. VERIFIED: https://martinfowler.com/articles/exploring-gen-ai/sdd-3-tools.html . She also notes it is hard to evaluate fairly and she tried only a few cases, so this is qualitative evidence from one reviewer.
- **GitHub spec-kit** announcement claims (MARKETING / not opened): https://github.blog/ai-and-ml/generative-ai/spec-driven-development-with-ai-get-started-with-a-new-open-source-toolkit/ . I found no controlled study showing SDD improves defect rates or reduces cost. Absence of evidence, not evidence of absence.
- **METR RCT** (early-2025 tools, 16 experienced devs, 246 issues in their own mature repos): AI use made them ~19% *slower* while they believed ~20% faster. UNVERIFIED (search summary): https://metr.org/blog/2025-07-10-early-2025-ai-experienced-os-dev-study/ . Old tools and tiny sample; relevant mainly as a warning that perceived speedup is unreliable and that you need to measure.
- **Agentless** (above) shows rigid, cheap, structured phases can match or beat open-ended agents on well-scoped issue repair.
- **Net reading**: heavyweight planning pays off when (a) the task is large, ambiguous, or has many interacting decisions, (b) the spec doubles as a verifiable definition of done (tests/acceptance criteria), and (c) a fresh session or parallel workers consume it. It is a net cost for small, clear tasks. The existing SDD "calibration" (complexity 1-4) is the right mechanism; the risk is that complexity-1/2 tasks still pay for ideate+research+plan artifacts. `sdd:quick` and `sdd:fix-bug` exist for that, so the real lever is making the *router* (which entry point to pick) cheap and explicit, and making artifacts terse and non-redundant.

---

## 6. Verification and review loops: cost vs. defect-catch

- **Verification beats self-review.** "Give Claude a way to verify its work" (tests, build, screenshots) is Anthropic's top recommendation. VERIFIED page: https://code.claude.com/docs/en/best-practices
- **Fresh-context reviewer helps; same-context self-review mostly doesn't.** Claude Code `/code-review` runs the diff in a fresh subagent that never saw the conversation, "not swayed by the reasoning that produced the code". VERIFIED: best-practices page. This matches the intrinsic self-correction literature: LLMs struggle to self-correct reasoning without external feedback and can get worse (Huang et al., "Large Language Models Cannot Self-Correct Reasoning Yet"), UNVERIFIED beyond abstract summary: https://arxiv.org/abs/2310.01798 . External signals (tests, linters, type checkers, a different model or prompt) are what make loops pay.
- **Orchestrated review limits error propagation**: centralized 4.4x vs independent 17.2x error amplification in the Google study (VERIFIED blog). So multiple reviewers should report to one synthesizer; do not chain reviewers that each see only the previous reviewer's output.
- **Anthropic eval guidance**: single LLM-judge call with a rubric was more consistent than multi-judge; start with ~20 test cases; humans still catch what automation misses. VERIFIED: multi-agent post.
- **Dynamic workflows** (`/deep-research`, codebase audit) vote/cross-check findings and filter claims that fail; docs warn runs can use "meaningfully more tokens" and advise running on a small slice first. VERIFIED: https://code.claude.com/docs/en/workflows
- **Evidence gap**: I found **no public measurement of tokens spent per real defect caught** for AI review layers, nor any dataset that says whether 3 parallel review agents catch more than 1 good one. The honest conclusion: a deterministic gate (tests/lint/types/build, plus hooks) is the cheapest high-value verifier; LLM review layers should be scaled by calibration and measured empirically. 6-verify at 427 lines with 2 parallel layers + refactor pass + skill-candidate analysis is the single largest cost line in the suite and has no cited evidence for its marginal value.

---

## 7. Copy-able instruction patterns for SKILL.md files

Each pattern notes its source or the reason it should work. Test, don't assume.

**A. Effort-scaling rule at the top of every fan-out skill** (source: Anthropic multi-agent post, VERIFIED)
```
Scale agents to the task. Complexity 1: do it inline, 0 subagents. Complexity 2: at most 2 agents,
Complexity 3: at most 4, Complexity 4: at most 6. Never exceed the cap; merge dimensions instead.
```

**B. Delegation brief template** (Anthropic: objective, output format, tools/sources, boundaries; VERIFIED)
```
Each Agent prompt MUST contain: (1) objective in one sentence, (2) exact output file path and
section headings, (3) files/dirs the agent may read or write, (4) what is OUT of scope,
(5) a stop condition ("stop after N findings or 15 tool calls"). Put the shared preamble first and
the task-specific lines last.
```

**C. File handoff, 3-line return** (Anthropic Appendix, VERIFIED)
```
Write full output to <path>. Return ONLY: path, a <=3-line summary, and any blocking question.
Do not paste file contents into your reply.
```

**D. One message, all independent calls** (already used; add the negative rule)
```
Send every independent Agent call in ONE message. Do not wait on read-only agents whose output
the next step does not need; set background and continue. Never launch an Agent whose input is
another running Agent's output.
```

**E. Cache-friendly parallel prompts** (caching docs, VERIFIED mechanics)
```
All workers in a batch share an identical first block (project context, constraints, output
rules). Put per-worker variables (epic id, file list) after it. Never put timestamps or
run IDs in the shared block. Do not change model or effort mid-session in the lead thread.
```

**F. Model routing in agent definitions, not in the lead thread** (sub-agents doc, VERIFIED)
```yaml
# .claude/agents/sdd-gatherer.md
model: haiku
tools: Read, Grep, Glob
maxTurns: 12
effort: low
```
Reserve `model: opus`/`effort: high` for plan synthesis, adversarial review, root-cause work. Keep the lead on one model per phase.

**G. Keep SKILL.md small and front-load the rules** (skills doc, VERIFIED: 5,000-token post-compaction re-attach; body persists every turn)
```
Target: SKILL.md <= ~150 lines; critical gates and "never" rules in the first 40 lines.
Move rubrics, templates, and long checklists to sibling files and reference them:
"When X applies, read ./reference/x.md" (progressive disclosure).
```

**H. Preprocess with `` !`cmd` `` or a script instead of letting the model explore** (skills doc and Skills eng blog, VERIFIED)
```
Current diff stat: !`git diff --stat origin/main...HEAD`
Surface map: !`./scripts/surface-map.sh`   # deterministic, zero model tokens
```

**I. Phase-skill hygiene** (skills doc, VERIFIED)
```yaml
disable-model-invocation: true   # slash-only; keeps description out of the skill listing
```
Use for `1-ideate` ... `7-ship` since they are always invoked by command.

**J. Complexity gate before any artifact** (Fowler/Bockeler critique + Anthropic plan-skip, VERIFIED/partly)
```
Before writing any phase artifact, classify: C1 (clear, <=3 files) -> stop and use /sdd:quick.
Artifacts for C1-C2 are one page; do not restate content already in code or in an earlier artifact.
Reference earlier artifacts by path, do not re-summarize them.
```

**K. Deterministic gate before LLM review** (best-practices "verify", VERIFIED)
```
Run tests/lint/typecheck/build first. If any fail, fix and re-run BEFORE dispatching any review
agent. Reviewers receive the diff and the gate output, never the implementation transcript.
```

**L. Cap the loop** (best-practices "/clear after two failed corrections", VERIFIED)
```
Max 2 fix iterations per gap. On the third failure, stop, write the failure to notes, and hand back
for a fresh-context retry with the lessons folded into the prompt.
```

**M. Reviewer with read-only tools** (best-practices, VERIFIED)
```yaml
tools: Read, Grep, Glob   # enforced by Claude Code, not by prompt
```

**N. Worktree isolation for parallel writers** (sub-agents doc, VERIFIED)
```yaml
isolation: worktree
```
Only for epics whose file sets overlap or are unknown; disjoint file sets can share the tree.

---

## Candidate changes to SDD skills (ranked by expected impact)

Impact = expected reduction in spend and/or wall-clock, or quality gain, per run. All are hypotheses for the benchmarking project to confirm; none has a measured SDD-specific number.

1. **Add model/effort routing via custom agent definitions (impact: high on cost; evidence: official guidance, no phase-level measurement).** Create `.claude/agents/` definitions (e.g. `sdd-gatherer` haiku/low, `sdd-researcher` sonnet/medium, `sdd-reviewer` opus-or-sonnet read-only, `sdd-worker` sonnet) and reference them from phases 2, 4, 5, 6. Today nothing sets `model:` so every subagent inherits the lead's (likely Opus) model. Sources: sub-agents and costs docs. Keep the lead on one model to protect the cache.
2. **Make complexity routing the first gate of `full` and enforce caps (impact: high; evidence: Anthropic effort-scaling, Bockeler sledgehammer, Google sequential penalty).** C1/C2 -> redirect to `quick`/`fix-bug` with zero artifacts; per-complexity agent-count caps (pattern A) in phases 2, 3, 4, 6. Only parallelize research and reviewers; keep plan synthesis single-threaded.
3. **Shrink `6-verify` (427 lines) and run the deterministic gate first (impact: high; largest skill, no evidence for marginal review-layer value).** Split into SKILL.md (~120 lines: gates and dispatch rules) plus `reference/` files for per-language rubrics and refactor/skill-candidate analyses, loaded only when the surface map calls for them. Run tests/lint/build before any LLM reviewer (pattern K). Gate the refactor-candidate and skill-candidate steps behind complexity 3-4.
4. **File-handoff contract with 3-line returns and delegation-brief template across all fan-out phases (impact: medium-high; evidence: Anthropic Appendix and delegation lessons).** Patterns B and C in phases 2-6; reduces lead-context growth and the "telephone game". Add `maxTurns` and stop conditions so a stuck worker cannot block a batch.
5. **Cache-aware prompt layout for parallel batches (impact: medium; evidence: caching docs).** Shared preamble block first, per-worker variables last (pattern E); no timestamps in the shared block; avoid mid-session `/model` or per-skill `model:` overrides in the lead thread; finish phase batches within the cache TTL or end the session and start fresh from artifacts. Verify via the `Prompt cache` line in `/usage` / `/cost` before and after.
6. **Shrink every phase SKILL.md and front-load rules (impact: medium; evidence: skills doc, recurring per-turn cost and 5k-token post-compaction cap).** Target about 150 lines and critical gates in the first 40 lines; add `disable-model-invocation: true` to phase skills invoked by slash command; move templates to sibling files.
7. **Replace model-driven exploration with preprocessing (impact: medium; evidence: costs doc and Skills blog).** `` !`...` `` injection or scripts for diff stats, surface map, hotspot ranking, project detection, `status` (the 48-line `status` skill is a natural script).
8. **Bound fix loops and use fresh-context retries (impact: medium; evidence: best-practices two-correction rule).** Max 2 iterations per gap in 5-implement and 6-verify; third failure goes to notes and a fresh agent.
9. **Isolation and ownership rules for parallel writers in `5-implement` (impact: quality/rework, medium; evidence: Cognition + Google error amplification).** Require an interface/contract file written *before* dispatch; assign each epic an owned file set; use `isolation: worktree` when sets overlap. Keep a single integrator (centralized, not independent).
10. **Optional: advisor-style checkpoint instead of an always-on Opus reviewer (impact: unknown; evidence: only the advisor docs intro).** Evaluate cheap worker + strong checkpoint at "before approach" and "before done". Test before adopting.
11. **Instrument before and after (prerequisite for all of the above).** Record per-phase tokens by agent type, cache hit share, wall-clock, and pass/fail on a small fixed task set (~20 tasks per Anthropic's guidance). Use the Claude Code usage attribution (skills/subagents share) and `Prompt cache` stats. Without this, ranks 1-10 stay conjecture.

### Open questions / gaps (not resolved by sources found)
- No public per-phase model-routing measurements for coding agents; no tokens-per-defect data for AI review layers; no controlled SDD-vs-no-SDD study.
- The "Subagents and the cache" subsection of the Claude Code caching doc was not read in full; confirm how subagent prefixes interact before encoding rule E.
- Several secondary claims (METR, RouteLLM/FrugalGPT, MAST, Huang self-correction) are UNVERIFIED search-summary level; open the arXiv/METR pages before quoting them.
- Newest-generation model prices were not captured; recompute cost ratios from https://platform.claude.com/docs/en/about-claude/pricing before building a cost model.
