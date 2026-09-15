# ADR-001: Extension Fork-Pin-Review Manifest & Enforcement Gate

**Date**: 2026-09-14
**Status**: Accepted

## Context

`requirements.md` forbids silently forking or auto-installing third-party Pi
extensions: every third-party package must be forked under Tyler's control,
reviewed, and pinned to an exact commit before it can activate
(requirements.md Constraints). `extension-audit.md` already describes a
seven-step review gate in prose ("Required gate before enabling any
candidate"), and `full-featured-profile-research.md` names specific upstream
candidates and review anchors.

The existing renderer, `PiConfigSource`
(`stapler-scripts/llm-sync/src/sources/pi_config.py`), already enforces the
*shape* of a pin — `_is_allowed_package_source` rejects any `github.com/`
source that isn't `github.com/tstapler/<repo>@<40-or-7-hex-char-commit>` (or a
local path, or a `trustedPackageScopes`-listed npm scope). It has no way to
know whether that pinned fork commit was actually reviewed — a syntactically
valid pin is not evidence of a completed review.

## Decision

Add a second, tracked registry — the Extension Manifest
(`.config/pi/extensions-manifest.json`) — recording one entry per
forked/reviewed extension: upstream repo/commit, fork repo/commit, license,
reviewer, review date, disposition (`candidate` / `hold` / `rejected` /
`approved`), and free-text review notes. Wire a new validation step,
`verify_pinned_sources_reviewed()` (`stapler-scripts/llm-sync/src/sources/extension_manifest.py`),
into `sync_pi_settings()` (`stapler-scripts/llm-sync/src/cli.py`) so that any
rendered `packages`/`extensions` source matching the `github.com/tstapler/`
fork shape must have a matching manifest entry with `disposition: "approved"`
at the *exact same commit* — otherwise the sync raises `PiConfigError` and
writes nothing.

Critically, the tooling that scaffolds manifest entries (the fork-and-pin
helper, `stapler-scripts/llm-sync/scripts/fork_pin_extension.py`) has no code
path that can write `disposition: "approved"`. It only ever writes
`"candidate"`. Approval is exclusively a human hand-edit — a separate,
reviewable git diff — of `disposition`, `approved_by`, and `approved_date`.

This mirrors the pattern `PiConfigSource` already established for credential
material and pin format: the answer to "must never happen" in this codebase is
executable validation, not documentation.

## Alternatives Considered

1. **Fully automated fork+pin CLI** that also flips `disposition` to
   `approved` on success. Rejected: this automates away the one step
   requirements explicitly reserve for a human — the actual security review
   and go/no-go decision — which is precisely the silent-fork failure mode the
   requirements forbid.
2. **Manual-only process** — Tyler runs `gh repo fork` and hand-writes the
   manifest JSON with no validator checking it against rendered config.
   Rejected: the review gate would then be enforced only by Tyler remembering
   to check it every time, the same convention-only gap `PiConfigSource`
   already closed for credentials and pin format.
3. **Fold review metadata directly into `config.d` fragments** (e.g. an
   `_review` key alongside each `packages` entry) instead of a separate
   manifest file. Rejected: review records and activation state have
   different lifecycles — an entry can be reviewed and approved long before
   (or after) it's actually enabled in a fragment, and mixing them would let
   disabling an extension silently discard its review history.

## Consequences

- Every future third-party Pi extension needs one manifest entry before it can
  render, at zero marginal enforcement cost per extension (the validator is
  written once).
- A re-pin to a new upstream commit requires a fresh, explicit re-approval —
  `verify_pinned_sources_reviewed()` checks the fork commit exactly, so an
  approval at an old commit does not carry forward automatically. This is
  intentional: it directly implements requirements' "Bootstrap must not
  silently advance third-party ... extension/package versions."
- The manifest is public (tracked, non-secret metadata only — no credential
  material, matching every other file in `.config/pi/`).
