---
description: Maintenance shortcut — rank refactor candidates by complexity × churn, refactor the top one, verify
user-invocable: true
---

# sdd:fix-hotspot

Four-phase maintenance workflow for structural debt: rank → diagnose → refactor → verify. The
refactor analog of `sdd:fix-bug` — same shape, applied to "what's the worst file to work in"
instead of "what broke."

## Instructions

1. **Select the target.** If an argument names a file, package, or directory, treat it as the
   target and skip to Phase A. Otherwise rank candidates first — don't start reading files hoping
   to spot a smell:

   - Invoke `code-hotspot-analysis` for the repo (or the subtree implied by the request). It
     combines static coupling (kibitzer / goda / gocyclo / ast-grep) with temporal coupling (git
     co-change) into a complexity × churn hotspot score.
   - Before ranking from scratch, check for an existing ledger at
     `docs/reference/hotspot-ranking.md` (target repo's own doc root — adjust if the repo uses a
     different convention). If it exists and is recent enough to trust (repo structure/churn
     hasn't shifted enough to invalidate it — use judgment, don't recompute reflexively), resume
     from its next `pending` row instead of re-deriving the whole list. This is what makes the
     ranking survive a `/clear` or a fresh session with no memory of a prior run's conversation.
   - Pick the single top-ranked file or package — ideally one flagged by both axes (structurally
     central *and* a temporal hotspot). Don't queue up the whole ranked list; this command fixes
     one target per run. Re-run it to work the next one down the list.
   - If the top hit is generated code (ORM output, protobuf bindings) or a vendored/third-party
     path, skip it and take the next real candidate — the hotspot skill's own scoring notes this
     as a known false-positive shape.
   - **Write the ranking to disk immediately after computing it**, before starting Phase A —
     create or overwrite `docs/reference/hotspot-ranking.md` with the full ranked table (file,
     complexity sum, churn count, score, status). Every row starts `pending` except the one this
     run is about to work, which starts `in-progress`. This must happen even if the run gets
     interrupted before finishing — a ranking that only ever lived in conversation state is lost
     the moment the session clears, which is exactly the gap that prompted this rule.

2. **Phase A — Diagnose.**

   A high hotspot score says *where* to look, not *why* it's bad or *what* to do about it. Hand
   the target to `quality:architecture-review`, scoped narrowly (`--target=file:X` /
   `--target=package:Y`, never a full-codebase sweep) to get the principle-level finding: which
   SOLID/DDD/Clean-Architecture violation is actually driving the complexity, and which axis
   flagged it (a static-coupling problem wants an interface/boundary extraction; a temporal
   coupling finding across unrelated packages wants a missing shared abstraction).

   State the diagnosis in one sentence before moving on: "This is bad because X."

3. **Phase B — Refactor.**

   - Tidy First timing check (Kent Beck, via `code:refactor`): is this worth doing now on its own,
     or should it wait for a change that touches the same code? A hotspot found via `/sdd:fix-hotspot`
     is by definition not blocking any in-flight behavior change — default to doing it now as its
     own isolated commit, but say so explicitly rather than assuming.
   - Execute with `code-refactoring` (ast-grep to map scope + confirm blast radius, gritql for the
     mechanical transformation, or `Edit` directly if the fix is a single-file extraction too small
     to warrant gritql). Preserve behavior — this is structural work, not a feature change.
   - Keep the structural change in its own commit(s), separate from any behavior change, per
     `git:commit`.

4. **Phase C — Verify.**

   Claim the refactor is done only after running the project's actual build/lint/test commands and
   showing the passing output — reading the diff is not verification. Run:
   - The build/compile step for the affected package.
   - The full test suite for the affected package (not just the whole repo's smoke tests) — an
     extraction that compiles but silently changes behavior is the most common failure shape here.
   - Lint, if the project gates on it.

   If the target has no tests covering the code being restructured, say so explicitly and add the
   minimum regression coverage needed to trust the refactor — don't skip verification because
   coverage was already thin.

5. **Phase D — Gate (prevent regrowth).**

   A hotspot fixed once and left ungated tends to reform — the churn that made it a hotspot doesn't
   stop after one cleanup. Per `code-hotspot-analysis`'s CI Enforcement section:
   - If the repo doesn't already gate on the complexity metric that flagged this file (cyclomatic/
     cognitive complexity, function length, file length), propose adding one — scoped to
     new/changed code only (e.g. `golangci-lint-action`'s `only-new-issues: true`, ESLint on the
     diff's changed files), thresholded off this repo's own measured average, not a textbook
     default.
   - If a gate already exists and this file was somehow still allowed to grow past it (e.g. it was
     grandfathered, or the gate only just landed), note that explicitly rather than silently
     re-adding the same exclusion.
   - This phase is a proposal + implementation if the project's CI config is something this session
     can edit; if it's out of scope (a separate infra repo, a decision only the user can make),
     state what gate *should* exist and let the user decide, rather than skipping the question.

6. **Update the ledger.** Flip this run's row in `docs/reference/hotspot-ranking.md` from
   `in-progress` to `done`, recording the commit SHA(s) and one line of what changed. If no ledger
   existed before this run (an argument-named target, or a repo with no prior `/sdd:fix-hotspot`
   history), create one now with just this row plus a note that the rest of the ranking hasn't
   been computed yet — don't leave the file absent just because this run skipped Phase 1's full
   ranking.

7. Output:
   ```
   ✅ Hotspot refactored and verified

   Target: <file/package> — hotspot score: <complexity × churn, or "N/A, user-specified target">
   Diagnosis: <one sentence — which principle violation, from Phase A>
   Refactor: <one sentence — what changed structurally>
   Verification: <build/test/lint commands run + result>
   Regrowth gate: <what was added, or "already gated" or "proposed, needs a decision on X">
   Ledger: <path to hotspot-ranking.md, updated>
   ```

## When NOT to Use This

- **A single obviously-bad file the user already pointed at with a clear fix in mind.** Skip
  straight to `code-refactoring` — this command's value is the ranking step, which is wasted effort
  when the target and fix are already known.
- **A young codebase with little git history.** `code-hotspot-analysis`'s temporal axis needs
  enough commits to be meaningful; static coupling alone (still available) is a weaker signal for
  picking a single "highest value" target — say so rather than presenting a temporal ranking as
  confident when it isn't.
