---
name: tiered-configuration
description: Design, implement, or review config.d-style layered configuration using Tyler's standard precedence model: tracked universal base, tracked overlay fragments, untracked machine-local base, and untracked machine-local fragments. Use whenever adding configuration that varies by machine, employer/work overlay, environment, or repository; when replacing a monolithic settings file; or when deciding how multiple dotfiles repositories can contribute configuration without owning the same file.
---

# Tiered Configuration

Use one predictable layering model whenever configuration must be universal by default but extensible by another repository or a single machine.

## Standard precedence

Apply layers in this order, with later layers taking precedence:

1. **Tracked universal base** — safe defaults owned by the primary repository.
2. **Tracked `config.d` fragments** — additions or overrides owned by other tracked sources, including work overlay repositories.
3. **Untracked machine-local base** — one machine's broad overrides.
4. **Untracked machine-local `config.d` fragments** — independently owned machine-specific additions or overrides.

Within each fragment directory, load files in lexical filename order. Prefer numeric prefixes such as `20-personal.json`, `50-work.json`, and `90-machine.json` when order matters.

## Canonical layout

Adapt names to the application while preserving the four roles:

```text
.config/<app>/
├── config.json                 # tracked universal base
├── config.d/
│   └── 50-work.json            # tracked overlay contribution
├── config.local.json           # untracked machine-local base
└── config.local.d/
    └── 90-experiment.json      # untracked machine-local fragment
```

If the application has established names, retain them. For example, a file named `mcp-servers.json` should pair with `mcp-servers.d/`, `mcp-servers.local.json`, and `mcp-servers.local.d/` rather than being renamed to `config.json`.

## Ownership rules

- Let each repository own individual files, not a shared directory symlink. This allows multiple repositories to contribute fragments without replacing one another.
- Keep universal public configuration in the primary dotfiles repository.
- Keep employer-specific or confidential configuration in its overlay repository.
- Keep machine-only configuration untracked.
- Never put credentials or generated authentication state in any tracked layer.
- Do not make a repository own an application's entire mutable config directory when it also contains sessions, caches, trust state, credentials, or generated files.

## Merge semantics

Choose and document deterministic semantics before writing the loader:

- Merge objects recursively.
- Let scalar values replace earlier values.
- Replace arrays by default; implicit array concatenation creates duplication and makes removal ambiguous.
- Use JSON `null` as a deletion marker when the format can represent it safely.
- For collections that need independent add/replace/disable behavior, model source entries as a map keyed by stable logical ID, then render the enabled values into the application's native list format.
- Reject malformed layers. Do not silently skip an invalid override and continue with surprising defaults.
- Report every loaded layer in effective precedence order.

Example keyed collection:

```json
{
  "packages": {
    "base-tools": {
      "enabled": true,
      "source": "git:github.com/example/base-tools@<commit>"
    },
    "optional-tool": {
      "enabled": false,
      "source": "git:github.com/example/optional-tool@<commit>"
    }
  }
}
```

A later layer can disable `base-tools` without copying or rewriting the rest of the package list.

## Applying generated configuration

When the target application lacks native include support:

1. Merge source layers into an effective model.
2. Validate the complete effective model before touching the destination.
3. Render the application's native configuration atomically.
4. Track which destination fields/files are managed.
5. On later runs, remove stale previously managed values while preserving unmanaged and machine-generated state.
6. Keep credentials, sessions, caches, and trust databases outside the managed surface.

Prefer native include directives when the application supports them; generating a monolithic file is a fallback, not the goal.

## Validation requirements

Leave one cheap deterministic check that covers:

- all four precedence levels;
- lexical fragment ordering;
- nested object merge behavior;
- array replacement;
- explicit deletion or disable behavior;
- malformed input failure with the responsible path;
- an empty/missing optional layer;
- idempotent output;
- preservation of unmanaged target state, if a generated destination is used.

For bootstrap integration, provide a dry-run that shows source layers and intended destination changes without exposing secret values.

## Review checklist

Before approving a tiered configuration change, verify:

- [ ] The universal base works without any overlay.
- [ ] A tracked overlay can contribute one file without editing universal files.
- [ ] Local files are gitignored explicitly.
- [ ] Precedence and merge semantics are documented next to the configuration.
- [ ] Disable/removal behavior is possible without copying the whole base.
- [ ] Invalid fragments fail loudly and name the file.
- [ ] Re-running produces no unintended changes.
- [ ] No secret or mutable runtime state enters tracked files.
- [ ] The bootstrap order applies overlays before generating the effective configuration.

## Avoid

- One giant settings file containing personal, work, and machine-specific branches.
- Whole-directory symlinks over application-owned mutable state.
- Deep-merging arrays without an explicit collection-specific identity rule.
- Swallowing parse errors and silently omitting a layer.
- Treating fragment filename order as incidental.
- Copying a base file into an overlay just to change one entry.
- Calling a system idempotent when stale managed entries are never removed.
