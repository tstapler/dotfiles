# ADR-003: Replace vim-airline with lualine.nvim as the statusline

**Status**: Accepted
**Date**: 2026-07-15
**Deciders**: Tyler Stapler
**Related**: research/stack.md, research/features.md §2, `.vimrc.dein` lines 138-139, 525-543

## Context

The current config uses `vim-airline` + `vim-airline-themes` (`.vimrc.dein` lines 138-139) with gruvbox theming and a coc-status integration (`set statusline^=%{coc#status()}...`, line 345). Removing coc.nvim breaks that statusline integration, so the statusline must be reconsidered regardless. vim-airline is vimscript, its config is scattered (lines 525-543), and it pulls `vim-airline-themes` as a second plugin.

## Decision

**Adopt `nvim-lualine/lualine.nvim`, themed to match the retained gruvbox colorscheme, and remove `vim-airline` + `vim-airline-themes`.**

## Rationale

- lualine is the near-universal modern Lua statusline; it reads native `vim.diagnostic` counts, LSP client name, and git branch directly — replacing the coc-status integration that native LSP removes.
- Single plugin (built-in themes, including gruvbox) vs. airline's two-plugin split.
- Config lives in one place in `lua/tstapler/plugins/ui.lua` alongside the colorscheme, fixing airline's scattered-config problem.
- Fast, lazy-loadable on `VeryLazy`, and its `sections` API cleanly surfaces the LSP/diagnostics/git info an IntelliJ transplant expects in the chrome.

## Consequences

- `lua/tstapler/plugins/ui.lua` owns colorscheme (gruvbox) + lualine together.
- Drop the `%{coc#status()}` statusline line and `g:airline_*` variables.
- lualine integrates with gitsigns' `b:gitsigns_status_dict`, so the git branch/diff-count segment lands for free once ADR/plan's gitsigns story is done.

## Alternatives Rejected

| Alternative | Reason rejected |
|---|---|
| `mini.statusline` | Lighter and fine, but lualine has broader gruvbox theme parity with the current look, larger reference base, and richer LSP/diagnostics segments matching the "IDE-like" goal. |
| Keep vim-airline | Vimscript, two plugins, scattered config, and its coc-status integration dies with coc removal anyway — no reason to preserve it through a rewrite. |
| Native `statusline` string, no plugin | Minimal, but hand-rolling diagnostics/LSP/git segments re-implements what lualine already ships; not worth the effort for a personal config. |
