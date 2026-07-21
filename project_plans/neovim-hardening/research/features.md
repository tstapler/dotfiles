# Research: Feature Landscape — "IntelliJ-parity Neovim" (2025-2026)

Agent 2 (Features) — Phase 2 research for `neovim-hardening`.

## Existing config context (for calibration)

Read directly from the worktree before researching:

- `.vimrc.plug` (the file `.vimrc.dein` symlinks to) is **already on `lazy.nvim`**, not dein/vim-plug as the requirements doc's baseline language implies — the plugin *manager* migration to Lua has already happened at the bootstrap level. What hasn't happened: the actual plugin set is still the old vimscript-era stack (`coc.nvim` + `ale` for LSP-like features, `ctrlp.vim` + `vim-ctrlspace` + `fzf.vim` for fuzzy-finding, `vim-fugitive` + `Merginal` + `vimagit` for git, `NERDTree` for file browsing, no DAP at all).
- `coc_global_extensions` includes `coc-flutter`, `coc-solargraph` (Ruby), `coc-java`, `coc-python` (legacy, superseded by pyright) — several are for out-of-scope languages per requirements (Dart/Ruby/Java) and should be pruned regardless of the vimscript-vs-Lua decision.
- vimwiki config: `g:vimwiki_list` maps `~/personal-wiki/logseq/pages` with `'ext':'.md'` (Markdown, not the default `.wiki` syntax) — this matters directly for research question 5 below, since vimwiki's own markdown-syntax handling only applies when a buffer is recognized as a vimwiki buffer, and file-type/syntax precedence issues change under a Lua/treesitter setup.
- `.vimrc` has a global autocmd forcing `*.md` → `filetype=mkd` (line ~205), which predates and is likely to conflict with any treesitter-markdown or markdown LSP addition — flagged for the planning phase.
- No DAP, no treesitter config, no telescope present anywhere in the current setup — confirms baseline description in requirements.md is accurate for the debugging/navigation/code-intel gap.

---

## 1. Hardest IntelliJ features to replicate, and what closes the gap today

| IntelliJ feature | Neovim 2025-2026 answer | Maturity / caveat |
|---|---|---|
| Extract method/variable, inline, move statements | `ThePrimeagen/refactoring.nvim` (LSP + treesitter based; the closest thing to a general-purpose refactor library) and the newer, narrower `mraspaud/lsp-refactor.nvim` (extract_function, extract_variable, move_statements_into_function/to_callers — explicitly Python/Rust/Go only) | These are heuristic, treesitter-node-based transforms, not full semantic refactors like IntelliJ's — they work well for single-file extract/inline but are not as bullet-proof as IntelliJ's AST-verified transforms. Expect occasional manual cleanup after extract-method in complex code. |
| Safe rename across files | LSP `textDocument/rename` via `vim.lsp.buf.rename()` — this is the one place Neovim is genuinely at parity with IntelliJ, because it delegates entirely to the language server (gopls, rust-analyzer, pyright, vtsls/tsserver all implement it solidly) | Quality is a function of the LSP server, not the editor — gopls/rust-analyzer rename is considered production-grade; ts-server rename across a monorepo can miss files outside the detected project root (see §3). |
| Call hierarchy (incoming/outgoing calls) | Built-in `vim.lsp.buf.incoming_calls()` / `outgoing_calls()`, or nicer UIs via `lspsaga.nvim` (`Lspsaga incoming_calls`) or `jmacadie/telescope-hierarchy.nvim` | **Known gap**: both Neovim's built-in implementation and Trouble.nvim only display one level of the hierarchy at a time (you re-invoke per node) rather than IntelliJ's expandable tree-in-a-panel. Functional but noticeably clunkier than IntelliJ's Ctrl+Alt+H. |
| Structural search-and-replace (SSR) | `MagicDuck/grug-far.nvim` — supports both ripgrep (text/regex) and **ast-grep** as a backend, giving genuine structural (AST-pattern) search-and-replace in one unified buffer UI. LazyVim replaced `nvim-spectre` with `grug-far.nvim` for this reason (better UI, ast-grep support). | This is the best current answer to IntelliJ's SSR dialog. `nvim-spectre` is the older, still-common alternative but is regex/text-only — no structural matching. Tyler's CLAUDE.md already prefers `ast-grep`/`sg` for structural search, so `grug-far.nvim` is a natural fit and reuses a tool already in his workflow. |
| Inline error/warning gutters + as-you-type diagnostics | Built-in `vim.diagnostic` virtual text/signs are functional but visually noisy (multi-line, pushes text). `rachartier/tiny-inline-diagnostic.nvim` is the current community favorite for a compact, IntelliJ-like inline diagnostic (single-line, doesn't shift code, actively maintained through 2025-2026). | Straightforward win — this is a pure UX plugin layered on the LSP client's diagnostics, no server-side dependency. |
| Parameter hints / inlay hints | Native as of Neovim 0.10+ via `vim.lsp.inlay_hint.enable()` — no plugin needed, works directly off LSP `textDocument/inlayHint` (gopls, rust-analyzer, pyright/basedpyright, vtsls all support it) | Straightforward native win once on a real LSP client (not available under coc.nvim's older protocol handling without extra config). |
| Quick-fix / code actions | Native `vim.lsp.buf.code_action()`; UX sugar via lspsaga's "lightbulb" indicator showing a code action is available at cursor, similar to IntelliJ's yellow bulb | Works well; the lightbulb indicator is the main "unstated need" gap vs. raw code action calls (see §4). |
| Breadcrumbs (symbol path in header) | `lspsaga.nvim`'s winbar breadcrumb feature, or `Bekaboo/dropbar.nvim` (dedicated breadcrumb/winbar plugin), both LSP-symbol-driven | lspsaga's winbar had reported gaps (older versions showed only file path, not symbol path) — verify current lspsaga version behavior in planning/spike; `dropbar.nvim` is a narrower, purpose-built alternative if lspsaga's winbar underdelivers. |
| "Recent Files" / "Recent Locations" | `telescope-recent-files` (tracks recently opened buffers), `telescope-frecency` (frecency-ranked — most useful proxy for IntelliJ's algorithm), or `fff.nvim` (frecency + git-status-aware fuzzy file picker) | Multiple viable options; frecency-based ranking is the closest conceptual match to IntelliJ's "Recent Files" (recency + frequency weighted, not just MRU). |
| Structural code folding | Native treesitter-based folding (`foldmethod=expr`, `foldexpr=nvim_treesitter#foldexpr()`) plus `kevinhwang91/nvim-ufo` for a much better fold UI/preview | Treesitter folding alone is serviceable; `nvim-ufo` is the widely-recommended layer for IntelliJ-like fold previews and performance. |
| Minimap | `Isrothy/neominimap.nvim` (successor to the older, less-maintained `codewindow.nvim`) — shows code structure, diagnostics, and git changes in the minimap | Genuinely optional/cosmetic; not load-bearing for the "replace IntelliJ" goal, low priority. |

**Bottom line for this section**: LSP-delegated features (rename, hover, definition, references, inlay hints) are at or near parity today given a real LSP client (i.e., contingent on the vimscript-vs-Lua / coc-vs-native-LSP decision made elsewhere in this research). The genuine, still-open gaps vs. IntelliJ are (a) call-hierarchy as a persistent expandable tree rather than one-level-at-a-time, and (b) fully-verified multi-step semantic refactors (extract-interface, safe-delete-with-usage-check) — these remain heuristic/best-effort in the Neovim ecosystem, not solved.

---

## 2. Prior art: what LazyVim / NvChad / AstroNvim / kickstart.nvim actually ship

- **LazyVim** is the community consensus pick for 2025-2026: largest ecosystem, most active maintainer (folke, who also wrote `lazy.nvim` and `grug-far.nvim`), and an **extras system** (`:LazyExtras`) that is directly relevant to this project's scope — there are ready-made, maintained extras for `lang.go`, `lang.rust`, `lang.python`, `lang.typescript`, and `dap.core` + per-language DAP wiring. Each language extra bundles: LSP server config (nvim-lspconfig), treesitter parser, formatter (conform.nvim), linter (nvim-lint), DAP adapter wiring, and test runner (neotest) integration — i.e., almost exactly the shape of what this project's scope calls for, per language, already assembled and maintained upstream.
  - Go extra: gopls + delve (via nvim-dap-go) + neotest-golang.
  - Rust extra: `rustaceanvim` (the actively-maintained successor to the now-archived `rust-tools.nvim`) + codelldb.
  - Python extra: choice of pyright/basedpyright + ruff, debugpy, venv-selector.nvim (virtualenv switching — a real gap in the old coc-pyright setup).
  - TypeScript extra: choice of `vtsls` (VSCode's own TS extension repackaged as an LSP — richer than `typescript-language-server`, and LazyVim's current default) or `tsgo`, js-debug-adapter, oxc/biome as a fast linter/formatter option.
- **NvChad**: leaner, more "starting framework" than batteries-included distro; less prescriptive about DAP/refactor tooling out of the box — better fit for someone who wants to hand-assemble than someone who wants per-language packages pre-wired.
- **AstroNvim**: closer to LazyVim in scope, ships DAP by default in many of its language packs (arguably even more DAP-eager out of the box than LazyVim, which gates DAP behind opting into the extra). Strong community/Discord, actively maintained.
- **kickstart.nvim**: intentionally a single-file, heavily-commented *starting point*, not a distribution — no built-in DAP/refactor/git-UI opinions; you build it yourself. Good if the goal were "learn Lua config from scratch," less good as a fast path to the specific feature set this project needs (search didn't surface direct kickstart-vs-others feature comparisons for 2025-2026; treat as the "roll your own" baseline rather than a competitor to LazyVim/AstroNvim on features).
- **LunarVim**: explicitly called out in current community commentary as stalled/unmaintained as of 2026 — do not consider as a base.

**Differentiation vs. marketing**: the genuinely differentiated thing LazyVim/AstroNvim offer over a from-scratch config is *maintained glue code per language* (root-dir detection quirks, DAP adapter path discovery, formatter/linter wiring) — this is exactly the "fragile, time-consuming" work flagged as a Rabbit Hole in requirements.md. The lazy-loading and UI polish (dashboard, which-key, statusline) are marketing-grade nice-to-haves, not differentiators for this project's actual goals. Given Tyler's config already has meaningful personal customization (vim-zettel/vimwiki workflow, custom filetype rules, personal snippets, `vim-oscyank` tmux integration), **forking wholesale is higher-risk than adopting the per-language extras pattern (or literally vendoring LazyVim's language-extra Lua files) inside a custom config** — this is a build-vs-adopt tradeoff to make explicit in planning, not just "distro vs. no distro."

---

## 3. Edge cases / failure modes specific to this migration

- **Multi-root / monorepo projects**: `nvim-lspconfig`'s default root-marker search is described upstream as "breadth-first" — it can find multiple matching root markers across a monorepo rather than stopping at the nearest ancestor, causing an LSP server to attach at the wrong (too-high) root. The LSP client tracks a root per-buffer, so different files in the same monorepo can legitimately get different roots — this is workable but requires a custom `root_dir` function (checking for `pnpm-workspace.yaml`, `nx.json`, `go.work`, etc.) rather than relying on defaults, especially for the TS/JS extra where monorepos are most common. Flag as a planning-phase task, not an assumption.
- **Projects without a clear root marker**: any bare-directory Python/Go script folder with no `go.mod`/`pyproject.toml`/`.git` present will fail root detection outright — the LSP either won't attach or attaches with `root_dir = nil` (single-file mode), which silently degrades cross-file features (no workspace-wide rename/find-references). Needs an explicit "single-file LSP mode" fallback config, not silent failure.
- **Large files**: nvim-treesitter has a long-standing, still-relevant performance issue on very large files (documented example: a 90k-line C header) — the community answer is a size-based cutoff to skip treesitter highlighting/folding above a threshold, and/or restricting the parsed context to a window around the cursor. This needs an explicit `max_filesize` guard in the treesitter config (LazyVim ships one by default; a from-scratch config must add it manually or risk visible input lag on large generated files — a real risk given monorepo generated code in Go/TS).
- **Remote/SSH editing**: no single dominant, mature solution yet. Options as of 2025-2026: `remote-ssh.nvim` (runs LSP on the remote host, edits locally — addresses the specific "LSP feels laggy over SSH" problem) vs. `distant.nvim`/SSHFS-style approaches (filesystem ops happen remotely, avoiding chatty round-trips for file-heavy operations). Native Neovim itself has an open GSoC 2026 discussion and issue thread about building first-class remote-dev support, meaning **this is explicitly not a solved problem upstream yet** — if Tyler does real SSH-based work, budget this as a known-rough edge rather than "install a plugin and done."
- **Projects mixing multiple languages** (e.g., a Go backend + TS frontend in one repo): each language's LSP client attaches independently per buffer/filetype, which works fine in principle, but root-detection edge cases (above) compound — a mixed-language monorepo is the worst case for root-marker ambiguity, since Go's marker (`go.mod`) and TS's marker (`package.json`/`tsconfig.json`) may sit at different directory depths in the same tree.

---

## 4. Unstated needs — things an IntelliJ daily user expects and would miss

- **Inline diagnostics as-you-type that don't reflow the line** — IntelliJ's right-margin gutter squiggle + tooltip doesn't shift code; Neovim's default virtual-text diagnostics can visually push lines around. `tiny-inline-diagnostic.nvim` specifically addresses this non-intrusiveness.
- **A visible "code action available" indicator (lightbulb)** — without it, discovering that a quick-fix exists requires manually invoking `code_action()` speculatively; IntelliJ's yellow bulb makes this passive/glanceable. lspsaga provides this; worth calling out explicitly since it's easy to end up with code actions "working" but undiscoverable.
- **Breadcrumbs / symbol path in the window header** — useful for orientation in large files; not critical but a real "oh I miss that" moment coming from IntelliJ. Cheap to add (`dropbar.nvim` or lspsaga winbar).
- **Persistent per-project sessions (reopen exactly where you left off, per git branch)** — `persisted.nvim` / `folke/persistence.nvim` / `coffebar/neovim-project` all solve this; `persisted.nvim` and `neovim-project` both specifically support **per-git-branch session state**, which is a closer match to IntelliJ's per-branch-aware window/tab restoration than plain session managers. This is a real unstated need — IntelliJ's "reopen last project state" is invisible until it's gone.
- **Frecency-ranked recent files, not just MRU** — `telescope-frecency` / `fff.nvim` reproduce IntelliJ's "Recent Files" ranking algorithm (recency + frequency), which behaves noticeably better than a flat most-recently-used list once a project has been open a while.
- **Structural code folding done well (fold preview, not just fold/unfold)** — `nvim-ufo` gives fold-content preview on hover, closer to IntelliJ's inline collapsed-block preview than bare treesitter folding.
- **Minimap** — genuinely optional; lowest-priority item on this list, listed for completeness (`neominimap.nvim`).
- **"Did you mean" typo suggestions** — no direct equivalent surfaced in research; this is generally handled implicitly by completion-engine fuzzy matching (nvim-cmp/blink.cmp) rather than a dedicated feature. Worth noting as a gap that likely doesn't need a dedicated plugin — LSP-driven completion with fuzzy matching covers most of what IntelliJ's typo-correction does in practice.
- **Virtualenv/interpreter switching for Python** — not in the original requirements list but surfaced repeatedly in LazyVim's Python extra (`venv-selector.nvim`); the current coc-pyright setup has no equivalent, and this is exactly the kind of thing a daily Python/IntelliJ (PyCharm-adjacent) user would silently miss without knowing to ask for it up front.

---

## 5. vimwiki / vim-zettel compatibility risk with a modernized Lua/treesitter config

This is the sharpest concrete risk surfaced in research, because Tyler's current config already has non-default settings that increase collision surface:

- **Filetype override collision**: `.vimrc` (line ~205) has a bare autocmd forcing `*.md`/`*.markdown` → `filetype=mkd` globally, *outside* of vimwiki's own filetype handling. vimwiki's own list config additionally sets `'ext':'.md'` for the personal-wiki path specifically (i.e., vimwiki buffers under `~/personal-wiki/logseq/pages` want `filetype=vimwiki`, but the global autocmd is racing it toward `mkd`). This is a **pre-existing latent bug/fragility**, not something introduced by modernization — but adding treesitter-markdown or a markdown LSP (e.g., `marksman`) makes the failure mode worse, not better, because both of those attach based on filetype/extension and will silently do the wrong thing (or nothing) if `filetype` isn't consistently `vimwiki` for wiki pages.
- **Treesitter markdown parser not auto-attaching**: current community reports (2025) show the treesitter markdown parser sometimes requires manually calling `vim.treesitter.start(0, "markdown")` — it doesn't always auto-attach the way older regex-based syntax highlighting did. Combined with the filetype-override issue above, this raises real risk that either (a) treesitter never activates on wiki pages (silent, but low-severity — no different from today), or (b) it activates and its markdown grammar's opinions about e.g. embedded/injected-language code blocks conflict with vimwiki's own syntax highlighting for the same buffer, per the embedded-language-highlighting bug reports found in `neovim/neovim` discussions (injected-language buffers can break sibling-language highlighting).
- **No LSP-markdown-vs-vimwiki conflict was found in the wild** in this research — no evidence of `marksman` or similar markdown LSP servers actively fighting vimwiki's own syntax/keymapping layer; the realistic risk is confined to **treesitter highlighting/filetype interaction**, not LSP.
- **Recommendation for planning phase**: (1) do not add a markdown LSP server or treesitter-markdown highlighting without first explicitly excluding vimwiki buffers (e.g., `vim.treesitter.language.register` guarded by a check that `&filetype != 'vimwiki'`, or simply not enabling treesitter for the `vimwiki` filetype at all — vimwiki's own syntax file already handles wikilinks/checkboxes/etc. that a generic markdown grammar doesn't understand); (2) fix the pre-existing `*.md` → `mkd` global override collision as a small, explicitly-scoped cleanup, since it's already fragile and out-of-scope creep is easy to avoid by treating it as a "don't break it further" fix rather than a redesign; (3) since vimwiki/vim-zettel are vimscript plugins with no Lua rewrite in progress (none surfaced in research), they will keep working unmodified under `lazy.nvim` regardless of the vimscript-vs-Lua decision for the rest of the config — `lazy.nvim` loads vimscript plugins natively, so this is a low-risk area as long as filetype detection stays correct.

---

## Sources

- [lsp-refactor.nvim](https://codeberg.org/mraspaud/lsp-refactor.nvim)
- [ThePrimeagen/refactoring.nvim](https://github.com/ThePrimeagen/refactoring.nvim)
- [Search and replace in Neovim](https://tpoe.dev/blog/search-and-replace-in-neovim)
- [grug-far.nvim](https://github.com/MagicDuck/grug-far.nvim)
- [grug-far.nvim vs nvim-spectre PR discussion](https://github.com/LazyVim/LazyVim/pull/4099)
- [Neovim Multiline Search and Replace with grug-far.nvim (ast-grep)](https://linkarzu.com/posts/neovim/grug-far/)
- [LazyVim vs LunarVim vs AstroNvim (SumGuy's Ramblings)](https://sumguy.com/lazyvim-vs-lunarvim-vs-astronvim/)
- [Exploring Top Neovim Distributions (Medium)](https://medium.com/@adaml.poniatowski/exploring-the-top-neovim-distributions-lazyvim-lunarvim-astrovim-and-nvchad-which-one-reigns-3adcdbfa478d)
- [LazyVim Language-Specific Support (DeepWiki)](https://deepwiki.com/LazyVim/LazyVim/9-language-specific-support)
- [LazyVim Extras System (DeepWiki)](https://deepwiki.com/LazyVim/LazyVim/10-extras-system)
- [LazyVim Go extra](https://www.lazyvim.org/extras/lang/go)
- [LazyVim Rust extra](http://www.lazyvim.org/extras/lang/rust)
- [LazyVim TypeScript extra](http://www.lazyvim.org/extras/lang/typescript)
- [LazyVim DAP Core](http://www.lazyvim.org/extras/dap/core)
- [rustaceanvim](https://github.com/mrcjkb/rustaceanvim)
- [rust-tools.nvim archived → rustaceanvim](https://programming.dev/post/8302555)
- [vtsls](https://github.com/yioneko/vtsls)
- [gopls transformation/refactoring features](https://github.com/golang/tools/blob/master/gopls/doc/features/transformation.md)
- [Get root directory · nvim-lspconfig#320](https://github.com/neovim/nvim-lspconfig/issues/320)
- [Conditionally load LSP servers by root markers · neovim#38771](https://github.com/neovim/neovim/discussions/38771)
- [Neo-tree CWD vs root dir monorepo discussion](https://github.com/LazyVim/LazyVim/discussions/2150)
- [nvim-treesitter slow on very big files #556](https://github.com/nvim-treesitter/nvim-treesitter/issues/556)
- [remote-ssh.nvim](https://github.com/inhesrom/remote-ssh.nvim)
- [distant.nvim / remote-sshfs.nvim](https://github.com/nosduco/remote-sshfs.nvim)
- [GSoC 2026: VSCode remote-ssh-like feature in neovim #38564](https://github.com/neovim/neovim/discussions/38564)
- [Making editing snappier over remote networks #24690](https://github.com/neovim/neovim/issues/24690)
- [tiny-inline-diagnostic.nvim](https://github.com/rachartier/tiny-inline-diagnostic.nvim)
- [neominimap.nvim](https://github.com/Isrothy/neominimap.nvim)
- [Lspsaga](https://nvimdev.github.io/lspsaga/)
- [telescope-hierarchy.nvim](https://github.com/jmacadie/telescope-hierarchy.nvim)
- [vim.lsp.buf.incoming_calls one-level limitation #26817](https://github.com/neovim/neovim/issues/26817)
- [persisted.nvim](https://github.com/olimorris/persisted.nvim)
- [folke/persistence.nvim](https://github.com/folke/persistence.nvim)
- [coffebar/neovim-project](https://github.com/coffebar/neovim-project)
- [telescope-recent-files](https://github.com/smartpde/telescope-recent-files)
- [nvim-dap debug adapter installation wiki](https://codeberg.org/mfussenegger/nvim-dap/wiki/Debug-Adapter-installation)
- [Debugging Rust with NeoVim (codelldb)](https://romangeber.com/blog/tech/nvim_rust_debugger)
- [Treesitter markdown parser not auto-attaching (render-markdown.nvim #607)](https://github.com/MeanderingProgrammer/render-markdown.nvim/issues/607)
- [Embedded language syntax highlighting stops working in markdown #37552](https://github.com/neovim/neovim/discussions/37552)
