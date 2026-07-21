# Stack Research: Neovim Hardening (Go / Rust / Python / TS-JS)

Date: 2026-07-15
Scope: technology stack recommendations for modernizing `.vimrc.dein`/`.vimrc.plug`
(lazy.nvim already bootstrapped) on nvim 0.11.6, for Tyler's daily-rotation languages.

## Existing config snapshot (for reference)

- `.vimrc.dein` is a symlink → `.vimrc.plug`, which contains a `lazy.nvim` bootstrap
  and `require('lazy').setup({...})` plugin list (~50 entries).
- Completion/LSP today: `coc.nvim` (release branch) + `w0rp/ale`, with
  `coc-tsserver`, `coc-go`, `coc-rust-analyzer`, `coc-pyright`, `coc-python`,
  plus many language extensions outside daily rotation (coc-flutter, coc-solargraph,
  coc-java, etc.) — evidence supporting the "audit unused languages" scope item.
- Fuzzy-finding: `ctrlpvim/ctrlp.vim`, `vim-ctrlspace/vim-ctrlspace`, `junegunn/fzf`
  + `fzf.vim` all present simultaneously — the "three fuzzy-finders" problem is
  confirmed directly in the plugin list.
- Git: `tpope/vim-fugitive`, `vim-scripts/Merginal`, `jreybert/vimagit` — three
  separate git UIs, confirmed.
- Syntax: `sheerun/vim-polyglot` (no treesitter at all currently).
- No DAP plugins present at all today.
- `.vimrc.local`, `.vimrc.bundles.local`, `.vimrc.plug`-as-dein-name are the
  orphaned/confusing files named in requirements (`.vimrc.plug` itself is NOT
  dead — it's the real file; `.vimrc.dein` is just a misleadingly-named symlink
  to it).

---

## 1. Native LSP vs coc.nvim in 2026

**Recommendation: migrate to native LSP (`vim.lsp` + `nvim-lspconfig`).**

- Neovim 0.11 shipped `vim.lsp.config()` / `vim.lsp.enable()`, making native LSP
  setup dramatically simpler than in the 0.5–0.10 era — this was the biggest
  blocker to migrating off coc.nvim and it's now resolved. `nvim-lspconfig` itself
  is transitioning to being a thin collection of `lsp/*.lua` server config files
  consumed directly by the new `vim.lsp.config`/`enable` API rather than a setup
  wrapper — using it alongside the new API is the currently-recommended path and
  is explicitly forward-compatible.
- Community trend is unambiguous: LazyVim, kickstart.nvim, and the broad
  ecosystem have standardized on native LSP + Mason for server installs.
  coc.nvim discussion threads (e.g. neoclide/coc.nvim#4866) show the honest
  trade-off: coc.nvim is more batteries-included out of the box, but native LSP
  has caught up in capability while giving finer-grained control and one
  consistent client across all languages instead of coc's separate extension
  model per language.
- Migration complexity is real but bounded: coc.nvim currently provides
  completion, snippets, formatting, diagnostics, and code actions all through
  one plugin. Native LSP requires assembling equivalents: `nvim-lspconfig` (or
  `lsp/*.lua` configs) for servers, a completion engine (see below), a snippet
  engine (`LuaSnip` or Neovim 0.10+ native `vim.snippet`), and `conform.nvim` /
  `nvim-lint` (or continue relying on `ale` for linting/formatting non-LSP
  cases) for formatting/diagnostics that aren't LSP-native. This is the
  "touches everything simultaneously" rabbit hole flagged in requirements —
  plan phase should sequence it (e.g. LSP+completion first, formatting second,
  snippets third) rather than one big-bang swap.
- coc.nvim and a native LSP client should **not** run the same language server
  for the same language simultaneously (both will attach and produce duplicate
  diagnostics/completions) — this confirms the feasibility risk in requirements.
  Plan should treat this as an all-or-nothing cutover per language, not a
  gradual per-language migration if both stacks are loaded at once (safest: rip
  out coc.nvim as one atomic step, don't try to dual-run).

### Completion stack: blink.cmp vs nvim-cmp

**Recommendation: `blink.cmp`.**

- `blink.cmp` (saghen/blink.cmp) is now the modern default — both LazyVim and
  kickstart.nvim have switched their default completion engine to it.
- Performance: blink.cmp updates on every keystroke with ~0.5–4ms overhead vs.
  nvim-cmp's default 60ms debounce and 2–50ms hitches; it ships a fast native
  fuzzy matcher (Rust, with a Lua fallback for platforms without prebuilt
  binaries) with typo resistance, versus nvim-cmp's fzf-style matching via
  external plugin.
  built-in without extra source plugins), whereas nvim-cmp needs the classic
  `cmp-nvim-lsp` / `cmp-buffer` / `cmp-path` source plugins.
- nvim-cmp is still fine and stable if there's a strong reason to keep it
  (huge existing source-plugin ecosystem), but for a fresh setup in 2026
  blink.cmp is the better default.

---

## 2. Treesitter

**Important/time-sensitive finding:** the `nvim-treesitter/nvim-treesitter`
repo was **archived by its maintainer on 2026-04-03** (roughly 3 months before
this research), after a public dispute over the plugin's `main` branch being
rewritten to hard-require Neovim ≥0.12 while a chunk of the user base was still
on 0.11.x. Key facts:

- The **`master` branch is frozen** (no further updates, but functional) and
  works with Neovim 0.11.x — this is what a config staying on nvim 0.11.6
  should pin to (e.g. `branch = "master"` in lazy.nvim), understanding it will
  receive no further parser/query updates going forward.
- The **`main` branch is a full incompatible rewrite** requiring Neovim ≥0.12:
  the old `setup({ highlight = {...}, indent = {...}, ensure_installed = {...} })`
  table is gone; features like highlighting are no longer auto-enabled and must
  be wired up through Neovim's core APIs directly; parser installation is now a
  separate explicit function call rather than a config list.
- Neovim 0.12 (released 2026-03-29) ships **built-in treesitter support**
  (parser/query loading, plus a native plugin manager `vim.pack` and native LSP
  completion) directly in core, which is *why* the plugin's role shrank enough
  for the maintainer to feel comfortable archiving it.
- **Implication for this project**: since the constraint is nvim 0.11.6 as a
  *floor*, not a ceiling, the planning phase should explicitly decide whether
  to (a) stay on 0.11.6 and pin `nvim-treesitter` to the frozen `master` branch
  (parsers/queries stop advancing, but it works today with a config style
  close to the current plugin ecosystem's assumptions), or (b) upgrade Neovim
  to 0.12+ as part of this project and lean on built-in treesitter +
  `nvim-treesitter-textobjects` (still separately maintained, main branch) for
  textobjects only. Given the "no CI/test coverage, solo effort, evenings/
  weekends" constraints, (a) is lower-risk short-term; (b) is more future-
  proof and avoids inheriting a now-unmaintained dependency. Recommend
  flagging this explicitly as an ADR-worthy decision in Phase 3.
- Parser status for the four languages in scope (Go, Rust, Python,
  TypeScript/JS) is mature and stable in either branch — these are among the
  most well-maintained tree-sitter grammars in the ecosystem; no risk there.
- Use cases: syntax highlighting and incremental selection are rock-solid;
  textobjects via `nvim-treesitter-textobjects` are mature; treesitter-based
  **indentation** is still explicitly documented as experimental/imperfect for
  some languages (worth keeping vim-polyglot's or filetype-plugin indentation
  as fallback where treesitter indent misbehaves); treesitter-based
  **folding** works via `foldexpr`/`foldmethod=expr` and is commonly used, but
  adds some perf overhead on very large files (Konfekt/FastFold, already in the
  current plugin list, works alongside it and is worth keeping regardless of
  which treesitter branch is chosen).

---

## 3. Fuzzy-finding

**Recommendation: `fzf-lua`** — good fit given fzf is already installed and in
daily use, and it is now the more actively favored option community-wide,
though `telescope.nvim` remains extremely close and defensible.

- As of LazyVim 14 (released Dec 2024), the LazyVim default fuzzy finder
  changed from Telescope to fzf-lua — this is a meaningful community signal
  since LazyVim's defaults strongly shape ecosystem consensus.
- Rationale: `fzf-lua` shells out to a separate process for matching/filtering
  (the same fzf binary approach the user already has installed and has
  muscle memory for), giving shell-like responsiveness and much better
  performance on large repos/monorepos, since Telescope's picker pipeline is
  mostly synchronous Lua and can bog down on large result sets.
- `telescope.nvim` (paired with `telescope-fzf-native.nvim`, a C-compiled
  sorter) is still an excellent, more "native Neovim UI" experience with the
  larger extension ecosystem (many community pickers/extensions are
  Telescope-first) — a defensible choice if extension breadth matters more
  than raw performance.
- Either choice is a clean win over the status quo of `ctrlp.vim` +
  `vim-ctrlspace` + `fzf.vim` running simultaneously — all three should be
  removed as part of consolidation regardless of which target is picked.
  `fzf.vim` itself is the plain-Vimscript fzf wrapper and is now the
  "legacy" option relative to fzf-lua/Telescope for anyone doing a Lua-based
  config.
- Given the requirements' explicit note that "the user already has fzf
  installed" and the appetite for minimizing new external tool dependencies,
  `fzf-lua` is the pick — it reuses the exact binary already on the system
  and keybinding intuitions transfer more directly than adopting Telescope's
  different UI paradigm.

---

## 4. DAP (debugging)

`nvim-dap` (mfussenegger/nvim-dap) + `nvim-dap-ui` (+ `nvim-nio` as a required
dependency of dap-ui) is the only serious, actively maintained DAP client in
the Neovim ecosystem — not really a "vs" decision, this is the foundation
regardless of language. Recommend also `nvim-dap-virtual-text` for inline
variable values, and `mason-nvim-dap.nvim` to manage adapter installation
through Mason.

Per-language adapter maturity, from most to least plug-and-play:

| Language | Adapter | Plug-and-play? | Notes |
|---|---|---|---|
| **Go** | Delve, via `leoluz/nvim-dap-go` | **Yes — genuinely easy.** | `nvim-dap-go` wraps Delve config generation (`require('dap-go').setup()`), including per-test debugging out of the box. Delve installs cleanly via `go install` or Mason. Lowest-friction adapter of the four. |
| **Python** | `debugpy`, via `mfussenegger/nvim-dap-python` | **Yes, with Mason.** | Mason installs `debugpy` into an isolated venv (`~/.local/share/nvim/mason/packages/debugpy/venv/bin/python`); `nvim-dap-python` auto-detects project virtualenvs (`VIRTUAL_ENV`/`CONDA_PREFIX`/`venv`/`.venv` folder conventions). Setup is a couple of lines once Mason path is wired in. Recommend `mason-nvim-dap.nvim` with `ensure_installed = {"python"}` for automatic install. |
| **Rust** | CodeLLDB, via Mason, wired through **`rustaceanvim`** (not raw `nvim-dap` config) | **Mostly yes, moderate setup.** | `rust-tools.nvim` (the previous standard) was **archived Jan 2024** — its author explicitly redirects users to `mrcjkb/rustaceanvim`, a heavily modified fork. Rustaceanvim is deliberately "setup-less" and does *not* depend on `nvim-lspconfig` — it manages the rust-analyzer LSP client and DAP wiring (`:RustLsp debuggables`) itself. CodeLLDB installs cleanly via Mason. This is a bigger API-shape change vs. old rust-tools.nvim (command renames: `:RustRunnables`→`:RustLsp runnables`, etc.) so existing muscle memory / any legacy rust-tools config would need rewriting, not just swapping a dependency name. |
| **TS/JS** | vscode-js-debug, via `mxsdev/nvim-dap-vscode-js` (or Mason's `js-debug-adapter` package) | **No — genuinely fragile, flag this explicitly.** | Confirmed by multiple independent sources as the hardest of the four to set up. Historically required manually cloning `vscode-js-debug`, running `npm install --legacy-peer-deps`, `npx gulp vsDebugServerBundle`, and moving `dist/` → `out/` by hand — Mason's `js-debug-adapter` package now automates most of this, which should be preferred over the manual build. Even with Mason, the adapter's config surface (multiple debug types: `pwa-node`, `pwa-chrome`, attach vs. launch, source maps) is meaningfully more complex than the other three languages. Budget disproportionate time here relative to Go/Python, and treat "TS/JS debugging fully working" as the stretch goal of the DAP work rather than a given. |

`nvim-dap-ui` itself is mature and stable (breakpoints, variable inspection,
call stack, REPL, watches) — no maturity concerns there; it satisfies the
"DAP-based debugger... for at least Go and Python" success metric cleanly for
those two languages. Recommend scoping DAP work as Go + Python first (both
genuinely plug-and-play), then Rust, with TS/JS as an explicit stretch/lower-
confidence item given its adapter fragility — this maps directly onto the
"DAP adapter setup per language is fragile" rabbit hole flagged in
requirements.

---

## 5. Git integration

**Recommendation: keep `vim-fugitive`, add `gitsigns.nvim`; `neogit` +
`diffview.nvim` as optional upgrades, not required.**

- `vim-fugitive` (tpope) remains widely regarded as best-in-class for its core
  job (`:G`, `:Gdiffsplit`, blame, commit/rebase workflows) — there's no strong
  "native Lua fugitive replacement" the community has coalesced around the way
  there is for LSP/completion/fuzzy-finding. Nothing in the research surfaced
  a reason to rip it out; it's Vimscript but mature, fast, and has no
  functional deficiency vs. Lua alternatives for the workflows Tyler already
  uses it for.
- `gitsigns.nvim` is the near-universal complement, not a competitor — it adds
  the sign-column hunk markers, inline blame, hunk stage/unstage/reset, and
  hunk-navigation text objects that fugitive doesn't provide. Actively
  maintained (6.7k★, commits as recent as March 2026). This should be added
  regardless of what else changes — it's pure addition, not a migration risk.
- `neogit` (a Magit-alike, the direct modern replacement for the existing
  `vimagit`) and `diffview.nvim` (a unified diff/merge-conflict UI, the direct
  modern replacement for `Merginal`) are the natural swaps for the two
  redundant git UIs currently in the plugin list. One real-world report found
  in research: "Neogit is used the most by far, Gitsigns is mainly for the
  aesthetic, and diffview is useful when merging" — i.e. these three
  compose well together rather than compete.
  `diffview.nvim`'s last commit in that search snapshot was June 2024 (vs.
  gitsigns' March 2026) — worth a quick freshness check in Phase 3 before
  committing, but no evidence of abandonment, just a slower cadence typical of
  a feature-complete utility plugin.
- **Recommended consolidation**: drop `vimagit` and `Merginal` (redundant,
  confirmed dead-weight per requirements), keep `vim-fugitive`, add
  `gitsigns.nvim` unconditionally, and add `neogit` + `diffview.nvim` if Tyler
  wants a more visual staging/merge experience than fugitive's buffer-based
  UI — otherwise fugitive + gitsigns alone is a complete, defensible git
  stack and the simpler option (fewer plugins = less to maintain, in the
  spirit of the pruning goal).

---

## 6. Plugin manager

**Confirmed: `lazy.nvim` is still current best practice** for a config staying
on Neovim 0.11.x, and is already correctly bootstrapped in `.vimrc.plug`
(nothing to change there mechanically — just the misleading `.vimrc.dein`
symlink name, which the requirements already flag for cleanup/rename).

- `lazy.nvim` remains the most mature, most widely adopted plugin manager:
  async install/update, UI, lockfile (`lazy-lock.json`), conditional lazy-
  loading (`event`, `ft`, `cmd`, `keys`), and the largest ecosystem
  documentation/examples (LazyVim, kickstart.nvim, most current blog
  tutorials assume lazy.nvim syntax).
- `pckr.nvim` (packer.nvim's spiritual successor) is a lighter alternative but
  explicitly less stable/mature than lazy.nvim per community sources — no
  reason to switch to it here.
- `mini.deps` is now **frozen** — its own maintainer has paused development in
  favor of Neovim 0.12's new built-in `vim.pack` plugin manager. Since this
  project's floor is 0.11.6 (not 0.12), `vim.pack` isn't a realistic target
  yet without also deciding to bump the Neovim version (see the treesitter
  0.12 discussion above — these two decisions are linked: if the plan decides
  to require nvim 0.12+, `vim.pack` becomes a live option worth a quick
  look; if it stays on 0.11.6, lazy.nvim is simply the correct choice with no
  serious contenders).
- No version/API-relevant breaking changes surfaced for `lazy.nvim` itself in
  the 2025–2026 window — it has been the stable incumbent throughout the
  ecosystem churn documented above (blink.cmp, fzf-lua, treesitter
  archival), which is itself a point in its favor for a low-maintenance solo
  setup.

---

## 7. Current recommended versions/tags

Nearly everything in this stack is consumed as a **rolling HEAD dependency**
via lazy.nvim (no meaningful semver tags the way e.g. npm packages have) —
this is normal for the Neovim plugin ecosystem and matches how the existing
`.vimrc.plug` already pins plugins (by repo, not by version). The concrete
pins/branches worth calling out explicitly in the plan:

| Plugin | Pin/branch guidance |
|---|---|
| `neovim/nvim-lspconfig` | HEAD (rolling); works with both old `.setup()` style and new `vim.lsp.config`/`enable` API — no branch pin needed. |
| `saghen/blink.cmp` | HEAD; project publishes tagged releases (check latest at implementation time) — lazy.nvim users commonly pin `version = '*'` to track releases rather than main if stability matters more than bleeding-edge features. |
| `nvim-treesitter/nvim-treesitter` | **Decision-dependent**: `branch = "master"` if staying on nvim 0.11.6 (frozen, but works); `branch = "main"` only if the project also upgrades Neovim to ≥0.12. Do not mix — the two branches are incompatible rewrites. |
| `nvim-treesitter/nvim-treesitter-textobjects` | Track whichever branch matches the main treesitter branch decision above; still separately maintained regardless of the parent repo's archival. |
| `ibhagwan/fzf-lua` | HEAD (rolling); requires the `fzf` binary already installed on the system (satisfied). |
| `nvim-telescope/telescope.nvim` (if chosen instead) | HEAD, paired with `nvim-telescope/telescope-fzf-native.nvim` (requires `make` to build the C sorter). |
| `mfussenegger/nvim-dap` | HEAD (rolling, no tags). |
| `rcarriga/nvim-dap-ui` + `nvim-neotest/nvim-nio` | HEAD; `nvim-nio` is a hard dependency, must be listed explicitly in lazy.nvim deps. |
| `leoluz/nvim-dap-go` | HEAD. |
| `mfussenegger/nvim-dap-python` | HEAD; pairs with Mason-installed `debugpy`. |
| `mrcjkb/rustaceanvim` | HEAD; **note it replaces `simulrat39/rust-tools.nvim` entirely** — do not add both. |
| `mxsdev/nvim-dap-vscode-js` | HEAD; pair with Mason's `js-debug-adapter` package rather than the manual vscode-js-debug build steps. |
| `mason-org/mason.nvim` + `jay-babu/mason-nvim-dap.nvim` | HEAD; recommended glue for all four DAP adapters above. |
| `lewis6991/gitsigns.nvim` | HEAD (rolling, actively maintained as of March 2026). |
| `NeogitOrg/neogit` | HEAD, optional. |
| `sindrets/diffview.nvim` | HEAD, optional; slower commit cadence, verify freshness at implementation time. |
| `tpope/vim-fugitive` | HEAD; keep as-is per requirements' explicit allowance. |
| `folke/lazy.nvim` | `branch = "stable"` (already what `.vimrc.plug` bootstraps today) — no change needed. |

---

## Key cross-cutting takeaway for Phase 3 (planning)

Two upstream ecosystem events happened *very recently* relative to this
research (Neovim 0.12 release 2026-03-29, nvim-treesitter archival
2026-04-03) that directly intersect the "nvim 0.11.6 minimum" constraint.
The plan should treat **"stay on 0.11.6 vs. upgrade to 0.12+"** as an explicit
early decision (ADR-worthy) because it cascades into: which treesitter branch
to use, whether `vim.pack` is viable as an alternative to lazy.nvim, and
whether to rely on Neovim's new built-in LSP completion vs. blink.cmp/nvim-cmp.
Staying on 0.11.6 is safe and fully supported by every recommendation above;
upgrading to 0.12+ trades some near-term migration work for less reliance on
the now-archived nvim-treesitter plugin going forward.
