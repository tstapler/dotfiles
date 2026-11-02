# pm:triad-review cost analysis (2026-11-01)

Sources: `.claude/skills/pm/skills/triad-review/SKILL.md` (111 lines), `.claude/skills/sdd/skills/4-validate/SKILL.md` step 6,
`.claude/agents/{ux-expert,project-coordinator}.md`, 45 session transcripts with `attributionSkill:"pm:triad-review"`
(helper `phase_cost_report.py` plus per-agent scripts in the session scratchpad). Costs use the helper's fitted $/token rates, so treat them as
predictive (+/-25%). Six oldest sessions (claude-sonnet-5, 09-08..10-15) have no rate fit and price at $0; they count in rounds, not dollars.
Labels: VERIFIED = computed from transcripts or agent descriptions; INFERRED = my reading.

## How the skill runs (VERIFIED)
- Per round: 3 lens agents in one message (Product = `general-purpose`, UX = `ux-expert`, Eng = `project-coordinator`). Each writes
  `/tmp/triad-<lens>-<feature>.txt` and returns JSON `{status,gaps,blockers}` through SubagentHandback. All Sonnet; no Haiku/Opus.
- Between rounds the coordinator spawns ONE serial "repair" agent (not in SKILL.md; comes from 4-validate step 6 or ad hoc) that reads the three /tmp files and edits plan.md, ux.md, requirements.md, validation.md.
- Later rounds re-run only the non-green legs (R3/R4 often hold just UX or just Eng). Fresh agents each round, by design.
- 4-validate caps repairs at 3; observed runs reached 4-5 lens rounds (05f798f4, 6fe9a80a), so the cap is not reliably enforced.

## (a) Per-run table
Strict triad scope = lens + repair agents spawned after the Skill call, plus coordinator turns in that window.
rounds = clustered lens spawns (<180 s apart); lens/rep = agent counts; L/R/M = lens / repair / coordinator dollars.
| session | date | project | rounds | lens | rep | L$ | R$ | M$ | total$ | last-round status |
|---|---|---|---|---|---|---|---|---|---|---|
| f1d0ad89 | 10-08 | files-viewer revamp | 4 | 10 | 4 | 7.9 | 22.2 | 4.0 | 34.1 | P/U/E needs-work |
| 05f798f4 | 10-17 | gphotos-organizer | 5 | 11 | 3 | 7.7 | 15.9 | 2.2 | 25.8 | E ready, U needs |
| 3113016c | 10-16 | files-viewer | 3 | 9 | 4 | 5.1 | 15.3 | 1.7 | 22.1 | P ready, U/E needs |
| 6fe9a80a | 10-11 | kibitzer | 5 | 13 | 3 | 8.2 | 7.0 | 1.3 | 16.5 | E ready, U needs |
| e1217064 | 10-13 | personal-wiki | 4 | 8 | 3 | 4.0 | 7.9 | 1.3 | 13.1 | U needs (R3, R4 UX-only) |
| a364f374 | 10-16 | gphotos (dotfiles) | 4 | 9 | 3 | 4.0 | 7.6 | 0.9 | 12.6 | U not-ready, 24 gaps |
| f350c9e9 | 10-22 | gh-signal | 4 | 12 | 3 | 6.1 | 5.3 | 0.8 | 12.2 | P ready, U/E needs |
| 48d00f1e | 10-23 | review-q | 3 | 9 | 3 | 4.2 | 7.2 | 0.7 | 12.2 | all ready (R3) |
| 63a73c31 | 10-31 | enchdiff | 3 | 7 | 2 | 3.0 | 7.7 | 0.5 | 11.2 | all ready |
| db2db88b | 10-28 | stelekit unwired-features | 3 | 9 | 2 | 5.1 | 4.9 | 1.0 | 11.0 | P/U ready, E needs (then a forced final repair) |
| 8f1af5b4 | 10-17 | cohesion | 2 | 6 | 2 | 2.9 | 6.9 | 0.9 | 10.7 | P/E ready, U needs |
| 18df9d24 | 10-10 | stelekit | 4 | 8 | 3 | 3.7 | 5.6 | 1.0 | 10.3 | U ready at R4 (R3, R4 UX-only) |

Remaining 33 sessions: $0-7 each, 1-3 rounds. Rounds histogram over 45 sessions: 1 round: 15, 2: 14, 3: 8, 4: 5, 5: 2, none: 1. 33 of 45 had at least one repair agent.
Totals: strict scope = $292 = lens $107 (37%) + repair $133 (46%) + coordinator $52 (18%); that is about 34% of the $846 fitted for the label (baseline row says $870).
Per agent (median): lens $0.35, 5 turns, 78 s, 0.3M cache-read. Eng lens is 2x the others (mean $0.79, 10.5 turns, 1.16M cr, cache-write 136k vs 75k Product / 95k UX). Triad-repair agent: median $1.93, 43 turns, 642 s, 8.0M cr; max $5.0 (63a73c31 pass 2, 102 turns).
Parallelism: all lenses overlap in every multi-lens round (span intersection, VERIFIED). Session parallelism 1.0 comes from strictly serial lens round, repair, lens round; a repair (about 11 min) dwarfs a lens round (about 2 min).
Cost by round index (lens + repair attributed to the preceding lens round): R1 $99 (169 agents), R2 $77, R3 $42, R4 $21, R5 $7. Rounds >=3 = $70 (29% of strict); >=4 = $28.

## (b) Top 5 waste patterns
1. **Label bleed inflates the baseline about 3x (VERIFIED).** $513 of the $846 label cost sits in subagents described as "Implement U1 guardrails", "Run SDD Phase 5 implement", "Run SDD Phase 6 verify", "Phase 5 milestone 2-4", "Held-out round N blind eval" (db2db88b from 10-28 02:38; f1d0ad89 10-08; 3113016c 10-16; 05f798f4 10-17; 6fe9a80a 10-12 on). Main-thread turns after the gate also carry the label ($121). The skill itself is about $290, not $870. A before/after benchmark must window from the first Skill call to the last triad lens/repair agent, not use the label.
2. **The repair agent is the largest line (46% of strict) and grows the plan, which seeds the next round's gaps.** In db2db88b the repairs took UX criteria 62 -> 82 -> 97, tasks 121 -> 127 -> 135, estimate 29.2M -> 33.2M CU (repair handbacks, 10-28 01:58 and 02:12); the repair prompt asked it to fix every PRODUCT, UX and ENG gap, not just blockers. Counts VERIFIED; causality INFERRED, supported by next-round gaps that cite newly added text (a364f374 R3 B1 "keyboard model self-contradiction", G24 "queued-intent example differs between ux.md S2 and Story 4.5", 10-17 02:19-02:37).
3. **Gap counts rise with round and "ready" does not converge (VERIFIED stats, n=239 lens runs with parseable output).** Mean gaps by nth run: Eng 5.4 -> 7.3 -> 8.4 -> 10.3; UX 7.4 -> 8.4 -> 10.6 -> 11.0; Product flat at 5-6. Ready rate: UX 17% -> 28% -> 25% -> 25%; Eng 38% -> 45% -> 40% -> 33%; only Product improves (28% -> 80%). UX blocker incidence 41% -> 58% by the third run. Confound: only hard cases reach R3+, and repairs add text. Rounds 3-5 cost $70 and mostly produced new polish gaps (a364f374 R4 UX "not-ready", 24 gaps, 10-17 02:37).
4. **Same artifacts re-read by every agent every round (VERIFIED).** In the 23 sessions with >=6 lens agents, lens agents made 577 `Read` calls on 163 distinct files (3.5x); in db2db88b every one of the 9 files was read by more than one agent (40 Reads). The Eng lens reads plan + validation + pre-mortem + architecture-review + adversarial-review + consistency + ESTIMATION.md (db2db88b, 10-28 01:45), i.e. it re-reviews the other 4-validate subagents' outputs. First-turn cache-write is 75-136k tokens per lens agent, paid again each round by fresh agents. Repair agents re-read the same set plus the /tmp analyses (83 sub-agent reads of /tmp/triad-*); the coordinator also read them 176 times across sessions, which undercuts the "return only a short summary" design.
5. **Exit rule is "all three green", not "no blockers" (partly VERIFIED).** Lenses marked ready still carry 5-10 gaps (P "ready g7", E "ready g6"), and needs-work with zero blockers triggers another repair + round (f350c9e9 R4: statuses P ready, U/E needs, blockers 0/0/0, 10-22 07:36+, then a $2.69 final repair). 15 of 45 sessions went past 2 rounds, 7 past 3. INFERRED: a blockers==0 exit saves about one repair ($2-3) in those runs plus the UX-only rounds in e1217064 and 18df9d24. Later rounds already re-run only failing legs, which is an existing saving.
Minor (INFERRED, about 5-10% of lens cost): `project-coordinator.md` is 21 KB (about 5k tokens) vs 10 KB for ux-expert, and Eng lens runs use 2x the turns (6fe9a80a 10-12: 94 Bash calls, mostly `sed -n` slices of plan.md).

## (c) Ranked candidate changes (savings are fractions of strict $292)
1. **Blocker-scoped, diff-bounded repair** (SKILL.md iterative mode + 4-validate step 6): repair fixes blockers and correctness gaps only; other gaps go to an "accepted gaps" list appended to plan.md with no new criteria/tasks/stories. Metric: repair $ (46%), UW/task-count delta per round, next-round gap count. Expected -15 to -25%. Risk: real UX polish stays open; mitigate by reviewing the accepted-gaps list once in 6-verify.
2. **Exit on blockers==0, cap 2 repairs; round 3 only for a lens that reported a blocker in round 2** (replace "all three green / 4 iterations"). Metric: rounds per run, cost by round (R3+ = $70). Expected -15 to -25%. Risk: Eng blockers appeared in 40% of third runs (db2db88b G1/G2 mergeability and ordering were real), so keep Eng eligible for R3 when R2 had a blocker.
3. **Shared digest instead of per-agent re-reads:** one step per round writes `triad-digest.md` (requirements summary, plan story/unit index, UX criteria list, upstream review verdicts); lens prompts read the digest and open full files only to verify a claim. The Eng lens consumes 4-validate verdicts instead of re-reading all upstream reviews. Metric: Read calls per lens, cache-write per lens, lens $ (37%). Expected -20 to -35% of lens $ (about -8 to -13% of strict). Risk: digest hides detail a lens would catch; benchmark d3 measures this.
4. **Single pass at Complexity 2 and when R1 has zero blockers** (4-validate already skips the gate at C1): gaps go to plan Open Questions, no repair loop. Metric: share of sessions with a repair (33 of 45). Expected -10 to -15%. Risk: UX gaps shipped on small features; low severity.
5. **Stop the coordinator reading /tmp analyses:** read handback JSON only; pass paths to the repair agent. Metric: main-thread reads of /tmp/triad-* (176) and coordinator $ (18%). Expected -3 to -6%. Risk: none known.
6. **Cheaper model for Product lens** (5 turns, $0.30): Haiku. Saves about $15 (about 5%). Keep UX and Eng on Sonnet. Metric: Product seed recall in d1. Low priority.
7. **Fix attribution** (measurement): end the triad window at the last lens/repair agent so Phase 5 work stops inheriting `pm:triad-review`. Metric: label cost vs strict cost (846 vs 292).
Combined plausible target (INFERRED, not additive): -40 to -55% of strict ($120-160 on this sample) while leaving R1 lens detection untouched.

## (d) Benchmark task ideas (frozen artifacts, deterministic checks)
Freeze `requirements.md + design/ux.md + implementation/plan.md (+ validation.md)` under `project_plans/sdd-skill-benchmarking/fixtures/triad-*/`; never run against live repo state.
1. **Seeded-gap fixture (12 gaps):** start from a small plan (e.g. gh-signal) and inject 4 greppable defects per lens, each with an ID.
   Product: goal with no metric; user "everyone"; out-of-scope list removed; no risky assumption. UX: error state of one flow removed; empty state removed; modal with no keyboard path; destructive action with no confirm. Eng: story touching 9 files unsplit; Story 2 uses a table created in Story 5; stated perf requirement with no NFR; effort in human weeks.
   Check: parse the handback JSON and match per-ID keyword sets over `gaps+blockers`; recall = hits/12, require >=11/12 at R1 and <=2 blockers outside the seed list. Metric: lens $ plus coordinator $ per run, N=3 runs per variant.
2. **Convergence fixture:** take the all-ready artifacts from 48d00f1e R3 (clean) and a copy with 2 injected blockers. Check: with changes 1+2 the loop ends in <=2 rounds reporting both blockers; on the clean copy it reports 0 blockers in 1 round. Deterministic growth check: `grep -c` of UW criteria and task headings before/after repair; repair adds <=5.
3. **Digest-fidelity fixture (change 3):** run the d1 fixture with full-read prompts and with digest prompts. Pass if seed recall differs by <=1 gap and lens $ drops >=20%. Add one seed where the plan asserts "file X exists" while the fixture omits it, so the Eng lens must still open the file to verify.
Measurement: window by spawn time (b1), pin model per leg, group lens spawns <180 s apart into rounds, count Read tool_use per agent from the subagent transcripts.

## Caveats / gaps
- Rate fit is predictive; 6 sonnet-5 sessions price at $0. The strict regex treats agents named repair/patch/fix/apply/fold as repair; "Implement PR-A1 core sync fix" in 18df9d24 may be mis-bucketed (about $4).
- I did not check semantic novelty of every gap; "fresh agents surface new gaps" rests on count trends plus reading a364f374 (4 UX rounds) and db2db88b (3 rounds) in full.
- Value of findings (defects avoided in Phase 5-6) is not measured. Gap-count yield only: Product about 5.4 gaps for $0.30 (18/$), UX about 8.6 for $0.36 (24/$), Eng about 6.6 for $0.61 (11/$); unweighted by severity, INFERRED.
