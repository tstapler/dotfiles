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

Before forking, pinning, or enabling any third-party extension, follow the
fork-pin-review gate documented in
[`.claude/skills/pi-extension-review/SKILL.md`](../../.claude/skills/pi-extension-review/SKILL.md).

Never put credentials, OAuth state, sessions, trust data, or other mutable Pi
runtime state in these files.

## Hook parity

Pi uses TypeScript extensions rather than Claude Code's shell-hook JSON:

- `plugins/dotfiles-hooks/pi/index.ts` provides command-output compaction,
  the PR review reminder, `/magic-compact`, and post-compaction context audit.
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

## Package lifecycle

VERIFIED via a manual temp-`HOME` spike (pi 0.84.4, 2026-09-21), using the
real npm-hosted extension `@gotgenes/pi-permission-system` referenced in
`project_plans/pi-dotfiles/full-featured-profile-research.md`:

```bash
TMPHOME=$(mktemp -d)
mkdir -p "$TMPHOME/.pi/agent"
find "$TMPHOME" -type f | sort > before.txt      # empty

HOME="$TMPHOME" pi install npm:@gotgenes/pi-permission-system --no-approve
find "$TMPHOME" -type f | sort > after-install.txt
```

**Artifact path**: an npm `packages` entry lands under a dedicated npm
workspace at `~/.pi/agent/npm/` — `package.json` (declares the package as a
`dependencies` entry), `package-lock.json`, a `.gitignore` (`*` /
`!.gitignore`), and the installed files under
`~/.pi/agent/npm/node_modules/<package>/` plus its own transitive
dependencies as npm siblings under the same `node_modules/`. `pi install`
also rewrites `~/.pi/agent/settings.json`'s `packages` key as a flat array of
source strings (e.g. `{"packages": ["npm:@gotgenes/pi-permission-system"]}`),
not the map-keyed-by-id object shape this file's own layered-config examples
above show — the map shape is this repo's authoring format, and `llm-sync`
must render it down to Pi's actual array-of-strings runtime shape. Installing
also seeds an ordinary npm cache at `~/.npm/` (`_cacache`, `_logs`), which is
npm's own global cache, not Pi-specific state.

**Removal via `pi remove`**: `HOME="$TMPHOME" pi remove
npm:@gotgenes/pi-permission-system --no-approve` fully prunes the artifact —
it empties `settings.json`'s `packages` array, updates
`~/.pi/agent/npm/package.json`/`package-lock.json`, and deletes
`~/.pi/agent/npm/node_modules/<package>/` along with any transitive
dependency no longer needed by another installed package. Nothing was left
behind or errored.

**Removal by hand-editing `settings.json` (the path `llm-sync` actually
takes) does *not* prune anything.** Given the artifact installed above, then
directly rewriting `settings.json`'s `packages` array to `[]` (simulating
`PiSettingsTarget.save()`) and re-running Pi — tried as `pi --version`,
`pi list --no-approve` (which reports "No packages installed" while the
files are still on disk), and a full non-interactive startup attempt
(`pi -p "hi" --offline --no-approve`, which fails only on missing API
credentials) — `~/.pi/agent/npm/node_modules/@gotgenes/pi-permission-system/`
remained on disk in every case. Pi does not garbage-collect installed
packages based on `settings.json` content alone; pruning only happens
through the explicit `pi remove <source>` (or `pi uninstall <source>`) CLI
path. This confirms the risk this plan's Rabbit Holes/Unresolved Questions
sections flagged as unverified: **Epic 2.2's `PiPackageLedger` is required**
for stale-artifact cleanup — Pi will not do it on its own from a rendered
`settings.json`.

**Caution for Epic 2.2 tooling**: bare `pi update` (no source argument)
self-updates the `pi` binary itself via `npm --prefix ~/.local`, outside any
temp `HOME` sandboxing (it updated the real system-wide install during this
spike, from the repo-pinned 0.84.4 to 0.86.1; reverted with `npm install
--global --prefix ~/.local --no-audit --no-fund
"@earendil-works/pi-coding-agent@0.84.4"`). Any future reconciliation
tooling must never invoke bare `pi update` — use `pi update --extensions` or
target specific sources.

## Package ownership ledger

`llm-sync` tracks which Pi package artifacts it installed in a ledger at
`~/.config/llm-sync/pi-package-state.json` (override with
`--pi-package-ledger-state-file`), since hand-editing `settings.json` alone
doesn't prune anything (see Package lifecycle above).

- `--prune-stale-pi-packages` — a package the ledger owns but that's no
  longer enabled in the rendered config is always reported as stale; this
  flag actually deletes its on-disk artifact.
- `--reconcile-pi-package-ledger` — rebuilds ledger entries missing from a
  prior sync that was interrupted between writing `settings.json` and
  writing the ledger, from the current config's enabled packages.
