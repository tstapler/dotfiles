# ADR-001: Rendered Template Cache Location
Status: Accepted
Date: 2026-06-15

## Context

cfgcaddy's templating feature (Feature 1) renders `.tmpl` source files via Jinja2 and writes the output to a cache directory. The symlink for the dotfile points to the rendered file, not the source template. This means the rendered file must exist and be stable for shell startup and other dotfile consumers to function correctly.

The initial requirements specified `~/.cache/cfgcaddy/rendered/` as the output location. The XDG Base Directory Specification defines two relevant directories:

- `XDG_CACHE_HOME` (`~/.cache/`): Non-essential cached data that applications can recreate on demand. Tools, CI systems, disk-cleanup scripts, and users themselves routinely clear this directory.
- `XDG_DATA_HOME` (`~/.local/share/`): Persistent user-specific application data that must survive normal system maintenance.

Rendered dotfiles are not caches in the XDG sense — they are the live targets of symlinks that shell startup scripts depend on. If the rendered directory is deleted, every symlink pointing into it becomes broken, and shell startup fails with `No such file or directory`. This failure is visible but disruptive, especially on a fresh machine restore or in CI environments that prune `~/.cache/`.

Additionally, rendered files may contain actual secrets if the user stores token values directly in `local.toml` rather than `op://` URIs. The directory must be created with restricted permissions.

## Decision

Use `~/.local/share/cfgcaddy/rendered/` (resolved via `XDG_DATA_HOME`) as the rendered template output directory, not `~/.cache/cfgcaddy/rendered/`.

The directory is created on first use with mode `0700`.

The full resolved path mirrors the source structure:
- Source template: `~/dotfiles/.shell/env.sh.tmpl`
- Rendered output: `~/.local/share/cfgcaddy/rendered/.shell/env.sh`
- Symlink: `~/.shell/env.sh` → `~/.local/share/cfgcaddy/rendered/.shell/env.sh`

The rendered path uses a fixed mirrored structure (not content-addressed hashes). The symlink target never changes after initial creation; re-renders atomically overwrite the rendered file in place.

## Alternatives Considered

**`~/.cache/cfgcaddy/rendered/` (original spec)**
Rejected. `~/.cache/` is semantically clearable per the XDG spec and in practice. Clearing it breaks all rendered-file symlinks. Shell startup files are among the most critical paths on a machine — breaking them silently is unacceptable. The "re-render on detect broken symlink" mitigation requires cfgcaddy to be on PATH and invocable at shell startup, which is circular.

**Content-addressed filenames (e.g., `~/.local/share/cfgcaddy/rendered/<sha256>/env.sh`)**
Rejected. Content addressing requires updating the symlink target every time the rendered content changes (because the hash changes). This adds complexity with no benefit for this use case. Fixed mirrored paths allow atomic in-place overwrites without symlink changes.

**Store rendered files alongside source templates**
Rejected. Rendered files may contain secrets. They must not be in the dotfiles repository directory, which is tracked by git and potentially public.

**Re-render on every `cfgcaddy link` run (with `~/.cache/`)**
Partially mitigates the cache-clearing risk but does not eliminate it — if cache is cleared and cfgcaddy is not immediately run, all symlinks are broken. This also does not address the permissions requirement. XDG_DATA_HOME is the correct semantic location.

## Consequences

**Positive:**
- Shell startup is robust against disk cleanup, CI cache purges, and fresh machine restores.
- Rendered files containing secrets are stored in a directory with `0700` permissions, reducing accidental exposure.
- Semantically correct per XDG: rendered dotfiles are persistent user data, not ephemeral cache.

**Negative:**
- Slight deviation from the initial requirements spec; any documentation referring to `~/.cache/cfgcaddy/` must be updated.
- `~/.local/share/` may be unfamiliar to users who inspect cfgcaddy's footprint; it should be documented in `cfgcaddy doctor` output and help text.

**Implementation notes:**
- Respect `XDG_DATA_HOME` environment variable when set; default to `~/.local/share/`.
- Create rendered dir with `os.makedirs(rendered_dir, mode=0o700, exist_ok=True)`.
- Individual rendered files inherit source permissions via `shutil.copymode(template_path, rendered_path)` after atomic write.
- Tests must override `XDG_DATA_HOME` (or inject `output_dir`) to avoid writing to the real user's data directory.
