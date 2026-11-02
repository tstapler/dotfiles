# Skills changelog

Changes to skill text and the evidence behind them. Newest first. A skill change should land here
with the experiment that justified it (or the one that rejected it). Method and harness:
`project_plans/sdd-skill-benchmarking/plan.md`, `meta-skill-effectiveness-audit/scripts/`.

Dollar figures from `phase_cost_report.py` are fitted from billed cost (about ±25% per session):
use them to rank, not to total. Experiment numbers come from `~/.cache/skill-ab/` and use sonnet,
12 runs per arm, on the fixture named in each entry.

## 2026-11-01

### Experiments (no skill text changed)

- **sdd:4-validate step 6 — blockers per leg, mandatory fresh re-review, max 2 rounds: rejected.**
  Fixture `triad-demo-export`, 12 runs per arm against current text (arm A).
  All 3 seeded blockers fixed: A 8/12, variant 1/12. Variant mean cost $0.79 vs A $0.37 (CI of the
  difference excludes zero). 10 of 12 variant runs ended at NOT READY, where the skill halts without
  repairing. Branch `bench/triad-v2` (local only).
- **sdd:4-validate step 6 — lean exit (proceed on NEEDS WORK with no blockers, repair blockers only,
  max 2 rounds): rejected.** Same fixture. All 3 blockers fixed: A 8/12, variant 1/12 (Fisher exact
  p about 0.009). Mean cost $0.47 vs $0.90, CI includes zero; cost per success $5.64 vs $1.35. In the
  transcript read, the orchestrator re-labelled product and UX blockers as accepted gaps. Branch
  `bench/triad-v1` (local only).
- Open: score a halt at NOT READY as its own outcome rather than a failure; results are one fixture
  and one model, and arm A's mean cost varied between batches ($0.90, $0.37).

### Added

- `meta-skill-effectiveness-audit/scripts/phase_cost_report.py`: per-phase cost, cache-hit share,
  active wall-clock and parallelism from session transcripts. Baseline:
  `project_plans/sdd-skill-benchmarking/baseline-phase-report-2026-11-01.txt`.
- `ab_runner.py` and `ab_report.py`: run a fixture against git-ref arms in throwaway HOMEs and report
  bootstrap confidence intervals and cost per success.
- Fixture `project_plans/sdd-skill-benchmarking/fixtures/triad-demo-export/` (12 seeded gaps).

### Findings that feed later changes (not yet acted on)

- `sdd:*` phases are 43–52% of fitted cost; `sdd:5-implement` is the largest. Research notes for
  `pm:triad-review`, `github:pr-ship`, `code:review`, `backlog:*` and `golang-development` are in
  `project_plans/sdd-skill-benchmarking/research/`. Savings estimates there are agent estimates and
  unmeasured.
