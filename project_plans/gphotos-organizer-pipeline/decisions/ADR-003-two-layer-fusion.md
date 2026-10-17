# ADR-003: Two-layer date fusion (hard guards, then weighted per-year log-score)

**Status**: Accepted · **Plan**: Stories 2.6, 2.7, 2.8

## Context
Plugin votes are uneven and correlated (age and era both use pixels; folder-year and filename-year both derive from the album). Anchors may be sparse, so fully calibrated Bayesian likelihoods are not assured (`research/architecture.md` s6, `research/pitfalls.md` s4).

## Decision
- **Layer A**: deterministic guards prune the year axis and are never overridden: BirthDeathBounds, FolderYearBounds (configurable k), Anchor, UploadWindowCeiling, PhysicalPlausibility. An empty result is `Conflict`: reviewed, never written.
- **Layer B**: discretized per-year log-score over surviving years with plugin weights capped by calibration (`weight_cap`), a `correlation_group` discount (`group_cap`), abstain contributing nothing. Output: highest-mass contiguous window; confidence = mass inside it; fewer than `min_independent_voters` => `Review`.
- Fusion is pure; `--min-confidence` changes are a re-run of `fuse`, not of analysis.
- Ship Layer A and the review flow first so the pipeline is safe with weak statistics.

## Consequences
Explainable (guards and voters recorded per decision); golden-file tests pin behavior; uncalibrated plugins can raise a file to review but not to write.

## Alternatives rejected
Pure Bayesian product (double-counts correlated votes, needs calibrated likelihoods); pure interval intersection (cannot represent soft evidence).
