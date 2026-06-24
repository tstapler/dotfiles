# Adversarial Review: git-ssh-fallback (Re-Review Pass 3)

Date: 2026-06-24
Reviewer: Adversarial Architecture Review Pass 3
Previous verdict: BLOCKED (1 blocker — N1: reactive path destroys streaming output)
This verdict: PASS (0 blockers)

---

## Patch Verification: Epic 2.4 Proactive-Always-SSH Strategy

### Prior Blocker N1: Reactive path streaming destruction — RESOLVED

Task 2.4.1b replaced the reactive stderr-capture-and-retry approach with a proactive
strategy: for non-gh-managed hosts, probe `_detect_ssh_agent()` before any git invocation.
If a live agent is found, emit FallbackWarning, inject ConfigInjection, exec `RealGit "$@"`
with SSH rewriting directly. No HTTPS attempt, no stderr buffering, no temp files, no double
invocation.

This is a clean resolution. The streaming destruction concern arose because capturing stderr
from a subprocess while forwarding stdout live requires non-trivial fd plumbing in POSIX sh.
The proactive path avoids this entirely by making the routing decision before exec.
The rejected Approach B concern (buffering breaks progress output) no longer applies to
Epic 2.4.

Prior concerns N2 (reactive exit-128 non-auth stderr buffered) and N4 (reactive retry
SSH agent probe adds unbounded latency) were both artifacts of the reactive approach.
Both are eliminated by this change.

BLOCKER N1: RESOLVED. No new blockers introduced.

---

## Assessment: New Correctness Issues in Proactive-Always-SSH Path

### CONCERN: GitHub Enterprise Server instances are misclassified as non-gh-managed

Task 2.4.1a hardcodes `GH_MANAGED_HOSTS="github.com gist.github.com"` plus the user-
supplied `GIT_SSH_FALLBACK_GH_HOSTS` env var. GitHub Enterprise Server (GHES) deployments
use custom hostnames (e.g., `git.company.com`). `gh` fully manages these when configured
via `gh auth login --hostname git.company.com`. Under the current plan, a GHES host not
listed in `GIT_SSH_FALLBACK_GH_HOSTS` takes the non-gh path (proactive SSH if agent
present), bypassing the `gh auth token` check entirely.

Consequence: A developer with a live SSH agent and HTTPS credentials for a GHES host
always gets SSH routing even when HTTPS would work. This is silent and not warned beyond
the FallbackWarning. The user may not know the routing decision was made, and SSH may fail
if their SSH key is not enrolled on that GHES instance.

The plan requires the user to manually populate `GIT_SSH_FALLBACK_GH_HOSTS` for every GHES
instance. This is a documentation gap and a likely misconfiguration vector.

Severity: CONCERN (not a blocker — the fallback on no-agent path to vanilla HTTPS catches
the hard case; SSH failure is a recoverable error message, not a hang or data loss).

Mitigation path: Query `gh auth status --hostname "$host"` exit code to detect GHES
management, or document that GHES hostnames must be explicitly added to
`GIT_SSH_FALLBACK_GH_HOSTS`. A task for this documentation is missing.

### CONCERN (inherited, unchanged): `GIT_SSH_FALLBACK_GH_HOSTS` injection risk — N3

Task 2.4.1a defines `GH_MANAGED_HOSTS` as a space-separated env var. The
`_is_gh_managed_host()` implementation is not specified beyond "returns 0 if host is in
the list." If the implementation uses an unquoted `case` pattern or `echo "$list" | grep`
without `-F -w`, glob metacharacters in the env var (`github.com*`, `*.com`) could produce
false positives, preventing SSH fallback for unexpected hosts. If the implementation uses
`eval` or unquoted expansion, it is a code-injection vector.

Required resolution before implementation: specify `_is_gh_managed_host()` uses exact
word-boundary matching only (e.g., `case "$host" in $(echo "$GH_MANAGED_HOSTS" | tr ' ' '|'))`
is unsafe; a POSIX-safe loop with `[ "$host" = "$candidate" ]` is required).

---

## Surviving Issues From Prior Reviews (Unpatched, Unchanged Severity)

### CONCERN: `set -euf` silent breakage on optional-failure paths — C1

`set -euf` at the top of the script causes silent exit on any unguarded non-zero return.
Optional-failure operations (Task 2.2.1a's `find "$cache_file" -mmin -5 | grep -q .`,
Task 1.3.1b's `git remote get-url`, the SSH agent liveness chain) must use `|| true`
guards or a `set +e` subshell scope. No task specifies this. With the proactive path in
Epic 2.4 adding more conditional branches, the risk surface is larger than in Pass 2.

### CONCERN: `GIT_CONFIG_COUNT` clobber — C2

Tasks 2.3.1a and 2.4.1b both set `GIT_CONFIG_COUNT=1` unconditionally. Pre-commit
hooks and other tools (lefthook, husky, devtools) may set `GIT_CONFIG_COUNT` before
invoking git. The wrapper drops existing config entries silently. The fix (read current
count, offset by it, increment) is straightforward but unplanned.

### CONCERN: `remote update` host extraction unhandled — C3

`remote update` is in `NETWORK_SUBCOMMANDS` but Epic 1.3 only handles clone and
fetch/push/pull. `remote update` takes a group name or `--all`, not a single remote.
`git remote get-url <group-name>` fails, and under `set -e` this kills the wrapper.
Still unresolved.

### CONCERN: Submodule latency multiplication — C4

`--recurse-submodules` triggers N parallel wrapper invocations with simultaneous AuthCache
misses. No throttle, no documentation. Still unresolved.

### CONCERN: IDE integration gap — C5

VSCode `git.path` and JetBrains use absolute git binary paths, bypassing PATH. No story,
task, or documentation note covers this. Still unresolved.

### MINOR: `StrictHostKeyChecking=accept-new` security downgrade — M1

Task 2.3.1b sets `accept-new` without justification against the requirements constraint
that SSH keys for target hosts must already be configured. Still unresolved.

### MINOR: `--self-test` shallow coverage — M2

Three trivial assertions; auth cache, SSH agent, ConfigInjection not exercised.
Still unresolved.

### MINOR: ADR files in inventory, no tasks assigned — M3

ADR-002 and ADR-003 listed in file inventory with no implementing tasks. Still unresolved.

### MINOR: FallbackWarning message inconsistency — M4

requirements.md uses `[git-ssh-fallback] gh auth not found for HOST, falling back to SSH`;
plan uses `warning: falling back to SSH (gh not authenticated for HOST)`. Still unresolved.

### MINOR: No PATH-order validation at deploy time — M5

No task verifies `~/.local/bin` precedes `/usr/bin` in PATH post-deploy. Still unresolved.

---

## Summary Table

| # | Issue | Severity | Status |
|---|-------|----------|--------|
| B1 | `gh auth token` Keychain timeout | BLOCKER | RESOLVED (Pass 2) |
| B2 | SSH agent liveness not validated | BLOCKER | RESOLVED (Pass 2) |
| B3 | Reactive safety net absent | BLOCKER | RESOLVED (Pass 2) |
| N1 | Reactive path destroys streaming output | BLOCKER | RESOLVED (Pass 3) |
| N2 | Reactive path exit-128 non-auth stderr buffered | CONCERN | ELIMINATED (reactive path removed) |
| N4 | Reactive retry adds unbounded latency | CONCERN | ELIMINATED (reactive path removed) |
| N3 | `GIT_SSH_FALLBACK_GH_HOSTS` injection risk | CONCERN | UNPATCHED |
| P1 | GHES hostnames misclassified as non-gh-managed | CONCERN | NEW (Pass 3) |
| C1 | `set -euf` silent breakage on optional-failure paths | CONCERN | UNPATCHED |
| C2 | `GIT_CONFIG_COUNT` clobber | CONCERN | UNPATCHED |
| C3 | `remote update` host extraction unhandled | CONCERN | UNPATCHED |
| C4 | Submodule latency unaddressed | CONCERN | UNPATCHED |
| C5 | IDE integration gap | CONCERN | UNPATCHED |
| M1 | `StrictHostKeyChecking=accept-new` | MINOR | UNPATCHED |
| M2 | `--self-test` shallow coverage | MINOR | UNPATCHED |
| M3 | ADR files unassigned | MINOR | UNPATCHED |
| M4 | FallbackWarning message inconsistency | MINOR | UNPATCHED |
| M5 | No PATH-order validation at deploy | MINOR | UNPATCHED |

Blockers: 0
Concerns: 7 (1 new — P1; 1 inherited unpatched — N3; 4 inherited unpatched — C1–C5 minus C5=5... see table; 2 eliminated)
Minors: 5 (all inherited, unpatched)

---

## Verdict

PASS. The proactive-always-SSH strategy for non-gh-managed hosts correctly resolves the
streaming destruction blocker. No new blockers are introduced. The proactive path is
architecturally sound: a single exec path, no subprocess output capture, no streaming
side effects, clear fallback semantics when no agent is present.

The 7 unresolved concerns and 5 minors from prior reviews remain acceptable for initial
implementation given the personal-dotfiles scope and single-user rollout. They should be
addressed in follow-up iterations before any multi-user distribution.

Required before implementation starts:
1. Specify `_is_gh_managed_host()` as exact-match only (no glob, no eval) — N3.
2. Add `|| true` guards on all optional-failure operations under `set -euf` — C1.
3. Document GHES hostname manual enrollment in `GIT_SSH_FALLBACK_GH_HOSTS` — P1.
