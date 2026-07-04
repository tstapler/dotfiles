---
name: journeys-verify
description: >
  Verifies that docs/journeys/*.md spec files (written by journeys-extract) still
  hold true — every source_ref path still exists and every test_id is still
  findable in the repo's test suite. Runs a cheap deterministic script (Tier 1,
  safe for CI/pre-commit on every PR) that flips each journey's status between
  draft/verified/stale, plus an optional LLM semantic-drift pass (Tier 2, per
  journey, checks whether the narrative still matches the actual UI/code) for a
  fuller review. Use to check journeys are still accurate — for a quick CI gate
  ("is anything broken"), or before trusting a journey doc during onboarding or
  planning. Does not discover new journeys (journeys-extract) or improve/deepen
  journey content (journeys-enrich).
---

# Journeys: Verify

Check that persisted journey specs (`docs/journeys/*.md`) still describe reality.
Two tiers: a deterministic script that checks mechanical links (fast, CI-safe,
no LLM judgment needed), and an optional LLM pass per journey that checks whether
the step narrative still matches the actual UI/code (slower, judgment-based).

## When to Use

- CI/pre-commit gate: fail the build if any journey is stale (Tier 1 only)
- Before relying on `docs/journeys/` for onboarding, planning, or a PR review —
  confirm it's not lying
- After `journeys-extract` flags journeys `updated-marked-stale`, to confirm
  whether the drift is real or the linked tests just moved
- NOT for discovering journeys that don't exist yet (`journeys-extract`) or for
  writing/improving journey narrative (`journeys-enrich`)

## Input

```
/journeys:verify [--strict] [--full]
```

- `--strict`: exit 1 if any journey ends up `stale` (for CI gating)
- `--full`: also run the Tier 2 semantic-drift pass (default: Tier 1 only)

## Tier 1 — Deterministic (always runs)

```bash
uv run .claude/skills/journeys-verify/scripts/verify_journeys.py check --strict
```

For every `docs/journeys/*.md` file (except `README.md`), this script:
- Checks every `source_refs` path still exists on disk
- Checks every `test_ids` string is still findable as a full-text substring
  somewhere in the repo (excluding `.git`, `node_modules`, `dist`, `build`,
  `.venv`, `__pycache__`, and `docs/journeys/` itself)
- Sets `status`: `verified` if both checks pass and `test_ids` is non-empty;
  `stale` if either check fails; `draft` if `test_ids` is empty (nothing to
  verify yet — not a failure)
- Sets `last_verified` to today's date only when `status` becomes `verified`
- Records why in `verify_notes` (a list of reason strings)
- Never touches `title`, `user_types`, `source_refs`, or the body — those are
  extraction-owned

Read the script's JSON output (`{results: [...], counts: {...}}`) directly —
don't re-derive counts by hand.

## Tier 2 — Semantic Drift (only with `--full`)

For each journey the script left `verified` (mechanical links hold), spawn one
lean agent per journey **in parallel** to check whether the narrative still
matches reality — this is the check no script can do:

```
Read the journey spec at <path>. Read its source_refs files (and the UI/code
they point to). Compare the journey's numbered Steps against what the code/UI
actually does today.

Does the narrative still accurately describe the flow? Consider: renamed
screens/buttons referenced in a step, steps that no longer trigger the way
described, missing steps for new required fields, dead-end states not reflected
in the diagram.

Return ONLY this JSON:
{
  "slug": "<journey_id>",
  "still_accurate": true|false,
  "drift_notes": ["specific mismatch, if any"]
}
```

For any journey where `still_accurate: false`, update its `status` to `stale`
and append `drift_notes` to `verify_notes` — do this directly with the Edit tool
on just those two frontmatter fields (don't touch anything else in the file, and
don't re-run Tier 1's script afterward or it will silently overwrite your edit
based on stale in-memory assumptions — apply Tier 2 edits last).

## Pre-commit / CI Integration

`scripts/pre-commit-hook.sh` wraps Tier 1 for git hooks: it no-ops if the repo
has no `docs/journeys/` (safe to install anywhere), runs `verify_journeys.py
check --strict`, and blocks the commit if status changed (needs re-staging) or
any journey is still stale. Requires `uv` on `PATH`.

**Install into a target repo** (fresh hook):
```bash
ln -s "$(pwd)/.claude/skills/journeys-verify/scripts/pre-commit-hook.sh" .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

**Append to an existing hook** instead of overwriting it:
```bash
echo '.claude/skills/journeys-verify/scripts/pre-commit-hook.sh || exit 1' >> .git/hooks/pre-commit
```

**CI (any runner)** — same script, minus the git-diff staging check, run non-strict
in normal jobs and `--strict` as a merge gate:
```bash
uv run .claude/skills/journeys-verify/scripts/verify_journeys.py check --strict
```

**jj-colocated repos**: `jj` does not reliably invoke `.git/hooks/pre-commit` the
way plain git does — verify this on the target repo before relying on it; if it
doesn't fire, wire the same command into CI instead.

## Reporting

Tell the user: counts per status (verified/stale/draft), and for any stale
journey, its `verify_notes` reasons. If `--strict` and CI failed, name which
journeys blocked it. Do NOT dump full journey files into the conversation —
counts + reasons are enough for a decision.

## Anti-Patterns

- **Don't hand-edit `status`/`last_verified`/`verify_notes` outside this skill** —
  they're recomputed here; manual edits get silently overwritten on the next run.
- **Don't run Tier 2 on every CI invocation** — it's LLM-driven and not free;
  reserve `--full` for periodic review or explicit request, keep CI on Tier 1.
- **Don't treat `draft` as a failure** — a journey with no `test_ids` yet is
  expected during early adoption; that's `journeys-enrich`'s job to fix, not a
  verify failure. Only gate CI on `stale`.
