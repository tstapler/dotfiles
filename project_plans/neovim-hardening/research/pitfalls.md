# Research: Known Pitfalls — Neovim Hardening Migration

**Agent**: 4 (Pitfalls)
**Scope**: What goes wrong in practice when migrating a decade-old vimscript+coc.nvim config (lazy.nvim, ~50 plugins, nvim 0.11.6) toward native LSP/treesitter/DAP, for a solo daily driver across Go/Rust/Python/TS-JS.

---

## 1. coc.nvim → native LSP migration pitfalls

**The core hazard is well-documented and matches the requirements' own Feasibility Risk**: coc.nvim and the native LSP client cannot cleanly run side-by-side for the same language server. coc.nvim spawns its own `coc-*` extension processes (often wrapping the same `gopls`/`rust-analyzer`/`pyright`/`tsserver` binaries) that attach to the buffer independently of anything `vim.lsp` or `nvim-lspconfig` starts. If both are pointed at the same filetype simultaneously:

- **Duplicate diagnostics**: two LSP clients publish `textDocument/publishDiagnostics` for the same file, so virtual text and the loclist/quickfix show every issue twice.
- **Competing completion popups**: coc's own popup menu (`coc#refresh()`) and native `vim.lsp` completion (or nvim-cmp/blink.cmp) both try to render on `InsertCharPre`/`TextChangedI`, causing flicker, wrong-item-selected bugs, or the two popups fighting for the same z-order.
- **Keymap collisions**: `gd`, `gr`, `K`, `<leader>rn` are the exact bindings both ecosystems expect to own. coc.nvim deliberately does **not** set these itself (to "avoid conflict with other plugins" — confirmed on the coc.nvim README/discussions), which means *your own* mappings currently call `coc#rpc#...` functions. If lspconfig/native LSP is added without first deleting the coc-era mappings, the last `nnoremap` registered silently wins and the other system's binding becomes dead code — the classic "why isn't this working" mid-migration confusion.
- **Diagnosing which system currently owns a key**: `:verbose nmap gd` / `:verbose nmap K` shows the source file/line of the winning mapping — the standard debugging move called out repeatedly in migration writeups (gierdo's blog, mark-story.com).

**Snippet engine migration** (coc-snippets, which itself wraps UltiSnips/vim-snippets syntax) → native `vim.snippet` (nvim 0.10+) or LuaSnip:
- coc-snippets supports both its own snippet syntax and UltiSnips syntax via a `pythonx`-dependent provider; if the migration path is coc-snippets → LuaSnip, existing personal UltiSnips-style snippets are **not directly compatible** — `mireq/luasnip-snippets` exists specifically because vim-snippets/UltiSnips-format snippets need conversion to LuaSnip's Lua-table format. Personal snippets accumulated over a decade should be inventoried before ripping out coc-snippets, or they silently stop being available.
- LuaSnip is the more mature choice for nvim-cmp/blink.cmp integration; native `vim.snippet` (0.10+) is lighter but has less LSP-snippet placeholder/choice-node polish as of nvim 0.11.6 — worth prototyping with one real Go/TS snippet before committing.

**How people get stuck mid-migration** (recurring pattern across the sources): they add nvim-lspconfig/mason for one language to "try it out," get diagnostics/completion partially working, but don't rip out the corresponding `coc-<lang>` extension or the coc keymaps — producing a hybrid that's strictly worse than either pure setup (duplicate signs in the sign column, `K` sometimes showing coc's hover and sometimes native hover depending on which loaded last). The nvim-lspconfig migration issue thread (#3494) and neovim/neovim discussion #35942 confirm this exact failure mode is common enough that maintainers explicitly warn against partial adoption — **the requirements.md rabbit-hole callout ("easy to half-migrate") is accurate and should be treated as the primary execution risk, not a hypothetical.**
- Mitigation: migrate **one language at a time, fully** (disable the coc extension for that filetype entirely, remove its coc keymaps/autocmds, verify with `:checkhealth vim.lsp` that exactly one client is attached via `:LspInfo` before moving to the next language) rather than flipping a global "use native LSP" switch.

---

## 2. DAP setup pitfalls (nvim-dap + adapters)

Confirms the requirements' Feasibility Risk that DAP setup is "the most fragile part of a modern config" — budget real time.

**Go / delve**:
- `dlv` must be resolvable by nvim-dap's adapter config, but relying on `$PATH` alone is a common failure point when delve is installed via Mason into `~/.local/share/nvim/mason/bin` rather than `go install`. The reliable pattern is to hardcode the adapter's `command` to `vim.fn.stdpath("data") .. "/mason/bin/dlv"` (or the `go install` GOBIN path) rather than assuming PATH inheritance — shells launched from GUI app launchers or from `nvim` invoked via a wrapper script often don't have the same PATH as an interactive shell.
- Remote-attach mode (`dlv dap` server + attach) has known rough edges (go-delve/delve#3029) — prefer the simpler launch-mode config unless remote debugging is actually needed.

**Python / debugpy**:
- `nvim-dap-python`'s venv auto-detection checks `$VIRTUAL_ENV`, `$CONDA_PREFIX`, and `venv`/`.venv`/`env`/`.env` directories relative to CWD or the LSP root_dir — but this **only works if nvim is launched with the venv already active or the venv directory follows one of those exact names**. A poetry/pipenv project with a venv in a non-standard location (e.g. pipenv's hashed path outside the project dir) will silently resolve to system Python and then fail to import `debugpy`, or worse, debug against the wrong interpreter without an obvious error. A custom `resolve_python()` function (or explicit `pythonPath` per launch config) is the robust fix, not the default auto-detect.
- On Debian/Ubuntu, Mason's debugpy install can fail if `python3-venv` isn't installed system-wide (a genuine footgun since the failure looks like a Mason bug, not a missing system package) — worth checking with `python3 -m venv --help` before troubleshooting the Neovim side.
- Test with `/path/to/python -m debugpy --version` to isolate "wrong Python" from "nvim-dap config" bugs.

**Rust / codelldb vs rust-analyzer**:
- Community consensus (rustaceanvim maintainer guidance, multiple threads) is to **not** let Mason manage `rust-analyzer` — version drift between a Mason-pinned rust-analyzer and the project's actual Rust toolchain version causes subtle diagnostic/macro-expansion mismatches that are hard to distinguish from real bugs. Prefer `rustup component add rust-analyzer` (toolchain-matched) over `:MasonInstall rust-analyzer`.
- codelldb (the DAP adapter, separate from rust-analyzer) is comparatively more decoupled from toolchain version but still needs to match the target's debug-info format; `rustaceanvim` auto-wires nvim-dap configs on LSP attach, which reduces (but doesn't eliminate) manual codelldb path wiring. Run `:checkhealth rustaceanvim` after setup.

**Cross-cutting DAP pitfalls**:
- **launch.json-equivalent duplication across projects**: nvim-dap configs are Lua tables per-filetype in your Neovim config, not per-project — meaning every Go/Python/Rust project shares one global launch config unless you add per-project overrides (e.g. a `.nvim.lua` local config, gated behind `exrc`/`vim.trust`, or nvim-dap's project-local `.vscode/launch.json` reader via `nvim-dap-vscode-js`-style shims). Decide up front whether per-project launch config support is in scope, since the "one config to rule all projects" default breaks as soon as two projects need different args/env/cwd.
- **Breakpoints not binding on lazy-loaded DAP plugins**: if `nvim-dap` itself is lazy-loaded on `cmd = "DapToggleBreakpoint"` or similar, a breakpoint set before the plugin loads (e.g. via a keymap that doesn't force-load first) can silently no-op. Load nvim-dap eagerly or make every DAP-related keymap force the plugin to load synchronously before calling into it (lazy.nvim's `keys` trigger handles this correctly if configured as a lazy-load trigger, but a raw keymap defined outside the lazy spec will not).

---

## 3. Treesitter pitfalls

**Parser/query version drift after nvim upgrades**: nvim-treesitter parsers are versioned independently from the plugin and from Neovim's bundled tree-sitter runtime ABI. Multiple GitHub issues (nvim-treesitter#6618, #4915) show highlighting/query breakage after a Neovim upgrade when installed parsers were compiled against an older tree-sitter ABI — the fix is always `:TSUpdate` after any nvim version bump, but this is easy to forget and manifests as confusing "highlighting just broke" reports days after an unrelated system update (e.g. `pacman -Syu` bumping neovim on Manjaro, which is this user's OS).

**Markdown parser vs vimwiki — this is the requirements' explicit "must not break" dependency (`~/personal-wiki/logseq/pages`)**:
- Confirmed real-world conflict (nvim-treesitter#6720): vimwiki buffers throw `no parser for 'vimwiki' language` errors when treesitter folding is active, because there is no dedicated `vimwiki` tree-sitter grammar — treesitter has nothing to parse vimwiki's own syntax with, yet folding/highlighting machinery still tries.
- Separately (nvim-treesitter#5922), the **markdown parser itself has a known bug where switching between markdown buffers corrupts parse state when `foldmethod=marker`** — relevant because vimwiki files are often also `.md`-adjacent or configured with marker-based folding.
- **Concrete mitigation for this repo**: explicitly exclude the `vimwiki` filetype from treesitter's `highlight`/`indent`/`fold` module attachment (`disable = { "vimwiki" }` in the parser config, or via an `ftplugin`/autocmd that keeps vimwiki on its native vimscript syntax+folding). Do not let treesitter's generic markdown parser attach to `*.wiki` files even if the filetype detection is ambiguous. Since vim-zettel/vimwiki are explicitly out-of-scope for improvement but must not regress, the safest move is an explicit disable rule tested against the real `~/personal-wiki/logseq/pages` files before merging, not an assumption that "it'll just work."
- Nested-list folding is also independently buggy in the markdown parser (#5366) — irrelevant to vimwiki specifically but relevant if the migration also touches note-taking-adjacent markdown scratch files.

---

## 4. Plugin-pruning pitfalls ("is this actually used?")

There is no automated way to answer "is this plugin load-bearing" — none of the plugin managers (dein, lazy.nvim, vim-plug) have a reliable usage-tracking feature; `dein#check_clean()` and similar tools only detect *installed-but-not-declared* plugins, not *declared-but-unused* ones. Practical detection strategies, since none exist off-the-shelf:

- **Keymap audit**: grep the vimscript/Lua config for every `nnoremap`/`vnoremap`/`nmap` bound to a plugin's command, then check personal muscle memory / shell history / recent usage against that list. For `vim-ctrlspace` specifically: it provides *workspace/session persistence* (multi-buffer/tab layouts saved per project) that's easy to take for granted until it's gone — if fzf.vim or Telescope becomes the single fuzzy-finder, **explicitly verify whether session/workspace persistence needs a replacement** (e.g. `mksession`-based autosave, or a dedicated session plugin) rather than assuming Telescope's session extension is a drop-in replacement — it usually isn't at feature parity.
- **`undotree`**: low interaction-surface (usually one keymap, `:UndotreeToggle`) — easy to verify usage by checking if that keymap has muscle memory attached; safe to test in isolation since it has no cross-plugin dependents.
- **`vim-surround` / `vim-repeat`**: these have a real dependency relationship — vim-surround (and several other tpope plugins) call `repeat#set()` to make `.` re-run their last action; vim-repeat is a shared *dependency*, not a competing/redundant plugin. **Do not prune vim-repeat while keeping vim-surround** — that would silently break `.`-repeat for surround operations specifically (the surround mapping still works, but pressing `.` afterward does a generic Vim repeat instead of re-running the surround command, which is a subtle enough regression to go unnoticed for a while).
- General rule for this migration: for each of the ~50 plugins, before deleting, grep the config for its command names/keymaps *and* mentally walk through "when did I last invoke this" — treat "I don't remember" as "probably safe to remove, but note it in a rollback list" rather than deleting blind, since the whole point of the worktree-based risk control is that removal mistakes are cheap to catch — but only if there's a checklist of what was removed to re-add from if a workflow gap surfaces later.

---

## 5. lazy.nvim-specific pitfalls

**Lazy-loading misconfiguration ("installed but broken")**: this is a confirmed, still-open class of bugs (lazy.nvim#858, #1049) — plugins lazy-loaded on `event` triggers can miss the actual event firing correctly, particularly when:
- A plugin needs `BufReadPre`/`BufReadPost` (which fire *before* `FileType`) but is configured to lazy-load on `FileType` — by the time it loads, the earlier events it depends on have already fired and won't re-fire, so the plugin initializes into a buffer state it never saw the setup events for.
- The fix pattern the lazy.nvim maintainers and community land on: for plugins with autocmd-dependent setup, either lazy-load on the *earliest* relevant event (usually `BufReadPre` rather than `FileType`), or accept eager-loading for anything whose setup logic is order-sensitive. `:checkhealth lazy` and manually re-triggering with `:e` (re-open current buffer) are the standard debugging techniques when a plugin "is installed, `:Lazy` shows it loaded, but it doesn't seem to do anything."

**Plugin spec merge conflicts**: lazy.nvim merges per-plugin specs across every `lua/plugins/*.lua` file, but the merge semantics differ by key type:
- Key-value table opts (most `opts = {...}` blocks) merge automatically.
- **List-like tables (e.g. `keys`, some `opts` that are arrays) get *overridden*, not merged, by default** — a second spec file redefining `keys` for a plugin wipes out the first file's keys entirely unless `opts_extend` is explicitly declared for that key. This is a real footgun when splitting a monolithic plugin config into per-file specs (which this migration explicitly plans to do via `init.lua` + `lua/` modules) — moving from one big spec table to several files can silently drop list-valued config unless `opts_extend` is set per plugin that needs it.
- lazy.nvim resolves same-named-plugin specs across files alphabetically by filename, so whichever file sorts first becomes the "parent spec" for override purposes — an implicit, easy-to-forget ordering dependency worth documenting in the eventual plan (e.g. a numbering/naming convention for `lua/plugins/*.lua` files).

**Startup-time regression risk**: the requirements explicitly gate on `vim-startuptime` not regressing. The main lazy.nvim-specific way to regress startup despite using a "modern" lazy-loading plugin manager is over-eager `event = "VeryLazy"` or `lazy = false` usage during migration — it's common to eager-load things "just to get them working" while debugging lazy-load trigger issues (see previous bullet) and then forget to convert them back to a proper lazy trigger before merging.

---

## 6. cfgcaddy / dotfiles deployment pitfalls

**Single-file → `lua/` directory tree migration**: the current cfgcaddy mapping is `.vimrc` → two destinations (`~/.vimrc`, `~/.config/nvim/init.vim`) — a single-file symlink. If the new config becomes `init.lua` + a `lua/` module tree, this is no longer a single-file symlink relationship:
- **Stale symlinks**: if cfgcaddy's mapping isn't updated to reflect the new file set (e.g. it still tries to symlink a `.vimrc` that no longer exists, or fails to add mappings for the new `lua/` directory), a machine that re-runs the deploy script may end up with a stale dangling symlink pointing at a deleted `.vimrc`, while the actual live config lives untracked in `~/.config/nvim/lua/`.
- **Partial syncs across machines**: if cfgcaddy maps individual files rather than the whole `lua/` directory as one unit, adding a new module file to the Lua config requires *also* remembering to add its own mapping entry — easy to forget, and the failure mode is silent (the file works locally in the worktree/dev machine but is simply absent on a second machine after `cfgcaddy sync`, because it was never added to `.cfgcaddy.yml`). Prefer mapping the whole `nvim/` directory (or `lua/` subtree) as a single recursive symlink/directory mapping over per-file entries, specifically to avoid this class of bug.
- Confirm whether cfgcaddy supports directory-level symlinking (symlink the whole directory once) vs. file-level only — this determines whether the "add a new lua module = add a new cfgcaddy entry" trap exists at all.

**`lazy-lock.json` and `.gitignore`**: community consensus (LazyVim discussions #850, #4403) is split but leans toward **committing** the lockfile if the same config is used across multiple machines and reproducible plugin versions matter — which is exactly this user's situation (dotfiles repo, deployed to multiple machines via cfgcaddy). Recommendation: **commit `lazy-lock.json`**, not gitignore it, so that a `cfgcaddy sync` onto a second machine reproduces the exact plugin versions validated during the worktree testing phase, rather than pulling latest-and-possibly-broken versions on first install elsewhere. The alternative (gitignore it) trades reproducibility for less commit noise — not worth it here given the explicit "don't regress startup time / don't break daily-driver workflows" requirements, which are easier to guarantee with pinned versions.

---

## 7. Personal risk for a daily-driver, even with the worktree mitigation

The plan's stated risk control (build/dogfood entirely inside the `dotfiles-harden-neovim` worktree, master stays untouched, cutover is a single merge) correctly isolates *config file* risk. It does **not** fully isolate *machine state* risk. Concretely, things that can still bite mid-week despite testing only in the worktree:

- **`~/.local/share/nvim` is shared, not branch-scoped.** Neovim's plugin install directory, Mason's installed binaries, and the lazy.nvim lockfile-resolved plugin checkouts all live in a single global `~/.local/share/nvim` regardless of which config (master's or the worktree's) is active — because both configs point `nvim` at the same data directory by default. Testing the new config installs new plugins and new Mason LSP/DAP binaries into that same shared directory. If master's coc.nvim setup and the new lspconfig/DAP setup both get exercised in the same week (e.g. switching back to master briefly for a "just get this done" moment), there's no isolation between their plugin installs — a broken Mason binary install from testing, or a lazy.nvim plugin left in a partially-updated state, can affect master's session too, because master will `require` from the same `~/.local/share/nvim/lazy/*` checkouts if the plugin names overlap.
  - **Mitigation worth adding to the plan**: point the worktree's nvim invocation at an isolated `NVIM_APPNAME` (e.g. `NVIM_APPNAME=nvim-harden nvim`, which as of nvim 0.9+ isolates `~/.config/nvim-harden`, `~/.local/share/nvim-harden`, `~/.local/state/nvim-harden` automatically) rather than relying on the worktree's file content alone. Without this, "testing in the worktree" only isolates the *config source*, not the *runtime state* — which is exactly the gap the requirements' own Observability Requirements section doesn't call out.
- **The global `~/.config/nvim` symlink is a single pointer.** Since cfgcaddy deploys via symlink, `~/.config/nvim` points at one location at a time. If it's re-pointed at the worktree's config during testing, then *every* terminal session/editor invocation for the rest of that week — including ones unrelated to this project — is running the experimental config, not master's known-good one. A mid-week deadline task in an unrelated repo, opened with muscle-memory `nvim`, inherits whatever half-working state the harden branch is in that day. This is the actual "goes wrong mid-week" failure mode the requirements gesture at ("Rollback is `git checkout master`") — but `git checkout master` only fixes the symlink target on next launch, not an nvim session already running against a broken LSP/DAP setup, and it does nothing about the shared `~/.local/share/nvim` state above.
- **Mason-installed LSP/DAP binaries drift out of sync with the config that expects them.** If a Mason package is uninstalled/reinstalled or upgraded during worktree experimentation (e.g. testing a rust-analyzer version), and then master's coc.nvim setup (which may also shell out to some of the same binaries, e.g. `gopls` if coc-go wraps the same install) is used in between, version mismatches (see Section 2's codelldb/rust-analyzer warning) can appear in the *old* master config too, misattributed as a master regression when it's actually cross-contamination from worktree testing.
- **Net recommendation for the plan**: use `NVIM_APPNAME` (or equivalent full data-dir isolation) for the duration of development, not just a separate `~/.config/nvim` symlink target, so that a mid-week emergency `nvim` invocation via the normal command reliably gets master's untouched, fully-working setup with its own untouched plugin/Mason state — and so that the "worktree isolates risk" claim in the Risk Control section is actually true at the runtime-state level, not just the config-source level.

---

## Sources

- [neovim config - native lsp support instead of coc — gierdo's blog](https://gierdo.astounding.technology/blog/2024/09/19/nvim-lsp)
- [Switching to NeoVim Native LSP — Mark Story](https://mark-story.com/posts/view/switching-to-neovim-native-lsp)
- [CoC vs native LSP (mason/lspconfig) · neoclide/coc.nvim Discussion #4866](https://github.com/neoclide/coc.nvim/discussions/4866)
- [neoclide/coc.nvim](https://github.com/neoclide/coc.nvim)
- [Migrate to vim.lsp.config (non-breaking) · nvim-lspconfig#3494](https://github.com/neovim/nvim-lspconfig/issues/3494)
- [How to migrate lspconfig to 0.11 · neovim/neovim Discussion #35942](https://github.com/neovim/neovim/discussions/35942)
- [Debugging in Neovim — harrisoncramer.me](https://harrisoncramer.me/debugging-in-neovim/)
- [I'm struggling to use dlv dap with remote attach · go-delve/delve#3029](https://github.com/go-delve/delve/issues/3029)
- [Debugging in Neovim with nvim-dap — John Tobin](https://www.johntobin.ie/blog/debugging_in_neovim_with_nvim-dap/)
- [mfussenegger/nvim-dap-python](https://github.com/mfussenegger/nvim-dap-python)
- [Fixing AstroNvim Python Debugging: DAP "No Adapter" and debugpy Issues](https://vcfvct.wordpress.com/2026/05/28/fixing-astronvim-python-debugging-dap-no-adapter-and-debugpy-issues/)
- [Python Debugging Nightmare · mfussenegger/nvim-dap Discussion #1268](https://github.com/mfussenegger/nvim-dap/discussions/1268)
- [Neovim Rust debugging — more zeros than ones](https://morezerosthanones.com/posts/neovim_rust_debugging/)
- [mrcjkb/rustaceanvim](https://github.com/mrcjkb/rustaceanvim)
- [Rust/Cargo and nvim-dap/codelldb interaction · nvim-dap Discussion #671](https://github.com/mfussenegger/nvim-dap/discussions/671)
- [markdown grammar broken · nvim-treesitter Discussion #6618](https://github.com/nvim-treesitter/nvim-treesitter/discussions/6618)
- [vimwiki parser issue · nvim-treesitter#6720](https://github.com/nvim-treesitter/nvim-treesitter/issues/6720)
- [switching markdown buffers makes parsing fail with foldmethod=marker · nvim-treesitter#5922](https://github.com/nvim-treesitter/nvim-treesitter/issues/5922)
- [Markdown folds don't work correctly with nested lists · nvim-treesitter#5366](https://github.com/nvim-treesitter/nvim-treesitter/issues/5366)
- [bug: plugins lazy loaded with autocmd events don't always execute · lazy.nvim#858](https://github.com/folke/lazy.nvim/issues/858)
- [bug: some autocmd events are not fired when lazy loading · lazy.nvim#1049](https://github.com/folke/lazy.nvim/issues/1049)
- [Lazy Loading | lazy.nvim docs](https://lazy.folke.io/spec/lazy_loading)
- [Debugging and Troubleshooting | folke/lazy.nvim DeepWiki](https://deepwiki.com/folke/lazy.nvim/9.2-debugging-and-troubleshooting)
- [Structuring Your Plugins | lazy.nvim docs](https://lazy.folke.io/usage/structuring)
- [Could someone please elucidate how "merging" specs works · lazy.nvim Discussion #1706](https://github.com/folke/lazy.nvim/discussions/1706)
- [Can I add lazy-lock.json to .gitignore? · LazyVim Discussion #850](https://github.com/LazyVim/LazyVim/discussions/850)
- [can i put lazy.lock to .gitignore? · LazyVim Discussion #4403](https://github.com/LazyVim/LazyVim/discussions/4403)
- [Lockfile | lazy.nvim docs](https://lazy.folke.io/usage/lockfile)
- [mireq/luasnip-snippets](https://github.com/mireq/luasnip-snippets)
- [From UltiSnips to LuaSnip — cj.rs](https://cj.rs/blog/ultisnips-to-luasnip/)
- [neoclide/coc-snippets](https://github.com/neoclide/coc-snippets)
- [vim-ctrlspace/vim-ctrlspace](https://github.com/vim-ctrlspace/vim-ctrlspace)
- [thaerkh/vim-workspace](https://github.com/thaerkh/vim-workspace)
- [mbbill/undotree](https://github.com/mbbill/undotree)
- [Support linking executables using relative symlinks · mason.nvim#1156](https://github.com/mason-org/mason.nvim/issues/1156)
- [Mason offline (or portable Mason?) · mason.nvim Discussion #1526](https://github.com/mason-org/mason.nvim/discussions/1526)
- [Switching configs in Neovim — Michael Uloth](https://michaeluloth.com/neovim-switch-configs/)
