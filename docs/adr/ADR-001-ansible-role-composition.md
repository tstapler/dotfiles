# ADR-001: Ansible Role Composition — Prefer Roles-List Ordering Over Tag Coupling and Meta-Dependencies

**Date**: 2026-06-18
**Status**: Proposed
**Deciders**: Tyler Stapler

## Context

The bootstrap playbook (`bootstrap/playbook.yml`) grew two roles with a real
prerequisite relationship:

- **`github`** — generic SSH key generation, `gh` authentication, and key
  registration. Needed by *every* machine.
- **`fbg`** — FBG-specific layering: SSH host aliases (`github.com` = work,
  `github-personal` = personal), the work git identity, and cloning the private
  `dotfiles-fbg` repo. Depends on the keys/auth that `github` produces.

These were originally developed in parallel on two machines and duplicated key
generation and registration logic. After consolidating that logic into the
`github` role, a question remained: **how should `fbg`'s dependency on `github`
be expressed**, given that `github` must also run standalone for all machines —
and such that tag-scoped runs (`--tags fbg`, `--tags github`) behave sensibly?

Ansible offers several composition mechanisms with subtly different
deduplication and tag-inheritance semantics, so the choice needed to be
deliberate and documented.

## Decision

Express the prerequisite via **roles-list ordering**: keep `github` as a
top-level role listed **before** `fbg` in `playbook.yml`. Roles run in listed
order (dependencies first), so a full bootstrap always runs `github` then `fbg`.

Shared values (`github_primary_key`, `github_personal_key`) live in the
`github` role's `defaults/main.yml` and are referenced by `fbg`'s SSH config, so
the two roles agree on key paths without `fbg` re-deriving them.

Tag behavior: `--tags github` runs the generic setup; `--tags fbg` runs only the
FBG layer (assuming a prior full run set up keys); `--tags github,fbg` runs both
for a scoped combined run. This is documented in the `fbg` role header.

## Rationale

- **Single execution.** A full run executes `github` exactly once. The
  meta-dependency approach double-ran it (see Alternatives).
- **Loose coupling.** The Ansible docs explicitly advise keeping roles loosely
  coupled and avoiding unnecessary dependencies. Ordering expresses the
  prerequisite without `github` having to know `fbg` exists (no `fbg` tag inside
  `github`, no `meta` edge).
- **Matches the real workflow.** Fresh machines are provisioned by a full
  `run.sh` (no tags), where ordering already guarantees `github` → `fbg`.
  Standalone `--tags fbg` is only used for incremental FBG-only changes, where
  the base keys already exist.
- **Idiomatic key sharing.** Putting shared key paths in role `defaults` is the
  standard precedence-friendly way to share values across roles.

## Alternatives Considered

| Option | Rejected because |
|--------|------------------|
| **`meta/main.yml` dependency** (`fbg` depends on `github`) | Tags *do* inherit to dependencies, so `--tags fbg` correctly pulled `github` in. But because `github` is *also* a top-level role, dedup did not merge the two references (different effective tags), so `github` ran **twice** on a full bootstrap — wasteful and confusing. Verified via `--list-tasks` (26 vs 13 task lines). |
| **Dual-tagging `github` tasks `[github, fbg]`** | Makes `--tags fbg` self-sufficient with single execution, but couples the generic `github` role to `fbg`'s tag — `github` shouldn't have to know about its consumers. Acceptable but less clean. |
| **`include_role`/`import_role` from inside `fbg`** | `import_role`/`include_role` do **not** accept role params (only `vars:`, which leak to play scope), and this still wouldn't run `github` for non-FBG machines — a top-level entry would remain, reintroducing the double-reference. |
| **Parameterized `github` invoked per account via `roles:` params + `allow_duplicates`** | Cleanest in theory (one generic "register key for account X" role called per account), but a larger refactor than warranted for two accounts; deferred as possible future work. |

## Consequences

- **Trade-off accepted:** `--tags fbg` run *standalone on a never-bootstrapped
  machine* will not generate keys — it assumes a prior full run. Mitigated by
  documenting `--tags github,fbg` for scoped combined runs, and by the fact that
  initial setup is always a full `run.sh`.
- **Convention established:** prerequisite relationships between bootstrap roles
  are expressed by **ordering in the `roles:` list**, not by `meta`
  dependencies or cross-role tags. Future roles should follow this.
- **Cross-role shared values** belong in the providing role's `defaults/`.
- **Follow-up (optional):** if account-specific key handling proliferates,
  revisit the parameterized-role approach.

## Standard Deviation

None. This repository had no documented role-composition convention; this ADR
establishes one. It aligns with the Ansible roles documentation's guidance on
loose coupling and execution ordering.
