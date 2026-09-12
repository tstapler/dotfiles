# Pi configuration

`llm-sync` renders these declarative layers into `~/.pi/agent/settings.json`.
It owns only the rendered top-level keys and preserves Pi-generated and other
unmanaged settings.

Precedence, from lowest to highest:

1. `config.json` — tracked universal base.
2. `config.d/*.json` — tracked fragments, in lexical order.
3. `~/.config/pi/config.local.json` — untracked machine override.
4. `~/.config/pi/config.local.d/*.json` — untracked fragments, in lexical order.

Objects merge recursively, arrays replace, and `null` deletes inherited keys.
Pi resources use maps keyed by stable IDs so later layers can disable one entry:

```json
{
  "packages": {
    "example": {
      "enabled": true,
      "source": "git:github.com/tstapler/example@<commit>"
    }
  },
  "extensions": {
    "local-example": {
      "path": "~/dotfiles/path/to/extension.ts"
    }
  }
}
```

Set `"enabled": false` in a later layer to disable an inherited resource.
Third-party packages must come from a reviewed `tstapler` fork pinned to an
exact commit. Tyler-owned npm packages must use the `@tstapler` scope and an
exact version. Unpinned packages are allowed only from scopes listed in a
top-level `trustedPackageScopes` array (e.g. `["npm:@work-org"]`) — a work
overlay's own tracked fragment can add its scope there because its
internally managed update channel owns that package's cadence. Local
package paths are also allowed.

Never put credentials, OAuth state, sessions, trust data, or other mutable Pi
runtime state in these files.

## Hook parity

Pi uses TypeScript extensions rather than Claude Code's shell-hook JSON:

- `plugins/dotfiles-hooks/pi/index.ts` provides command-output compaction,
  the PR review reminder, `/magic-compact`, and post-compaction context audit.
- `plugins/ponytail/pi/index.ts` provides Ponytail on demand; Pi starts with it
  off because always-on full mode is too aggressive for general work.
- Stapler Squad owns its approval extension. The pyinfra Pi deploy runs the
  idempotent `ssq-hooks install pi` command instead of copying that generated
  extension into this repository.
- Kibitzer owns its own Pi extension and config fragment.

Do not translate arbitrary Claude hook JSON automatically. Pi event contracts
and Claude hook stdin/stdout contracts differ; add or reuse a reviewed Pi-native
adapter for each behavior.

## Installation ownership

The pyinfra bootstrap defaults to `pi_install_mode=auto`: it preserves any Pi
already on `PATH` (including the work-managed distribution) and installs the
exact public release under `~/.local` only when Pi is absent. Override per run
when needed:

```bash
# Another machine manager owns installation.
uv run pyinfra -y inventory.py main.py --data pi_install_mode=external

# Explicitly converge the public ~/.local install to the configured pin.
uv run pyinfra -y inventory.py main.py --data pi_install_mode=managed
```

The public pin lives in `bootstrap-pyinfra/group_data/all.py`. Updating it is a
deliberate reviewed change; `auto` never replaces or downgrades an existing Pi.

Preview only Pi resource and configuration changes with:

```bash
uv run --directory stapler-scripts/llm-sync main.py --target pi --dry-run
```

A Pi-only target does not install Claude/Antigravity plugins or rewrite their
MCP settings.
