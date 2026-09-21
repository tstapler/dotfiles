---
name: pi-extension-review
description: Fork-pin-review gate for adding any third-party Pi extension, package, or MCP source. Use before running fork_pin_extension.py, before hand-editing .config/pi/extensions-manifest.json, or whenever asked to add/enable a Pi extension not already wired via a first-party fragment.
---

# Pi Extension Fork-Pin-Review Gate

No third-party Pi extension, package, or MCP source may render into
`settings.json` without an approved manifest entry. This is enforced in
code, not just convention: `verify_pinned_sources_reviewed()` in
`stapler-scripts/llm-sync/src/sources/review_gate.py` cross-references every
rendered `tstapler`-fork-shaped source against
`.config/pi/extensions-manifest.json` and raises `PiConfigError` unless a
matching entry exists at the exact pinned commit with `disposition ==
"approved"`.

**Only a human hand-edits `disposition`, `approved_by`, and `approved_date`.**
No script or tool in this repo writes the literal string `"approved"` —
`fork_pin_extension.py` always writes `disposition: "candidate"` with
`approved_by`/`approved_date` left `null`, and `ManifestEntry.__post_init__`
in `stapler-scripts/llm-sync/src/sources/extension_manifest.py` raises
`ManifestError` if `disposition == "approved"` is ever constructed without
both approval fields present. Approval is a diff Tyler authors by hand, not
a flag any automation can set.

## Required gate before enabling any candidate

Reproduced from `project_plans/pi-dotfiles/extension-audit.md`'s "Required
gate before enabling any candidate" — complete all steps, in order, before
changing `disposition` to `"approved"`:

1. Fork the exact upstream repository to the Tyler-owned GitHub namespace.
2. Record upstream URL, upstream commit, fork commit, license, package
   paths, and reviewer notes.
3. Inspect lifecycle scripts, network destinations, subprocess execution,
   filesystem writes, environment access, secret handling, and telemetry.
4. Run upstream tests from the fork commit and add threat-focused
   regression tests for the capabilities actually enabled.
5. Pin the Pi package source to the exact fork commit; mutable
   branches/tags and upstream npm packages are rejected by `PiConfigSource`.
6. Introduce candidates disabled or in an opt-in fragment first, then
   validate in a temporary Pi home before current macOS and Linux rollout.
7. Upgrades repeat this process; no automated upstream advancement.
8. Check maintenance liveness — last commit date, release cadence, and
   contributor count — and record the finding in the manifest entry's
   `notes` field. An unmaintained upstream must be caught here, not only
   during the later capability review.

## How to run the helper + validator

`fork_pin_extension.py` scaffolds the mechanical parts of step 1 and 2 —
forking via `gh repo fork` and writing a `candidate` manifest entry — but
has no code path that can write `"approved"`:

```bash
# Preview the plan; makes no gh calls, writes nothing.
uv run --directory stapler-scripts/llm-sync scripts/fork_pin_extension.py fork \
  <upstream-owner>/<upstream-repo> \
  --id <stable-manifest-id> \
  --capability "<comma,separated,capability,tags>" \
  --dry-run

# Actually fork and write the candidate entry.
uv run --directory stapler-scripts/llm-sync scripts/fork_pin_extension.py fork \
  <upstream-owner>/<upstream-repo> \
  --id <stable-manifest-id> \
  --capability "<comma,separated,capability,tags>"
```

This creates `github.com/tstapler/<repo>` and appends an entry to
`.config/pi/extensions-manifest.json` with `disposition: "candidate"`. From
there, steps 2-8 above are manual review work: hand-edit the entry's
`license`, `package_paths`, `reviewer`, `review_date`, and `notes` fields as
you complete each step, citing real file paths as evidence.

After any manifest or review-gate change, validate with:

```bash
make llm-sync-test
```

This runs every `stapler-scripts/llm-sync/test_*.py` module, including
`test_extension_manifest.py`, `test_review_gate.py`, and
`test_fork_pin_extension.py` — covering the approval-field invariant, the
gate's rejection of unreviewed/mismatched-commit/non-approved sources, and
the no-automated-approval guarantee.

## When a candidate fails review

Not every candidate reaches `approved`. If the review at any step above
turns up a blocker — unmaintained upstream, a capability that can't be
scoped safely, a security finding, or a reviewer decision to wait — set
`disposition` to `hold` (revisit later, evidence not yet conclusive) or
`rejected` (reviewed and declined). Both are legal terminal-for-now states
the manifest schema already supports; leaving a rejected or stalled
candidate at `disposition: "candidate"` misrepresents it as still pending
review. `verify_pinned_sources_reviewed()` blocks sync for `hold` and
`rejected` exactly as it does for `candidate` — only `approved` passes the
gate.
