# Repo Map

Tyler's personal dotfiles — cross-platform config (Manjaro/Ubuntu Linux primary,
macOS at work, some WSL2) plus the Ansible bootstrap that provisions a new
machine end to end. See `README.md` for the human-facing feature tour; this
file is the orientation map for working in the repo.

## How it fits together

1. **`install.sh`** — entry point for a brand-new machine. Clones this repo,
   then hands off to `bootstrap/run.sh`.
2. **`bootstrap/run.sh`** → **`bootstrap/playbook.yml`** — installs Homebrew,
   then runs the Ansible roles in `bootstrap/roles/*` in order (see the
   playbook for the current sequence: `claude`, `homebrew`, `dotfiles`,
   `overlays`, `llm-sync`, `shell`, `asdf`, `nix`, `secrets`, `fonts`,
   `github`, `fbg` (work-only), `ssh-bastion-client`, `sudo-mfa`).
3. **`Brewfile`** (macOS, casks allowed) / **`Brewfile.linux`** (Linuxbrew;
   GUI-only casks are excluded, but CLI-only casks like `1password-cli` work
   fine since Homebrew Cask on Linux just installs the binary artifact) —
   consumed by the `homebrew` role via `brew bundle`.
4. **`cfgcaddy/`** — git submodule, the actual symlinking tool. `.cfgcaddy.yml`
   at repo root declares every dotfile → `$HOME` symlink, including OS-specific
   targets (`os: "Linux Darwin"` etc.). The `dotfiles` Ansible role invokes it.
5. **`.claude/`** — this directory *is* `~/.claude` (symlinked in via
   cfgcaddy): agents, commands, skills, plugins, and both this file's sibling
   `.claude/CLAUDE.md` (Claude Code's own operating instructions, distinct
   from this file) live here and apply globally, not just to this repo.
6. **`stapler-scripts/`** — grab-bag of standalone scripts and small tools
   (git helpers, `llm-sync` which mirrors Claude config — including MCP
   servers from `.config/mcp/mcp-servers.json` — to Gemini/OpenCode/Antigravity,
   proxies, installers; see `stapler-scripts/llm-sync/AGENTS.md` for how to add
   a new MCP server). Symlinked onto `PATH` via `.cfgcaddy.yml`.
7. **`docs/adr/`, `docs/plans/`, `project_plans/`** — Manifest-Driven
   Development artifacts (requirements/research/plan docs) for larger repo
   changes; see `.claude/CLAUDE.md` for the phase workflow.

## Ansible roles worth knowing

- **`secrets`** — installs/verifies 1Password. The CLI (`op`) comes from the
  Brewfile cask on both platforms. The desktop app comes from the Brewfile
  cask on macOS; on Linux it's installed from 1Password's official `.tar.gz`
  into `/opt/1Password` (signature-verified against their signing key), not
  Flatpak/Snap — those sandboxed builds can't do CLI/SSH-agent/MCP-client
  integration at all, confirmed by inspecting the sandbox directly (see
  `bootstrap/roles/secrets/tasks/main.yml`).
- **`sudo-mfa`** — optional (`sudo_mfa_enabled` var), Arch-only, layers a
  YubiKey/TOTP PAM stack onto `sudo`.
- **`fbg`** — work-specific (Fanatics Gaming), auto-skipped unless the
  hostname matches `fbg-*`.

## Checks before pushing

`make ready` runs `ansible-lint` (via `uvx`) and `shellcheck` over the
bootstrap playbook and shell entry points — sentinel files in `.cache/` skip
reruns when nothing changed. `make run` re-runs the bootstrap playbook
locally.

## Version control

This repo uses **jj** (Jujutsu) in colocated mode over the git backend, not
plain git — see memory for the orphaned-commit recovery workflow if `jj log`
shows commits not reachable from `master`.
