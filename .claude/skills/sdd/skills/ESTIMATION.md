# Estimating LLM-executed work

Shared reference for every SDD phase that sizes, budgets or schedules work (`1-ideate` appetite, `3-plan` task sizing and effort section, `4-validate` readiness, `pm:triad-review` engineering lens). Same role as `SETUP.md`: read it, don't restate it.

## The rule

**Never estimate agent-executed work in human time** — no hours, days, weeks, person-months, "~5 min per task". A worker agent finishes in minutes what a person schedules in days, so a human-time total is wrong by one to two orders of magnitude and drives bad decisions (a plan summing to "389 h, 13–19 weeks" was an afternoon of agent runs plus owner decisions).

Estimate in these three units instead:

| Unit | What it measures | Use for |
|---|---|---|
| **Cost** (cost class, in price-weighted units) | The real marginal cost: context reads, generation, review and repair loops, weighted by what each token type costs | Per-story cost, budgets, overrun thresholds |
| **Agent runs / waves** | Parallel fan-out and serial dependency depth | Critical path, "what can run concurrently" |
| **Wall-clock blockers** | Things that do not run at token speed (listed below) | The only place calendar time belongs |

## Price-weighted units — bare token counts mislead

Token types are not priced alike. Default weights, relative to one fresh input token (**INFERRED from public API price ratios — check current pricing before relying on a dollar figure**):

| Token type | Weight |
|---|---|
| Fresh (uncached) input | 1 |
| Cache write | 1.25 |
| Cache read | 0.1 |
| Output (generation: code, docs, review text) | 5 |

**Cost unit (CU) = fresh-input-equivalent tokens** = `in + 1.25·cache_write + 0.1·cache_read + 5·out`. Consequences:
- Re-reading the same plan or repo context across review/repair loops is mostly **cached input and cheap**; writing large documents or lots of code is **output and expensive**. A repair loop that re-reads a plan costs far less than its raw token count suggests; an agent that rewrites a 900-line plan costs more.
- Estimate each task's **output share** (code written, docs written, findings written) separately from its context-read share, and state the assumed mix. When no mix is known, assume output ≈ 10–15% of tokens for implementation runs and ≈ 5–10% for review runs (INFERRED).
- Harness reports (`subagent_tokens`) give one undifferentiated total, so measured calibration is in raw tokens only; convert with the assumed mix and say so.

## Cost classes (raw tokens per worker-agent run, at a typical mix)

Bands are **INFERRED**, not measured on implementers — calibrate against the first real implementation run of the project and update the plan. Classes size relative effort; convert to CU with the weights above when comparing against a budget.

| Class | Tokens | Shape of task |
|---|---|---|
| XS | < 30k | One function or config change, 1–2 files, pattern already in the repo |
| S | 30–80k | A component plus its tests, 2–3 files |
| M | 80–180k | A small feature across layers, 3–5 files, some exploration |
| L | 180–300k | Cross-cutting or unfamiliar area. **Split it**; if it can't be split, say why |

- A **task** is one worker-agent run in one focused context (max 3–5 files). It is a unit of context, not of time.
- A **story** = its tasks + a verification multiplier of **×1.5–2** (spec-compliance and code-quality review per story, `6-verify` layers, CI reruns).
- A **project** total adds the planning overhead below if planning is still ahead.

## Calibration data point (VERIFIED from task-notification `subagent_tokens`)

Planning for `cross-graph-merge-share-target` (Complexity 3, 18 epics / 33 stories / ~140 task headings, Oct 2026) used **~3.5M subagent tokens across 29 agent runs**; the coordinator thread used ~50k on top.

| Stage | Tokens | Share |
|---|---|---|
| Research (6 agents) + first plan draft | ~0.67M | ~19% |
| Everything after: reviews, validation, pre-mortem, consistency, 7 repair passes, 2 triad rounds | ~2.83M | ~81% |

Takeaways (shares are in RAW tokens — the harness gives no input/output/cache split, so the true cost share of the loops is lower than 81%: they mostly re-read the same plan as cached input, while research and drafting are output-heavy):
- **Review and repair loops dominate raw token volume, not the first draft.** Budget them; don't treat them as free, but don't treat them as 5× output either.
- A single repair agent ran 76k–256k tokens; planning/review agents 76k–157k. That is the only evidence for the class bands above.
- The triad's second round re-found mostly owner decisions and gate-boundary polish — cost with little new signal (see stop rules).

## Scope default: pursue the full project

**The owner is comfortable with large projects. Plan and build the full scope by default.** Do not ask whether to downscale, defer, cut, or re-baseline; do not add "cut lines", MVP-versus-full interrogations, or appetite questions to the interview or the plan. Downscale only when the owner explicitly asks to — then cut exactly what they name.

Size is therefore a *tracking* figure, not a scope gate:
- Record the estimate as a **band in cost units** so the owner can see the order of magnitude and so overrun is detectable.

| Size | Cost (CU, all agents incl. review/verify) | Typical shape |
|---|---|---|
| Small | ≤ 0.5M | One context window; `/sdd:quick` territory |
| Medium | 0.5–3M | One feature, a few stories |
| Large | 3–15M | Multi-epic, several systems |
| XL | > 15M | Migration or cross-cutting |

(Bands INFERRED.) If the estimate lands in a larger band than the request implied, **say so in one line and proceed**; do not turn it into a question. Splitting into ordered gates is for sequencing and risk (spikes first, riskiest stories early), not for shrinking scope.
- Every plan still carries an **overrun checkpoint**: if spend runs **> 25%** over the table value for the stories completed, pause and report the delta with the cause (a wrong estimate or a real surprise) — informational, not an invitation to cut.

## Wall-clock blockers — the only legitimate use of calendar time

List these separately from the token estimate, each with an owner:

- Owner decisions and product input (persona, priority, opportunity cost)
- Observation or soak windows (e.g. "log real usage for 2 weeks", a nightly build, a dogfood period)
- Real-device, real-platform or CI-queue runs the agent cannot speed up (Android device pass, app-store review, long CI)
- Merging or releasing a dependency branch that someone else controls
- Human review latency for anything that needs a person to sign off

A plan's *duration* is then: critical path of agent waves (minutes to hours) **plus** the longest chain of wall-clock blockers. Usually the blockers, not the code, set the calendar.

## What goes in a plan's Effort section

1. A table: **Story · tasks · cost class · est. raw tokens · assumed output share · est. CU · wall-clock blocker (if any)**.
2. The sum, the verification multiplier applied, and the resulting size band (informational, per "Scope default").
3. The critical path in **agent waves** (which stories can fan out in parallel, which serialize on a shared file or a spike).
4. The overrun checkpoint in CU.
5. A "Wall-clock blockers" list with owners.
6. A one-line note of the basis: "bands and weights INFERRED; recalibrate after the first implementer run".

Do **not** include a "cut line", "what to drop first" list, or an "appetite — owner confirmation needed" item.

## Prioritisation (RICE / ICE)

Score the Effort term by **size band of the whole scope** (1 = Small, 2 = Medium, 3 = Large, 4 = XL, in CU), not person-days. If a framework demands a number of days, convert via the wall-clock-blocker chain, not via tokens.

## Stop rules (control the 81%)

- Cap review/repair iterations per the `3-plan` calibration; **stop looping when the remaining findings are owner decisions or polish** — report them instead of spending another round.
- Don't re-run a full multi-reviewer round to confirm cosmetic fixes; scope re-reviews to the previously blocked items.
- Prefer one repair agent that fixes all open findings over several narrow ones (each re-reads the same plan).

## Anti-patterns

- Human-time units in any plan, ADR, requirement or triad report ("~5 min", "389 h", "13–19 weeks").
- Summing per-task estimates with no verification multiplier.
- Treating "fits N weeks" or "fits the budget" as a gate, or asking the owner whether to downscale; the owner pursues large projects unless they say otherwise.
- Quoting bare token counts as if they were cost; weight output and cache reads (see "Price-weighted units").
- Inventing precision: say INFERRED, state the band, and recalibrate.
