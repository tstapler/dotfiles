# Requirements: Pi Dotfiles Support

**Date**: 2026-09-03
**Type**: cross-cutting feature addition and configuration migration
**Complexity**: 4 — high-stakes / cross-cutting

## Problem Statement

Pi support in the dotfiles is partial. The existing `llm-sync` target copies compatible Claude skills and commands into Pi, but the bootstrap does not install Pi or consistently provision its broader configuration, extensions, packages, workflow integrations, or platform preferences. A new machine therefore cannot reach a complete, reproducible Pi setup from the dotfiles alone.

The dotfiles need to provision a secure and reproducible Pi environment across personal and work machines while retaining controlled machine- and environment-specific customization.

## Baseline

Today:

- `stapler-scripts/llm-sync` exports Claude skills to `~/.pi/agent/skills/` and commands to `~/.pi/agent/prompts/`.
- `bootstrap-pyinfra` invokes that sync.
- Pi itself is not declared in either Brewfile or otherwise installed by the bootstrap.
- Pi settings, keybindings, themes, extensions, and package selection are not managed by this repository.
- The current machine's `~/.pi/agent/settings.json` includes a work-owned Pi package and work-specific default provider/model configuration.
- Authentication state and other generated files coexist under `~/.pi/agent/`, making whole-directory linking inappropriate.
- Reproducing the current setup on another machine requires manual installation and configuration.

This baseline is the regression anchor: existing skill and prompt synchronization must continue to work while broader provisioning is added.

## Users / Consumers

- Tyler on personal macOS and Linux machines.
- Tyler on work-managed macOS machines, with work-specific overlays supplied separately from universal public dotfiles.
- The pyinfra bootstrap and `llm-sync` automation that converge machine state.
- Future coding agents asked to create or modify tiered configuration in this repository or related overlay repositories.

## Success Metrics

A successful end state has the following observable behavior:

1. Starting from a supported personal machine without Pi, one bootstrap run installs Pi and produces a usable universal configuration. A work overlay can declare Pi externally managed so the work machine's existing installer remains authoritative.
2. The same run provisions the approved, pinned extension/package set and synchronizes compatible Claude assets.
3. Existing tracked and local configuration layers can add, replace, disable, or reconfigure universal entries without editing the universal source.
4. A work overlay can contribute work-specific packages and defaults without placing those settings in the public universal configuration.
5. Re-running bootstrap is idempotent and makes no unintended changes.
6. Dry-run and temporary-directory validation complete before configuration is adopted on a real machine.
7. The resulting Pi setup supports all required Claude workflow categories: skills/prompts, instructions, hooks and safety controls, MCP/tool integrations, subagent/parallel-agent workflows, settings/models/keybindings/themes/UI preferences, and session/workflow utilities.
8. No credential material is written to or copied through the dotfiles. Runtime credential-provider extensions may securely retrieve credentials from OS credential stores.
9. A reusable Agent Skill documents and enforces Tyler's preferred tiered/config.d configuration model.

## Appetite

Large/unbounded. Correctness, security, portability, and maintainability take priority over a fixed delivery date.

## Constraints

- Supported platforms are macOS and Linux, specifically the repository's existing macOS, Arch/Manjaro, and Debian/Ubuntu families.
- Windows and WSL2 are not required for this effort.
- Universal configuration belongs in the public dotfiles repository; work-specific configuration must remain in an appropriate work overlay.
- The universal installer must be overridable. On work machines, the work-provided Pi installation remains authoritative and bootstrap must not install or replace the public Pi distribution.
- Dotfiles must never contain, copy, or provision API keys, OAuth sessions, work credentials, `auth.json`, or other credential material.
- Credentials may be obtained at runtime only through explicitly approved extensions that integrate with secure desktop/OS credential stores or equivalent providers.
- Third-party open-source Pi extensions/packages must be forked under Tyler's control, reviewed, and pinned to an exact commit or immutable version from that fork.
- work-owned packages and Tyler-owned packages/extensions do not require an additional fork. Tyler-owned packages/extensions remain pinned; work-owned packages may follow their internally managed unpinned release channel.
- Bootstrap must not silently advance third-party or Tyler-owned extension/package versions. work-owned packages are the explicit exception.
- Existing Pi skill and prompt synchronization must not regress.

## Non-functional Requirements

- **Performance SLO**: No strict runtime latency target. Idempotent bootstrap checks should avoid unnecessary reinstalls, downloads, and rewrites.
- **Scalability**: Must remain understandable and deterministic as the curated extension set and number of configuration fragments grow.
- **Security classification**: Universal configuration is public; work overlays are internal. Credential material is excluded from both.
- **Data residency**: No special residency requirement; no secret data should be introduced into configuration artifacts.
- **Portability**: Equivalent behavior on supported macOS and Linux distributions, with platform-specific entries allowed where necessary.
- **Determinism**: Approved extension/package sources and versions are immutable until deliberately updated.
- **Idempotency**: Repeated bootstrap runs converge without unintended file churn or duplicate entries.

## Scope

### In Scope

- Automated Pi installation on supported personal platforms, with an overlay-controlled externally-managed mode for work machines.
- Reproducible provisioning of Pi settings, non-secret provider/model metadata, keybindings, themes, extensions, and packages.
- Curating and evaluating useful Pi extensions, including candidates from <https://composio.dev/content/top-pi-extensions>.
- A universal extension/configuration base with layered overrides and additions.
- Consistent tiered configuration using the existing precedence model:
  1. tracked universal base;
  2. tracked `config.d` fragments, including fragments supplied by overlay repositories;
  3. untracked machine-local base overrides;
  4. untracked machine-local `config.d` fragments;
  5. later layers take precedence, with explicit add, replace, and disable behavior.
- Personal/work separation, including compatibility with work-owned Pi packages and model/provider configuration.
- Functional parity for the requested Claude workflow categories:
  - skills and slash-command/prompt equivalents;
  - global and project instructions;
  - hooks and safety controls;
  - MCP and tool integrations through Pi extensions;
  - subagent or parallel-agent workflows;
  - settings, models, keybindings, themes, and UI preferences;
  - session and workflow utilities.
- Secure runtime credential-provider extensions, where approved, without provisioning credential contents.
- Validation, idempotency tests, rollback documentation, and user-facing setup documentation.
- A reusable skill describing the preferred tiered/config.d configuration pattern for future projects.

### Out of Scope

- Storing, copying, backing up, or generating credential material.
- Automatically logging into providers or restoring OAuth/API sessions.
- Silently tracking latest upstream extension/package releases.
- Supporting native Windows or WSL2 in this effort.
- Exact visual or interaction-level cloning of Claude Code where functional workflow parity is sufficient.
- Forking work-owned or Tyler-owned packages merely to satisfy the third-party fork policy.
- Requiring immutable pins for work-owned packages that already have an internally managed update channel.

## Rabbit Holes

- Pi deliberately omits native MCP, subagents, permission popups, plan mode, and background bash; parity may require evaluating or building extensions rather than copying Claude configuration.
- Extension candidates may overlap, conflict, be abandoned, execute arbitrary code, or assume unsupported platforms.
- Forking every third-party open-source extension creates an ongoing ownership, security-review, and update burden.
- Pi package installation may mix mutable package-manager state with declarative settings, complicating exact convergence and removal of stale packages.
- Pi's config files may not natively support fragments, requiring deterministic merge behavior with clear ownership and deletion semantics.
- Universal settings may conflict with work package defaults or machine-generated Pi state.
- Installation ownership must be resolved before package/config sync so the universal installer cannot shadow or replace a work-managed Pi executable.
- Claude hooks, agents, and MCP definitions may not have direct Pi equivalents and must not be translated mechanically without preserving safety semantics.
- Credential-provider plugins could accidentally expose secrets through logs, model context, subprocess environments, or generated configuration.
- Whole-directory symlinking could overwrite sessions, authentication, trust decisions, package caches, or other mutable Pi state.

## Alternatives Considered

- Continue the current skills/prompts-only sync and configure the rest manually. Rejected because it does not make new machines reproducible.
- Symlink the entire Pi agent directory. Rejected because mutable authentication, session, trust, package, and cache state shares that directory.
- Use one universal settings file with no overlays. Rejected because personal, work, and machine-specific requirements differ.
- Install directly from third-party upstreams or track floating releases. Rejected in favor of controlled forks and immutable pins.
- Store credentials in dotfiles or bootstrap them directly. Rejected; only secure runtime credential-provider extensions are permitted.

## Feasibility Risks

- Pi's current extension/package APIs may not expose enough declarative state to guarantee full idempotent provisioning and stale-entry cleanup.
- Some desired Claude capabilities may have no mature Pi extension and may require custom extension development.
- Candidate extensions may not support both macOS and Linux.
- Public forks may not be legally or operationally suitable for every upstream extension; license review is required.
- work-owned Pi configuration may impose constraints not represented in the public repository.
- Layered merging must preserve valid Pi schemas while handling arrays, object replacement, deletion/disable markers, and platform-specific values predictably.
- The existing `llm-sync` hash/state behavior may not account for all ownership and deletion cases required by declarative provisioning.

## Observability Requirements

- Bootstrap output must identify the effective configuration layers, extension/package actions, and whether each item was installed, updated, disabled, skipped, or already converged.
- Validation must report malformed fragments, unknown entries, duplicate/conflicting definitions, missing pinned sources, and unsupported-platform selections before applying changes.
- Dry-run output must show intended changes without exposing credentials or secret values.
- Failures must name the responsible layer and configuration entry.
- No operational alerting is required; this is local bootstrap automation rather than an online service.

## Risk Control

Use staged adoption:

1. Validate merge and provisioning behavior using dry-run mode and temporary destination directories.
2. Back up or inventory the current unmanaged Pi configuration.
3. Adopt and verify on the current macOS machine.
4. Verify idempotent re-runs and rollback behavior.
5. Roll out to supported Linux families.

Rollback must restore the pre-adoption managed files and package/extension selection without touching credentials, sessions, trust state, or other mutable Pi data.

## Open Questions

- Which candidate extensions provide unique value, overlap with existing work-provided functionality, or should be rejected for security/maintenance reasons?
- Which Pi resources are best managed directly versus generated from the existing Claude source of truth?
- What exact merge semantics should apply to nested objects, arrays, deletions, and per-platform values?
- How should extension forks be inventoried, reviewed, pinned, and deliberately upgraded?
- Which existing `~/.pi/agent` settings are universal preferences versus work-only or machine-generated state?
- What Pi-native or extension-based mechanisms best satisfy hooks, MCP, subagent/parallel-agent, and credential-provider requirements?
- What ownership manifest is needed to remove stale managed resources without deleting user-created or machine-generated files?
