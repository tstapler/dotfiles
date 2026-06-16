# ADR-003: Alternate File Scoring Algorithm
Status: Accepted
Date: 2026-06-15

## Context

cfgcaddy Feature 2 introduces `##`-suffixed alternate files that allow machine-specific variants of a dotfile. When multiple candidates exist for a target (e.g., `gitconfig##os.darwin`, `gitconfig##hostname.work-laptop`, `gitconfig##default`), the engine must select exactly one.

The core constraint is: **more-specific files must always win over less-specific files**, regardless of which specific attributes match. A file that matches both OS and hostname should always beat a file that matches only OS.

The naive approach — assign each attribute a fixed weight and sum them — has an ambiguity problem: if `hostname` weight is 32 and `os` weight is 2, then `##hostname` scores 32 and `##os##profile` scores 18. But what if `os` weight is 16 and `profile` weight is 16? Then `##os##profile` scores 32, tying `##hostname`. Attribute weight assignment becomes fragile and the "more conditions always wins" invariant is not guaranteed.

## Decision

Adopt the yadm-style scoring formula:

```
score = 1000 * match_count + sum(attribute_weights)
```

Where attribute weights are:

| Attribute | Weight |
|-----------|--------|
| `hostname` | 32 |
| `profile`  | 16 |
| `os`       | 2  |
| `default`  | 0  |

`match_count` is the number of attributes in the filename's `##` suffix that match the current machine context. Only attributes that actually match are included in `match_count`; non-matching candidates are excluded from consideration entirely.

### Why this formula guarantees "more conditions always beats fewer conditions"

The `1000 * match_count` term dominates. Any file with 2 matching conditions scores at least 2000, while any file with 1 matching condition scores at most `1000 + 32 + 16 + 2 = 1050`. Because `1000 > sum(all weights) = 50`, a file with more matching conditions always outscores a file with fewer matching conditions, regardless of which attributes are involved.

The `sum(attribute_weights)` term is a tiebreaker within files that match the same number of conditions. It encodes the semantic priority of attributes: `hostname` (most specific, identifies one machine) > `profile` (identifies a usage mode) > `os` (identifies a platform class).

### The `##default` convention

`##default` always matches and has `match_count = 1`, `attribute_weight = 0`, so `score = 1000`. A bare filename (no `##` suffix) is treated identically to `##default` — it always matches with `score = 1000`.

This preserves backward compatibility: existing files without `##` suffixes behave as before, and are overridden by any file with a real matching attribute (`score >= 2000`).

### No-match behavior

If no candidates match the current machine context (all candidates have `##` suffixes and none match, with no bare file or `##default`), **no file is linked** and a WARNING is emitted:

```
WARN: No candidate for target '.gitconfig' matches current machine (os=darwin, hostname=personal-laptop, profile=none). Skipping.
```

`cfgcaddy doctor` flags this as WARN.

### Tie-breaking

If two candidates have identical scores after applying the formula, cfgcaddy raises an error during `cfgcaddy link` and reports the tie as FAIL in `cfgcaddy doctor`. The tie must be resolved by the user (rename or remove one candidate). Deterministic tiebreaking by lexicographic filename order is intentionally not implemented — a tie almost certainly indicates a user configuration mistake, and silently picking one would mask it.

Exception: the tie between a bare filename and `##default` (both score 1000) is resolved by preferring `##default` over bare filename. A warning is emitted. This case is unusual but not necessarily a mistake.

## Alternatives Considered

**Simple additive scoring without match_count multiplier**
Rejected. With only additive weights, ties between different attribute combinations are possible (e.g., `##os##profile` with `os=16, profile=16` ties `##hostname` with `hostname=32`). The "more conditions always wins" invariant cannot be guaranteed without carefully chosen weights. The yadm formula eliminates this class of ambiguity entirely.

**Lexicographic tiebreaking (deterministic, no error)**
Rejected for non-default ties. Ties between two non-default candidates strongly suggest a user configuration error (e.g., `gitconfig##os.darwin` and `gitconfig##hostname.work-laptop` on a macOS work laptop — the user probably intended one to be `gitconfig##os.darwin##hostname.work-laptop`). Silently picking one masks the mistake. The `doctor` FAIL report is more useful.

**yadm's exact implementation (copy verbatim)**
Not fully adopted. yadm's scoring is the direct inspiration, but cfgcaddy uses Python and supports a `profile` attribute yadm does not have. The formula is the same; the attribute set is extended.

**Semantic versioning-style comparison (tuple comparison)**
Rejected. Tuple comparison (`(match_count, hostname_match, profile_match, os_match)`) is logically equivalent to the numeric formula but less transparent when debugging scores and harder to document.

## Consequences

**Positive:**
- The "more conditions always beats fewer conditions" invariant is mathematically guaranteed, regardless of which attributes are involved.
- Scoring is deterministic and testable — given a machine context and a set of candidates, the winning file is always the same.
- The formula is explainable: `1000 * match_count + attribute_weight_sum`.
- Backward compatible: bare filenames score identically to `##default` (score 1000), overridden by any real match (score ≥ 2002).

**Negative:**
- Users who expect `##hostname` to beat `##os##profile` (because hostname is more specific) may be surprised that `##os##profile` wins when both conditions match. The attribute weights handle single-match ties; for multi-match files the match count dominates. Documentation must be explicit.
- Score values (1000, 1032, 2000, 2050) are not immediately intuitive without understanding the formula. `cfgcaddy doctor` should display computed scores when reporting candidates to aid debugging.

**Test requirements:**
- `##os.darwin##hostname.work-laptop` (score 2034) beats `##os.darwin` (score 1002) on a macOS work laptop.
- `##hostname.work-laptop` (score 1032) beats `##os.darwin` (score 1002) when both match.
- `##os.darwin##hostname.other-machine` does not match a machine with `hostname=work-laptop` — excluded.
- Bare `gitconfig` and `gitconfig##default` both score 1000; `##default` wins with a warning.
- Tie between two non-default candidates raises an error.
- No-match scenario emits WARNING and links nothing.
