# ADR-004: Replace NERDTree with oil.nvim (edit-directory-as-buffer)

**Status**: Accepted
**Date**: 2026-07-15
**Deciders**: Tyler Stapler
**Related**: research/ux.md §2 (project-tree mental model), `.vimrc.dein` line 144 + 424 (`<C-e> :NERDTreeToggle`)

## Context

The current config uses `preservim/nerdtree` as a permanent-drawer file explorer, toggled with `<C-e>` (`.vimrc.dein` line 424). ux.md's core finding is that Neovim-native "IDE" configs deliberately do **not** reproduce IntelliJ's always-visible left tree: fuzzy-find covers "I know roughly what I want" (the majority case), and the remaining "browse / rename / move files" case is best served by editing the directory as a normal buffer. A permanent sidebar costs fixed horizontal space the split model doesn't want to give up.

## Decision

**Adopt `stevearc/oil.nvim` as the file explorer and remove `nerdtree`.** Map `-` (oil's idiomatic default) to open the parent directory as a buffer, and keep `<C-e>` bound to an oil toggle to preserve muscle memory.

## Rationale

- oil.nvim edits a directory as a buffer: `dd` deletes a file, yank/paste copies/moves, normal `:w` commits the changes — no separate tree-navigation modal to learn. This matches ux.md's "translate the need, don't clone the panel" rule.
- Fuzzy-find (fzf-lua, ADR/plan finder story) already covers the "open a file I can name" case that NERDTree was mostly used for, so the explorer only needs to serve browse/manipulate — exactly oil's strength.
- Actively maintained, single plugin, integrates with the git/diagnostics ecosystem.

## Consequences

- `lua/tstapler/plugins/explorer.lua` owns oil.nvim; `<C-e>` and `-` bind through the safe-map registry (zero-duplicate guarantee).
- Remove the `<C-e> :NERDTreeToggle` mapping and the NERDTree plugin spec.
- No permanent drawer by default. If a persistent tree for exploring a large unfamiliar codebase turns out to be missed during dogfooding, `neo-tree.nvim` can be added later as an on-demand fallback — recorded as a deferred option, not built now (avoids reintroducing the sprawl the project is pruning).

## Alternatives Rejected

| Alternative | Reason rejected |
|---|---|
| `neo-tree.nvim` / `nvim-tree` (permanent drawer) | Reproduces the IntelliJ sidebar reflex ux.md explicitly advises against; costs fixed horizontal space; more config surface than the browse/manipulate need requires. Kept as a deferred fallback only. |
| Keep NERDTree | Vimscript, drawer-model, and being pruned anyway; oil is a strict ergonomic upgrade for the actual job. |
| No explorer, fuzzy-find only | Leaves the "rename/move/delete files without a shell" gap; oil fills it cheaply with one plugin. |
