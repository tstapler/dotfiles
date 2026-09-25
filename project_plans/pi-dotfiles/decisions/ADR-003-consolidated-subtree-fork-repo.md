# ADR-003: Consolidate Third-Party Extension Forks Into One Subtree Repo

**Date**: 2026-09-24
**Status**: Accepted
**Amends**: ADR-001 (keeps its manifest/gate invariants; replaces its "one
native GitHub fork per upstream repo" mechanism)

## Context

ADR-001 established the fork-pin-review manifest and its enforcement gate,
built on top of `fork_pin_extension.py` scaffolding a **native GitHub fork**
per upstream (`gh repo fork <upstream>` -> `github.com/tstapler/<repo>`).
`full-featured-profile-research.md` and `extension-audit.md` name a dozen
upstream candidates across five tiers, which under the ADR-001 mechanism
means a dozen independently-owned fork repos, each with its own branch
protection, CI, dependency updates, and npm/pnpm workspace to maintain —
almost all of that plumbing identical across forks.

Before any manifest entry existed, twelve of these upstreams were already
forked natively (`gotgenes-pi-packages`, `pi-lens`, `narumiruna-pi-extensions`,
`pi-mcp-adapter`, `jmcombs-pi-extensions`, `pi-web-access`,
`pi-async-compaction`, `pi-sessions`, `diegopetrucci-pi-extensions`,
`99percentpeople-pi-extensions`, `pi-image-tools`, `pi-rewind`). Tyler asked
to consolidate ongoing and future forks into the existing
`tstapler/pi-extensions` repo instead — the same repo that already holds the
Tyler-owned `@tstapler/pi-claude-compat` compatibility package — accepting
that this mixes reviewed-third-party and Tyler-authored code in one tree,
rather than splitting them into a second consolidated repo.

Verified before deciding: GitHub permits `git fetch <url> <exact-commit-sha>`
for a public upstream even when that commit isn't an advertised branch/tag
tip (tested live against `gotgenes/pi-packages` at the
`e64946b5ce96ca004b753d98932c8b13106dd132` review anchor — succeeded). This
means a subtree import can still pin the *upstream* commit exactly, not just
whatever the upstream's default branch happens to be pointing at.

## Decision

Replace the fork step of `fork_pin_extension.py` with a **git subtree
import** into `tstapler/pi-extensions`, instead of a native `gh repo fork`:

1. Clone `https://github.com/tstapler/pi-extensions.git` into a scratch
   directory.
2. `git fetch <upstream-url> <upstream-commit>` (proven above to work for an
   exact SHA, not just a ref tip).
3. `git subtree add --prefix third-party/<entry-id> FETCH_HEAD --squash` —
   `--squash` is deliberate: it keeps `pi-extensions`' own history linear and
   readable, at the cost of not carrying the upstream's full commit-by-commit
   history into our tree (the upstream repo and its history remain visible at
   `upstream_repo`/`upstream_commit` in the manifest regardless).
4. Push the resulting commit to `tstapler/pi-extensions` (a feature branch,
   not directly to `main` — see Consequences).
5. Record that push's commit SHA as `fork_commit`, and `third-party/<entry-id>`
   as the manifest entry's `package_paths` entry.

No manifest schema change is required. `ManifestEntry.fork_repo` was never
constrained to be unique per entry, and `package_paths` already exists (it
was added for monorepo upstreams like `rpiv-mono`) — multiple entries simply
now share `fork_repo: "https://github.com/tstapler/pi-extensions"` with
different `fork_commit`/`package_paths` per entry, instead of each having a
distinct `fork_repo`. `verify_pinned_sources_reviewed()` and
`_fetch_fork_tree_paths()`'s per-entry `gh api .../git/trees/<fork_commit>`
check both already operate per (fork_repo, fork_commit) pair and need no
change.

`fork_pin_extension.py fork` keeps its existing CLI contract
(`upstream --id --capability [--dry-run]`); only its internal mechanism
changes. It still only ever writes `disposition: "candidate"` — this ADR
does not touch the approval-gate invariant from ADR-001.

The twelve already-created native forks are **not** migrated by this ADR.
Migrating them (subtree-importing each into `pi-extensions` and archiving
the standalone fork repo) is a separate, explicitly-confirmed follow-up per
fork, tracked as an Unresolved Question below — none of them has a manifest
entry yet, so none is currently relied on by the sync pipeline.

## Alternatives Considered

1. **Second consolidated repo** (e.g. `tstapler/pi-vendor`) for third-party
   subtree imports, keeping `pi-extensions` exclusively Tyler-owned. Rejected
   per Tyler's explicit choice: fewer repos in total outweighs keeping
   trust levels in separate trees, and per-package review notes/manifest
   entries already carry the provenance distinction that the repo split
   would otherwise provide.
2. **`git subtree add` without `--squash`**, importing full upstream history.
   Rejected: it would import histories with potentially thousands of commits
   across a dozen upstreams into one repo's `git log`, and offers no real
   benefit here since `upstream_repo`/`upstream_commit` already give a
   reviewer a path back to the original history when needed.
3. **Keep native forks, add a meta-repo of git submodules instead.**
   Rejected: submodules would still leave a dozen repos to maintain (CI,
   branch protection, dependency bots) — the actual maintenance burden Tyler
   is trying to cut — and add submodule-pointer drift as a new failure mode.

## Consequences

- One repo (`tstapler/pi-extensions`) to maintain CI, lint, and dependency
  policy for, instead of a dozen-plus.
- Push-by-script is a new, more consequential capability than the old
  `gh repo fork` (which only creates a fork with GitHub-side history, no
  local write access needed). `fork_pin_extension.py` must push to a
  **feature branch** (`extension/<entry-id>`), never `main` directly, so a
  human still reviews and merges the diff that lands new third-party code —
  this is the mechanism-level equivalent of ADR-001's "only a human hand-edits
  `disposition`" invariant, applied to code-import instead of manifest-edit.
- `pi-extensions`' README/SECURITY.md need updating to state it now holds
  both Tyler-owned and reviewed-third-party-subtree code, and that trust
  level is tracked per-package in the extension manifest, not by repo.
- A re-pin to a new upstream commit still requires a fresh subtree import (a
  new squash commit) and fresh manifest approval, exactly as ADR-001 already
  required for native forks — this property is unchanged.
- Local disk/network cost per fork run: a fresh scratch clone of
  `pi-extensions` (small — Tyler-owned code only, no bundled third-party
  history) plus one fetch of the specific upstream commit. No persistent
  local checkout is required or maintained by the script.

## Unresolved Questions

- Whether to migrate the twelve pre-existing native forks into
  `pi-extensions` (and archive the standalone repos), and in what order.
  Deferred: each migration is its own confirmed action, not implied by this
  ADR.
- Branch-protection and required-review settings for
  `tstapler/pi-extensions` now that it will receive more frequent, more
  security-sensitive pushes (subtree imports of unreviewed-at-fork-time
  third-party code) than it did as a Tyler-only-authored repo.
