# bootstrap-pyinfra

Strangler-fig port of `../bootstrap/` (Ansible) to [pyinfra](https://pyinfra.com). Both
projects coexist during the migration — each role lives in exactly one of them at a
time, never both. See `../.claude/plans/quizzical-stirring-kahan.md` for the full plan.

## Usage

```bash
cd bootstrap-pyinfra
uv run pyinfra -y inventory.py main.py [--dry]
```

`-y` is required in non-interactive contexts (CI, this repo's own tooling) — without it,
pyinfra prompts for confirmation before running. `--dry` previews without executing
(pyinfra's analog to `ansible-playbook --check`).

Operations that need root (`_sudo=True`) will prompt interactively for a sudo password —
run this from a real terminal, not a non-interactive shell.

## Per-role migration status

| Ansible role | Status | pyinfra deploy |
|---|---|---|
| `sudo-mfa` | Ported, pending live verification (sudo steps need a real terminal) | `deploys/sudo_mfa.py` |
| `secrets` | Ported, pending live verification (sudo steps need a real terminal) | `deploys/secrets.py` |
| `overlays` | **Done** — run live twice, removed from playbook.yml | `deploys/overlays.py` |
| `fonts` | **Done** — run live twice, removed from playbook.yml | `deploys/fonts.py` |
| `dotfiles` | **Done** — run live twice, removed from playbook.yml | `deploys/dotfiles.py` |
| `homebrew` | Ported, pending live verification (Linux-prereq sudo step needs a real terminal) | `deploys/homebrew.py` |
| `asdf` | **Done** — no sudo needed, run live twice, removed from playbook.yml | `deploys/asdf.py` |
| `nix` | Ported, pending live verification (fresh-install path needs a real terminal for sudo; already-installed path run live twice on this machine, plus the redirect/tag/URL resolution logic verified read-only against the real install.determinate.systems service) | `deploys/nix.py` |
| `shell` | Ported, pending live verification (chsh step needs a real terminal for sudo — pyinfra's own `server.user` fact-check needs it too, not just the mutation; zplug clone run live twice, idempotent) | `deploys/shell.py` |
| `github` | Ported, no sudo needed at all — run live twice on this machine, fully idempotent, confirmed against real GitHub state (`gh ssh-key list` shows `onyx-primary` registered, matching this code's title format exactly). NOT moved to Done: the personal-account (FBG) branch is completely unexercised on this non-FBG machine — needs verification on an FBG machine before removing from playbook.yml | `deploys/github.py` |
| `llm-sync` | **Done** — no sudo needed, run live twice (really synced skills/agents/MCP config both times), removed from playbook.yml | `deploys/llm_sync.py` |
| `claude` | Ported, pending live verification (fresh-install path not run for real, to avoid disrupting the currently-running Claude Code session — but its component logic verified live: real platform detection `linux-x64`, real version resolution `2.1.212`, real checksum pulled from the manifest; already-installed path run live twice on this machine, correctly printed the real installed version both times) | `deploys/claude.py` |
| `fbg` | Ported (work-specific, hostname-auto-gated like `bootstrap/run.sh`). NOT run for real or via `--dry` on this non-FBG machine after a mistake during development (see "`--dry` does NOT protect immediate execution" below) — code review only. Needs live verification on an actual FBG machine before removing from playbook.yml | `deploys/fbg.py` |
| `ssh-bastion-client` | Not started | — |

**`zerobrew`** (no Ansible equivalent — new, opt-in): builds/installs `zb`/`zbx` from
`github.com/tstapler/zerobrew` (branch `linux-reflink-ficlone`, a fork adding a Linux
btrfs/XFS reflink fast path upstream only has for macOS). Built from source, not a
downloaded binary, so it's auditable. Runs alongside Homebrew, never replacing it — off
by default (`--data zerobrew_enabled=true` to turn on), since building Rust from source
is slow and this is experimental. `deploys/zerobrew.py`. Verified live: correctly no-ops
when disabled, correctly skips the rustup/clone/build steps when `zb` is already built
(confirmed both paths on this machine).

A role only moves to "Done" once: it's been run for real (not just `--dry`), a second
run confirms zero changes (idempotency), and it's removed from
`bootstrap/playbook.yml`'s `roles:` list. Once every role above is "Done", `bootstrap/`
(Ansible + Mitogen) gets deleted and this directory is renamed to `bootstrap/`.

## Critical rule: queued operations vs. immediate execution

pyinfra queues operations (`brew.packages`, `files.download`, `server.shell`, etc.) and
only actually runs them in a separate "execute" phase, after **all** prepare-time Python
across the entire deploy file (every function called from `main.py`) has finished
running. Any `host.get_fact()` call — including `common.shell_ok`/`shell_capture` — runs
**immediately**, during prepare, regardless of what operations have been queued before
it.

Confirmed empirically: queuing a `files.file` operation to create a file, then
immediately checking for that file with a fact, reports it as **not existing** — the
queued operation hasn't run yet. It only exists once the whole pyinfra invocation
finishes.

This bit `homebrew.py` and `asdf.py`: an immediate check ("is `brew`/`asdf` installed,
does `brew bundle check` pass") was checking state that an *earlier-queued* install
operation hadn't actually produced yet. It didn't show up in testing because this
machine already had everything installed — it would have broken on a genuinely fresh
machine, which is the actual point of a bootstrap script.

**The rule going forward:** if *anything* later in the same run — same deploy, or a
later-called deploy in `main.py` — needs to immediately check or use the result of an
install/creation step, that step must run via `shell_capture`/`shell_ok` (immediate),
not a queued operation. Queued operations are fine only for steps nothing else in the
same run depends on seeing completed (e.g. a final symlink, a last cleanup step).
`_if` (pyinfra's execution-time-deferred condition) does not fix this for plain Python
logic — it only defers whether an *operation's own* commands run, not values used by
ordinary code (parsing a file, building a command string, branching).

## `--dry` does NOT protect immediate execution — learned the hard way

`--dry` only withholds **queued** pyinfra operations from actually running. Plain
Python and `shell_capture`/`shell_ok` calls (the immediate-execution style used
throughout this project, per the rule above) run for real regardless of `--dry` —
because they're not operations at all, pyinfra has no way to intercept them.

This bit `deploys/fbg.py` directly: it's entirely immediate-execution (by design, per
its own docstring), and running it with `--dry` on this (non-FBG, personal) development
machine — intending a safe, side-effect-free check — actually wrote `~/.gitconfig.fbg`
(a real work email/identity), created `~/.ssh/config` from scratch, wrote SSH host
aliases, created `~/WorkProjects/`, and made a real SSH connection + `git clone` attempt
against a private repo. All of it had to be manually reverted. The clone attempt
happened to fail harmlessly (no access to the private repo from this account), but nothing
about `--dry` prevented any of it from being attempted for real.

**The rule:** never invoke an immediate-execution deploy function directly to "test"
it — not even with `--dry` — unless you've read every line and are certain none of it
has real side effects (network calls, file writes, subprocess calls with mutating
intent). For anything with real side effects that shouldn't run outside its intended
target (e.g. `fbg.py` outside an actual FBG machine), the only safe verification is
static code review, or testing individual pure-logic helpers in isolation with paths/
inputs that can't touch real state.

## Project layout

- `inventory.py` — single `@local` host, no SSH.
- `group_data/all.py` — static config only (Ansible group_vars equivalent). Anything
  OS/arch-dependent does NOT belong here — group_data is evaluated before any host is
  connected, so it can't call `host.get_fact()`.
- `common.py` — the dynamic equivalent of `playbook.yml`'s `pre_tasks` (`is_wsl`,
  `brew_prefix`, `is_archlinux`, `github_personal_user`), computed via facts at deploy
  time.
- `deploys/` — one module per ported role, `@deploy`-decorated functions, called from
  `main.py` in the same order as `playbook.yml`'s `roles:` list.
- `operations/` — custom operations for the two confirmed gaps in pyinfra's built-ins:
  GPG signature verification (`gpg.verify`) and PAM-file-with-backup (handled inline in
  `deploys/sudo_mfa.py` via `server.shell` + `files.put`, not worth its own operation
  for a single use site).

## Tooling

```bash
make pyinfra-lint   # ruff + mypy, from repo root
make pyinfra-dry     # dry-run against this machine, from repo root
make ready           # runs both of the above alongside the existing ansible-lint/shellcheck checks
```

mypy runs in `strict` mode; pyinfra's `@operation`/`@deploy` decorators don't preserve
type information (confirmed upstream issue, not fixable from here), so decorated
functions carry a documented `# type: ignore[attr-defined]` on their pyinfra imports.
