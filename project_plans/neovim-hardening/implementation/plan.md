# Implementation Plan: neovim-hardening

**Feature**: Full Lua rewrite of Tyler's decade-old vimscript+coc.nvim Neovim config into a modular `init.lua` + `lua/tstapler/` tree on native LSP + DAP + treesitter, pruning ~50 plugins to an audited minimal set, migrating language-by-language (Go pilot first), on Neovim 0.11.6.
**Date**: 2026-07-15
**Status**: Ready for implementation
**System type**: Personal developer-tooling config migration — cross-cutting, Complexity 4, Large appetite (3–6 weeks)
**ADRs**: ADR-001 (stay on nvim 0.11.6 + treesitter `master`), ADR-002 (drop vim support, full Lua rewrite), ADR-003 (lualine statusline), ADR-004 (oil.nvim explorer)

---

## Step 0.5 — Creative pass: sequencing/rollout strategy (chosen + rejected)

Three high-level rollout strategies were considered (stack choices are already fixed by research; this is purely about ordering):

- **(a) Infrastructure-first** — get lazy.nvim, options, keymaps, statusline, explorer, fzf-lua, gitsigns, treesitter fully solid before touching any LSP. *Strength*: clean, stable foundation. *Weakness*: defers the load-bearing, highest-risk work (coc→native-LSP, DAP) to the very end — you don't learn whether the risky part works until weeks in.
- **(b) Pilot-language-first** — prove the full LSP+DAP+nav+git vertical on Go end-to-end before building shared infra. *Strength*: retires the biggest risk first. *Weakness*: builds LSP/DAP keymaps and treesitter before the shared keymap module and safe-map registry exist, guaranteeing rework of the keymap layer.
- **(c) Parallel-track** — interleave infra and pilot LSP work. *Weakness*: worst fit for a solo, evenings/weekends effort — context-switching cost and harder failure isolation.

**CHOSEN — Hybrid "thin-infra-then-pilot vertical"**: build only the shared foundation the pilot actually depends on (plugin manager, options, the keymap module + safe-map registry, treesitter, statusline, explorer, fzf-lua, gitsigns, and all the deletions/cutover isolation) in Phase 1, then immediately prove the *entire* LSP+DAP+nav+git vertical on Go end-to-end in Phase 2 before replicating it for Rust/Python/TS-JS. This front-loads the shared scaffolding that would otherwise force rework (strategy (a)'s benefit) while retiring the load-bearing LSP/DAP risk on one language as early as the foundation allows (strategy (b)'s benefit), without (c)'s context-switching tax.

Rejected approaches are recorded in Pattern Decisions below.

---

## Domain Glossary
| Term | Definition | Notes |
|------|-----------|-------|
| **plugin spec** | A lazy.nvim table describing one plugin (`{ "owner/repo", opts=…, config=…, keys=…, ft=… }`). | One spec's declaration and config live in the same table — the core fix for the current 565-line file's declaration/config separation. |
| **lazy-loading trigger** | The `event` / `ft` / `cmd` / `keys` key that defers a plugin's load until needed. | Correctness-first: use broad triggers (`VeryLazy`, `BufReadPre`) during migration, tighten only after smoke test (pitfalls.md §5). |
| **lazy-lock.json** | lazy.nvim's committed lockfile pinning every plugin to an exact commit. | **Committed** to the repo (multi-machine reproducibility, pitfalls.md §6). Lives at `.config/nvim/lazy-lock.json`. |
| **`vim.lsp.config()` / `vim.lsp.enable()`** | Neovim 0.11 native LSP API: `config()` registers a server's settings, `enable()` turns it on for matching filetypes. | The idiomatic 0.11 path (ADR-001). NOT the older `require('lspconfig').<server>.setup{}` (drift risk, build-vs-buy.md §4). |
| **LSP client** | A running language-server connection attached to a buffer (`gopls`, `rust-analyzer`, `basedpyright`, `vtsls`). | Invariant: **exactly one** client per buffer per filetype — never coc + native simultaneously (architecture.md §6). |
| **LspAttach / on_attach** | The autocmd/callback that wires buffer-local LSP keymaps once a client attaches. | Keymaps set here go through the safe-map registry too. |
| **root_dir / root-marker** | The project-root directory an LSP client uses, detected from markers (`go.mod`, `pyproject.toml`, `Cargo.toml`, `tsconfig.json`, `.git`). | Needs custom logic for monorepos + a single-file fallback (features.md §3). |
| **capabilities** | The client-capability table advertised to a server, extended by blink.cmp so completion works. | Easy-to-forget step: server attaches but completion stays basic if capabilities aren't passed (architecture.md §6.5). |
| **blink.cmp** | The completion engine (`saghen/blink.cmp`) replacing coc's completion popup. | LazyVim/kickstart default; supplies `capabilities` (stack.md §1). |
| **code-action popup** | `tiny-code-action.nvim`'s floating action list with a diff/preview of the effect before applying, bound to `gra` (overriding the 0.11 native default) and the `<leader>a` code-action-group key. | Replaces the raw `vim.lsp.buf.code_action()` prompt, which has no diff preview — Story 2.1.2 (ux.md §1d). |
| **mason.nvim tool** | A binary (LSP server / DAP adapter / linter) mason installs into `~/.local/share/nvim/mason/bin`. | `ensure_installed` declares required tools. Exception: rust-analyzer via `rustup`, not mason (pitfalls.md §2). |
| **DAP adapter** | The debug backend for a language (Delve, debugpy, codelldb) that nvim-dap talks to. | Adapter path should be hardcoded to `vim.fn.stdpath("data").."/mason/bin/…"`, not `$PATH` (pitfalls.md §2). |
| **DAP configuration** | A per-filetype Lua launch table (`dap.configurations.<ft>`) — the launch.json equivalent. | Global per filetype, not per project, unless per-project overrides added (pitfalls.md §2). |
| **treesitter parser** | A compiled grammar (`go`, `rust`, `python`, `typescript`) providing highlighting/folding/textobjects. | Pinned via lazy-lock; `:TSUpdate` is a deliberate reviewed action (ADR-001). |
| **safe-map registry** | Project helper (`lua/tstapler/util.lua`) wrapping `vim.keymap.set`; errors on any duplicate `(mode, lhs)`. | Enforces the "zero duplicate binds" acceptance criterion at startup across the whole config. |
| **gitsigns hunk** | A contiguous changed region gitsigns tracks in the sign column, stageable/resettable per-hunk. | Complements fugitive; not a replacement (ux.md §1c). |
| **NVIM_APPNAME** | Env var isolating a config's `~/.config/<name>` + `~/.local/share/<name>` + state/cache dirs. | Set to `nvim-next` during development to isolate runtime state from the live config (pitfalls.md §7). |
| **cfgcaddy mirror** | cfgcaddy's default behavior: every repo file links to the same relative `$HOME` path unless ignored. | `.config/nvim/**` mirrors automatically — no new `links:` entry needed (architecture.md §2). |
| **leader** | The `<space>` prefix key (`vim.g.mapleader = " "`). | Space is the single chosen leader (ux.md §0); the dead `,` declaration is deleted. |
| **vimwiki filetype** | The `filetype=vimwiki` applied to `~/personal-wiki/logseq/pages/*.md` buffers. | Must be excluded from treesitter/markdown-LSP handling to protect the live wiki (pitfalls.md §3). |

---

## Pattern Decisions
| Component | Pattern Chosen | Source | Alternative Rejected | Reason |
|-----------|---------------|--------|---------------------|--------|
| Module layout | `init.lua` + `lua/tstapler/{options,keymaps,autocmds,util}.lua` + `plugins/*.lua` (+ `plugins/lang/*.lua`), grouped by concern; `lazy.setup({ import = "tstapler.plugins" })` | architecture.md §1, kickstart/LazyVim | Single `init.lua`; or one-file-per-plugin (50+ files) | Single-file re-encodes the current declaration/config-separation defect; per-plugin adds navigation overhead. Group-by-concern is the sweet spot. |
| Base skeleton | Fork/adapt kickstart.nvim philosophy; assemble specs from community-tested references (LazyVim lang-extras, kickstart debug.lua, AstroCommunity) | build-vs-buy.md Opt 2/4 | Adopt LazyVim/AstroNvim/NvChad wholesale; or LLM-improvise specs | Distros reintroduce sprawl against the "minimal/audited" metric; hand-writing risks stale-API drift on 0.11's new `vim.lsp.config`. |
| LSP setup API | `vim.lsp.config()` + `vim.lsp.enable()` (0.11 native) with `nvim-lspconfig` as config source | stack.md §1, build-vs-buy.md §4 | `require('lspconfig').<server>.setup{}` | Older wrapper style is being displaced; native API is the forward-compatible 0.11 idiom. |
| Completion | `blink.cmp` | stack.md §1 | `nvim-cmp` (+ cmp-* sources); coc completion | blink is the 2026 LazyVim/kickstart default: faster, built-in fuzzy matcher, fewer source plugins. |
| Code-action UI | `tiny-code-action.nvim`, overriding native `gra` | ux.md §1d, Story 2.1.2 | Raw `vim.lsp.buf.code_action()` (0.11 native picker); `lspsaga.nvim`; `nvim-code-action-menu` | Native picker has no diff preview — a direct gap against the "refactor confidently without checking IntelliJ" goal. tiny-code-action.nvim is lightweight and actively maintained; lspsaga is heavier (bundles many unrelated UI features) and nvim-code-action-menu is less actively maintained. |
| Fuzzy finder | `fzf-lua` (single finder) | stack.md §3, ux.md §1a | Telescope; keep ctrlp/ctrlspace/fzf.vim | fzf binary already installed + in muscle memory; LazyVim 14 default; better on large repos. All 3 legacy finders removed. |
| Statusline | `lualine.nvim` | ADR-003 | vim-airline (+themes); mini.statusline | See ADR-003. |
| File explorer | `oil.nvim` | ADR-004, ux.md §2 | NERDTree; neo-tree permanent drawer | See ADR-004. |
| Treesitter version | nvim 0.11.6 + `nvim-treesitter` `branch = "master"` | ADR-001 | 0.12 + built-in TS + `main` branch | See ADR-001. |
| Git stack | Keep `vim-fugitive`; add `gitsigns.nvim`; drop Merginal + vimagit; `neogit`/`diffview.nvim` optional, sequenced last | stack.md §5, ux.md §1c/§5 | Rip out fugitive; add all git UIs up front | No consensus Lua fugitive replacement; gitsigns is pure addition; neogit/diffview are the modern swaps for the two redundant UIs but low-urgency. |
| DAP client | `nvim-dap` + `nvim-dap-ui` + `nvim-nio` + `nvim-dap-virtual-text` + `mason-nvim-dap` | stack.md §4 | nvim-dap-view (single-window) | dap-ui is the battle-tested default with broader adapter docs; dap-view noted as a future ergonomics experiment (ux.md §1b). |
| Rust tooling | `rustaceanvim` (manages rust-analyzer LSP + codelldb DAP itself) | stack.md §4, features.md §2 | `rust-tools.nvim`; raw nvim-dap Rust config | rust-tools archived Jan 2024, redirects to rustaceanvim; API-shape change, not a drop-in swap. |
| rust-analyzer install | `rustup component add rust-analyzer` (toolchain-matched) | pitfalls.md §2 | mason-managed rust-analyzer | Mason-pinned version drifts from the project toolchain → subtle macro/diagnostic mismatches. |
| Keymap uniqueness | `safe_map` registry in `lua/tstapler/util.lua`, errors on duplicate `(mode,lhs)` at startup | pitfalls.md §1/§4, ux.md §3 | Rely on manual review / `:verbose nmap` | Makes "zero duplicate binds" a self-enforcing startup invariant, not a hope. |
| Discoverability | `which-key.nvim` | ux.md §2/§3 | None (raw leader keys) | Highest-leverage discoverability plugin for an IntelliJ transplant; shows leader groups on hesitation. |
| Auto-install UX | mason `ensure_installed` + treesitter `auto_install` | ux.md §4 | Manual per-tool install | Turns "missing tool" from a standing silent failure into a one-time self-healing event — near-mandatory for the "works without IntelliJ" bar. |
| Rollout sequencing | Hybrid thin-infra-then-pilot vertical (Step 0.5) | Step 0.5 | Pure infra-first (a); pure pilot-first (b); parallel (c) | (a) defers load-bearing risk; (b) forces keymap rework; (c) worst for solo focus. |

---

## Migration Plan
*(Repurposed as the config cutover plan — not a schema migration. Live daily-driver; master stays usable until cutover.)*

- **Development isolation (resolves the pitfalls.md §7 NVIM_APPNAME gap)**: Do NOT re-point `~/.config/nvim` at the worktree during development. Instead symlink `~/.config/nvim-next -> <worktree>/.config/nvim` (one symlink, bypassing cfgcaddy) and always launch the new config as `NVIM_APPNAME=nvim-next nvim`. This isolates `~/.config/nvim-next`, `~/.local/share/nvim-next`, `~/.local/state/nvim-next`, `~/.cache/nvim-next` from the live `~/.config/nvim` + `~/.local/share/nvim` (coc/master) — so a broken Mason binary or half-updated plugin during testing cannot contaminate master's runtime state, and a mid-week emergency `nvim` still gets master's known-good setup. Add a shell alias `nvn='NVIM_APPNAME=nvim-next nvim'` for the dev loop (in a local, un-synced shell file, not committed).
- **Reversibility**: master branch is untouched throughout; the live `~/.config/nvim/init.vim -> .vimrc` symlink and coc setup keep working. Rollback at any pre-cutover point = keep using plain `nvim` (master) and delete the `~/.config/nvim-next` symlink. `lazy-lock.json` is committed so plugin versions validated in the worktree are exactly what cutover deploys.
- **Cutover strategy**: (1) Build entirely in the worktree under `NVIM_APPNAME=nvim-next`. (2) Progressively dogfood: once a language's phase smoke test passes **against one of Tyler's actual real projects for that language, not a toy example** (2.3.2 Go, 3.1.1b Rust, 4.1.1c Python, 5.1.1b TS/JS) and its coc-teardown task lands immediately after (2.3.3a Go, 3.1.1c Rust, 4.1.1d Python, 5.1.1c TS/JS), shift that language's real daily-driver work to `nvn` (see Risk Control's "Master stays the daily driver..." bullet) — until then, that language's real work stays on plain `nvim`/master. Once all four languages have shifted, dogfood a full week per the success metric using `nvn` for real daily work across all four languages. (3) Only when stable, merge `dotfiles-harden-neovim` → `master`. (4) The merge deletes the two `.vimrc → init.vim` cfgcaddy rename entries and the `coc-settings.json` link, and adds nothing (the `.config/nvim/` tree default-mirrors). (5) Run cfgcaddy install: `~/.config/nvim/init.vim` symlink disappears, `~/.config/nvim/init.lua` + `lua/**` + `lazy-lock.json` appear. (6) First plain `nvim` launch installs plugins/Mason tools from the committed lockfile.
- **Rollback procedure (mid-migration, per-language)**: if a language's real-project smoke test fails, or its native LSP/DAP breaks on real work *after* Tyler has already shifted that language's daily-driver use to `nvn`, rollback is per-language, not repo-wide: switch that language's daily-driver work back to plain `nvim`/master immediately. coc.nvim's extension for that language is still installed and functional on master — its teardown task (e.g. Task 2.3.3a for Go) only ever edits the `nvn` worktree's `autocmds.lua`/`g:coc_global_extensions`, never master's — so master's fallback needs zero repair and no `git revert` is needed. Any other language that has already progressively cut over keeps using `nvn` unaffected; only the broken language's daily use reverts, while the worktree keeps evolving to fix it and re-attempts its own cutover once fixed.
- **Rollback procedure (post-cutover)**: `git checkout master~1` (or revert the merge) in `~/dotfiles`, re-run cfgcaddy install to restore the `init.vim` symlink, relaunch `nvim`. The old coc config is fully intact because master before the merge was never modified. Because dev used a separate `NVIM_APPNAME`, master's `~/.local/share/nvim` (coc/lazy state) was never touched by testing, so rollback is genuinely clean — not just at the config-source level.

## Observability Plan
*(Not a service. Substitutes per requirements.md.)*
- **Accessibility statement**: Keyboard-only operation is preserved by construction — no plugin choice in this plan (oil.nvim, fzf-lua, which-key.nvim, tiny-code-action.nvim, gitsigns, nvim-dap-ui) introduces a mouse-only interaction; every action has a keyboard binding. Diagnostics and status signs use color AND text/icon, never color alone: native `vim.diagnostic` signs (Task 2.1.1a) render distinct glyphs per severity, not just a colored sign-column highlight, and lualine's diagnostics segment (Task 1.7.1a) renders severity counts as icon+number, not a bare color chip. This turns an otherwise-implicit property into a documented, deliberate check rather than an assumption.
- **Startup benchmark**: Capture baseline BEFORE any change: `nvim --startuptime /tmp/nvim-baseline.log` on master's config, 3 runs, record the final "NVIM STARTED" total. After each phase, `NVIM_APPNAME=nvim-next nvim --startuptime /tmp/nvim-next.log`, 3 runs. Also keep `dstein64/vim-startuptime` (`:StartupTime`) in the new config. Gate: new-config median total must be ≤ baseline median (Success Metric). If a phase regresses it, the regression is almost always over-eager `lazy = false`/`VeryLazy` left in from debugging (pitfalls.md §5) — convert to a proper `ft`/`cmd`/`keys` trigger before proceeding.
- **Smoke-test checklist** (run under `nvn` before calling any language story done — the per-language criteria appear in each Story's acceptance section). **Before that language's coc-teardown task specifically, this checklist must run against an existing real project Tyler actively works in for that language, not a toy/example repo** (Go: Story 2.3.2; Rust: Task 3.1.1b; Python: Task 4.1.1c; TS/JS: Task 5.1.1b) — pre-mortem.md P1 #3: a setup that only works on a toy repo but breaks on the real thing after the coc fallback is gone leaves no recovery path:
  - **LSP**: open a real file of the language → `:checkhealth vim.lsp` shows exactly ONE client attached for the buffer; `gd` jumps to definition; `grr` lists references; `grn` renames across files; `K` shows hover.
  - **DAP**: set a breakpoint, launch debug, confirm it stops, inspect a variable in dap-ui, step over, continue to exit.
  - **Fuzzy-find**: `<leader>ff` opens files with live preview; `<leader>fg` live-greps.
  - **Git**: edit a tracked file → gitsigns shows the hunk in the sign column; `<leader>hs` stages it; `:Git` (fugitive) opens status.
  - **No-duplicate-keymap**: config loads with zero errors (safe-map registry throws on any duplicate `(mode,lhs)` — see Story 1.3.1).

## Risk Control
- **Feature flag**: not gated — feature-branch worktree (`dotfiles-harden-neovim`) instead, per requirements.md Risk Control. No parallel-config env switching beyond the dev-only `NVIM_APPNAME=nvim-next` isolation.
- **NVIM_APPNAME isolation**: the `nvim-next` app-name (Migration Plan above) is the concrete mechanism making "the worktree isolates risk" true at the runtime-state level (shared `~/.local/share/nvim`, Mason binaries, lazy checkouts), not just the config-source level — closing the pitfalls.md §7 gap.
- **Rollback procedure**: pre-cutover — use plain `nvim` (master), delete `~/.config/nvim-next`. Mid-migration, per-language — see Migration Plan's "Rollback procedure (mid-migration, per-language)" bullet: switch just that language's daily use back to master; no repo-level action needed. Post-cutover — revert the merge in `~/dotfiles` + re-run cfgcaddy. Maintain a `REMOVED-PLUGINS.md` scratch list (dev-only, not committed) of every pruned plugin so a surfaced workflow gap can be re-added from a known list rather than rediscovered (pitfalls.md §4).
- **Staged rollout as staging**: the per-language sequence (Go pilot → Rust → Python → TS/JS) IS the staging strategy, and it applies to coc.nvim's teardown too — not just the native-LSP rollout. Each language's coc extension + `b:coc_enabled` disable is torn down only after that language's native LSP/DAP stack is proven **against a real project Tyler actively works in** (Task 2.3.3a for Go, 3.1.1c for Rust, 4.1.1d for Python, 5.1.1c for TS/JS — which also removes the `coc.nvim` plugin spec itself, since TS/JS is the last language). coc.nvim and a native client are never dual-run *persistently* for the SAME filetype (architecture.md §6/§4A) — the brief overlap between a language's real-project smoke test and its teardown task (both back-to-back within the same phase) is a deliberate, minimal-duration exception, not a standing violation; coc.nvim legitimately keeps serving every not-yet-migrated filetype throughout Phases 2-4. That is a required, deliberate state, not an oversight (pitfalls.md §1: migrate one language at a time, fully; never a global flip).
- **Master stays the daily driver for not-yet-migrated languages**: during Phases 2-5, Tyler's real daily-driver work for a language that hasn't reached its phase's coc-teardown task yet continues under plain `nvim` (master, coc.nvim fully intact for that language) — `nvn` is dev/test-only for that language until its phase's real-project smoke test and coc-teardown task both land, at which point daily use for that language shifts to `nvn` **immediately**, not waiting on the other languages. This was implicit in the NVIM_APPNAME isolation design; it is now an explicit rule, not an assumption a future reader has to infer.
- **Progressive cutover banks partial progress (go/no-go safety net)**: because each language's daily-driver shift happens the moment its own teardown lands, a stall or burnout after Phase 2 does not waste the work already done — Go's LSP/DAP win is already in real daily use and stays that way indefinitely, with zero dependency on Rust/Python/TS/JS ever landing. Story 2.3.2/2.3.3 (Go) is the de facto go/no-go checkpoint for the rest of the project: if it passes, the pattern is proven and worth replicating; if the project stops there, nothing already shipped needs to be reverted (pre-mortem.md P1 #1).
- **Cutover muscle-memory friction (acknowledged, mitigated lightly)**: during the multi-week progressive per-language cutover, Tyler alternates between master's old flat/ad-hoc leader keys and `nvn`'s new grouped scheme depending on which language he's touching that day — a real, if minor, daily friction cost the Migration Plan should name rather than leave implicit. Mitigation: keep a printed/pinned one-page keymap cheat-sheet, generated from `lua/tstapler/leader_groups.lua` (the single source of truth already established, Task 1.3.2b), covering the new grouped scheme, visible during the transition weeks (Task 1.3.2c). This is a small, one-time generation step, not a new feature.

## Unresolved Questions
- [ ] Does cfgcaddy symlink `.config/nvim` as one directory unit or file-by-file? If file-by-file, adding a new `plugins/*.lua` requires re-running cfgcaddy install. — blocks confident multi-machine deploy — owner: Tyler (cheap empirical check, Task 1.6.2a). Dev loop is unaffected (dev uses a manual `~/.config/nvim-next` symlink).
- [ ] Are there personal UltiSnips-format snippets in `~/.vimsnippets` still in daily use that must be ported to LuaSnip/blink? — blocks Story 5-adjacent snippet parity (deferred; inventory in Task 1.6.3a) — owner: Tyler.
- [ ] Is per-project DAP launch config (different args/env/cwd per project) needed, or is one global config per filetype enough for now? — blocks Story 2.3.x scope — owner: Tyler (default: global-per-filetype; revisit if a real project needs overrides).
- [ ] Does `vim-ctrlspace`'s session/workspace persistence need a replacement (mksession autosave / persistence.nvim)? — blocks final pruning sign-off — owner: Tyler (Task 7.3.1a verifies before deleting).

## Dependency Visualization
```
Phase 1: SHARED INFRA (thin foundation the pilot needs)
  1.1 bootstrap ─┐
  1.2 options ───┤
  1.3 keymaps + safe-map registry ──┐
  1.4 which-key ─┤                   │
  1.5 treesitter (ADR-001) ──────────┤
  1.6 deletions + cfgcaddy + isolation setup
  1.7 statusline(ADR-003)+explorer(ADR-004)+fzf-lua+gitsigns+fugitive
                 │
                 ▼
Phase 2: GO PILOT (proves the full vertical end-to-end)
  2.1 mason+blink.cmp+ale-removal ──▶ 2.2 gopls ──▶ 2.3.1 nvim-dap core + nvim-dap-go
      (coc.nvim + coc-go UNTOUCHED;                       (DAP proven on Go;
       both epics run with coc-go                          coc-go still live in parallel)
       still live in parallel)
                 │
                 ▼
        2.3.2: REAL-PROJECT smoke test — one of Tyler's actual
               Go repos (a real go.work multi-module workspace if
               he has one in daily use), NOT a toy example —
               full LSP+DAP+nav+git checklist must pass on it
                 │  passes
                 ▼
        2.3.3a: coc-go torn down ONLY NOW (gated on 2.3.2 passing) —
                coc.nvim STAYS installed for Rust/Python/TS/JS,
                per pitfalls.md §1. Go's daily-driver work shifts
                to nvn immediately (go/no-go checkpoint banked).
                 │
                 ▼
        ┌────────┼────────┐            (Phases 3-5 replicate the proven LSP+DAP pattern —
        ▼        ▼        ▼             each already runs its OWN real-project smoke test
Phase 3: RUST   Phase 4: PYTHON   Phase 5: TS/JS       BEFORE tearing down that language's coc
 rustaceanvim    basedpyright+ruff  vtsls + treesitter  extension, same as Go now does)
 (LSP+codelldb)  + nvim-dap-python  (+ optional JS DAP = stretch)
 3.1.1b: real     4.1.1c: real       5.1.1b: real monorepo smoke
 multi-crate      asdf/direnv        test (mandatory, not "ideally")
 Cargo workspace  Python project     ──▶ 5.1.1c: coc-tsserver torn
 smoke test ──▶   smoke test ──▶     down AND coc.nvim plugin spec
 3.1.1c: coc-     4.1.1d: coc-       FULLY REMOVED (last language —
 rust-analyzer    pyright torn       does not wait on the 5.1.2
 torn down        down (coc.nvim     stretch DAP goal)
 (coc.nvim        still installed
 still installed  for TS/JS)
 for Python/TS/JS)
        └────────┼────────┘
                 ▼
Phase 6: GIT UI CONSOLIDATION (optional, last per ux.md) — neogit + diffview
                 ▼
Phase 7: CLEANUP + CUTOVER — .ideavimrc, vimwiki/markdown verify, final prune sweep, merge to master
```

---

## Phase 1: Shared infrastructure

### Epic 1.1: Bootstrap the Lua config tree
**Goal**: A loading `init.lua` + `lua/tstapler/` skeleton with lazy.nvim, isolated under `NVIM_APPNAME=nvim-next`, before any feature plugin exists.

#### Story 1.1.1: Create the init.lua bootstrap and module namespace
**As a** Neovim user, **I want** a thin `init.lua` that bootstraps lazy.nvim and requires my namespace, **so that** adding a plugin file never requires editing `init.lua`.
**Acceptance Criteria**:
- `NVIM_APPNAME=nvim-next nvim` starts with zero errors and `:Lazy` opens.
  - *Given* a fresh `~/.local/share/nvim-next` (no plugins installed), *When* I run `NVIM_APPNAME=nvim-next nvim` for the first time, *Then* lazy.nvim self-clones, the `:Lazy` UI is available, and `:messages` shows no errors.
- Leader is space, set before lazy loads.
  - *Given* the config is loaded, *When* I run `:echo mapleader`, *Then* it prints a single space and there is no `let mapleader=","` anywhere in the tree.
**Files**: `.config/nvim/init.lua`, `.config/nvim/lua/tstapler/init.lua`

##### Task 1.1.1a: Write init.lua bootstrap (~4 min)
- Port the lazy.nvim bootstrap block from `.vimrc.dein` lines 4-19 into `.config/nvim/init.lua` (Lua, no heredoc).
- Set `vim.g.mapleader = " "` and `vim.g.maplocalleader = "\\"` BEFORE `require("tstapler")` (pitfalls.md: leader before lazy).
- End with `require("tstapler")`.
- Files: `.config/nvim/init.lua`

##### Task 1.1.1b: Write namespace init.lua (~4 min)
- `lua/tstapler/init.lua` requires `options`, `keymaps`, `autocmds`, then calls `require("lazy").setup({ { import = "tstapler.plugins" }, { import = "tstapler.plugins.lang" } }, { lockfile = vim.fn.stdpath("config").."/lazy-lock.json" })`.
- Files: `.config/nvim/lua/tstapler/init.lua`

##### Task 1.1.1c: Set up NVIM_APPNAME dev isolation (~3 min)
- Create symlink `~/.config/nvim-next -> <worktree>/.config/nvim`.
- Add a dev-only (un-synced) alias `nvn='NVIM_APPNAME=nvim-next nvim'`.
- Capture the startup baseline first: `nvim --startuptime /tmp/nvim-baseline.log` on master (3 runs).
- Files: (no repo files — machine setup + `/tmp` baseline log)

### Epic 1.2: Port options and autocmds
**Goal**: Non-plugin editor settings and filetype rules moved from vimscript to Lua, minus vim-compat cruft.

#### Story 1.2.1: Port .vimrc Options block to options.lua
**As a** Neovim user, **I want** my editor options in `options.lua`, **so that** settings live in one typed Lua file without vim-only branches.
**Acceptance Criteria**:
- All still-relevant options from `.vimrc` lines 10-90 are present as `vim.opt.*`; vim-only branches dropped.
  - *Given* the new config loaded, *When* I run `:set number? mouse? undofile? inccommand?`, *Then* `number`, `mouse=a`, `undofile`, and `inccommand=nosplit` are all set as in the old `.vimrc`.
**Files**: `.config/nvim/lua/tstapler/options.lua`

##### Task 1.2.1a: Translate options to vim.opt (~5 min)
- Port `.vimrc` lines 17-83: `mouse+=a`, `showcmd`, `magic`, `wildmenu`/`wildmode`, `incsearch`, `number`, `laststatus=2`, `autoread`, `listchars`, `undodir`/`undofile`, `signcolumn=yes`, `updatetime=300` (from `.vimrc.dein` 222/226), `hidden`, `nobackup`/`nowritebackup`.
- DROP: `t_Co`, the `if !has("nvim")` ttymouse block, the `if exists('&inccommand')` guard (0.11 always has it → set directly), the zsh/bash `set shell` block (keep only if smoke test needs it).
- Files: `.config/nvim/lua/tstapler/options.lua`

#### Story 1.2.2: Port filetype autocmds to autocmds.lua (excluding the markdown/vimwiki race)
**As a** Neovim user, **I want** my per-filetype indent settings in `autocmds.lua`, **so that** the 12+ filetype tabstop rules survive the rewrite without the broken markdown override.
**Acceptance Criteria**:
- Each `au FileType` indent rule from `.vimrc` 133-218 is reproduced via `vim.api.nvim_create_autocmd("FileType", …)`; the global `*.md → filetype=mkd` autocmd (lines 203-208) is NOT ported.
  - *Given* a Go file is opened, *When* I check `:setlocal tabstop? shiftwidth?`, *Then* both are 2 and expandtab is on (matching old `.vimrc` line 161).
  - *Given* a file under `~/personal-wiki/logseq/pages/foo.md` is opened, *When* I run `:set filetype?`, *Then* it is `vimwiki` (or markdown), never `mkd` — the racing override is gone (Story 7.2.1 finalizes wiki protection).
**Files**: `.config/nvim/lua/tstapler/autocmds.lua`

##### Task 1.2.2a: Port FileType indent autocmds (~5 min)
- Port indent rules for: docker-compose, ts/typescript, make (noexpandtab), python, javascript, go, ruby, java, vim, yml, fish, c, sh, haproxy, dart, html.
- OMIT the `augroup markdown` block (lines 203-208) entirely — replaced by controlled markdown handling in Phase 7.
- Port the `YankBufferFilename()` function (`.vimrc.dein` 185-189) here — it has no plugin dependency. The `vim-oscyank` `TextYankPost` autocmd from the same block is NOT ported here; it moves to `editing.lua`, colocated with the `vim-oscyank` plugin spec (Task 1.7.5a), to avoid recreating the declaration/config-separation defect the module-per-file layout exists to prevent (architecture-review.md concern #4).
- Files: `.config/nvim/lua/tstapler/autocmds.lua`

### Epic 1.3: Keymap module with zero-duplicate enforcement
**Goal**: A single non-plugin keymap module plus a safe-map registry that makes duplicate binds a hard startup error.

#### Story 1.3.1: Build the safe-map registry
**As a** config author, **I want** a `map()` wrapper that errors on any duplicate `(mode, lhs)`, **so that** the current config's silent double-binds (`<leader>f`, `<leader>a`/`<space>a`) can never recur.
**Acceptance Criteria**:
- `require("tstapler.util").map(mode, lhs, rhs, opts)` registers a bind and calls `error()` if the same `(mode, lhs)` is registered twice.
  - *Given* two calls `map("n","<leader>f",...)` and `map("n","<leader>f",...)`, *When* the config loads, *Then* Neovim throws `duplicate keymap: n <leader>f` at startup and `:messages` names both — the config refuses to load silently-broken.
  - *Given* all real keymaps across the whole config use `map()`, *When* the config loads cleanly, *Then* `<leader>f`, `<leader>a`, `gd`, `gr`, `<leader>w` each resolve to exactly one binding (verify `:verbose nmap <leader>f`).
  - *Given* a plugin needs lazy.nvim's own `keys=` spec field for force-loading (e.g. DAP, Task 2.3.1a), *When* those binds are declared, *Then* each `(mode, lhs)` is still registered in the same collision table via `reserve()` (below), so the "zero duplicate binds" invariant covers lazy-loaded plugin keys too, not just direct `map()` calls (architecture-review.md concern #1).
**Files**: `.config/nvim/lua/tstapler/util.lua`

##### Task 1.3.1a: Implement safe_map with a module-level registry (~5 min)
- Registry table keyed `mode.."\0"..lhs`; on collision, `error("duplicate keymap: "..mode.." "..lhs)`; else record and call `vim.keymap.set`.
- Export `map` and a `map_group(mode, {lhs=…})` convenience.
- Export `reserve(mode, lhs)`: registers `(mode, lhs)` in the SAME collision table as `map()` (same error on duplicate) but does NOT call `vim.keymap.set` — for plugins whose keys are actually bound later by lazy.nvim's own `keys=` mechanism (force-load triggers), so those binds still participate in the duplicate-bind invariant instead of being an unacknowledged blind spot.
- Files: `.config/nvim/lua/tstapler/util.lua`

#### Story 1.3.2: Port non-plugin keymaps + establish the space-leader group scheme
**As a** Neovim user, **I want** my global keymaps and a documented leader-group scheme, **so that** bindings are consistent and discoverable (which-key), with none of the old collisions.
**Acceptance Criteria**:
- Non-plugin maps from `.vimrc` (F3 quickfix cycle, `Y→y$`, F7 terminal) are ported via `map()`; leader groups (`f`ind/`c`ode/`d`ebug/`g`it/`h`unk) are defined once in `leader_groups.lua` and reserved/documented from there.
  - *Given* the config loaded, *When* I press `Y` in normal mode, *Then* it yanks to end of line (old `.vimrc` line 99).
  - *Given* I press `<F7>`, *When* zsh is available, *Then* a `:new term://zsh` split opens (old `.vimrc` line 104).
  - *Given* `leader_groups.lua` is the single source of truth, *When* a group is renamed there, *Then* both `keymaps.lua`'s header comment and `which-key.lua`'s registration reflect it without a second edit (architecture-review.md concern #3).
**Files**: `.config/nvim/lua/tstapler/keymaps.lua`, `.config/nvim/lua/tstapler/leader_groups.lua`

##### Task 1.3.2a: Port global keymaps (~4 min)
- Port: `<F3>`/`<S-F3>` quickfix cycle, `Y`→`y$`, `<F7>` terminal (Lua `has` check via `vim.fn.executable`).
- Add a header comment that documents the leader-group scheme by referencing `lua/tstapler/leader_groups.lua` (Task 1.3.2b) — e.g. "leader groups: see `require('tstapler.leader_groups')`, the single source of truth" — rather than re-listing the f/c/d/g/h/e/w prefixes inline, so the comment cannot drift out of sync with the table which-key.lua actually registers (architecture-review.md concern #3).
- Files: `.config/nvim/lua/tstapler/keymaps.lua`

##### Task 1.3.2b: Create the shared leader_groups.lua module (~2 min)
- New file returning a plain table: `return { f = "find", c = "code", d = "debug", g = "git", h = "hunk", e = "explorer", w = "window" }` (prefixes per ux.md §3).
- This becomes the single source of truth both `keymaps.lua`'s header comment (Task 1.3.2a) and `which-key.lua`'s group registration (Task 1.4.1a) read from — a comment alone cannot enforce sync (architecture-review.md concern #3), so the value lives in exactly one executable place.
- Files: `.config/nvim/lua/tstapler/leader_groups.lua`

##### Task 1.3.2c: Generate a one-page keymap cheat-sheet from leader_groups.lua (~3 min)
- Small script/one-liner (Lua or shell) that iterates `require("tstapler.leader_groups")` (Task 1.3.2b) plus the per-group leaf bindings already documented across Stories 1.3.2/1.7.x/2.x, and renders a one-page printable/pinnable reference (plain text or Markdown is fine — no tooling investment beyond this) of the new grouped leader scheme.
- Purpose: mitigate the muscle-memory friction of alternating between master's old flat leader keys and `nvn`'s new grouped scheme during the multi-week progressive cutover (Risk Control: "Cutover muscle-memory friction"). Keep it visible (printed or pinned) during the transition weeks.
- Files: (dev-only scratch output; not a committed repo file unless Tyler wants it kept as `docs/keymap-cheatsheet.md`)

### Epic 1.4: Discoverability
**Goal**: which-key surfaces leader groups so the keyboard-only scheme is learnable.

#### Story 1.4.1: Add which-key.nvim
**As an** IntelliJ transplant, **I want** a popup showing available leader keys on hesitation, **so that** I don't have to memorize the whole scheme at once.
**Acceptance Criteria**:
- which-key shows the leader group menu, sourced from `leader_groups.lua`, not an independently-maintained table.
  - *Given* the config loaded, *When* I press `<leader>` and wait ~0.5s, *Then* a popup lists groups `f find / c code / d debug / g git / h hunk` with their labels.
**Files**: `.config/nvim/lua/tstapler/plugins/which-key.lua`

##### Task 1.4.1a: Add which-key spec + register group labels (~4 min)
- Spec `folke/which-key.nvim`, `event = "VeryLazy"`; register group names by iterating `require("tstapler.leader_groups")` (Task 1.3.2b) rather than re-declaring the f/c/d/g/h/e/w prefix table inline — this is the other consumer of the single source of truth (architecture-review.md concern #3).
- Files: `.config/nvim/lua/tstapler/plugins/which-key.lua`

### Epic 1.5: Treesitter (ADR-001)
**Goal**: treesitter highlighting/folding/textobjects for the four languages, pinned to `master`, with the large-file guard and vimwiki exclusion.

#### Story 1.5.1: Configure nvim-treesitter on the master branch
**As a** Neovim user, **I want** treesitter highlighting/folding/incremental-selection for go/rust/python/ts/js and config filetypes, **so that** I get modern syntax awareness without vim-polyglot.
**Acceptance Criteria**:
- Parsers install and highlight; large files and vimwiki are guarded.
  - *Given* a `.go` file open, *When* I run `:InspectTree`, *Then* a parse tree renders and `:checkhealth nvim-treesitter` shows the `go` parser OK.
  - *Given* a 60k-line generated file, *When* I open it, *Then* treesitter highlighting is skipped (size guard) and there is no input lag.
  - *Given* a `~/personal-wiki/logseq/pages/*.md` (filetype `vimwiki`) buffer, *When* it opens, *Then* treesitter does NOT attach a markdown parser to it (no `no parser for 'vimwiki'` error).
**Files**: `.config/nvim/lua/tstapler/plugins/treesitter.lua`

##### Task 1.5.1a: Add treesitter spec pinned to master + textobjects (~5 min)
- `nvim-treesitter/nvim-treesitter` `branch = "master"`, `build = ":TSUpdate"`; `nvim-treesitter/nvim-treesitter-textobjects` matching branch.
- `ensure_installed = { go, rust, python, typescript, tsx, javascript, lua, vimdoc, bash, yaml, json, markdown, markdown_inline }`; `auto_install = true`; `highlight = { enable = true, disable = function(lang, buf) ... end }` disabling on `vimwiki` filetype AND on files > `max_filesize` (~100KB).
- Keep `Konfekt/FastFold` (stack.md §2); set treesitter folding via `foldexpr`.
- Files: `.config/nvim/lua/tstapler/plugins/treesitter.lua`

### Epic 1.6: Deletions, cfgcaddy cleanup, migration debt
**Goal**: Remove the dead files and the conflicting cfgcaddy entries so the new tree deploys cleanly.

#### Story 1.6.1: Delete the three orphaned legacy files
**As a** maintainer, **I want** the unsourced legacy files gone, **so that** the Success Metric "zero dead config files" is met.
**Acceptance Criteria**:
- `.vimrc.local`, `.vimrc.bundles.local`, `.vimrc.plug` are deleted; `.vimrc.dein` symlink is deleted; nothing sources them.
  - *Given* the repo after this story, *When* I `grep -rn "vimrc.local\|vimrc.bundles.local\|vimrc.plug\|vimrc.dein" .`, *Then* there are no remaining `source`/reference hits (only historical plan docs).
**Files**: `.vimrc.local`, `.vimrc.bundles.local`, `.vimrc.plug`, `.vimrc.dein`

##### Task 1.6.1a: Delete orphaned files (~2 min)
- Delete `.vimrc.local` (NeoBundle/YCM era), `.vimrc.bundles.local` (NeoBundle), `.vimrc.plug` (the real lazy bootstrap, now superseded by `init.lua`), and the `.vimrc.dein` symlink.
- Confirm `.vimrc` no longer needs its `source ~/.vimrc.dein` block — but `.vimrc` is retained for the no-nvim fallback (ADR-002), so leave `.vimrc` itself in place, unmodified except as Story 1.6.4 dictates.
- Files: (deletions)

#### Story 1.6.2: Remove conflicting cfgcaddy entries and confirm mirror behavior
**As a** maintainer, **I want** the `.vimrc → init.vim` renames and the coc-settings link removed, **so that** no stale `init.vim` sits beside the new `init.lua`.
**Acceptance Criteria**:
- Both `.vimrc → init.vim` entries (Linux/Darwin lines 15-17, Windows lines 30-32) and the `.config/nvim/coc-settings.json` entry (line 18) are removed from `.cfgcaddy.yml`; the `.vimsnippets` stale dein dest is pruned.
  - *Given* `.cfgcaddy.yml` after this story, *When* I search it for `init.vim`, *Then* there are zero matches, and `.config/nvim/init.lua` mirrors by default with no explicit entry.
**Files**: `.cfgcaddy.yml`

##### Task 1.6.2a: Empirical cfgcaddy directory-vs-file check (~3 min)
- Touch a temp file under an existing dir-linked path (e.g. `.claude/skills/`) and check if it appears under `~/.claude/skills/` without re-running cfgcaddy. Record whether linking is directory-level or file-level (Unresolved Question #1).
- If file-level: document "re-run cfgcaddy install after adding a new `plugins/*.lua`" in the cutover checklist.
- Files: (investigation; note result in this plan / cutover checklist)

##### Task 1.6.2b: Edit .cfgcaddy.yml (~3 min)
- Remove the two `.vimrc → init.vim` link blocks (Linux/Darwin + Windows).
- Remove the `.config/nvim/coc-settings.json` link (coc is being deleted).
- Remove the `.vim/bundle/.dein/stapler-snips` dest from the `.vimsnippets` entry (architecture.md §0 migration debt) after confirming nothing reads it.
- Files: `.cfgcaddy.yml`

#### Story 1.6.3: Delete coc-settings.json and inventory snippets
**As a** maintainer, **I want** `coc-settings.json` removed and my personal snippets inventoried, **so that** coc's config surface is gone and no personal snippets are silently lost.
**Acceptance Criteria**:
- `.config/nvim/coc-settings.json` is deleted; a snippet inventory of `~/.vimsnippets` exists (Unresolved Question #2).
  - *Given* the repo after this story, *When* I look for coc config, *Then* `.config/nvim/coc-settings.json` does not exist.
  - Note: the proselint/languagetool `diagnostic-languageserver` linters in the old coc-settings (for text/vimwiki) are prose tools, out of scope; record them in the inventory as "not reimplemented unless missed."
**Files**: `.config/nvim/coc-settings.json`

##### Task 1.6.3a: Inventory ~/.vimsnippets and delete coc-settings.json (~3 min)
- List `~/.vimsnippets` contents; note any personal (non-vendored) UltiSnips-format snippets for possible LuaSnip port (deferred, Unresolved Question #2).
- Delete `.config/nvim/coc-settings.json`.
- Files: `.config/nvim/coc-settings.json` (delete); inventory note (dev-only)

#### Story 1.6.4: Trim .vimrc vim/nvim-shared cruft (fallback file only)
**As a** maintainer, **I want** `.vimrc` reduced to a clean plain-vim fallback, **so that** it stops implying it configures Neovim.
**Acceptance Criteria**:
- `.vimrc` no longer sources `~/.vimrc.dein` and no longer carries the dead `let mapleader=","` as if nvim reads it; it remains a working minimal plain-vim config for the no-nvim box (ADR-002).
  - *Given* `.vimrc` after this story, *When* I read it, *Then* there is no `source ~/.vimrc.dein` line and a header comment states "plain-vim fallback only; Neovim is configured in .config/nvim/".
**Files**: `.vimrc`

##### Task 1.6.4a: Prune .vimrc plugin-manager source + add fallback header (~3 min)
- Remove the `Plugin Manager` block (`.vimrc` lines 121-129) that sources `~/.vimrc.dein`; replace the `else colorscheme slate` with a plain `colorscheme slate`.
- Add a top comment: fallback-only, see `.config/nvim/`.
- Leave the options/mappings/autocmds intact (harmless for the rare bare-vim case).
- Files: `.vimrc`

### Epic 1.7: Core UI, navigation, git ambient layer
**Goal**: statusline, explorer, single fuzzy-finder, and gitsigns + fugitive — the shared surface the pilot builds on. (Editing plugins that survive pruning also land here.)

#### Story 1.7.1: Statusline (lualine) + colorscheme (ADR-003)
**As a** Neovim user, **I want** lualine with gruvbox, **so that** I keep my look and get LSP/diagnostics/git segments, replacing airline + coc-status.
**Acceptance Criteria**:
- lualine renders with gruvbox; airline is gone.
  - *Given* the config loaded, *When* I open any file, *Then* a lualine statusline shows mode/branch/filename/diagnostics and `:echo exists(':AirlineToggle')` is 0.
**Files**: `.config/nvim/lua/tstapler/plugins/ui.lua`

##### Task 1.7.1a: Add gruvbox + lualine specs (~4 min)
- `morhetz/gruvbox` (or `ellisonleao/gruvbox.nvim`) set as colorscheme, `background=dark`; `nvim-lualine/lualine.nvim` `event = "VeryLazy"`, theme `gruvbox`, sections with `diagnostics` + `branch` + `diff`.
- Files: `.config/nvim/lua/tstapler/plugins/ui.lua`

#### Story 1.7.2: File explorer (oil.nvim) (ADR-004)
**As a** Neovim user, **I want** oil.nvim, **so that** I browse/rename/move files as a buffer instead of a NERDTree drawer.
**Acceptance Criteria**:
- oil opens the parent dir as a buffer; NERDTree is gone.
  - *Given* an open file, *When* I press `-`, *Then* oil opens its parent directory as an editable buffer; `<C-e>` toggles oil; `:echo exists(':NERDTreeToggle')` is 0.
**Files**: `.config/nvim/lua/tstapler/plugins/explorer.lua`

##### Task 1.7.2a: Add oil.nvim spec + keymaps (~4 min)
- `stevearc/oil.nvim`; `map("n","-", …)` and `map("n","<C-e>", …)` via safe-map.
- Files: `.config/nvim/lua/tstapler/plugins/explorer.lua`

#### Story 1.7.3: Single fuzzy-finder (fzf-lua)
**As a** Neovim user, **I want** fzf-lua as my one finder, **so that** files/grep/buffers/symbols share one UI, replacing ctrlp + ctrlspace + fzf.vim + ctrlsf.
**Acceptance Criteria**:
- `<leader>f*` pickers work with preview; the three legacy finders are gone.
  - *Given* a git repo open, *When* I press `<leader>ff`, *Then* an fzf-lua file picker opens with a live preview pane; `<leader>fg` live-greps; `:echo exists(':CtrlP')` is 0.
**Files**: `.config/nvim/lua/tstapler/plugins/finder.lua`

##### Task 1.7.3a: Add fzf-lua spec + finder keymaps (~5 min)
- `ibhagwan/fzf-lua`; map `<leader>ff` files, `<leader>fg` live_grep, `<leader>fb` buffers, `<leader>fr` oldfiles, `<leader>fh` helptags, `<leader>fd` diagnostics (all via safe-map).
- Reserve `<leader>fs`/`<leader>fS` (document/workspace symbols) for the LSP phase.
- Files: `.config/nvim/lua/tstapler/plugins/finder.lua`

#### Story 1.7.4: Git ambient layer (gitsigns + fugitive)
**As a** Neovim user, **I want** gitsigns hunks + fugitive, **so that** I get inline hunk awareness/staging and keep fugitive's status/blame, dropping Merginal + vimagit.
**Acceptance Criteria**:
- gitsigns shows/stages hunks; fugitive `:Git` works; Merginal/vimagit gone.
  - *Given* a tracked file with one edited line, *When* I view it, *Then* gitsigns marks the hunk in the sign column, `<leader>hs` stages it, `]c`/`[c` navigate hunks, and `:Git` opens fugitive status; `:echo exists(':Merginal')` is 0.
**Files**: `.config/nvim/lua/tstapler/plugins/git.lua`

##### Task 1.7.4a: Add gitsigns + fugitive specs + hunk keymaps (~5 min)
- `lewis6991/gitsigns.nvim` with `on_attach` binding `<leader>hs` stage, `<leader>hr` reset, `<leader>hp` preview, `<leader>hb` blame line, `]c`/`[c` nav (all via safe-map); `tpope/vim-fugitive` (`cmd = {"Git","G"}`), map `<leader>gg` → `:Git`.
- Files: `.config/nvim/lua/tstapler/plugins/git.lua`

#### Story 1.7.5: Port surviving editing/utility plugins
**As a** Neovim user, **I want** my kept editing plugins re-declared, **so that** surround/commentary/repeat/undotree/oscyank/table-mode etc. keep working.
**Acceptance Criteria**:
- Surviving editing plugins load; vim-repeat kept alongside vim-surround (dependency, pitfalls.md §4).
  - *Given* the config loaded, *When* I run `ysiw"` then `.`, *Then* surround applies and `.` repeats it (proves vim-surround + vim-repeat both present).
**Files**: `.config/nvim/lua/tstapler/plugins/editing.lua`

##### Task 1.7.5a: Add editing-plugin specs (~5 min)
- Keep: `tpope/vim-surround`, `tpope/vim-commentary`, `tpope/vim-repeat`, `tpope/vim-speeddating`, `tpope/vim-abolish`, `mbbill/undotree`, `ojroques/vim-oscyank`, `dhruvasagar/vim-table-mode`, `godlygeek/tabular`, `christoomey/vim-sort-motion`, `christoomey/vim-titlecase`, `triglav/vim-visual-increment`, `chrisbra/NrrwRgn`, `dstein64/vim-startuptime`, `Konfekt/FastFold`.
- Add the `vim-oscyank` `TextYankPost` autocmd (ported from `.vimrc.dein` 185-189, moved from `autocmds.lua` per Task 1.2.2a) inline in this file, colocated with the `vim-oscyank` spec's `config`/`init` function — its declaration and its behavior-defining autocmd now live in one file instead of two (architecture-review.md concern #4).
- Consider native alternatives noted but not required now (e.g. commentary → 0.10 native `gc`); keep tpope versions for muscle-memory stability this pass.
- Files: `.config/nvim/lua/tstapler/plugins/editing.lua`

##### Task 1.7.5b: Add wiki + writing plugin specs (preserve, do not improve) (~5 min)
- `wiki.lua`: `tstapler/vimwiki` (`lazy = false` — vimwiki mis-detects under `ft=` lazy-loading, build-vs-buy.md §1), `michal-h21/vim-zettel`; port `g:vimwiki_list`/`g:zettel_format`/`g:vimwiki_table_mappings` as `vim.g.*` (architecture.md §5).
- `writing.lua`: `junegunn/goyo.vim`, `junegunn/limelight.vim`, `amix/vim-zenroom2`, `vim-pandoc/*` (3), `rhysd/vim-grammarous`, `jamessan/vim-gnupg`; port their `g:` settings and the `<leader>z`→`:Goyo` map (via safe-map).
- Files: `.config/nvim/lua/tstapler/plugins/wiki.lua`, `.config/nvim/lua/tstapler/plugins/writing.lua`

---

## Phase 2: Go LSP + DAP pilot (proves the full vertical)

### Epic 2.1: Native LSP core + completion
**Goal**: mason + blink.cmp + the native LSP scaffolding (LspAttach keymaps, diagnostics config) — coc.nvim itself, and Go's coc extension specifically, stay fully installed and untouched throughout this Epic. Go's coc.nvim teardown is deliberately deferred to Story 2.3.3, gated on gopls (Epic 2.2) and DAP (Epic 2.3) passing a real-project smoke test (Story 2.3.2) — not bundled into this scaffolding work, so a gap that only shows up on Tyler's actual repos is caught while coc-go is still the working fallback (pre-mortem.md P1 #3). coc.nvim and a native client are never dual-run *persistently* for the SAME filetype (architecture.md §4A) — the brief overlap between Story 2.3.2's real-project smoke test and Story 2.3.3's teardown is a deliberate, minimal-duration exception (see Story 2.3.2's testing note), not a standing violation.

#### Story 2.1.1: Add mason + native-LSP scaffolding + blink.cmp
**As a** Neovim user, **I want** the native LSP core and completion engine wired, **so that** any language server can attach with one consistent keymap/diagnostics/completion setup, before any per-language coc.nvim teardown happens (teardown is Story 2.3.3, gated on a real-project smoke test — pre-mortem.md P1 #3).
**Acceptance Criteria**:
- ale + coc-only completion-source plugins are removed; mason, blink.cmp, and the LspAttach keymap/diagnostic scaffolding exist (no server enabled yet); coc.nvim ITSELF, and Go's coc extension specifically, are untouched by this story.
  - *Given* the config loaded, *When* I run `:Mason`, *Then* the Mason UI opens and `:checkhealth vim.lsp` shows no attached clients (no server enabled yet — expected).
  - *Given* an `LspAttach` fires later, *When* a client attaches, *Then* buffer-local `gd`/`grr`/`grn`/`gra`/`K` are wired once (via safe-map) — verified in Story 2.2.1.
  - *Given* this story has landed but gopls has not yet been configured (Epic 2.2), *When* a `.go`/`.rs`/`.py`/`.ts` file is opened, *Then* coc.nvim still attaches and provides LSP features for every one of those filetypes exactly as before, and `:checkhealth vim.lsp` shows zero active native clients for any of them.
  - *Given* a Mason tool install fails (offline/rate-limited), *When* the install attempt runs, *Then* a clear `vim.notify` error surfaces within a bounded timeout instead of a silent hang or raw registry output (Task 2.1.1d, validation.md `mason_install_failure_should_surface_clear_error_not_silent_hang`).
**Files**: `.config/nvim/lua/tstapler/plugins/lsp.lua`, `.config/nvim/lua/tstapler/plugins/completion.lua`

##### Task 2.1.1a: Add mason + lsp scaffolding (~5 min)
- `mason-org/mason.nvim`, `mason-org/mason-lspconfig.nvim`, `neovim/nvim-lspconfig`.
- `LspAttach` autocmd wiring buffer-local keymaps via safe-map: keep 0.11 native defaults (`grn`,`gra`,`grr`,`gri`,`grt`,`gO`,`K`) and ADD `gd`→`vim.lsp.buf.definition`, `gy`→`vim.lsp.buf.type_definition`, `<leader>fs`→fzf-lua document symbols, `<leader>fS`→workspace symbols.
- Note: `gra` is Neovim 0.11's own built-in default (not registered via `safe_map` here) — Story 2.1.2 later overrides it with `tiny-code-action.nvim`'s popup-preview picker via an explicit `safe_map` call, which is the first registration of `(n, "gra")` in the collision table, so there is no duplicate-bind conflict.
- `vim.diagnostic.config({ virtual_text = true, signs = true })` (ux.md §2: enable explicitly).
- Files: `.config/nvim/lua/tstapler/plugins/lsp.lua`

##### Task 2.1.1b: Add blink.cmp + capabilities (~4 min)
- `saghen/blink.cmp` (`version = '*'`); export a `capabilities` helper (`require('blink.cmp').get_lsp_capabilities()`) consumed by every `vim.lsp.config`.
- Map snippet expand/jump to sensible keys (replace old `<C-l>`/`<C-j>` coc-snippets binds) via safe-map.
- Files: `.config/nvim/lua/tstapler/plugins/completion.lua`

##### Task 2.1.1c: Remove ale + coc-only completion-source plugins (~3 min)
- Ensure NO `w0rp/ale`, `Shougo/neoinclude.vim`, `Shougo/neco-syntax`, `Shougo/neco-vim`, `ujihisa/neco-look`, `Shougo/context_filetype.vim`, `Chiel92/vim-autoformat` specs exist in the new tree (they were never ported — this task is the audit that confirms none leaked in).
- These are safe to remove globally now, unlike coc.nvim's per-language LSP extensions: none of them are filetype-scoped LSP clients competing with a not-yet-migrated language's coc extension, so removing them doesn't risk the "two LSP clients for one filetype" hazard that Story 2.3.3's coc.nvim teardown must avoid.
- Files: (audit of `.config/nvim/lua/tstapler/plugins/**`)

##### Task 2.1.1d: Wire Mason install-failure notification path (~4 min)
- Native LSP fails silently when a server isn't installed/attached (ux.md §4); `ensure_installed` (Task 2.2.1a etc.) closes the "not yet installed" case but not the "install itself failed" case (offline, GitHub rate-limited, corporate proxy) — a cross-machine risk given cfgcaddy sync (adversarial-review.md CONCERN, closed by validation.md's `mason_install_failure_should_surface_clear_error_not_silent_hang`).
- Hook `mason-registry`'s package `on("install:failed", ...)` event (or wrap `MasonInstall`/`ensure_installed` triggers) with a `vim.notify(..., vim.log.levels.ERROR)` wrapper naming the failed tool and the likely cause (network/rate-limit), so a failed install surfaces a clear, actionable message instead of a silent hang or a wall of raw registry output.
- Acceptance is the validation.md check `mason_install_failure_should_surface_clear_error_not_silent_hang`: with network disabled, a fresh `:MasonInstall gopls` must show the clear failed-state notification within a bounded timeout, not hang silently.
- Files: `.config/nvim/lua/tstapler/plugins/lsp.lua`

#### Story 2.1.2: Add code-action preview popup (replaces raw native picker)
**As an** IntelliJ transplant, **I want** a floating code-action list with a diff preview before applying, **so that** I can refactor with the same "see it before you commit it" confidence as IntelliJ's Alt+Enter quick-fix popup, instead of the plain native picker (ux.md §1d).
**Acceptance Criteria**:
- `gra` opens `tiny-code-action.nvim`'s popup (navigable j/k, diff preview, Enter to apply) instead of the raw `vim.lsp.buf.code_action()` prompt.
  - *Given* a client has attached with at least one available code action, *When* I press `gra` (or `<leader>a`), *Then* a floating popup lists the actions with a diff/preview of each action's effect, and `<CR>` applies the highlighted one.
  - *Given* the safe-map registry, *When* the popup's `gra` override is registered, *Then* it is the ONLY registration of `(n, "gra")` — Task 2.1.1a deliberately left it as Neovim's built-in default rather than pre-registering it, so no duplicate-bind error fires here.
**Files**: `.config/nvim/lua/tstapler/plugins/lsp.lua`

##### Task 2.1.2a: Add tiny-code-action.nvim spec + gra/`<leader>a` override (~4 min)
- `rachartier/tiny-code-action.nvim` (`event = "LspAttach"` or lazy-loaded alongside the LSP scaffolding); wire `gra` and `<leader>a` via `require("tstapler.util").map("n", "gra", require("tiny-code-action").code_action, {...})` (safe-map), overriding the native default with the popup-with-preview UI.
- Default choice per ux.md §1d: `tiny-code-action.nvim` (lightweight, actively maintained) over `lspsaga.nvim` (heavier, bundles unrelated UI) or `nvim-code-action-menu` (less actively maintained) — see Pattern Decisions.
- Files: `.config/nvim/lua/tstapler/plugins/lsp.lua`

### Epic 2.2: gopls
**Goal**: Go code intelligence at IntelliJ parity via gopls on the native client.

#### Story 2.2.1: Enable gopls with root detection and single-file fallback
**As a** Go developer, **I want** gopls attached with correct roots, **so that** definition/references/rename/refactor work without IntelliJ and exactly one client attaches.
**Acceptance Criteria**:
- gopls attaches once per Go buffer; core LSP ops work; single-file mode degrades gracefully.
  - *Given* a Go file in a `go.mod` project with gopls attached, *When* I press `grn` on a variable, *Then* it renames across all files in the package and `:checkhealth vim.lsp` shows exactly ONE active client for the buffer.
  - *Given* a bare `.go` file with no `go.mod`/`.git`, *When* I open it, *Then* gopls still attaches in single-file mode (no crash) with a `vim.notify` if cross-file features are unavailable.
  - *Given* the Go smoke test (LSP section of Observability Plan), *When* run end-to-end, *Then* `gd`, `grr`, `grn`, `K` all pass.
  - *Given* Story 2.3.3 (coc-go teardown) has not yet landed, *When* gopls attaches per the above, *Then* coc-go may still also be providing completions/diagnostics for the same buffer in parallel — a deliberate, brief overlap that ends once Story 2.3.3's real-project-gated teardown lands (Story 2.3.2/2.3.3), not a regression.
**Files**: `.config/nvim/lua/tstapler/plugins/lang/go.lua`

##### Task 2.2.1a: Configure gopls via vim.lsp.config/enable (~5 min)
- Adapt LazyVim's `lang.go` gopls settings; `vim.lsp.config("gopls", { capabilities, settings = {...}, root_markers = {"go.work","go.mod",".git"} })`; `vim.lsp.enable("gopls")`.
- mason `ensure_installed = { "gopls" }`.
- Files: `.config/nvim/lua/tstapler/plugins/lang/go.lua`

### Epic 2.3: nvim-dap core + Go debugging (proves DAP end-to-end, then gates coc-go teardown)
**Goal**: The full DAP stack plus Go's plug-and-play adapter, establishing the DAP pattern the later languages reuse — then, ONLY once a real-project smoke test proves the whole vertical (Story 2.3.2), tear down coc-go (Story 2.3.3). This epic owns the gate: no coc-go teardown happens anywhere in Phase 2 until this epic's real-project smoke test passes.

#### Story 2.3.1: Add nvim-dap + dap-ui + Go adapter
**As a** Go developer, **I want** breakpoint/step/inspect debugging for Go, **so that** I stop switching to IntelliJ to debug — the core "removes the IntelliJ-to-debug habit" metric for Go.
**Acceptance Criteria**:
- Delve-backed debugging works with dap-ui; breakpoints bind even though dap is lazy-loaded.
  - *Given* a Go program with a breakpoint set via `<leader>db` on line N, *When* I press `<leader>dc` to launch, *Then* execution stops at line N, dap-ui shows the variable scope, `<leader>do` steps over, and `<leader>dc` continues to exit.
  - *Given* a Go test file, *When* I run debug-nearest-test (nvim-dap-go), *Then* the single test runs under the debugger and stops at a breakpoint inside it.
  - *Given* the DAP keymaps are defined, *When* a breakpoint is set before dap loads, *Then* the keymap force-loads dap first so the breakpoint binds (pitfalls.md §2 — use lazy `keys`, not raw maps).
**Files**: `.config/nvim/lua/tstapler/plugins/dap.lua`, `.config/nvim/lua/tstapler/plugins/lang/go.lua`

##### Task 2.3.1a: Add nvim-dap core stack (~5 min)
- `mfussenegger/nvim-dap`, `rcarriga/nvim-dap-ui` + `nvim-neotest/nvim-nio` (hard dep), `theHamsta/nvim-dap-virtual-text`, `jay-babu/mason-nvim-dap.nvim`.
- DAP keymaps via lazy `keys` (force-load, needed so a breakpoint set before dap loads still binds — pitfalls.md §2): `<leader>db` toggle breakpoint, `<leader>dc` continue, `<leader>di` step into, `<leader>do` step over, `<leader>dO` step out, `<leader>dr` repl, `<leader>du` toggle dap-ui. Before building the `keys` array, call `require("tstapler.util").reserve(mode, lhs)` for each of these `(mode, lhs)` pairs so they're checked against the same duplicate-bind registry `map()` uses (architecture-review.md concern #1) — `reserve()` only records the collision entry, it does not itself bind; lazy.nvim's `keys=` field still does the actual `vim.keymap.set` when the plugin force-loads.
- `dap-ui` auto-open/close on session events; `vim.notify` fallback when no config exists for the filetype (ux.md §4).
- Files: `.config/nvim/lua/tstapler/plugins/dap.lua`

##### Task 2.3.1b: Add nvim-dap-go + Delve (~4 min)
- `leoluz/nvim-dap-go`, `require('dap-go').setup()`; adapter `command` hardcoded to `stdpath("data").."/mason/bin/dlv"` (pitfalls.md §2); mason-nvim-dap `ensure_installed = { "delve" }`.
- Files: `.config/nvim/lua/tstapler/plugins/lang/go.lua`

#### Story 2.3.2: Pilot sign-off — full-stack Go smoke test on a real project + startup check
**As a** maintainer, **I want** the whole Go vertical validated against a real Go codebase Tyler actively works in — not a toy/single-module example — **so that** a gap that only shows up on real project layouts (e.g. a `go.work` multi-module workspace) surfaces while coc-go is still installed as a fallback (pre-mortem.md P1 #3), and the proven pattern can be replicated for Rust/Python/TS.
**Acceptance Criteria**:
- All five smoke-test sections pass on Go against an existing real project Tyler actively works in (not a fresh `go mod init test` toy example), and startup hasn't regressed.
  - *Given* gopls is configured (Story 2.2.1) and DAP is wired (Story 2.3.1), *When* opened against one of Tyler's actual multi-package Go repos — including a real `go.work` multi-module workspace if he has one in daily use, not a toy example — *Then* go-to-definition/references/rename resolve correctly across package (and module, for `go.work`) boundaries, `:checkhealth vim.lsp` shows one client, and the DAP breakpoint/step/inspect flow works against that real project's actual build/run configuration.
  - *Given* the Observability Plan smoke-test checklist, *When* run on that real Go project under `nvn`, *Then* LSP + DAP + fuzzy-find + git + no-duplicate-keymap all pass.
  - *Given* 3 `--startuptime` runs of the new config, *When* compared to `/tmp/nvim-baseline.log`, *Then* the median total is ≤ baseline.
  - *Given* coc-go is still installed and enabled at this point (Story 2.3.3 has not run yet), *When* isolating gopls for a clean test is useful, *Then* Tyler may temporarily run `:let b:coc_enabled=0` in that test buffer only (never committed to `autocmds.lua`) — if the real-project test then fails, nothing needs to be reverted because nothing was ever committed; coc-go keeps working exactly as it always has.
**Files**: (validation only — no new files)

##### Task 2.3.2a: Run Go smoke test against a real go.work/multi-module repo + record startup (~5 min)
- Execute the checklist against an existing real Go project Tyler actively works in (a `go.work` multi-module workspace if one is in daily use), not a fresh toy example; record startup medians; fix any over-eager loading before proceeding to Story 2.3.3's coc-go teardown.
- If the real-project test surfaces a gap gopls/delve don't handle, fix it here — coc-go is still the live fallback for daily Go work (Migration Plan), so there's no time pressure to skip this step.
- Files: (dev-only notes)

#### Story 2.3.3: Tear down coc.nvim's Go LSP-serving behavior (per-language teardown, gated on the real-project smoke test)
**As a** Neovim user, **I want** coc-go disabled only after gopls+delve have proven themselves on a real project, **so that** I never lose both the new tool and the old fallback at once (pre-mortem.md P1 #3).
**Acceptance Criteria**:
- coc-go is torn down ONLY after Story 2.3.2's real-project smoke test has passed; coc.nvim itself stays installed for Rust/Python/TS/JS.
  - *Given* Story 2.3.2's real-project smoke test has passed, *When* `coc-go` is removed from `g:coc_global_extensions` and the `b:coc_enabled=false` autocmd for `go` is committed to `autocmds.lua`, *Then* reopening a `.go` file shows `b:coc_enabled` is `0`, coc produces no diagnostics/completion for that buffer, and gopls (Story 2.2.1) is the sole client.
  - *Given* Story 2.3.2's real-project smoke test has NOT passed, *When* this story has not yet started, *Then* coc-go continues serving Go exactly as before — the explicit "do not proceed" branch that keeps the fallback alive if gopls/delve fail on Tyler's real repo.
**Files**: `.config/nvim/lua/tstapler/autocmds.lua`, wherever `g:coc_global_extensions` is declared

##### Task 2.3.3a: Disable coc.nvim's Go LSP-serving behavior only — per-language teardown, Go (~4 min)
- Precondition: Task 2.3.2a's real-project smoke test has passed. Do NOT run this task if it hasn't.
- Do NOT remove the `coc.nvim` plugin spec itself — Rust/Python/TS/JS still depend on it until Phases 3-5 land their native replacements (pitfalls.md §1: migrate one language at a time, fully; never a global flip).
- Remove `coc-go` from `g:coc_global_extensions`.
- Add `vim.api.nvim_create_autocmd("FileType", { pattern = "go", callback = function() vim.b.coc_enabled = false end })` in `autocmds.lua` — coc.nvim's documented per-buffer disable mechanism (`b:coc_enabled`). This is the real coc.nvim mechanism for this job; `g:coc_filetype_map` is NOT it (that remaps one filetype's server config onto another's, it doesn't disable coc for a filetype).
- `g:coc_global_extensions` is otherwise unchanged: `coc-rust-analyzer`, `coc-pyright`, `coc-tsserver` (or equivalents) stay installed and functioning for their filetypes until their own phase's teardown task (3.1.1c / 4.1.1d / 5.1.1c below).
- Once this lands, Tyler's real daily-driver Go work shifts to `nvn` immediately (Migration Plan / Risk Control "Master stays the daily driver..." bullet) — Go's win is now banked even if the rest of the migration stalls (pre-mortem.md P1 #1).
- Files: `.config/nvim/lua/tstapler/autocmds.lua`, wherever `g:coc_global_extensions` is declared (confirm exact location at implementation time — likely ported inline from the old coc config)

---

## Phase 3: Rust LSP + DAP

### Epic 3.1: Rust via rustaceanvim
**Goal**: Rust code intelligence + debugging via rustaceanvim (manages rust-analyzer + codelldb itself).

#### Story 3.1.1: Add rustaceanvim with toolchain rust-analyzer + codelldb
**As a** Rust developer, **I want** rustaceanvim wiring rust-analyzer and codelldb, **so that** I get LSP + debugging without IntelliJ, using the toolchain-matched analyzer.
**Acceptance Criteria**:
- rust-analyzer attaches (via rustup, not mason); codelldb debugging works; `:RustLsp` commands available.
  - *Given* an existing real Cargo project Tyler actively works in (a real multi-crate workspace if one is in daily use, not a fresh `cargo new` toy example) with rustaceanvim loaded, *When* I press `grn` on a struct field, *Then* it renames across the crate and `:checkhealth vim.lsp` shows one client (`rust-analyzer`) for the buffer.
  - *Given* a Rust binary with a breakpoint, *When* I run `:RustLsp debuggables` and pick the binary, *Then* codelldb stops at the breakpoint and dap-ui shows scopes.
  - *Given* rust-analyzer, *When* I check its origin, *Then* it comes from `rustup component add rust-analyzer` (toolchain-matched), NOT mason (pitfalls.md §2).
- Only after the Rust smoke test (Task 3.1.1b) passes, coc.nvim's Rust LSP-serving behavior is torn down the same way Go's was — coc.nvim itself stays installed (Python/TS/JS still depend on it).
  - *Given* rustaceanvim has passed its smoke test, *When* `coc-rust-analyzer` is removed from `g:coc_global_extensions` and `b:coc_enabled = false` is set for `rust` buffers, *Then* reopening a `.rs` file shows `:checkhealth vim.lsp` with exactly one client (`rust-analyzer`) and coc produces no diagnostics/completion for that buffer.
**Files**: `.config/nvim/lua/tstapler/plugins/lang/rust.lua`, `.config/nvim/lua/tstapler/autocmds.lua`

##### Task 3.1.1a: Add rustaceanvim spec (~5 min)
- `mrcjkb/rustaceanvim` (`ft = "rust"`); do NOT add nvim-lspconfig setup for rust (rustaceanvim owns it); pass shared `capabilities`; wire codelldb via mason (`ensure_installed = { "codelldb" }`) but rust-analyzer via rustup.
- Ensure `rust-tools.nvim` is absent (archived — features.md §2).
- Files: `.config/nvim/lua/tstapler/plugins/lang/rust.lua`

##### Task 3.1.1b: Rust smoke test against a real project (~4 min)
- Run LSP + DAP smoke sections against an existing real Rust project Tyler actively works in (a real multi-crate `Cargo.toml` workspace if one is in daily use) — not a fresh `cargo new` toy example; `:checkhealth rustaceanvim`.
- Do this before Task 3.1.1c tears down coc-rust-analyzer, same as Go's Story 2.3.2 does before Story 2.3.3: if rust-analyzer/codelldb fail on the real workspace, coc-rust-analyzer is still the live fallback (pre-mortem.md P1 #3).
- **Startup benchmark re-check** (closes adversarial-review CONCERN #3 / pre-mortem.md #2): run `NVIM_APPNAME=nvim-next nvim --startuptime /tmp/nvim-next-phase3.log` x3, take the median, and compare against `/tmp/nvim-baseline.log` — must be ≤ baseline before proceeding to Task 3.1.1c's coc-teardown.
- Files: (validation)

##### Task 3.1.1c: Tear down coc.nvim's Rust LSP-serving behavior (~4 min)
- Only after Task 3.1.1b's smoke test passes: remove `coc-rust-analyzer` from `g:coc_global_extensions`; add `rust` to the per-filetype `b:coc_enabled = false` autocmd alongside `go` (Task 2.3.3a) in `autocmds.lua`.
- Do NOT remove the `coc.nvim` plugin spec — Python/TS/JS still depend on it until Phases 4-5 (pitfalls.md §1).
- Files: `.config/nvim/lua/tstapler/autocmds.lua`, wherever `g:coc_global_extensions` is declared

---

## Phase 4: Python LSP + DAP

### Epic 4.1: Python via basedpyright/pyright + ruff + debugpy
**Goal**: Python code intelligence + debugging with robust venv handling.

#### Story 4.1.1: Enable Python LSP + nvim-dap-python with venv resolution
**As a** Python developer, **I want** pyright/basedpyright + ruff + debugpy with venv detection, **so that** I get code intelligence and debugging against the right interpreter without IntelliJ.
**Acceptance Criteria**:
- Python LSP attaches once; debugpy debugging works; venv resolves correctly (not system Python).
  - *Given* an existing real Python project Tyler actively works in — one managed via asdf/direnv, not a fresh toy `python -m venv` project — with basedpyright attached, *When* I press `grn` on a function, *Then* it renames across the project and `:checkhealth vim.lsp` shows one client for the buffer.
  - *Given* a Python script with a breakpoint and an active project `.venv`, *When* I launch debug, *Then* debugpy runs under the project's venv interpreter (not system Python) and stops at the breakpoint.
  - *Given* a poetry/pipenv project whose venv is outside the project dir, *When* auto-detect would pick system Python, *Then* a custom `resolve_python()` (or explicit `pythonPath`) selects the correct interpreter (pitfalls.md §2).
- Only after the Python smoke test (Task 4.1.1c) passes, coc.nvim's Python LSP-serving behavior is torn down the same way Go's and Rust's were — coc.nvim itself stays installed (TS/JS still depends on it).
  - *Given* basedpyright/ruff/debugpy have passed their smoke test, *When* `coc-pyright` is removed from `g:coc_global_extensions` and `b:coc_enabled = false` is set for `python` buffers, *Then* reopening a `.py` file shows `:checkhealth vim.lsp` with exactly one client (`basedpyright`, plus `ruff`) and coc produces no diagnostics/completion for that buffer.
**Files**: `.config/nvim/lua/tstapler/plugins/lang/python.lua`, `.config/nvim/lua/tstapler/autocmds.lua`

##### Task 4.1.1a: Configure Python LSP (~5 min)
- `vim.lsp.config("basedpyright", {...})` + `vim.lsp.config("ruff", {...})` (ruff for lint/format); `vim.lsp.enable({"basedpyright","ruff"})`; mason `ensure_installed = { "basedpyright", "ruff" }`; root markers `pyproject.toml`/`setup.py`/`.git`.
- Files: `.config/nvim/lua/tstapler/plugins/lang/python.lua`

##### Task 4.1.1b: Add nvim-dap-python + debugpy + venv resolver (~5 min)
- `mfussenegger/nvim-dap-python`; point at mason debugpy (`stdpath("data").."/mason/packages/debugpy/venv/bin/python"`); mason-nvim-dap `ensure_installed = { "python" }`; add a `resolve_python()` for non-standard venv paths.
- Note prereq: `python3 -m venv` must work system-wide (Debian/Manjaro footgun, pitfalls.md §2).
- Files: `.config/nvim/lua/tstapler/plugins/lang/python.lua`

##### Task 4.1.1c: Python smoke test against a real project (~4 min)
- Run LSP + DAP smoke sections against an existing real Python project Tyler actively works in — specifically one managed via asdf/direnv (not a toy `python -m venv` example) — plus the poetry/pipenv venv-outside-project case from Story 4.1.1's acceptance criteria.
- Do this before Task 4.1.1d tears down coc-pyright, same pattern as Go's Story 2.3.2/2.3.3: if basedpyright/ruff/debugpy misresolve the asdf/direnv-managed interpreter on the real project, coc-pyright is still the live fallback (pre-mortem.md P1 #3).
- **Startup benchmark re-check** (closes adversarial-review CONCERN #3 / pre-mortem.md #2): run `NVIM_APPNAME=nvim-next nvim --startuptime /tmp/nvim-next-phase4.log` x3, take the median, and compare against `/tmp/nvim-baseline.log` — must be ≤ baseline before proceeding to Task 4.1.1d's coc-teardown.
- Files: (validation)

##### Task 4.1.1d: Tear down coc.nvim's Python LSP-serving behavior (~4 min)
- Only after Task 4.1.1c's smoke test passes: remove `coc-pyright` from `g:coc_global_extensions`; add `python` to the per-filetype `b:coc_enabled = false` autocmd alongside `go`/`rust` in `autocmds.lua`.
- Do NOT remove the `coc.nvim` plugin spec — TS/JS still depends on it until Phase 5 (pitfalls.md §1).
- Files: `.config/nvim/lua/tstapler/autocmds.lua`, wherever `g:coc_global_extensions` is declared

---

## Phase 5: TypeScript/JavaScript LSP (+ optional-stretch DAP)

### Epic 5.1: TS/JS via vtsls
**Goal**: TS/JS code intelligence with monorepo-aware roots.

#### Story 5.1.1: Enable vtsls with monorepo root handling
**As a** TS/JS developer, **I want** vtsls attached with correct roots in monorepos, **so that** definition/references/rename work without IntelliJ.
**Acceptance Criteria**:
- vtsls attaches once per ts/js buffer; monorepo roots resolve to the nearest package.
  - *Given* a `.ts` file in a package inside a pnpm monorepo with vtsls attached, *When* I press `grr` on a function, *Then* references list across the package and `:checkhealth vim.lsp` shows one client for the buffer.
  - *Given* a monorepo with `tsconfig.json` at multiple depths, *When* vtsls attaches, *Then* a custom `root_dir` picks the nearest package root, not the repo top (features.md §3).
- Only after the TS/JS LSP smoke test (Task 5.1.1b) passes, coc.nvim's TS/JS LSP-serving behavior is torn down AND — since TypeScript/JavaScript is the last of the four languages to migrate — the `coc.nvim` plugin spec itself is fully removed from the tree (this does not wait on the stretch DAP goal, Story 5.1.2).
  - *Given* vtsls has passed its smoke test, *When* `coc-tsserver` teardown runs, *Then* `:echo exists(':CocInfo')` is 0, `coc.nvim` no longer appears in `:Lazy`, and `:checkhealth vim.lsp` shows exactly one client (`vtsls`) for `.ts`/`.js` buffers — coc.nvim is gone from all four languages at this point.
**Files**: `.config/nvim/lua/tstapler/plugins/lang/typescript.lua`, `.config/nvim/lua/tstapler/autocmds.lua`

##### Task 5.1.1a: Configure vtsls (~5 min)
- `vim.lsp.config("vtsls", { capabilities, root_dir = <nearest tsconfig/package.json fn> })`; `vim.lsp.enable("vtsls")`; mason `ensure_installed = { "vtsls" }`; ensure treesitter `typescript`/`tsx` parsers present.
- Files: `.config/nvim/lua/tstapler/plugins/lang/typescript.lua`

##### Task 5.1.1b: TS/JS LSP smoke test against a real project (~4 min)
- Run the LSP smoke section against an existing real TS/JS project Tyler actively works in — a real monorepo with `tsconfig.json` at multiple depths if one is in daily use (not a fresh `npm init` toy example), so the monorepo root-resolution logic (Task 5.1.1a) is actually exercised, not just assumed to work.
- Do this before Task 5.1.1c tears down coc-tsserver (and fully removes coc.nvim, the last language), same pattern as the other three languages: if vtsls misresolves roots on the real monorepo, coc-tsserver is still the live fallback (pre-mortem.md P1 #3).
- **Startup benchmark re-check** (closes adversarial-review CONCERN #3 / pre-mortem.md #2): run `NVIM_APPNAME=nvim-next nvim --startuptime /tmp/nvim-next-phase5.log` x3, take the median, and compare against `/tmp/nvim-baseline.log` — must be ≤ baseline before proceeding to Task 5.1.1c's coc-teardown + full coc.nvim removal.
- Files: (validation)

##### Task 5.1.1c: Tear down coc.nvim's TS/JS LSP-serving behavior + fully remove coc.nvim (last language) (~5 min)
- Only after Task 5.1.1b's smoke test passes: remove `coc-tsserver` from `g:coc_global_extensions`; add `typescript`/`javascript`/`typescriptreact`/`javascriptreact` to the per-filetype `b:coc_enabled = false` autocmd set (or simply stop registering it — moot once coc.nvim is uninstalled below).
- Since TS/JS is the last language to migrate, this task ALSO removes the `coc.nvim` plugin spec entirely from the plugin tree (unlike Go/Rust/Python's teardown tasks 2.3.3a/3.1.1c/4.1.1d, which left coc.nvim installed for the remaining languages) — delete the per-language `b:coc_enabled` autocmds added in those tasks too, since they're now dead code once coc.nvim no longer loads.
- This full removal does not depend on or wait for the stretch-goal TS/JS DAP story (5.1.2) — that story is optional and gated separately.
- Files: `.config/nvim/lua/tstapler/plugins/**` (remove coc.nvim spec), `.config/nvim/lua/tstapler/autocmds.lua` (remove now-dead `b:coc_enabled` autocmds)

#### Story 5.1.2 (STRETCH — do not block the plan): TS/JS DAP via js-debug-adapter
**As a** TS/JS developer, **I want** node/chrome debugging, **so that** I can debug JS without IntelliJ — accepted as lower-confidence.
**Acceptance Criteria**:
- If attempted and time allows, a node launch config hits a breakpoint; if fragile, it is explicitly deferred with a note (stack.md §4 flags this as the hardest adapter).
  - *Given* a Node script with a breakpoint, *When* I launch a `pwa-node` debug config, *Then* it stops at the breakpoint — OR this story is marked deferred with a `vim.notify` fallback and no half-working state is left behind.
**Files**: `.config/nvim/lua/tstapler/plugins/lang/typescript.lua`

##### Task 5.1.2a: (Stretch) Add nvim-dap-vscode-js + js-debug-adapter (~5 min)
- `mxsdev/nvim-dap-vscode-js` + mason `js-debug-adapter`; wire `pwa-node`. Timebox; if it fights, defer and document.
- Files: `.config/nvim/lua/tstapler/plugins/lang/typescript.lua`

---

## Phase 6: Git UI consolidation (optional, sequenced last per ux.md §5)

### Epic 6.1: Visual staging/merge (neogit + diffview)
**Goal**: Add a Magit-style staging UI and a merge/diff view IF the fugitive + gitsigns baseline leaves a felt gap after dogfooding.

#### Story 6.1.1: Add neogit + diffview (conditional on felt need)
**As a** Neovim user, **I want** neogit + diffview, **so that** I get visual staging and 3-way merge-conflict resolution — added only if fugitive+gitsigns proved insufficient during Phases 2-5.
**Acceptance Criteria**:
- If added, both work and compose with gitsigns; if not needed, skipped with a note.
  - *Given* a repo with a merge conflict, *When* I run `:DiffviewOpen` and pick the conflicted file, *Then* a 3-way (base/ours/theirs) view opens for resolution.
  - *Given* staged/unstaged changes, *When* I open neogit, *Then* I can stage hunks and write a commit message in its buffer.
**Files**: `.config/nvim/lua/tstapler/plugins/git.lua`

##### Task 6.1.1a: Add neogit + diffview specs (~5 min)
- `NeogitOrg/neogit` (+ dep `sindrets/diffview.nvim`); verify diffview freshness at implementation time (stack.md §5); map `<leader>gn`→neogit, `<leader>gd`→`:DiffviewOpen` via safe-map (distinct from `gd` LSP definition).
- **Startup benchmark re-check** (closes adversarial-review CONCERN #3 / pre-mortem.md #2): if this story is not skipped, run `NVIM_APPNAME=nvim-next nvim --startuptime /tmp/nvim-next-phase6.log` x3, take the median, and compare against `/tmp/nvim-baseline.log` — must be ≤ baseline.
- Files: `.config/nvim/lua/tstapler/plugins/git.lua`

---

## Phase 7: Cleanup, verification, cutover

### Epic 7.1: .ideavimrc minor shared-keybinding pass
**Goal**: Small, bounded IdeaVim cleanup per requirements (not a redesign).

#### Story 7.1.1: Align .ideavimrc leader/basic keys with the new scheme
**As an** IntelliJ+IdeaVim user, **I want** a few shared keybindings, **so that** muscle memory transfers where cheap.
**Acceptance Criteria**:
- `.ideavimrc` sets space leader and a couple of shared, safe IdeaVim actions; scope stays tiny.
  - *Given* `.ideavimrc` after this story, *When* I read it, *Then* it declares `let mapleader=" "` plus its existing `set surround`/`set commentary`, and at most a handful of shared maps (e.g. `<leader>ff` → GotoFile action) — no redesign.
**Files**: `.ideavimrc`

##### Task 7.1.1a: Add leader + minimal shared maps to .ideavimrc (~3 min)
- Add `let mapleader=" "`; optionally map `<leader>ff`→`:action GotoFile`, `<leader>fg`→`:action FindInPath`, `grn`→`:action RenameElement` to mirror the nvim scheme. Keep it under ~6 lines added.
- Files: `.ideavimrc`

### Epic 7.2: Wiki/markdown conflict final verification
**Goal**: Prove the live personal wiki is unbroken by the new treesitter/markdown handling.

#### Story 7.2.1: Verify vimwiki + markdown treesitter coexistence against real wiki files
**As a** note-taker, **I want** confirmation the wiki still works, **so that** `~/personal-wiki/logseq/pages` is not regressed.
**Acceptance Criteria**:
- Real wiki pages open as `vimwiki` filetype with native syntax; treesitter markdown does not attach to them; wiki links/tables work.
  - *Given* a real `~/personal-wiki/logseq/pages/*.md` file, *When* I open it, *Then* `:set filetype?` is `vimwiki`, `:InspectTree` reports no markdown parser attached, wikilinks follow on `<CR>`, and there is no `no parser for 'vimwiki'` error.
  - *Given* a non-wiki scratch `.md` file elsewhere, *When* I open it, *Then* markdown treesitter DOES attach (parity for normal markdown), confirming the exclusion is wiki-scoped, not global.
  - *Given* a fresh machine without `~/personal-wiki/logseq/pages` present yet, *When* `nvn` starts, *Then* it starts with zero errors — vimwiki degrades to unconfigured rather than erroring on the missing path (Task 7.2.1b).
**Files**: `.config/nvim/lua/tstapler/plugins/treesitter.lua`, `.config/nvim/lua/tstapler/autocmds.lua`, `.config/nvim/lua/tstapler/plugins/wiki.lua`

##### Task 7.2.1a: Finalize wiki-scoped markdown exclusion + test (~5 min)
- Confirm the treesitter `disable` predicate (Task 1.5.1a) excludes `vimwiki` filetype; verify no global `*.md → mkd` autocmd survives; test against real wiki files.
- Files: `.config/nvim/lua/tstapler/plugins/treesitter.lua`, `.config/nvim/lua/tstapler/autocmds.lua`

##### Task 7.2.1b: Guard vimwiki config against a missing `~/personal-wiki` directory (~3 min)
- Closes adversarial-review CONCERN #4 (validation.md `wiki_dir_absent_should_not_error_on_fresh_machine` / `wiki_dir_absent_on_fresh_machine_should_start_nvn_with_zero_errors`): `wiki.lua` (Task 1.7.5b) loads vimwiki eagerly (`lazy = false`) for every buffer, so any startup-path error from a missing wiki directory is maximally disruptive — this has been assumed safe, never verified.
- In `wiki.lua`, wrap the `g:vimwiki_list` assignment with an existence check: `if vim.fn.isdirectory(vim.fn.expand("~/personal-wiki/logseq/pages")) == 1 then vim.g.vimwiki_list = {...} end` (or equivalent) so a fresh machine without the personal wiki cloned yet degrades gracefully — vimwiki simply isn't configured — instead of erroring at startup.
- Acceptance: on a fresh machine (or the Task 7.4.1b second-machine dry-run) with `~/personal-wiki` absent, `nvn` starts with zero errors in `:messages`.
- Files: `.config/nvim/lua/tstapler/plugins/wiki.lua`

### Epic 7.3: Final plugin-prune sweep + no-redundancy audit
**Goal**: Confirm the audited minimal set — no redundant plugins, pruned list documented.

#### Story 7.3.1: Audit remaining plugins and prune superseded/unused
**As a** maintainer, **I want** a final prune pass, **so that** the "no redundant plugins" Success Metric holds and nothing dead remains.
**Acceptance Criteria**:
- The `.vimrc.dein` plugin list is fully accounted for: each old plugin is either ported, replaced (documented mapping), or pruned (with reason); ctrlspace session-persistence gap resolved before deleting it.
  - *Given* the old `.vimrc.dein` plugin list, *When* I diff it against the new tree, *Then* every entry maps to exactly one of {ported, replaced-by-X, pruned-because-Y}, and the pruned set includes: coc.nvim, ale, ctrlp.vim, vim-ctrlspace, fzf.vim, ctrlsf.vim, Merginal, vimagit, vim-airline(+themes), NERDTree, Shougo/neoinclude+neco-syntax+neco-vim+neco-look, context_filetype.vim, vim-autoformat, vim-polyglot, echodoc, alchemist.vim, vim-choosewin, emmet-vim (verify usage), plus the misc build-dep plugins (vimproc, vim-misc, webapi-vim, lh-vim-lib, vim-hier, vim-maktaba, vim-magnum) no longer needed by any surviving plugin.
  - *Given* vim-ctrlspace provides session/workspace persistence, *When* I remove it, *Then* either that need is confirmed unused OR a replacement (mksession autosave / persistence.nvim) is in place (Unresolved Question #4).
**Files**: `.config/nvim/lua/tstapler/plugins/**`

##### Task 7.3.1a: Produce old→new plugin mapping + resolve ctrlspace gap (~5 min)
- Build the ported/replaced/pruned table from the `.vimrc.dein` list; confirm the misc build-deps have no surviving dependents (grep new tree); decide ctrlspace session-persistence replacement.
- Files: (audit; adjust plugin specs if a gap surfaces)

##### Task 7.3.1b: Verify emmet/starlark/kubernetes/base64/hexmode/vim-kubernetes usage (~4 min)
- For ambiguous low-signal plugins (`emmet-vim`, `starlark.vim`, `vim-kubernetes`, `vim-base64`, `hexmode`, snippet-source plugins), check muscle memory/usage; port only if used, else prune and add to `REMOVED-PLUGINS.md`.
- Files: `.config/nvim/lua/tstapler/plugins/**`

### Epic 7.4: Cutover to master
**Goal**: Merge the validated config; deploy via cfgcaddy; confirm rollback path.

#### Story 7.4.1: Dogfood one week combined, then merge and deploy
**As a** daily-driver, **I want** to cut over only after all four languages have already progressively shifted to `nvn` (each on its own schedule, per Migration Plan) and then survived one further week of *combined* daily-driver use together, **so that** master stays safe until the fully-combined config is proven — this is NOT a single merge gated on building everything from scratch; each language already banked its own real-world win the moment its own teardown task landed (Story 2.3.3 Go, 3.1.1c Rust, 4.1.1d Python, 5.1.1c TS/JS).
**Acceptance Criteria**:
- After a week of `nvn` daily use with no reverts, the branch merges, cfgcaddy deploys `init.lua`, and plain `nvim` runs the new config with the committed lockfile; rollback is verified.
  - *Given* all four languages have already individually cut over to `nvn` for real daily-driver work (each gated on its own real-project smoke test per Fix 2, not this story), *When* a further full week of *combined* daily use under `nvn` across all four languages passes with no fallback to IntelliJ or master for a covered task, *Then* I merge to master and run cfgcaddy install, `~/.config/nvim/init.vim` is gone, `~/.config/nvim/init.lua` exists, plain `nvim` loads plugins from `lazy-lock.json`, and `:checkhealth` is clean.
  - *Given* a hypothetical post-cutover regression, *When* I revert the merge and re-run cfgcaddy, *Then* the old coc config returns intact (master's `~/.local/share/nvim` was never touched thanks to NVIM_APPNAME isolation).
**Files**: `.config/nvim/lazy-lock.json`, `.cfgcaddy.yml` (already edited in 1.6.2)

##### Task 7.4.1a: Commit lazy-lock.json + final cfgcaddy verification (~4 min)
- Ensure `lazy-lock.json` is committed (NOT gitignored — pitfalls.md §6); confirm `.cfgcaddy.yml` has no `init.vim`/`coc-settings.json` remnants; if the 1.6.2a check found file-level linking, re-run cfgcaddy install as part of cutover.
- Files: `.config/nvim/lazy-lock.json`, `.cfgcaddy.yml`

##### Task 7.4.1b: Second-machine (or disposable container/VM) fresh cfgcaddy dry-run (~10 min)
- Closes adversarial-review CONCERN #2 (validation.md `second_machine_fresh_cfgcaddy_deploy_should_reproduce_working_config`): Task 1.6.2a's directory-vs-file check used `.claude/skills/` as a proxy, and every smoke test so far ran on Tyler's single primary daily-driver machine — this task is the first genuine second-environment deploy of `.config/nvim` itself, run BEFORE declaring cutover complete (i.e. before Task 7.4.1c's merge).
- On a disposable container, VM, or a temp `$HOME` override (whichever is realistic for a personal dotfiles repo — a temp `$HOME` pointed at a fresh directory is the cheapest option), clone the worktree, run cfgcaddy install cold, and confirm: Mason auto-installs its tools fresh, `rustup component add rust-analyzer` succeeds on a clean toolchain, treesitter `auto_install` fires for the four languages, `~/personal-wiki` being absent doesn't error (Task 7.2.1b closes this specifically), and `:checkhealth` is clean.
- If a gap surfaces (e.g. `.config/nvim` turns out to be file-level linked per 1.6.2a, or a hardcoded path assumes the primary machine), fix it here before Task 7.4.1c.
- Files: (dev-only; no repo files unless a gap fix is needed)

##### Task 7.4.1c: Merge to master + deploy + rollback rehearsal (~5 min)
- Precondition: Task 7.4.1b's second-machine dry-run has passed.
- Merge `dotfiles-harden-neovim` → `master`; run cfgcaddy install; smoke test under plain `nvim`; rehearse the revert-and-redeploy rollback once to confirm it restores the old config.
- **Final startup benchmark re-check** (closes adversarial-review CONCERN #3 / pre-mortem.md #2 — the real merge gate): run `NVIM_APPNAME=nvim-next nvim --startuptime /tmp/nvim-next-final.log` x3 (or, post-merge, `nvim --startuptime` on the deployed config), take the median, and confirm it is ≤ `/tmp/nvim-baseline.log`'s median before treating cutover as done — this is a literal condition of this task's completion, not just Task 2.3.2a's.
- Files: (git + deploy operations)
