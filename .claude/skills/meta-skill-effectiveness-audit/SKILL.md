---
name: meta-skill-effectiveness-audit
description: >-
  Measure real skill/subagent/command usage and token cost from Claude Code
  session transcripts, score the highest-impact ones across evaluation
  dimensions (task success, token efficiency, instruction adherence, latency,
  drift), and hand the worst offenders to `meta-persona-hardening` as
  concrete, data-backed incidents instead of vague "improve this skill"
  guesses. Use when auditing a skills library for cost/quality, deciding
  which skill to harden next, or asked "which skills are we actually using
  and are they worth it."
when_to_use: "Periodic skills-library audit; deciding which skill/agent/command to harden next; investigating why a session burned an unusual number of tokens; before a meta-persona-hardening pass when there's no single named incident yet but usage data could surface one"
---

# Skill Effectiveness Audit

`meta-persona-hardening` fixes one named incident at a time — it explicitly
refuses to run against a hypothetical. This skill is what supplies that
incident when none is already in hand: it turns transcript history into a
ranked, falsifiable list of "this skill is used a lot and burns tokens
disproportionately, here's the specific run where it happened," then
hands the top of that list to `meta-persona-hardening`'s Step 1.

This skill does not itself rewrite personas or skills — it produces the
prioritized, evidenced target list that Step 5 below feeds into that process.

## Step 1 — Inventory Real Usage and Attributed Token Cost

Claude Code session transcripts (`~/.claude/projects/<project-slug>/*.jsonl`)
already contain every skill/subagent/slash-command invocation and every
turn's token usage. Nothing needs to be instrumented — it needs to be
parsed. Use
`~/dotfiles/.claude/skills/meta-skill-effectiveness-audit/scripts/skill_usage_report.py`:

```bash
SCRIPT=~/dotfiles/.claude/skills/meta-skill-effectiveness-audit/scripts/skill_usage_report.py

# Across every project this machine has ever run Claude Code in:
python3 "$SCRIPT" --min-count 3

# Scoped to one project (slug is the dirname under ~/.claude/projects,
# note the leading dash needs = syntax, not a space):
python3 "$SCRIPT" --project=-Users-tstapler-dotfiles

# Machine-readable, for feeding into Step 4's scoring:
python3 "$SCRIPT" --json > /tmp/skill-usage.json
```

**How attribution works** (so you can sanity-check the numbers, not just
trust them): the script walks each transcript in file order. An explicit
`Skill` tool call, an `Agent`/`Task` subagent call, or a `<command-name>`
tag in a user message starts a new attribution bucket (`skill:<name>`,
`agent:<subagent_type>`, `/<command>`). Every assistant turn after that,
deduped by message id, has `output_tokens + cache_creation_input_tokens`
added to the currently open bucket — generation cost plus newly-loaded
context (e.g. the SKILL.md body itself), not cache-read reuse. A run with
no invocation yet falls into `unattributed`; large `unattributed` or
`agent:unknown` buckets usually mean a subagent type wasn't recorded and
are worth a spot Read of the raw JSONL rather than trusted blindly.

This produces two rankings that matter for different reasons:
- **By count** — what gets invoked constantly (candidate for Step 5 because
  any fix compounds across many future runs)
- **By total_tokens** — what's actually expensive in aggregate (candidate
  even at low count, if `avg_tokens` is high — one skill run costing 800K
  tokens is worth investigating even if it only fired 3 times)

Neither ranking alone is the priority signal — Step 4 combines them with
the dimension scores from Step 3.

## Step 2 — Sanity-Check the Top Candidates Against Raw Transcripts

A high token count is a symptom, not a diagnosis. Before scoring anything,
open one or two of the actual runs behind the top 3-5 buckets from Step 1
and read what happened — Grep the transcript for the `Skill`/`Agent`
tool_use block that started the bucket, then read the turns that followed.

```bash
grep -n '"name":"Skill"' ~/.claude/projects/<slug>/<session>.jsonl
grep -n '"name":"Agent"' ~/.claude/projects/<slug>/<session>.jsonl
```

Distinguish: tokens spent because the task itself was genuinely large
(e.g. a thorough multi-file `Explore`) from tokens spent because the skill
re-reads files it already read, spawns redundant sub-agents, or emits a
verbose response nobody asked for. Only the second category is a hardening
target — the first is the skill doing its job. This is the same
"mine a concrete, real failure" discipline `meta-persona-hardening` Step 1
requires; this step is where that evidence actually gets read, not just
counted.

## Step 3 — Score Candidates Across Evaluation Dimensions

Raw token cost alone can't tell you whether a skill is *bad* — an
expensive skill that reliably succeeds may be worth every token; a cheap
one that silently produces the wrong answer is worse than expensive.
Score each Step-1/2 candidate on the dimensions practitioners actually use
for agent/prompt evaluation (researched, not invented — see citations):

| Dimension | What to check | How to check it here |
|-----------|---------------|----------------------|
| Task success rate | Did the invocation's stated goal actually get met, not just complete without error | Read the transcript's final turns / PR outcome for that run |
| Token efficiency | `avg_tokens` relative to task size — a ratio, not a raw number (score ÷ tokens, per AgencyBench's framing) | Compare `avg_tokens` across similar-scope runs of the same skill; a 3x outlier run is the one to read |
| Instruction adherence | Did the agent actually follow the skill's prescribed steps, independent of whether the outcome was fine anyway | Grep the transcript for whether each of the skill's numbered steps has a corresponding tool call/turn |
| Latency / turns-to-completion | Number of turns or tool calls before completion — tracked but rarely gated on | Count assistant turns in the bucket (the script's per-bucket turn count, or `wc -l` on the invoke-to-invoke slice) |
| Procedural compliance | Whether a reported "success" conceals a policy/step skip (a documented failure mode: gated review can drop reported success rates 27-78%) | Same transcript read as adherence, but looking specifically for skipped verification/review steps |

Sources: task success rate and the token-efficiency-as-ratio framing come
from AgentBench (arxiv.org/abs/2308.03688) and AgencyBench
(arxiv.org/abs/2601.11044, `score ÷ (attempts × tokens)`); the
adherence-vs-outcome split and LLM-judge calibration practice are LangSmith's
own evaluation methodology (docs.langchain.com/langsmith/evaluation,
langchain.com/blog/how-to-evaluate-voice-agents-execution-outcomes-and-experience);
procedural-compliance gating is arxiv.org/abs/2603.03116 ("Beyond Task
Completion"). No published methodology exists yet for per-skill token-cost
attribution or cross-model-version drift specifically for Claude Code
skills — Steps 1-2 above and the tracking loop in Step 6 are this skill's
answer to that gap, not a citation of an existing standard.

Anthropic's own stated approach (anthropic.com/engineering/claude-code-best-practices,
anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)
is empirical rather than benchmark-driven: run the skill on representative
real tasks, observe where it actually fails, patch incrementally, and grade
with a fresh-context reviewer rather than letting the same context
self-assess (self-review is lenient — it already rationalized its own
choices). Prefer a second agent invocation with no shared context for
Step 3's read-throughs over judging your own transcript summary.

## Step 4 — Rank and Prioritize

Combine Step 1's usage/cost numbers with Step 3's dimension scores into one
ranked list. A skill belongs near the top only if multiple signals agree —
this mirrors `meta-persona-hardening`'s existing caution against gates that
sound plausible but weren't actually built from a real failure:

- **High count AND low adherence/success** → top priority: cheap to fix,
  fires constantly, and is measurably not doing what it claims.
- **High total_tokens AND a genuine token-efficiency outlier** (not just
  "the task was big") → top priority: a concrete, bounded fix (dedupe a
  re-read, cut a redundant sub-agent spawn) pays for itself immediately.
- **High count but scores fine on every dimension** → not a target. Being
  used a lot is not itself a problem; don't manufacture a gate for it.
- **Low count, low cost, one bad run** → usually not worth a persona-level
  hardening pass; note it and move on unless the failure mode is severe
  (data loss, security) regardless of frequency.

## Step 5 — Hand Off to meta-persona-hardening

For each top-ranked candidate, write the one-or-two-sentence incident
statement `meta-persona-hardening` Step 1 asks for, using what Step 2's
transcript read actually showed — not a restatement of the token number:

> "`<skill-name>`, invoked N times across M sessions, re-reads the same
> file on 4 of 5 runs before writing (transcript:
> `~/.claude/projects/<slug>/<session>.jsonl` around the `Skill` tool_use
> at line L) — averaging <X> tokens/invocation against a <Y>-token peer
> doing the same task."

Then run `meta-persona-hardening` against that skill's own SKILL.md (or the
persona file that invokes it) starting from its Step 2, using this incident
as the anchor. This skill's job stops at handing over that anchor — don't
duplicate `meta-persona-hardening`'s judgment-gate/reference-audit steps
here.

## Step 6 — Close the Loop

After a hardening pass ships, re-run Step 1 scoped to sessions after the
change (`--project=<slug>` plus a manual filter on file mtime, since the
script has no built-in date filter) and compare `avg_tokens`/count against
the pre-change baseline captured in Step 1's first run. If the number
didn't move, the hardening didn't address the actual cost driver — go back
to Step 2 and re-read a fresh transcript rather than assuming the fix
worked because the diff looked right.

## Anti-Patterns

- **Ranking by token count alone.** A skill that reads five files to do a
  thorough job is not a problem; the ranking exists to find *disproportionate*
  cost, which requires Step 2's read, not just Step 1's number.
- **Treating high usage as inherently bad.** The opposite is often true — a
  skill used constantly and scoring well everywhere is a success story, not
  a queue entry.
- **Skipping Step 2 and handing raw numbers to `meta-persona-hardening`.**
  That skill explicitly wants a *concrete* incident; "used 200 times, cost
  31M tokens" is a statistic, not an incident, until a specific run has been
  read and quoted.
- **Self-grading Step 3's adherence check from the same context that ran
  the skill.** Use a fresh subagent invocation for the transcript read —
  the originating context already rationalized whatever it did.
- **Trusting the script's numbers where `agent:unknown` or `unattributed`
  dominate.** That means the invocation type wasn't captured cleanly; spot-
  check the raw JSONL before drawing conclusions from that bucket.

## Related Skills

| Skill | When to apply |
|-------|--------------|
| `meta-persona-hardening` | Where a top-ranked candidate from Step 4 actually gets fixed — this skill only supplies the incident (Step 5) |
| `meta-claude-technique-evaluator` | Evaluating a *new* skill/technique for adoption, not auditing existing usage — different direction of analysis |
| `code-hotspot-analysis` | The same "usage/churn signal, not a full audit" idea applied to source files instead of skills |
| `ponytail` | If Step 2's read shows a skill's own output is bloated/over-engineered rather than the invocation pattern being wasteful |
