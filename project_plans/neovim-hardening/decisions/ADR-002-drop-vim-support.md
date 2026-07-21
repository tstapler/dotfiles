# ADR-002: Full Lua rewrite; drop plain-vim support entirely

**Status**: Accepted
**Date**: 2026-07-15
**Deciders**: Tyler Stapler
**Related**: research/architecture.md §3 (Option C), research/build-vs-buy.md, requirements.md (Scope: vimscript-vs-Lua decision)

## Context

`.vimrc` (226 lines) is today a genuinely shared vim+nvim file — it has `has('nvim')` branches, sources `~/.vimrc.dein` (a symlink to `.vimrc.plug`, which bootstraps lazy.nvim), and is symlinked by cfgcaddy to **both** `~/.vimrc` and `~/.config/nvim/init.vim`. Architecture.md laid out three options:

- **A** — shared vimscript core + Lua IDE layer in heredocs (`has('nvim')`-gated).
- **B** — full Lua rewrite; freeze `.vimrc` as a legacy snapshot for bare vim.
- **C** — full Lua rewrite; drop bare-vim support entirely.

Architecture.md recommended **C with a cheap pre-check**: confirm bare `vim` (not `nvim`) is genuinely unused before deleting its config; fall back to B if the check fails.

## Decision

**Adopt Option C: build a Neovim-only `init.lua` + `lua/tstapler/` tree, and stop deploying `.vimrc` to nvim's config path.** Delete the vim-facing conditionals; do not carry a shared vimscript file forward for Neovim.

## Pre-check result (the load-bearing evidence)

Verified in this repo during planning:

- `.shell/aliases.sh:36` → `alias vim="nvim"`, guarded by `if [ "$EDITOR" = "nvim" ]`.
- `.shell/exports.sh` sets `EDITOR='nvim'` when nvim is on `$PATH`, and `GIT_EDITOR=$EDITOR`.
- The only `alias vim='vi'` (`.shell/exports.sh:92`) lives in the `else` branch that fires **only** on a box with neither nvim nor vim installed.

On the daily-driver machine (nvim 0.11.6 installed), every interactive `vim` invocation is aliased to `nvim`, and `$EDITOR`/`$GIT_EDITOR`/`core.editor` all resolve to `nvim`. Bare-vim usage is effectively zero. The pre-check passes → Option C is safe.

## Rationale

- Lowest long-term cost: one canonical config, one language, no permanent dual-maintenance burden.
- Directly serves the "audited, non-redundant, minimal" success metrics — no vim-compat cruft to reason about.
- The hardest work (coc → native LSP) is identical in size under A/B/C; only C also removes the maintainability defect and the dual-surface confusion.

## Consequences

- `.cfgcaddy.yml`: **delete** both `.vimrc → .config/nvim/init.vim` rename entries (Linux/Darwin and Windows). Leaving them would place a stale `init.vim` symlink beside the new `init.lua` — Neovim treats having both as an error/undefined-precedence condition (architecture.md §2). This removal must ship in the same change that adds the new tree.
- `.vimrc` still default-mirrors to `~/.vimrc` (no explicit entry needed), so the rare no-nvim fallback box keeps today's plain-vim experience unchanged. We are not deleting `.vimrc`; we are only stopping it from being nvim's config.
- Residual risk (accepted, low): a non-interactive context that hard-codes the bare `vim` binary (bypassing both the alias and `$EDITOR`) on a box that has vim but where we removed the nvim init — not a real scenario here, since we do not remove `.vimrc` itself.

## Alternatives Rejected

| Alternative | Reason rejected |
|---|---|
| Option A (heredoc Lua, has('nvim')-gated) | Papers over the core maintainability defect (declaration/config hundreds of lines apart, no `require()`, no per-file tooling); defers the load-bearing coc→LSP risk without buying safety. Wrong call for a "Large" appetite. |
| Option B (freeze `.vimrc` for bare vim) | The safe fallback if the pre-check had failed — but it didn't. B keeps a legacy surface for a use case that doesn't exist here. |
