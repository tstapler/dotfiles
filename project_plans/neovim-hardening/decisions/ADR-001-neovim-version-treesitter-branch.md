# ADR-001: Stay on Neovim 0.11.6 and pin nvim-treesitter to the frozen `master` branch

**Status**: Accepted
**Date**: 2026-07-15
**Deciders**: Tyler Stapler
**Related**: requirements.md (constraint "Must run on nvim 0.11.6"), research/stack.md §2 and §7, research/pitfalls.md §3

## Context

Two upstream events landed weeks before this project started and directly intersect the "nvim 0.11.6 minimum" constraint:

- **Neovim 0.12** released 2026-03-29 — ships built-in treesitter parser/query loading, a native plugin manager (`vim.pack`), and native LSP completion.
- **`nvim-treesitter/nvim-treesitter` was archived** by its maintainer on 2026-04-03 after a dispute over the `main` branch being rewritten to hard-require Neovim ≥0.12.

The repo now has two incompatible branches:
- `master` — **frozen** (no further parser/query updates) but fully functional on Neovim 0.11.x, and uses the classic `setup({ highlight = {...}, ensure_installed = {...} })` table that the entire current tutorial/reference ecosystem assumes.
- `main` — a full rewrite requiring Neovim ≥0.12; highlighting is no longer auto-enabled, parser installation is a separate explicit call, config style is entirely different.

The choice cascades: it determines the treesitter branch, whether `vim.pack` is a viable alternative to lazy.nvim, and whether to lean on Neovim's built-in LSP completion vs. blink.cmp.

## Decision

**Stay on Neovim 0.11.6 for this migration. Pin `nvim-treesitter` to `branch = "master"` and `nvim-treesitter-textobjects` to its matching branch. Do not bump Neovim to 0.12+ as part of this project.**

## Rationale

- The requirements pin 0.11.6 as the floor and never call for a version bump; adding an unplanned editor-version upgrade mid-migration compounds risk during a period when the config is already being torn down and rebuilt.
- The four in-scope languages (Go, Rust, Python, TS/JS) have mature, stable tree-sitter grammars on either branch — "frozen" costs nothing for these grammars in the near term.
- `master` matches the config idiom used by every reference snippet this project adapts (LazyVim extras, kickstart's debug.lua), reducing the API-drift/LLM-improvisation risk flagged in build-vs-buy.md.
- Constraints (solo, evenings/weekends, no CI) favor the lower-risk short-term path.
- lazy.nvim remains the correct plugin manager on 0.11.6; `vim.pack` and `mini.deps` are only live options on 0.12+, so this decision keeps lazy.nvim uncontested (stack.md §6).

## Consequences

- Positive: lowest-risk path; config style matches all reference material; no editor upgrade to coordinate.
- Negative: inheriting a now-unmaintained dependency; parser/query updates stop advancing on `master`.
- Follow-up: pin the treesitter revision via `lazy-lock.json` (committed — see ADR/plan). Treat `:TSUpdate` as a deliberate, reviewed action, never unattended — especially after a Manjaro `pacman -Syu` that bumps Neovim (pitfalls.md §3).
- Add a `max_filesize` guard in the treesitter config (from-scratch configs must add this manually or risk input lag on large generated files — features.md §3).
- **Revisit trigger**: schedule a future, separate project to move to Neovim 0.12+ built-in treesitter + `vim.pack` once the 0.12 ecosystem settles. This ADR deliberately defers, not rejects, that upgrade.

## Alternatives Rejected

| Alternative | Reason rejected |
|---|---|
| Upgrade to 0.12+, use built-in treesitter + `main` branch textobjects | More future-proof, but trades near-term migration safety for an unplanned editor bump during the highest-churn window; not required by any success metric. |
| Stay on 0.11.6 but track `main` branch | Incompatible — `main` hard-requires 0.12; would not load. |
| Drop treesitter entirely, keep vim-polyglot | Loses treesitter highlighting/folding/textobjects/incremental-selection that motivate the modernization; polyglot is the legacy approach being replaced. |
