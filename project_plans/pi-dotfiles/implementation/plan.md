# Implementation Plan: pi-dotfiles

**Feature**: Fork-pin-review governance, ownership ledger, and gated rollout of Pi extensions/credential providers on top of the already-working Pi bootstrap and tiered-config renderer.
**Date**: 2026-09-14
**Status**: Ready for implementation
**ADRs**: ADR-001 (Extension Fork-Pin-Review Manifest & Enforcement Gate), ADR-002 (Credential Provider Approach). No ADR for tiered-config merge semantics — already fully specified in `.config/pi/README.md` and implemented/tested in `stapler-scripts/llm-sync/src/targets/tiered_config.py` (`TieredJsonConfig`) and `stapler-scripts/llm-sync/src/sources/pi_config.py` (`PiConfigSource`).

---

## Baseline already in place (do not rebuild)

Before scoping new work, this is what the codebase already does — verified by reading the code and its tests, not assumed:

- **Pi installation**: `bootstrap-pyinfra/deploys/pi.py` (`plan_pi_install`) implements `auto`/`managed`/`external` install modes and never replaces a work-managed Pi. Pinned at `pi_install_version = "0.84.4"` in `bootstrap-pyinfra/group_data/all.py`.
- **Tiered config rendering**: `PiConfigSource.load()` (`stapler-scripts/llm-sync/src/sources/pi_config.py`) deep-merges `config.json` → `config.d/*.json` → `config.local.json` → `config.local.d/*.json`, renders stable-ID `packages`/`extensions`/`skills`/`prompts`/`themes` registries, rejects credential-shaped keys anywhere in the tree, and enforces exact-commit `tstapler`-fork or exact-version `@tstapler` pins (`trustedPackageScopes` exempts work scopes). Fully covered by `test_pi_config.py`.
- **Ownership-safe writes**: `PiSettingsTarget.save()` (`stapler-scripts/llm-sync/src/targets/pi_settings.py`) tracks a `managedKeys` ledger so re-renders only touch keys dotfiles own, preserving unmanaged/Pi-generated `settings.json` state. Covered by `test_pi_settings_target.py`.
- **Bootstrap wiring**: `bootstrap-pyinfra/main.py` runs `pi()` then, later, `llm_sync()` (`bootstrap-pyinfra/deploys/llm_sync.py`), which shells out to `stapler-scripts/llm-sync/main.py` — already idempotent and dry-run-capable (`--dry-run`, `--pi-dir`, `--pi-config-file`, etc., in `src/cli.py`).
- **Skills/prompts sync**: `PiTarget` (`stapler-scripts/llm-sync/src/targets/pi.py`) — regression anchor per requirements, untouched by this plan.
- **Tiered-config-pattern skill**: `.claude/skills/tiered-configuration/SKILL.md` already documents and enforces the config.d model (success metric 9 is already met).
- **First-party extensions**: kibitzer, ponytail, dotfiles-hooks are already wired via `.config/pi/config.d/{10,20,30}-*.json`.

What is genuinely missing, and what this plan builds: a **fork-pin-review manifest and enforcement gate** (no third-party extension may render without one), an **ownership ledger for on-disk package artifacts** (today's ledger only covers `settings.json` top-level keys), the **sequenced, human-gated fork-and-enable work** for the Tier 1+ candidates from the research docs, **credential-provider wiring**, and the **rollout/rollback runbook** the requirements' Risk Control section calls for.

---

## Step 0.5 — Creative pass: shape of the fork-review-pin pipeline

1. **Fully automated fork+pin tooling** — one command forks the upstream repo, captures the commit, writes the manifest entry, and flips it to enabled. *Strength*: fastest path from candidate to running code. *Weakness*: automates away the one step the requirements explicitly reserve for a human (the security review and go/no-go decision), which is exactly the "silently fork/auto-install" failure mode the requirements forbid.
2. **Manual-review checklist + declarative config renderer, no automation of fork mechanics** — Tyler runs `gh repo fork` and hand-writes the manifest JSON entry per a checklist; a validator only checks the result. *Strength*: keeps the highest-risk step unambiguously human. *Weakness*: repetitive, error-prone toil (typing commit SHAs, JSON structure already schema-defined elsewhere) invites drift from the schema `PiConfigSource` already enforces for everything else.
3. **Hybrid: scripted scaffolding for the mechanical parts, gated behind a field only a human can write** — a helper script runs `gh repo fork`, captures the commit, and writes a `candidate` manifest entry; the script has no code path that can write `disposition: "approved"` — only a human hand-edits that field (and the paired `approved_by`/`approved_date`) as a separate, reviewable git change. *Strength*: removes boring, error-prone toil while making the actual review non-skippable and auditable (approval is a diff Tyler authors, not a flag a script sets). *Weakness*: a scripted helper can create a false sense of completeness if someone pastes boilerplate into the required `notes` field instead of doing real review — mitigated by, not eliminated by, tooling.

**Chosen: approach 3 (hybrid).** It matches the codebase's existing philosophy — `PiConfigSource` already proves the preferred fix for "don't do X" is executable validation, not prose (see credential-material rejection, pin-format rejection). Approaches 1 and 2 are recorded as rejected alternatives in the Pattern Decisions table below.

---

## Domain Glossary

| Term | Definition | Notes |
|------|-----------|-------|
| Tier | A precedence layer in Pi config resolution (universal base, tracked fragment, local base, local fragment). | Implemented by `TieredJsonConfig`. |
| Config Fragment | One `config.d`/`config.local.d` JSON file, merged in lexical filename order. | |
| Universal Base | `.config/pi/config.json` — tracked, public, applies to every machine. | |
| Machine-Local Override | `~/.config/pi/config.local.json` / `config.local.d/*.json` — untracked. | |
| Resource Registry | A stable-ID-keyed map (`packages`, `extensions`, `skills`, `prompts`, `themes`) rendered by `PiConfigSource` into Pi's native arrays. | |
| Managed Key | A top-level `settings.json` key whose ownership `PiSettingsTarget` tracks via its `managedKeys` state file. | Existing; settings.json scope only. |
| Ownership Ledger | A state file recording which keys/resources dotfiles currently own, so re-renders and removals are safe. | This plan adds a second ledger (Package Ledger) for a different resource class. |
| Package Source | The `source` field of a `packages` registry entry — an npm scope, git fork URL, or local path. | |
| Pin | An exact, immutable reference (commit SHA or exact version) a Package Source must resolve to. | Enforced by `_is_allowed_package_source`. |
| Trusted Package Scope | An entry in the top-level `trustedPackageScopes` array exempting a scope (e.g. a work npm scope) from the fork/pin requirement. | |
| Extension Fork | A `tstapler`-owned GitHub fork of a third-party Pi extension repository, pinned to a reviewed commit. | |
| Extension Manifest | New tracked file `.config/pi/extensions-manifest.json` recording review metadata for every forked/reviewed extension. | Phase 1. |
| Manifest Entry | One record in the Extension Manifest: upstream repo/commit, fork repo/commit, license, reviewer, disposition, notes, approval fields. | Modeled as `ManifestEntry`. |
| Disposition | A Manifest Entry's review status: `candidate`, `hold`, `rejected`, or `approved`. | |
| Approval Gate | The rule that `disposition` can only become `approved` by a human hand-edit — no tool writes that value. | Enforced by Epic 1.3's helper never emitting it. |
| Fork-and-Pin Helper | The scripted scaffolding tool (`fork_pin_extension.py`) that creates the GitHub fork and a `candidate` Manifest Entry, but cannot approve it. | |
| Review Gate Specification | The validation rule (`verify_pinned_sources_reviewed`) that blocks any rendered fork source lacking an `approved` Manifest Entry at the matching commit. | |
| Credential Provider | A Pi extension that resolves secrets at runtime from an OS/desktop credential store without the value passing through tracked config. | e.g. forked `pi-1password`. |
| Credential Material | Any literal secret value (API key, token, password). | Already rejected by `PiConfigSource._reject_credential_material`. |
| Package Ledger | New state file (`PiPackageLedger`) extending the ownership-ledger concept to installed package artifacts on disk, not just `settings.json` keys. | Phase 2. |
| Stale Resource | A previously-managed package/extension artifact no longer declared in any config layer. | |
| Install Mode | `pi_install_mode` (`auto`/`managed`/`external`) controlling whether bootstrap installs, converges, or defers to an externally managed Pi. | Already implemented. |
| Workflow Category | One of the Claude-parity categories from requirements.md (skills/prompts, instructions, hooks, MCP, subagents, settings/UI, session utilities). | |
| Compatibility Matrix | New tracking doc mapping each Claude tool name synced skills use to its Pi status. | Phase 5. |
| Compatibility Shim | A small Tyler-owned Pi extension providing a Claude-named tool alias without requiring a third-party fork. | `pi-claude-compat`. |
| Opt-in Fragment | A tracked `config.d` fragment that registers a resource with `enabled: false`, requiring a machine-local override to activate it. | Staged-rollout mechanism. |

---

## Pattern Decisions

| Component | Pattern Chosen | Source | Alternative Rejected | Reason |
|-----------|---------------|--------|---------------------|--------|
| Fork-review workflow shape | Hybrid scripted scaffold + human-only approval field (Step 0.5 approach 3) | Type-driven design — illegal states unrepresentable | Fully automated fork+pin CLI (approach 1); pure manual checklist with no tooling (approach 2) | Approach 1 automates away the one step requirements demand stay human; approach 2 leaves error-prone, already-schema-defined mechanics fully manual, inviting drift from the schema `PiConfigSource` enforces elsewhere. |
| Fork/pin manifest storage | Registry — stable-ID keyed map, same shape as the existing `packages`/`extensions` registries | PoEAA (Registry) | One manifest file per extension under `project_plans/` | Splitting review state across many files defeats a single grep/validate point; matching the existing registry shape keeps the validator and mental model consistent with `PiConfigSource`. |
| Review Gate Specification | Specification pattern — validate-before-render, extending `PiConfigSource`'s existing credential/pin checks | GoF/DDD Specification | Convention-only documentation (checklist as prose in `extension-audit.md` with no enforcement) | `PiConfigSource` already proves this codebase's answer to "must never happen" is executable validation, not policy text; a prose-only gate is exactly the silent-install failure mode requirements forbid. |
| Config-fragment renderer / merge engine | Existing tiered override chain (`TieredJsonConfig`) — reused unchanged | Existing implementation | A second, extension-specific merge engine | The current engine already deep-merges objects, replaces arrays, and honors `null`-deletes, fully tested; a second engine would fork behavior for no functional gain. |
| Ownership/cleanup tracking for installed packages | External Ownership Ledger (Terraform-state-inspired snapshot), a sibling to the existing `managedKeys` ledger for a different resource class | PoEAA (Memento/Snapshot) | Assume Pi's own package manager garbage-collects unused installs | Unverified — Rabbit Holes explicitly flags this as a risk; treating it as self-cleaning without confirming (Epic 2.1's spike) risks the exact stale-entry problem requirements call out. |
| Credential-provider integration | Adapter — forked `pi-1password` wrapped behind the existing `packages` registry, disabled by default | GoF Adapter | Build a custom Tyler-owned credential extension from scratch | The research doc identifies `jmcombs/pi-1password` as the closest fit to the desired desktop-store model already; building new re-solves native-keyring/OAuth-adjacent risk the fork review already scopes. |
| Staged rollout / dry-run | Feature toggle via the existing `enabled` registry flag + tier-ordered promotion checklist | Existing implementation / Fowler feature toggle | A separate environment-variable rollout flag mechanism | A second, untyped flag would bypass the schema validation `PiConfigSource` already performs on the registry it would duplicate. |

---

## Tech Debt Disposition

| Area | Existing Issue | Disposition | Justification |
|------|----------------|--------------|----------------|
| llm-sync Pi package lifecycle | `PiSettingsTarget`'s ownership ledger (`managedKeys`) tracks only `settings.json` top-level keys, not on-disk package/extension artifacts Pi itself installs when a `packages` entry activates. Not a defect — narrower scope than this plan now needs. | Extend via a new sibling class (`PiPackageLedger`, Phase 2) rather than widen `PiSettingsTarget`. | `PiSettingsTarget` is tested and correct for its original scope; adding a second ownership model to one class would conflate two different resource kinds (settings keys vs. filesystem artifacts) in one abstraction. |
| Everything else | None identified. | — | No `research/architecture.md` exists for this project — it is new tooling, not an existing hotspot. `extension-audit.md` and `full-featured-profile-research.md` are intake/review docs, not an architecture hotspot report. |

---

## Migration Plan

Not N/A: the current macOS machine's `~/.pi/agent/settings.json` already contains a work-owned package and work-specific provider/model defaults mixed with universal preferences (per requirements.md Baseline). Before the first managed sync overwrites any `managedKeys`-tracked key on that machine:

1. Back up the current file (Story 5.2.1).
2. Classify every existing top-level key as universal / work-only / machine-generated (Story 5.2.2) — this closes the open question "which existing `~/.pi/agent` settings are universal vs. work-only vs. machine-generated."
3. Only keys classified universal are candidates for `.config/pi/config.json`; work-only keys move to the work overlay; machine-generated keys (sessions, auth, trust, package caches) are never touched — `PiConfigSource`/`PiSettingsTarget` already exclude them by only ever owning declared `managedKeys`.

## Observability Plan

- **Logs**: `llm_sync()` (`bootstrap-pyinfra/deploys/llm_sync.py`) already prints `main.py`'s full stdout, which itself reports per-resource install/update/disable/skip decisions via `rich.Console`. Phase 1/2 additions (manifest rejections, stale-package reports) extend the same stream with entry-id-named messages, matching the existing `PiConfigError`/`PiSettingsTargetError` style of naming the offending key.
- **Metrics**: none — this is local bootstrap automation, not an online service (per requirements.md Observability Requirements).
- **Alerts**: none. Failures surface as a non-zero-exit `DeployError` that halts the pyinfra run, exactly as `deploys/pi.py` already does for install failures.

## Risk Control

- **Feature flag**: every new resource (permission system, subagents, plan mode, compat shim, hooks bridge, credential provider) ships in its own opt-in `config.d` fragment with `enabled: false`; activation requires a machine-local override, mirroring the existing `enabled` mechanism `PiConfigSource` already validates.
- **Rollback procedure**: documented in `project_plans/pi-dotfiles/implementation/rollout-runbook.md` (Epic 5.1/5.2) — restore the pre-adoption `settings.json` backup; rollback never touches `~/.pi/agent/auth.json`, sessions, or trust state because those are never `managedKeys`.
- **Staged rollout**: matches requirements.md's five-step Risk Control list exactly — dry-run/temp-dir validation (Story 5.1.1) → backup/inventory (Story 5.2.1/5.2.2) → adopt+verify on current macOS machine (per-extension Story `.2` tasks, e.g. 3.2.2) → verify idempotent re-run and rollback (Story 5.2.1) → roll out to Linux families (after macOS verification, no separate story — same tooling, re-run of Story 5.1.1's runbook).

## Unresolved Questions

- [ ] Where exactly does Pi write installed-package artifacts under `~/.pi`, and does Pi prune them itself when an entry is removed from `settings.json`? — blocks Story 2.1.1 — owner: Tyler (requires a manual temp-`HOME` observation; no doc currently states this).
- [ ] Which of the current macOS machine's existing `~/.pi/agent/settings.json` top-level keys are universal vs. work-only vs. machine-generated? — blocks Story 5.2.2 and, transitively, the Migration Plan's step 3 — owner: Tyler.
- [ ] Does the missing standalone `LICENSE` file for `hsingjui/pi-hooks` (and `fractary/pi-claude-code`, `nicobailon/pi-interactive-shell`) get resolved by an upstream PR, an explicit written grant, or a decision to build a Tyler-owned replacement instead? — blocks Story 3.5.1 — owner: Tyler.
- [ ] Should `fork_pin_extension.py` fork into a dedicated `tstapler` GitHub organization or the personal `tstapler` namespace? — blocks Task 1.3.1a — owner: Tyler.

## Dependency Visualization

```
Phase 1: Fork-Pin-Review Governance
  (manifest schema, gate validator, helper script, review skill)
        |
        +---------------------+---------------------+
        v                     v                     v
Phase 3: Gated          Phase 4: Credential    Phase 2: Ownership
 Extension Rollout        Provider (1Password)   Ledger (package
 (permissions/subagents,                          lifecycle spike +
  plan mode, compat shim,                          stale cleanup)
  hooks bridge)
        |                     |                     |
        +----------+----------+---------------------+
                    v
        Phase 5: Validation, Rollback, Documentation
         (runbook, backup/rollback, compat matrix, doc sync)
```

---

## Phase 1: Fork-Pin-Review Governance

### Epic 1.1: Extension Manifest Schema & Storage
**Goal**: Create the tracked Extension Manifest file and its loader so review records have one canonical, validated home, mirroring the shape of the existing `packages`/`extensions` registries.

#### Story 1.1.1: Tracked manifest file with a defined schema
**As** the dotfiles maintainer, **I want** a tracked extensions manifest file with a defined schema, **so that** every forked/reviewed Pi extension has one auditable record.

**Acceptance Criteria**:
- The manifest file exists and starts as an empty, schema-valid registry.
  - *Given* a fresh clone of the repo, *When* `.config/pi/extensions-manifest.json` is read as JSON, *Then* it parses to `{"extensions": {}}`.
- A `ManifestEntry` loader rejects an entry missing required fields.
  - *Given* a `ManifestEntry` dict for id `gotgenes-pi-permission-system` missing `upstream_commit`, *When* `ExtensionManifestSource.load()` parses it, *Then* it raises `ManifestError` naming the entry id and the missing field.

**Files**: `.config/pi/extensions-manifest.json`, `stapler-scripts/llm-sync/src/sources/extension_manifest.py`, `stapler-scripts/llm-sync/test_extension_manifest.py`

##### Task 1.1.1a: Create the manifest file (~2 min)
- Create `.config/pi/extensions-manifest.json` with `{"extensions": {}}`.
- Files: `.config/pi/extensions-manifest.json`

##### Task 1.1.1b: Define `ManifestEntry` (~5 min)
- Add a frozen dataclass with fields: `id`, `capability`, `upstream_repo`, `upstream_commit`, `license`, `fork_repo`, `fork_commit`, `package_paths`, `disposition`, `reviewer`, `review_date`, `notes`, `approved_by`, `approved_date`.
- Files: `stapler-scripts/llm-sync/src/sources/extension_manifest.py`

##### Task 1.1.1c: Write `ExtensionManifestSource.load()` (~5 min)
- Validate required fields per entry; raise `ManifestError` naming the entry id and missing field.
- Files: `stapler-scripts/llm-sync/src/sources/extension_manifest.py`

##### Task 1.1.1d: Write initial tests (~5 min)
- Cover valid load and missing-field rejection.
- Files: `stapler-scripts/llm-sync/test_extension_manifest.py`

#### Story 1.1.2: Illegal manifest states are unrepresentable
**As** the dotfiles maintainer, **I want** the manifest to enforce the "approved requires approver" invariant in code, **so that** illegal manifest states can't be created by accident.

**Acceptance Criteria**:
- An `approved` entry with no `approved_by` is rejected.
  - *Given* a `ManifestEntry` for id `narumiruna-pi-plan-mode` with `disposition: "approved"` and `approved_by: null`, *When* `ExtensionManifestSource.load()` parses it, *Then* it raises `ManifestError` stating approved entries require `approved_by` and `approved_date`.
- A `candidate` entry with no `approved_by` loads successfully.
  - *Given* the same entry with `disposition: "candidate"` and `approved_by: null`, *When* loaded, *Then* it returns a `ManifestEntry` with `disposition == "candidate"`.

**Files**: `stapler-scripts/llm-sync/src/sources/extension_manifest.py`, `stapler-scripts/llm-sync/test_extension_manifest.py`

##### Task 1.1.2a: Add the invariant check (~3 min)
- Files: `stapler-scripts/llm-sync/src/sources/extension_manifest.py`

##### Task 1.1.2b: Add the two GWT-derived tests (~4 min)
- Files: `stapler-scripts/llm-sync/test_extension_manifest.py`

### Epic 1.2: Manifest Enforcement in llm-sync
**Goal**: Wire the manifest into the existing Pi settings sync so a pinned fork source can never render into `settings.json` without a matching `approved` Manifest Entry at the exact same commit.

#### Story 1.2.1: Sync refuses unreviewed fork sources
**As** Tyler, **I want** `sync_pi_settings` to refuse to write settings when a config.d fork source has no approved manifest entry at that exact commit, **so that** no third-party extension activates without recorded human approval.

**Acceptance Criteria**:
- An unreviewed fork source blocks the sync.
  - *Given* a `LoadedPiConfig` whose `packages` registry includes `git:github.com/tstapler/pi-permission-system@abc1234` and an `ExtensionManifest` with no entry for that fork/commit pair, *When* `verify_pinned_sources_reviewed()` runs, *Then* it raises `PiConfigError` naming the unreviewed source `git:github.com/tstapler/pi-permission-system@abc1234`.
- A matching approved entry at the exact commit passes.
  - *Given* the same `packages` entry and a manifest entry with `fork_commit: "abc1234"` and `disposition: "approved"`, *When* `verify_pinned_sources_reviewed()` runs, *Then* it returns without raising.
- A stale approval (approved at a different commit than the one now configured) still blocks.
  - *Given* a `packages` entry pinned at `def5678` and a manifest entry approved at `abc1234`, *When* `verify_pinned_sources_reviewed()` runs, *Then* it raises `PiConfigError` naming the mismatched commit.
- An entry that exists but is not approved still blocks — presence alone is not enough.
  - *Given* a `packages` entry pinned at `abc1234` and an existing manifest entry at that exact commit with `disposition: "hold"` (and, separately, `disposition: "rejected"`), *When* `verify_pinned_sources_reviewed()` runs, *Then* it raises `PiConfigError` naming the source and its non-approved disposition, for both dispositions.
- Commit comparison is case-insensitive; the manifest `fork_commit` and the config pin must otherwise match exactly — a prefix/abbreviated SHA in one that isn't byte-identical to the other, after case-folding, is treated as a mismatch, not a match.
  - *Given* a manifest entry with `fork_commit: "ABC1234"` and a `packages` entry pinned at `abc1234` (and, separately, the reverse casing), *When* `verify_pinned_sources_reviewed()` runs, *Then* both pass without raising — this is a stated, tested comparison rule, not an assumption inherited from `_is_allowed_package_source`'s bare regex match.
  - *Given* a manifest entry with `fork_commit: "abc1234def5678901234567890123456789012ab"` (full 40-char SHA) and a `packages` entry pinned at `abc1234` (its 7-char abbreviation), *When* `verify_pinned_sources_reviewed()` runs, *Then* it raises `PiConfigError` — a short-vs-long pair is a mismatch even though one is a true prefix of the other, since this gate does not implement prefix/length-tolerant matching.
- A duplicate manifest entry id is rejected at load time, before the gate ever runs.
  - *Given* `.config/pi/extensions-manifest.json` with two entries that resolve to the same id `gotgenes-pi-packages`, *When* `ExtensionManifestSource.load()` parses it, *Then* it raises `ManifestError` naming the duplicate id.

**Files**: `stapler-scripts/llm-sync/src/sources/extension_manifest.py`, `stapler-scripts/llm-sync/src/cli.py`, `stapler-scripts/llm-sync/test_extension_manifest.py`, `.github/workflows/ci.yml`

##### Task 1.2.1a: Add `verify_pinned_sources_reviewed()` (~5 min)
- Scans rendered `packages`/`extensions` values for `github.com/tstapler/` fork sources and checks each against the manifest.
- Files: `stapler-scripts/llm-sync/src/sources/extension_manifest.py`

##### Task 1.2.1b: Call it from `sync_pi_settings()` (~4 min)
- After `PiConfigSource.load()`, before `PiSettingsTarget.save()`.
- Files: `stapler-scripts/llm-sync/src/cli.py`

##### Task 1.2.1c: Add the three baseline GWT tests (~5 min)
- No-entry blocks; exact-match passes; commit-mismatch blocks.
- Files: `stapler-scripts/llm-sync/test_extension_manifest.py`

##### Task 1.2.1d: Add `--pi-extensions-manifest` CLI override (~4 min)
- Mirrors the existing `--pi-config-file`-style flags; default `.config/pi/extensions-manifest.json`.
- Files: `stapler-scripts/llm-sync/src/cli.py`

##### Task 1.2.1e: Add the hold/rejected-present and case-insensitive/exact-match commit comparison GWT tests (~5 min)
- Covers: entry present with `disposition: "hold"` blocks; entry present with `disposition: "rejected"` blocks; uppercase manifest `fork_commit` vs. lowercase config pin passes; lowercase manifest `fork_commit` vs. uppercase config pin passes; a full 40-char manifest `fork_commit` vs. its own 7-char prefix as the config pin is correctly treated as a MISMATCH (proves the comparison is exact-after-case-fold, not prefix-tolerant).
- Files: `stapler-scripts/llm-sync/test_extension_manifest.py`

##### Task 1.2.1f: Add the duplicate-manifest-id-at-load-time GWT test (~3 min)
- Extends `ExtensionManifestSource.load()`'s existing required-field validation (Task 1.1.1c) with a duplicate-id check; test lives alongside the other `verify_pinned_sources_reviewed()` coverage since it protects the same gate.
- Files: `stapler-scripts/llm-sync/src/sources/extension_manifest.py`, `stapler-scripts/llm-sync/test_extension_manifest.py`

##### Task 1.2.1g: Wire `make llm-sync-test` into the CI gate (~4 min)
- Add a step running `make llm-sync-test` to `.github/workflows/ci.yml`'s `test` job (or a sibling job), and add `stapler-scripts/llm-sync/**` and `.config/pi/**` to the workflow's `paths` triggers, so a regression in `verify_pinned_sources_reviewed()` or the manifest loader fails CI instead of only a local run. `make llm-sync-test` (Makefile:40) already exists and runs every `test_*.py` under `stapler-scripts/llm-sync`; it is not currently invoked by any workflow (VERIFIED: no match for `llm-sync` in `.github/workflows/ci.yml` as of this plan).
- Files: `.github/workflows/ci.yml`

#### Story 1.2.2: Work/Tyler-owned exemptions carry through
**As** Tyler, **I want** work-owned and Tyler-owned package sources exempted from the manifest gate, matching the existing `trustedPackageScopes`/`@tstapler` exemptions, **so that** the gate only ever blocks third-party forks, per requirements' explicit carve-out.

**Acceptance Criteria**:
- A `trustedPackageScopes`-listed source needs no manifest entry.
  - *Given* a `packages` entry `npm:@work-org/pi-tool@2.3.0` and `trustedPackageScopes: ["npm:@work-org"]`, *When* `verify_pinned_sources_reviewed()` runs, *Then* it does not raise even with an empty manifest.
- A `@tstapler`-scoped source is exempted the same way.
  - *Given* `npm:@tstapler/pi-claude-compat@1.0.0`, *When* checked, *Then* it is not required to appear in the manifest.

**Files**: `stapler-scripts/llm-sync/src/sources/extension_manifest.py`, `stapler-scripts/llm-sync/test_extension_manifest.py`

##### Task 1.2.2a: Restrict the scan to `github.com/tstapler/`-fork-shaped sources only (~3 min)
- Files: `stapler-scripts/llm-sync/src/sources/extension_manifest.py`

##### Task 1.2.2b: Add exemption tests (~4 min)
- Files: `stapler-scripts/llm-sync/test_extension_manifest.py`

### Epic 1.3: Fork-and-Pin Helper Script
**Goal**: Script the mechanical, safe parts of forking and pinning — never the approval itself.

#### Story 1.3.1: Scripted fork-and-scaffold, no approval path
**As** Tyler, **I want** a CLI that forks an upstream Pi extension repo and scaffolds a `candidate` manifest entry, **so that** I don't hand-type commit SHAs and JSON structure for every review.

**Acceptance Criteria**:
- Running the script creates a fork and a `candidate` manifest entry with the fork's current commit.
  - *Given* upstream `gotgenes/pi-packages` and no existing manifest entry `gotgenes-pi-packages`, *When* `uv run fork_pin_extension.py fork gotgenes/pi-packages --id gotgenes-pi-packages --capability "permission-system,subagents"` runs, *Then* `.config/pi/extensions-manifest.json` gains an entry with `disposition: "candidate"`, `fork_repo: "github.com/tstapler/pi-packages"`, and `fork_commit` set to the SHA `gh repo fork` produced.
- The script has no code path that can set `disposition: "approved"`.
  - *Given* the script's argument parser, *When* inspected for subcommands/flags, *Then* no flag accepts or writes the literal value `"approved"` to the `disposition` field.

**Files**: `stapler-scripts/llm-sync/scripts/fork_pin_extension.py`, `stapler-scripts/llm-sync/test_fork_pin_extension.py`

##### Task 1.3.1a: Write the `fork` subcommand (~5 min)
- uv inline-script, typer CLI per the `python-scripting` skill's conventions; calls `gh repo fork <upstream> --org tstapler --default-branch-only` and captures the resulting commit via `gh api`.
- Files: `stapler-scripts/llm-sync/scripts/fork_pin_extension.py`

##### Task 1.3.1b: Add manifest-skeleton writing (~5 min)
- `disposition` always `"candidate"`; `approved_by`/`approved_date` always `null`; reuses `ExtensionManifestSource` for validation.
- Files: `stapler-scripts/llm-sync/scripts/fork_pin_extension.py`

##### Task 1.3.1c: Add the no-approval-path test (~4 min)
- Static inspection of the typer app's declared options/subcommands for any `approved`-setting path.
- Files: `stapler-scripts/llm-sync/test_fork_pin_extension.py`

##### Task 1.3.1d: Add `--dry-run` (~3 min)
- Prints the planned fork + manifest diff without calling `gh`.
- Files: `stapler-scripts/llm-sync/scripts/fork_pin_extension.py`

### Epic 1.4: Review Process Skill
**Goal**: Turn `extension-audit.md`'s "Required gate" checklist into a discoverable, reusable skill so no agent (or Tyler, in a hurry) skips a step.

#### Story 1.4.1: A skill documents the gate and points at its enforcement
**As** a future coding agent asked to add a Pi extension, **I want** a skill documenting the fork-pin-review gate, **so that** I never silently enable a third-party extension.

**Acceptance Criteria**:
- The skill names the code that enforces the gate, not just convention.
  - *Given* `.claude/skills/pi-extension-review/SKILL.md`, *When* read, *Then* it names `verify_pinned_sources_reviewed()` in `stapler-scripts/llm-sync/src/sources/extension_manifest.py` as the enforcement point and states that only a human edits `disposition`/`approved_by`/`approved_date`.
- The skill's checklist matches `extension-audit.md`'s seven-step gate.
  - *Given* the skill file, *When* its checklist section is compared to `project_plans/pi-dotfiles/extension-audit.md`'s "Required gate before enabling any candidate" list, *Then* all seven steps are present.

**Files**: `.claude/skills/pi-extension-review/SKILL.md`

##### Task 1.4.1a: Write frontmatter + the seven-step checklist (~5 min)
- Files: `.claude/skills/pi-extension-review/SKILL.md`

##### Task 1.4.1b: Add "how to run the helper + validator" section (~4 min)
- References `fork_pin_extension.py` and `make llm-sync-test`.
- Files: `.claude/skills/pi-extension-review/SKILL.md`

##### Task 1.4.1c: Cross-link from `.config/pi/README.md` (~2 min)
- Files: `.config/pi/README.md`

---

## Phase 2: Ownership Ledger for Installed Resources

### Epic 2.1: Pi Package Lifecycle Spike
**Goal**: Determine, by direct observation, where Pi writes installed-package artifacts and whether it prunes them on its own, before designing cleanup tooling — no fix without a confirmed root cause.

#### Story 2.1.1: Documented, reproducible observation
**As** the dotfiles maintainer, **I want** a documented observation of Pi's package install/removal behavior in a temp Pi home, **so that** cleanup tooling is built on verified fact, not assumption.

**Acceptance Criteria**:
- The spike records the exact filesystem path(s) Pi writes when a `packages` entry activates.
  - *Given* a temp `HOME` with only `~/.local/bin/pi` and a rendered `settings.json` containing one `packages` entry, *When* `pi` is run once non-interactively against that `HOME`, *Then* the spike note records every path created or modified under that `HOME` (via a `find`-diff taken before and after).
- The spike records whether removing the entry and re-running Pi deletes the artifact.
  - *Given* the same temp `HOME` with the artifact present, *When* the entry is removed from `settings.json` and `pi` is re-run, *Then* the note states explicitly whether the artifact was deleted, left in place, or errored.

**Files**: `.config/pi/README.md` (new "Package lifecycle" subsection)

##### Task 2.1.1a: Run the before/after spike (~5 min)
- Manual/Bash in a temp `HOME`; no code file produced by this task.

##### Task 2.1.1b: Write the "Package lifecycle" subsection (~4 min)
- States the observed path(s) and prune behavior as VERIFIED findings, with the exact command used.
- Files: `.config/pi/README.md`

### Epic 2.2: Resource Ownership Ledger & Stale Cleanup
**Goal**: Extend the existing ownership pattern to on-disk artifacts, using Epic 2.1's findings, so stale entries can be reported and safely pruned.

#### Story 2.2.1: `PiPackageLedger` records and reports stale artifacts
**As** Tyler, **I want** a `PiPackageLedger` mirroring `PiSettingsTarget`'s `managedKeys` pattern for on-disk artifacts, **so that** removing an entry from config can be safely followed by removing its artifact.

**Acceptance Criteria**:
- Precondition: Epic 2.1's spike is done and its findings are recorded before any ledger code is written.
  - *Given* `.config/pi/README.md`'s "Package lifecycle" subsection (Task 2.1.1b) does not yet exist and state a VERIFIED artifact path pattern, *When* Task 2.2.1a starts, *Then* it must not proceed.
- A sync records artifact paths for every enabled entry.
  - *Given* a `LoadedPiConfig` with one enabled package `gotgenes-pi-packages` and Epic 2.1's confirmed artifact path pattern, *When* `PiPackageLedger.save(loaded)` runs, *Then* `~/.config/llm-sync/pi-package-state.json` contains `{"gotgenes-pi-packages": "<observed-path>"}`.
- Removing the entry reports it as stale without deleting anything.
  - *Given* a prior ledger containing `gotgenes-pi-packages` and a new sync where that entry is absent/disabled, *When* `PiPackageLedger.find_stale(current_ids)` runs, *Then* it returns `["gotgenes-pi-packages"]` and no file under the artifact path is deleted.
- An explicit prune deletes only ledger-recorded stale artifacts.
  - *Given* the same stale result and a path outside any ledger entry, *When* `PiPackageLedger.prune(stale, dry_run=False)` runs, *Then* only the ledger-recorded stale path is removed and the unmanaged path is untouched.
- A run interrupted between the settings write and the ledger write never permanently orphans the artifact from stale-detection.
  - *Given* a sync where `PiSettingsTarget.save()` succeeds (so `managedKeys`/`settings.json` reflect `gotgenes-pi-packages` as active) but the process is interrupted before `PiPackageLedger.save()` runs, so the ledger has no entry for it, *When* `uv run main.py --target pi --reconcile-pi-package-ledger` runs, *Then* it rebuilds the ledger entry for `gotgenes-pi-packages` by reading the current `settings.json` content for the managed keys plus Epic 2.1's confirmed artifact-path pattern, and a subsequent `find_stale()` does not report it as stale.

**Files**: `stapler-scripts/llm-sync/src/targets/pi_package_ledger.py`, `stapler-scripts/llm-sync/test_pi_package_ledger.py`, `stapler-scripts/llm-sync/src/cli.py`

##### Task 2.2.1a: Write `PiPackageLedger` (~5 min)
- `save`/`find_stale`/`prune`, modeled on `PiSettingsTarget`'s atomic-write pattern. Blocked on Epic 2.1's Task 2.1.1b per this story's precondition AC — do not start until that subsection exists.
- Files: `stapler-scripts/llm-sync/src/targets/pi_package_ledger.py`

##### Task 2.2.1b: Wire `save()` into `sync_pi_settings()` (~4 min)
- After a successful settings write.
- Files: `stapler-scripts/llm-sync/src/cli.py`

##### Task 2.2.1c: Add `--prune-stale-pi-packages` (~4 min)
- Reports stale entries always; deletes only with the flag.
- Files: `stapler-scripts/llm-sync/src/cli.py`

##### Task 2.2.1d: Write the three baseline GWT tests (~5 min)
- Save records paths; removal reports stale without deleting; prune deletes only ledger-recorded paths.
- Files: `stapler-scripts/llm-sync/test_pi_package_ledger.py`

##### Task 2.2.1e: Add `--reconcile-pi-package-ledger` (~5 min)
- Rebuilds ledger entries by reading the current `settings.json` content for the keys present in `managedKeys` (or re-loading the current config via `PiConfigSource.load()`) to recover per-entry package ids, then applying Epic 2.1's confirmed artifact-path pattern — `managedKeys` itself is only the flat set of top-level `settings.json` keys (`PiConfigSource`'s `managed_keys`) and does not enumerate package ids on its own. This recovers a ledger write that never happened (interrupted run, disk full, crash) without re-deriving anything Epic 2.1 didn't already confirm. Cheaper than making the settings and ledger writes transactional, and matches the codebase's existing idempotent-reconciliation philosophy (e.g. `PiSettingsTarget`'s `managedKeys` re-render).
- Files: `stapler-scripts/llm-sync/src/targets/pi_package_ledger.py`, `stapler-scripts/llm-sync/src/cli.py`

##### Task 2.2.1f: Add the interrupted-write-recovery GWT test (~4 min)
- Simulates a ledger write that never ran after a successful settings write, then asserts `--reconcile-pi-package-ledger` recovers the entry and `find_stale()` no longer reports it.
- Files: `stapler-scripts/llm-sync/test_pi_package_ledger.py`

#### Story 2.2.2: Stale reporting surfaces in bootstrap output
**As** Tyler, **I want** stale-package reporting surfaced in bootstrap output, **so that** a re-run tells me what it would prune without me hunting through `~/.pi`.

**Acceptance Criteria**:
- A bootstrap run prints every stale package id found.
  - *Given* a ledger with one stale entry `old-extension`, *When* `llm_sync()`'s deploy runs, *Then* its printed output includes the line `stale Pi package: old-extension (not pruned; run with --prune-stale-pi-packages)`.

**Files**: `bootstrap-pyinfra/deploys/llm_sync.py`

##### Task 2.2.2a: Confirm existing pass-through and document it (~2 min)
- `llm_sync()`'s existing `print(output)` already surfaces `main.py`'s stdout — no pyinfra change needed; add a one-line docstring note confirming this.
- Files: `bootstrap-pyinfra/deploys/llm_sync.py`

---

## Phase 3: Gated Rollout of Tier 0-2 Extensions

### Epic 3.1: Approval Gate Precondition
**Goal**: Make "no fork happens without explicit human approval" a literal, checkable precondition on every fork story below, not prose.

#### Story 3.1.1: Every fork story states and respects the precondition
**As** Tyler, **I want** every fork-and-enable story to declare "a human has recorded approval" as its first acceptance criterion, **so that** an agent can't skip it.

**Acceptance Criteria**:
- Each story in Epics 3.2-3.5 and 4.1 states the approval precondition before any fork action.
  - *Given* Story 3.2.1, *When* its Acceptance Criteria are read, *Then* the first bullet is the approval precondition, not a fork action.
- No task in Phase 3 or Phase 4 programmatically sets `disposition: "approved"`.
  - *Given* every task in Phase 3 and Phase 4, *When* scanned for `gh repo fork` invocations or `"approved"`-literal edits, *Then* none appear outside a task explicitly marked `[Tyler, manual]`.

**Files**: none — enforced by how Epics 3.2-3.5 and 4.1 are written below, and by Epic 1.3's no-approval-path test (Task 1.3.1c).

##### Task 3.1.1a: Record the cross-reference (~2 min)
- No files; this story is satisfied structurally by the stories that follow and by Task 1.3.1c's regression test.

### Epic 3.2: Permission System & Subagents Fork (`gotgenes/pi-packages`)
**Goal**: Once approved, fork, review, and pin `gotgenes/pi-packages` for the permission system and subagents — the strongest foundation per `full-featured-profile-research.md` — wired disabled by default.

#### Story 3.2.1: Fork, review, and pin `gotgenes/pi-packages`
**As** Tyler, **I want** `@gotgenes/pi-permission-system` and `@gotgenes/pi-subagents` forked, reviewed, and pinned, **so that** plan/subagent workflows have a deny-by-default safety boundary before anything else in the profile is enabled.

**Acceptance Criteria**:
- Precondition: Tyler has approved forking `gotgenes/pi-packages` at review anchor `e64946b5ce96ca004b753d98932c8b13106dd132` for capability `permission-system,subagents` (recorded as a dated note before work starts).
- The manifest entry is hand-edited to `approved` only after the Epic 1.4 checklist is complete.
  - *Given* the helper script has created a `candidate` manifest entry for `gotgenes-pi-packages`, *When* Tyler completes the seven-step review from `.claude/skills/pi-extension-review/SKILL.md` and edits `disposition` to `"approved"` with `approved_by`/`approved_date` set, *Then* `verify_pinned_sources_reviewed()` no longer raises for that source.
- The rendered fragment enables both packages disabled by default.
  - *Given* `.config/pi/config.d/50-gotgenes-permissions.json` with `packages.gotgenes-pi-permission-system.enabled: false` and `packages.gotgenes-pi-subagents.enabled: false`, *When* `PiConfigSource.load()` runs, *Then* neither package appears in the rendered `packages` array.

**Files**: `.config/pi/extensions-manifest.json`, `.config/pi/config.d/50-gotgenes-permissions.json`

##### Task 3.2.1a: PRECONDITION — Tyler only, manual — Approve and fork (~5 min)
- `gh repo fork gotgenes/pi-packages --org tstapler` at the review anchor; record approval date/notes.

##### Task 3.2.1b: Scaffold via the helper (~2 min)
- `fork_pin_extension.py fork gotgenes/pi-packages --id gotgenes-pi-packages --capability permission-system,subagents`

##### Task 3.2.1c: Manual review, not code — Complete the checklist (~5 min)
- Includes: verify fail-closed parser paths, deny/ask defaults for writes/external paths/credentials/git publication/package installation/destructive commands, children don't inherit secrets/capabilities by default, worktree cleanup — per `full-featured-profile-research.md`'s "Required review" list. Record findings in the manifest entry's `notes`.

##### Task 3.2.1d: Approve the manifest entry (~2 min)
- Hand-edit `disposition` to `"approved"` with `approved_by`/`approved_date`.
- Files: `.config/pi/extensions-manifest.json`

##### Task 3.2.1e: Add the opt-in fragment (~3 min)
- Both packages `enabled: false`.
- Files: `.config/pi/config.d/50-gotgenes-permissions.json`

#### Story 3.2.2: Validate on the current machine via a temp Pi home first
**As** Tyler, **I want** the permission system enabled with a conservative deny/ask policy on my current macOS machine only, validated in a temp Pi home first, **so that** I can catch problems before wider rollout.

**Acceptance Criteria**:
- A machine-local fragment enables the permission system with deny defaults.
  - *Given* `~/.config/pi/config.local.d/10-permissions.json` (untracked) with `packages.gotgenes-pi-permission-system.enabled: true` and a conservative policy object, *When* rendered in a temp `HOME`, *Then* the resulting `settings.json` shows the package enabled with that policy.
- Staged validation happens in a temp directory before the real machine.
  - *Given* `uv run --directory stapler-scripts/llm-sync main.py --target pi --dry-run --pi-dir /tmp/pi-staging`, *When* run, *Then* it prints the intended change without writing to the real `~/.pi/agent/settings.json`.

**Files**: none tracked (machine-local by design) — validated via existing `--dry-run`/`--pi-dir` flags.

##### Task 3.2.2a: Tyler, manual — Author the machine-local fragment (~5 min)
- Deny/ask defaults per the research doc's required review list.

##### Task 3.2.2b: Tyler, manual — Validate via temp `--pi-dir`, then adopt (~3 min)
- Per Phase 5's runbook.

### Epic 3.3: Plan Mode Fork (`narumiruna/pi-extensions`)
**Goal**: Same shape as Epic 3.2, for `@narumitw/pi-plan-mode`, so plan mode composes most-restrictively with the permission system rather than reactivating a tool the other gate denied.

#### Story 3.3.1: Fork, review, and pin plan mode
**As** Tyler, **I want** `@narumitw/pi-plan-mode` forked, reviewed, and pinned, **so that** plan mode blocks mutation the way Claude's plan mode does, without weakening the permission system.

**Acceptance Criteria**:
- Precondition: Tyler has approved forking `narumiruna/pi-extensions` at anchor `04aae270c51cf4de70479d84317eb15ac8e20e33` for capability `plan-mode`.
- An approved manifest entry at the reviewed commit lets the source render.
  - *Given* an approved manifest entry `narumiruna-pi-extensions-plan-mode` pinned at that fork's reviewed commit, *When* `verify_pinned_sources_reviewed()` runs against a config.d entry using that source, *Then* it passes.
- The fragment is disabled by default.
  - *Given* `.config/pi/config.d/51-plan-mode.json` with the package `enabled: false`, *When* rendered, *Then* plan mode does not appear in the active `packages` array until a machine-local override enables it.

**Files**: `.config/pi/extensions-manifest.json`, `.config/pi/config.d/51-plan-mode.json`

##### Task 3.3.1a: PRECONDITION — Tyler only, manual — Approve and fork (~5 min)

##### Task 3.3.1b: Scaffold via the helper (~2 min)

##### Task 3.3.1c: Manual review, not code — Complete the checklist, including an integration test proving plan mode and the permission system compose most-restrictively (~5 min)
- Per `full-featured-profile-research.md`'s explicit instruction: "add integration tests proving that the two independent gates compose most-restrictively and cannot reactivate a tool denied by the other."

##### Task 3.3.1d: Approve the manifest entry (~2 min)
- Files: `.config/pi/extensions-manifest.json`

##### Task 3.3.1e: Add the opt-in fragment (~3 min)
- Files: `.config/pi/config.d/51-plan-mode.json`

### Epic 3.4: Claude Tool-Name Compatibility Shim (Tyler-owned, no fork required)
**Goal**: Provide the minimal `AskUserQuestion`/`Grep`/`Glob`/`LS`/`Agent`-shaped aliases the existing synced skills need, as a small first-party extension — the research doc's own recommendation over carrying `fractary/pi-claude-code`'s full package given its incomplete license metadata.

#### Story 3.4.1: First-party compatibility aliases
**As** Tyler, **I want** a small first-party Pi extension providing Claude-named tool aliases, **so that** synced skills don't silently fail on Pi from a tool-name mismatch.

**Acceptance Criteria**:
- `AskUserQuestion` is registered as an alias for Pi's native ask-user tool.
  - *Given* `plugins/pi-claude-compat/pi/index.ts` loaded in a Pi session, *When* a skill calls a tool named `AskUserQuestion`, *Then* Pi's native ask-user prompt fires (no "unknown tool" error).
- It's wired the same way as the existing kibitzer/ponytail/dotfiles-hooks first-party extensions — no manifest entry required, since it's a local path source, not a fork.
  - *Given* `.config/pi/config.d/40-claude-compat.json` with `extensions.claude-compat.path: "~/dotfiles/plugins/pi-claude-compat/pi/index.ts"`, *When* `verify_pinned_sources_reviewed()` runs, *Then* it does not require a manifest entry (path sources are exempt, per Story 1.2.2's scan restriction).

**Files**: `plugins/pi-claude-compat/pi/index.ts`, `.config/pi/config.d/40-claude-compat.json`

##### Task 3.4.1a: Write the `AskUserQuestion` alias (~5 min)
- Files: `plugins/pi-claude-compat/pi/index.ts`

##### Task 3.4.1b: Add `Grep`/`Glob`/`LS` casing aliases (~5 min)
- Files: `plugins/pi-claude-compat/pi/index.ts`

##### Task 3.4.1c: Register the extension (~2 min)
- Files: `.config/pi/config.d/40-claude-compat.json`

##### Task 3.4.1d: Add a regression test for the local-path exemption (~3 min)
- Confirms `verify_pinned_sources_reviewed()`'s scan already exempts local `path` sources by construction.
- Files: `stapler-scripts/llm-sync/test_extension_manifest.py`

### Epic 3.5: Command-Hook Bridge Fork (`hsingjui/pi-hooks`) — blocked on license
**Goal**: Fork and pin the Claude-hook-compatible bridge once its missing-license concern is resolved (Unresolved Questions).

#### Story 3.5.1: Fork, review, and pin the hooks bridge, once unblocked
**As** Tyler, **I want** `hsingjui/pi-hooks` forked and pinned once its license concern is resolved, **so that** Claude-style command hooks have a compatibility bridge without adopting ambiguously-licensed code.

**Acceptance Criteria**:
- The block is explicit and checked before any fork step.
  - *Given* a draft manifest entry for `hsingjui-pi-hooks`, *When* `license` is set to `"MIT (no LICENSE file at anchor 8250a856d4f892f0a8a640ac2f1241d1a000701b)"`, *Then* the Epic 1.4 checklist's license-recording step forces an explicit written note rather than a silent MIT assumption.
- Once resolved, the fork proceeds identically to Epic 3.2's shape.
  - *Given* the license concern is resolved (per the Unresolved Questions entry), *When* the fork-review-approve sequence runs, *Then* it follows Tasks 3.2.1a-e's exact shape substituted for `hsingjui/pi-hooks`.

**Files**: `.config/pi/extensions-manifest.json`, `.config/pi/config.d/52-hooks-bridge.json`

##### Task 3.5.1a: BLOCKED — Do not start until the license question resolves (~0 min)
- Tracked in Unresolved Questions; placeholder only.

##### Task 3.5.1b-e: Same five-task shape as 3.2.1a-e, once unblocked
- Files: `.config/pi/extensions-manifest.json`, `.config/pi/config.d/52-hooks-bridge.json`

---

## Phase 4: Credential Provider (1Password)

### Epic 4.1: ADR + Fork-Review-Pin of `pi-1password`
**Goal**: Fork, review, and pin `@jmcombs/pi-1password` per ADR-002, so runtime credential resolution is possible without credential material ever entering the repo.

#### Story 4.1.1: Fork, review, and pin the credential provider
**As** Tyler, **I want** `@jmcombs/pi-1password` forked, reviewed, and pinned, **so that** credentials resolve at runtime from 1Password without any credential material in tracked config.

**Acceptance Criteria**:
- Precondition: Tyler has approved forking `jmcombs/pi-extensions` at anchor `733bb02439ed1f633909a7142bbbefb412245f81` for capability `credential-provider`, after reading ADR-002.
- The manifest entry's `notes` record the specific scoping/redaction/no-inheritance findings, not a generic sign-off.
  - *Given* the manifest entry for `jmcombs-pi-1password`, *When* its `notes` field is read, *Then* it states the least-privilege vault-item scoping, output-redaction, and no-subagent-inheritance findings from the review — not a placeholder like "reviewed, looks fine."
- `PiConfigSource`'s existing credential rejection still applies (regression-only check, no behavior change expected).
  - *Given* a hypothetical config.d fragment for this extension containing a key normalizing to `apikey`, *When* `PiConfigSource.load()` runs, *Then* it raises `PiConfigError`, exactly as it already does today.

**Files**: `.config/pi/extensions-manifest.json`, `project_plans/pi-dotfiles/decisions/ADR-002-credential-provider-approach.md`

##### Task 4.1.1a: PRECONDITION — Tyler only, manual — Approve and fork (~5 min)

##### Task 4.1.1b: Scaffold via the helper (~2 min)

##### Task 4.1.1c: Manual review, not code — Complete the checklist with explicit scoping/redaction/no-inheritance notes (~5 min)

##### Task 4.1.1d: Approve the manifest entry (~2 min)
- Files: `.config/pi/extensions-manifest.json`

##### Task 4.1.1e: Add a regression test documenting the credential-rejection guarantee (~3 min)
- Files: `stapler-scripts/llm-sync/test_pi_config.py`

### Epic 4.2: Opt-in Wiring & Redaction Verification

#### Story 4.2.1: Disabled-by-default wiring with a redaction check
**As** Tyler, **I want** the credential provider wired as a disabled-by-default opt-in fragment with a redaction check, **so that** enabling it on one machine never leaks a resolved secret into logs, sessions, or model context.

**Acceptance Criteria**:
- The package is disabled by default in tracked config.
  - *Given* `.config/pi/config.d/90-credential-1password.json` with `packages.jmcombs-pi-1password.enabled: false`, *When* rendered, *Then* it does not appear in the active `packages` array.
- Dotfiles never write `auth.json`.
  - *Given* the full set of files this plan adds or edits, *When* grepped for `auth.json`, *Then* no match exists outside prose documentation.
- A redaction dry-run never prints a resolved secret value.
  - *Given* a machine-local test with a dummy 1Password reference, *When* the extension resolves it in dry-run/log mode, *Then* the log shows the reference string (e.g. `!op read op://vault/item/field`), not the resolved value — VERIFIED manually by Tyler on his own machine (requires a real 1Password session, not reproducible in CI).

**Files**: `.config/pi/config.d/90-credential-1password.json`, `.config/pi/README.md`

##### Task 4.2.1a: Add the opt-in fragment, disabled by default (~3 min)
- Files: `.config/pi/config.d/90-credential-1password.json`

##### Task 4.2.1b: Document the `auth.json`-grep check (~3 min)
- Files: `.config/pi/README.md`

##### Task 4.2.1c: Tyler, manual — Perform the redaction dry-run and record the VERIFIED result in the manifest entry's `notes` (~5 min)
- Files: `.config/pi/extensions-manifest.json`

---

## Phase 5: Validation, Rollback, Documentation

### Epic 5.1: Staged Rollout & Dry-Run Runbook

#### Story 5.1.1: A runbook maps the five-step Risk Control to commands
**As** Tyler, **I want** a written runbook mapping requirements' five-step staged adoption to concrete commands, **so that** I don't improvise validation order under pressure.

**Acceptance Criteria**:
- The runbook's steps map 1:1 to requirements.md's Risk Control section.
  - *Given* `project_plans/pi-dotfiles/implementation/rollout-runbook.md`, *When* compared to requirements.md's Risk Control list, *Then* each of the five steps has a corresponding runbook section with a runnable command.
- Step 1 names the exact commands already available.
  - *Given* the runbook's step 1 section, *When* read, *Then* it shows `uv run --directory stapler-scripts/llm-sync main.py --target pi --dry-run --pi-dir /tmp/pi-staging` and `uv run pyinfra -y inventory.py main.py --data pi_install_mode=external --dry`.

**Files**: `project_plans/pi-dotfiles/implementation/rollout-runbook.md`

##### Task 5.1.1a: Write runbook steps 1-2 (~5 min)
- Dry-run/temp-dir validation; backup/inventory.
- Files: `project_plans/pi-dotfiles/implementation/rollout-runbook.md`

##### Task 5.1.1b: Write runbook steps 3-5 (~5 min)
- Adopt+verify macOS; verify idempotency/rollback; roll out Linux families.
- Files: `project_plans/pi-dotfiles/implementation/rollout-runbook.md`

### Epic 5.2: Backup/Rollback Procedure

#### Story 5.2.1: A tested rollback that never touches credentials/sessions/trust
**As** Tyler, **I want** a documented rollback that restores pre-adoption managed files without touching credentials/sessions/trust state, **so that** a bad rollout is reversible.

**Acceptance Criteria**:
- Rollback restores exactly the `managedKeys`-tracked keys.
  - *Given* a backup of `~/.pi/agent/settings.json` taken before adoption and the `managedKeys` state at that time, *When* the documented rollback restores from backup, *Then* only keys present in `managedKeys` at backup time are reverted; `auth.json`/session files under `~/.pi/agent/` are untouched.

**Files**: `project_plans/pi-dotfiles/implementation/rollout-runbook.md`

##### Task 5.2.1a: Add the "Backup before adopting" step (~2 min)
- `cp ~/.pi/agent/settings.json ~/.pi/agent/settings.json.pre-dotfiles-backup`.
- Files: `project_plans/pi-dotfiles/implementation/rollout-runbook.md`

##### Task 5.2.1b: Add the "Rollback" section (~4 min)
- Manual restore + re-run without `pi.py`'s managed mode.
- Files: `project_plans/pi-dotfiles/implementation/rollout-runbook.md`

#### Story 5.2.2: Classify the current machine's baseline before it's overwritten
**As** Tyler, **I want** the current machine's existing unmanaged `settings.json` classified into universal/work-only/machine-generated before the first managed sync, **so that** nothing work-specific leaks into the tracked universal base.

**Acceptance Criteria**:
- Every top-level key is classified before the first managed sync.
  - *Given* the current machine's real `~/.pi/agent/settings.json`, *When* each top-level key is reviewed against the three buckets, *Then* `project_plans/pi-dotfiles/implementation/rollout-runbook.md` records the classification table before Story 3.2.2's temp-dir validation runs.

**Files**: `project_plans/pi-dotfiles/implementation/rollout-runbook.md`

##### Task 5.2.2a: Tyler, manual — Classify and record the table (~5 min)
- Files: `project_plans/pi-dotfiles/implementation/rollout-runbook.md`

### Epic 5.3: Claude Workflow-Category Compatibility Matrix

#### Story 5.3.1: A matrix of Claude tool names to Pi status
**As** a future coding agent syncing a new skill to Pi, **I want** a matrix of every Claude tool name the synced skill corpus uses mapped to its Pi status, **so that** I don't assume parity that doesn't exist.

**Acceptance Criteria**:
- The matrix covers every Claude tool name referenced by the synced skill corpus.
  - *Given* `project_plans/pi-dotfiles/extensions/claude-tool-compat-matrix.md` and a grep of `.claude/skills/**/SKILL.md` for Claude tool names (`AskUserQuestion`, `WebSearch`, `WebFetch`, `Agent`, `TaskCreate`, `Grep`, `Glob`, `LS`), *When* compared, *Then* every found tool name has a matrix row stating its Pi status (native, shimmed via `pi-claude-compat`, extension-provided, or unsupported).

**Files**: `project_plans/pi-dotfiles/extensions/claude-tool-compat-matrix.md`

##### Task 5.3.1a: Run the grep across the skill/command corpus (~4 min)
- No file write; Bash/Grep only.

##### Task 5.3.1b: Write the matrix file (~5 min)
- One row per discovered tool name and its Pi status.
- Files: `project_plans/pi-dotfiles/extensions/claude-tool-compat-matrix.md`

### Epic 5.4: Documentation Sync

#### Story 5.4.1: Docs describe the manifest gate and package ledger
**As** a future reader of `.config/pi/README.md` or `stapler-scripts/llm-sync/AGENTS.md`, **I want** both updated to describe the manifest gate and package ledger, **so that** the docs don't drift from the enforcement code the requirements warn against.

**Acceptance Criteria**:
- `AGENTS.md`'s Pi section mentions the manifest gate.
  - *Given* `stapler-scripts/llm-sync/AGENTS.md`'s "Pi (pi.dev)" section, *When* read after this plan ships, *Then* it states that pinned fork sources require an approved `.config/pi/extensions-manifest.json` entry and names `verify_pinned_sources_reviewed()`.
- `.config/pi/README.md` documents the package ledger and prune/reconcile flags.
  - *Given* the README, *When* read, *Then* it documents `--prune-stale-pi-packages`, `--reconcile-pi-package-ledger`, and the `pi-package-state.json` ledger location.

**Files**: `stapler-scripts/llm-sync/AGENTS.md`, `.config/pi/README.md`

##### Task 5.4.1a: Update `AGENTS.md`'s Pi section (~4 min)
- Files: `stapler-scripts/llm-sync/AGENTS.md`

##### Task 5.4.1b: Update `.config/pi/README.md` (~4 min)
- Files: `.config/pi/README.md`
