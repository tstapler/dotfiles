# Phase 6 verify: dunnage v0.1.0 (55ccf79), read-only

Repo: ~/code/github.com/tstapler/disk-cleanup. Plan file read from branch plan/rust-disk-cleaner (not on master in ~/dotfiles).
Scope: Rust idioms, architecture, correctness/tests/security/errors. Skipped: browser UX, pty journeys (Gate F). No code edited, no --apply/delete run, nothing pushed.

## Verdict: FIX-THEN-SHIP (two small fixes; none is a data-loss bug in the default path)

## Evidence run
- `cargo test --workspace --offline` (TMPDIR=/tmp): 1742 passed, 0 failed, 3 ignored (recounted from `test result` lines in /tmp/vt.log). The "panicked at tui/tests/guard.rs:176" line is an expected-panic test, run exit 0.
- `cargo clippy --workspace --all-targets --offline -- -D warnings`: exit 0.
- `unsafe`: forbidden in cli/core/tui (`#![forbid(unsafe_code)]`); present only in adapters (signals.rs, fiemap.rs, space_meter.rs, probe/basic.rs) and scan/btrfs_tree.rs:309 (has SAFETY comment). Handler `on_signal` (signals.rs:148-156) is async-signal-safe (write + errno save/restore).
- Non-test `unwrap/expect/panic`: only 5 sites, all "unreachable by construction" (audit_verify.rs:71, compose.rs:556, fmt.rs:24,105) plus a test hook (explore.rs:286). Workspace lints warn on unwrap_used/expect_used (Cargo.toml:15-16).

## Findings, ranked

### 1. MEDIUM (INFERRED, not exercised: needs root) - symlink-following create+chown under sudo
- crates/adapters/src/audit.rs:49-56 opens the audit file with `create(true).append(true)` (follows symlinks), then `chown_if` (state.rs:108-111) calls `std::os::unix::fs::chown` (state.rs:104), which also follows symlinks. Same pattern in lock.rs:46-52 and state.rs:182/268/291/403.
- `Owner::for_euid` (state.rs:93-100) is set exactly when euid is 0 and the state dir is user-owned. So under `sudo dunnage`, a process running as the user can plant `audit.jsonl -> /some/root/file`; root then appends JSON lines to it and chowns it to the user.
- Fix: open with `O_NOFOLLOW` and `fchown` on the open fd (or `lchown`); same for lock/state files. Cheap, local to adapters.
- Not exercised: reproducing needs root, which this run must not use.

### 2. LOW-MEDIUM - delete identity is (dev, ino, kind) only (known)
- ids.rs:15-18 `Identity{dev,ino}`; plan.rs:289-293 `ItemIdentity{dev,ino,kind}` (doc at plan.rs:286-287 deliberately omits times). Checked at: dirops.rs:132, delete.rs:212, explorer_selection.rs:142,159,189 and in the plan id (plan.rs:360-361).
- On ext4 a directory deleted and recreated at the same path can get the same inode, so the plan id and the fresh check both pass and the new directory is deleted. Blast radius: same path, same kind, inside a reviewed root, and not $HOME or a mount (delete.rs:220, explorer_selection.rs:230). For cache/build kinds this deletes a regenerable dir; for explorer-selection it could delete a dir the user never reviewed.
- Fix: add statx `stx_btime` (where `STATX_BTIME` is reported; dirops.rs:272-290 already calls statx) to ItemIdentity and the plan-id hash, falling back to today's behavior when absent. Document the residual window otherwise. Tests already hold inode numbers to avoid this case (commit 55ccf79), so the limitation is acknowledged in tests but not in user docs; add a line to SECURITY.md.

### 3. LOW - exit hand-off is a filter, not exact, for Safe/Guarded tiers (known)
- handoff.rs:68-71 mints a plan id only when `needs_plan_id()` (selector.rs:473-475: destructive kinds or worktree discard). Safe/Guarded lines carry `--only` as a filter (handoff.rs:93-94 states so), so the paste re-discovers and applies whatever now matches within those kinds, not the exact marked set.
- Also handoff.rs:42-47: `Locator::Docker` yields no path, so a tier of only docker rows gets an empty `--only` and the line selects the whole kind. No test in tests/explore_handoff.rs mentions docker (grep returned nothing). INFERRED that the explorer cannot mark docker items, so likely unreachable; guard it anyway (skip or refuse the line).

### 4. LOW - platform gaps (known), confirm the user-facing messaging
- dirops.rs:317-329 and fiemap/settle/run_state/signals have non-Linux stubs; explorer delete and Steam are Linux-only per owner. `mnt_id` is `None` off Linux, and explorer_selection.rs:199-202 fails closed in that case, so on macOS explorer delete refuses rather than deleting unsafely. Good. RELEASE/README already note it (commit 3566969).

### 5. NIT - `signal(2)` instead of `sigaction` (signals.rs:160-165)
- Fine on Linux/macOS (comment at signals.rs:158 says restart semantics are wanted), but `sigaction` with SA_RESTART is portable and explicit. No action required for 0.1.0.

## Positives (verified by reading)
- delete_tree (delete.rs:171-228): argument validation, parent+name == policy.target, abort flag, sibling marker, dir-only target, identity, witness match, $HOME-chain, cross-device/mount check, all before the first unlink; iterative with bounded open handles; abort errnos (ENOSPC/EDQUOT/EIO) end the run (delete.rs:147-157).
- Capability token minted once, late (explore/apply.rs header lines 1-27); enforced by `check-token-sites.sh --expect-sites 1`.
- Explorer remove (explorer_selection.rs:174-262): fd-relative open, fstat against planned identity twice, root mount id required (fail closed), home-chain check on the opened dir.
- Audit file 0600, flock run lock 0600, sync on state writes.

## Not done
- No cargo-audit/cargo-deny run (not asked, tools not checked). No real filesystem delete was exercised; tests use fixtures only.
- Finding 1 not reproduced (needs root).
