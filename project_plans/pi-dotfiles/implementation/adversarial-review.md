# Adversarial Review: pi-dotfiles (iteration 3 — final blocker verification)

**Date**: 2026-09-14
**Verdict**: CONCERNS

## Blockers
(none — original blocker RESOLVED)

**Original blocker**: Story 1.2.1's AC claimed comment comparison was "not sensitive to short-vs-long hex form" and called this "a stated, tested comparison rule," but no GWT example or test exercised a short-vs-long pair.

**Fix verification**:
- The AC (`project_plans/pi-dotfiles/implementation/plan.md:205`) now reads: "Commit comparison is case-insensitive; the manifest `fork_commit` and the config pin must otherwise match exactly — a prefix/abbreviated SHA in one that isn't byte-identical to the other, after case-folding, is treated as a mismatch, not a match." This narrows the claim to something the plan actually delivers (case-fold only, no prefix tolerance) — no longer asserts an unimplemented guarantee.
- A new GWT bullet (`plan.md:207`) exercises a full-SHA-vs-7-char-prefix pair and asserts `PiConfigError`. Task 1.2.1e's test list (`plan.md:230`) states the matching case: "a full 40-char manifest `fork_commit` vs. its own 7-char prefix as the config pin is correctly treated as a MISMATCH (proves the comparison is exact-after-case-fold, not prefix-tolerant)." The AC bullet and the task's test-list entry describe the identical scenario and identical expected outcome — internally consistent.
- Case-insensitivity itself is separately covered by `plan.md:206` (uppercase-vs-lowercase, both directions) and mirrored in Task 1.2.1e's test list — also consistent.
- Cross-checked against ground truth in `stapler-scripts/llm-sync/src/sources/pi_config.py:178-198` (`_is_allowed_package_source`): that function validates only a single ref's hex shape (`re.fullmatch(r"[0-9a-fA-F]{7,64}", ref)`) and never compares two commit values against each other. The AC's disclaimer ("not an assumption inherited from `_is_allowed_package_source`'s bare regex match," `plan.md:206`) accurately reflects this — the manifest gate's exact-match-after-case-fold comparison is genuinely new logic, not a restatement of existing behavior.
- Task 1.2.1a (`plan.md:213-215`) scopes this new comparison to `extension_manifest.py` ("Scans rendered `packages`/`extensions` values for `github.com/tstapler/` fork sources and checks each against the manifest"), a different file from `pi_config.py` where `_is_allowed_package_source` lives — confirms the plan correctly treats this as new code, not a duplicate/extension of the existing regex check.

Classification: **RESOLVED**.

## Concerns
- [ ] Task 1.2.1e's example commit string `abc1234def5678901234567890123456789012a` in the AC (`plan.md:207`) is 39 characters, not the "full 40-char SHA" the same bullet calls it (verified: `len("abc1234def5678901234567890123456789012a") == 39`). The semantic point (long value vs. its 7-char prefix is a mismatch) survives regardless of exact length, but whoever implements Task 1.2.1e should use a literal 40-char hex string rather than copying this example verbatim, or the AC text should be corrected to say "39-char" / regenerate a true 40-char value — recommend fixing the string (or the "40-char" label) before or during implementation so the committed test fixture isn't off-by-one from its own description.

## Minors
- None beyond the concern above.
