# Tyler Stapler's Dotfiles

This repo holds the configuration, scripts, and AI tooling I use across the various machines I own. Over the years it has quietly grown from a `.zshrc` and a `.vimrc` into a personal monorepo for everything that follows me from machine to machine.

My primary machines run Manjaro Linux and Ubuntu Linux. My work machines are typically Macs. There are still a few bits to make the original Windows Subsystem for Linux work from a brief stint of using Windows at work.

## Getting Started

I install my dotfiles to a new machine using [this bootstrap script](./stapler-scripts/bootstrap-dotfiles.sh) (Windows users can use [`bootstrap-dotfiles.ps1`](./stapler-scripts/bootstrap-dotfiles.ps1)). It clones this repo and symlinks files into my home directory using [cfgcaddy](https://github.com/tstapler/cfgcaddy), a tool I wrote. The link map lives in [`.cfgcaddy.yml`](./.cfgcaddy.yml).

You can use alternatives such as [GNU Stow](https://www.gnu.org/software/stow/) or [yadm](https://yadm.io/docs/overview), which have more users and likely fewer bugs 😉.

The key idea is that you keep your dotfiles in a git repo somewhere like `$HOME/dotfiles` and symlink them into `$HOME` so other tools can find them.

Once you have that system set up, you can copy pieces of my configuration piecemeal. I don't recommend copying everything directly — this repo has grown organically over the years, so it contains plenty of configuration you may not want.

## Repo Layout

This repo doubles as my personal monorepo for anything I want versioned and synced across machines:

| Path | What's in it |
|---|---|
| [`.zshrc`](./.zshrc), [`.zplug_packages.zsh`](./.zplug_packages.zsh), [`.shell/`](./.shell) | Shell configuration, plugin manifest, and sourced helper scripts |
| [`.vimrc`](./.vimrc), [`.vimrc.plug`](./.vimrc.plug), [`.vim/`](./.vim), [`.vimsnippets/`](./.vimsnippets) | Vim/Neovim configuration and snippets |
| [`.config/`](./.config) | XDG config for Neovim, fish, goose, MCP, opencode, and more |
| [`.tmux.conf`](./.tmux.conf), [`.tmux/`](./.tmux) | tmux config with version-specific include files |
| [`.claude/`](./.claude) | Claude Code agents, commands, skills, and project instructions |
| [`.claude-plugin/`](./.claude-plugin), [`plugins/`](./plugins) | Claude Code plugin marketplace and the `sdd` plugin |
| [`.opencode/`](./.opencode) | opencode commands and skills |
| [`.gitconfig`](./.gitconfig), [`.gittemplates/`](./.gittemplates) | Global git config and shared hook templates |
| [`.fonts/`](./.fonts) | Powerline-patched fonts I keep around |
| [`stapler-scripts/`](./stapler-scripts) | Personal scripts symlinked into `~/bin/scripts` |
| [`cfgcaddy/`](./cfgcaddy), [`.cfgcaddy.yml`](./.cfgcaddy.yml) | Symlinking tool config |

## Features

### zsh

I have a fairly comprehensive [zsh configuration](./.zshrc).

[zplug](https://github.com/zplug/zplug) is my package manager. You can find the package manifest in [`.zplug_packages.zsh`](./.zplug_packages.zsh) — it installs both zsh plugins and a few binaries. [Powerlevel10k](./.p10k.zsh) drives the prompt.

The [`.shell/`](./.shell) directory contains scripts sourced from [`.zshrc`](./.zshrc); their names should be reasonably self-explanatory:

- [`aliases.sh`](./.shell/aliases.sh), [`functions.sh`](./.shell/functions.sh), [`exports.sh`](./.shell/exports.sh) — the usual suspects
- [`languages.sh`](./.shell/languages.sh) — language toolchain bootstrapping (see asdf below)
- [`osx.sh`](./.shell/osx.sh) — macOS-specific tweaks
- [`rust.sh`](./.shell/rust.sh) — Rust/cargo environment
- [`secrets.op.sh.tpl`](./.shell/secrets.op.sh.tpl), [`setup_1password.sh`](./.shell/setup_1password.sh) — 1Password CLI integration for secrets

### Vim and Neovim

I'm a heavy Vim user, so I have configuration for [IntelliJ's IdeaVim plugin](./.ideavimrc) as well as [actual Vim](./.vimrc), split across a few files. The Neovim init file is symlinked from the same `.vimrc` (see [`.cfgcaddy.yml`](./.cfgcaddy.yml)).

### Language management with asdf

I'm a polyglot when it comes to programming languages, so I use [asdf](https://github.com/asdf-vm/asdf) to manage language versions consistently across my machines.

- [`.tool-versions`](./.tool-versions) sets the global language version used across the system.
- [`.shell/languages.sh`](./.shell/languages.sh) installs the language-specific plugins.

### tmux

[`.tmux.conf`](./.tmux.conf) loads version-specific config from [`.tmux/`](./.tmux) so the same file works across the older tmux on long-lived servers and the latest tmux on my laptop.

### Git

Global git config lives in [`.gitconfig`](./.gitconfig). [`.gittemplates/hooks`](./.gittemplates/hooks) contains shared hooks linked into new clones via the `init.templateDir` setting.

### Claude Code, agents, and skills

The [`.claude/`](./.claude) directory is where most of the recent growth has happened. It is the source of truth for my Claude Code setup and gets symlinked into `~/.claude` on every machine:

- [`CLAUDE.md`](./.claude/CLAUDE.md), [`STAPLER.md`](./.claude/STAPLER.md), [`RTK.md`](./.claude/RTK.md) — project-wide instructions, the Manifest-Driven Development workflow, and notes for the Rust Token Killer proxy
- [`agents/`](./.claude/agents) — specialized subagents (PR review, Java/Go test debugging, postgres optimization, knowledge synthesis, and friends)
- [`commands/`](./.claude/commands) — slash commands organized by domain: `code/`, `db/`, `docs/`, `git/`, `github/`, `jira/`, `jj/`, `knowledge/`, `meta/`, `pm/`, `plan/`, `quality/`, `skill/`, `ux/`
- [`skills/`](./.claude/skills) — reusable skill definitions covering debugging, refactoring, testing, frontend design, knowledge synthesis, and more
- [`skills-index.md`](./.claude/skills-index.md) — a flat index that gets pulled into every session

The [`.claude-plugin/marketplace.json`](./.claude-plugin/marketplace.json) registers a small plugin marketplace, and [`plugins/sdd/`](./plugins/sdd) contains the Stapler-Driven Development plugin (a spec-before-code workflow with phase-gated commands).

[`.opencode/`](./.opencode) mirrors a smaller version of this for [opencode](https://opencode.ai).

### Personal scripts

[`stapler-scripts/`](./stapler-scripts) is symlinked into `~/bin/scripts` and is on my `PATH`. It collects everything I've written or vendored over the years, including:

- Bootstrap scripts ([`bootstrap-dotfiles.sh`](./stapler-scripts/bootstrap-dotfiles.sh), [`bootstrap-notes.sh`](./stapler-scripts/bootstrap-notes.sh), [`bootstrap.yaml`](./stapler-scripts/bootstrap.yaml))
- Ansible roles for setting up new machines ([`roles/`](./stapler-scripts/roles), [`requirements.yml`](./stapler-scripts/requirements.yml))
- LSP installers and wrappers for Clojure and Kotlin
- Proxies and helpers for LLM tooling ([`claude-proxy`](./stapler-scripts/claude-proxy), [`litellm-proxy`](./stapler-scripts/litellm-proxy), [`llm-sync`](./stapler-scripts/llm-sync))
- Git utilities ([`fix_git_emails`](./stapler-scripts/fix_git_emails), [`set_git_emails`](./stapler-scripts/set_git_emails), [`check_commit_email`](./stapler-scripts/check_commit_email), [`git-filter-repo`](./stapler-scripts/git-filter-repo))
- One-off scripts I refused to throw away ([`mkpdf`](./stapler-scripts/mkpdf), [`har2img.py`](./stapler-scripts/har2img.py), [`slack-emoji-export`](./stapler-scripts/slack-emoji-export), [`write-better`](./stapler-scripts/write-better), and so on)

### Other configuration

A non-exhaustive list of the rest:

- [`.aider.conf.yml`](./.aider.conf.yml) — aider AI pair programming config
- [`.config/goose/`](./.config/goose), [`.config/mcp/`](./.config/mcp), [`.config/opencode/`](./.config/opencode) — other AI tools
- [`.config/nvim/`](./.config/nvim) — Neovim-specific config (coc settings)
- [`.config/fish/`](./.config/fish) — fish shell config (used occasionally)
- [`.config/nixpkgs/`](./.config/nixpkgs) — Nix home-manager config
- [`.config/zathura/`](./.config/zathura), [`.config/terminator/`](./.config/terminator), [`.config/regolith/`](./.config/regolith) — Linux desktop apps
- [`.i3/`](./.i3) — i3 window manager
- [`.idea/`](./.idea), [`.ideavimrc`](./.ideavimrc) — JetBrains IDE settings
- [`.mixxx/`](./.mixxx), [`.qlcplus/`](./.qlcplus) — DJ and lighting controller configs
- [`hosts.yaml`](./hosts.yaml), [`icmp_hosts.yaml`](./icmp_hosts.yaml) — Ansible inventory
