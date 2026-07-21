# UX Research: Interaction & Workflow Ergonomics (Agent 5)

**Scope**: How Neovim "IDE" setups structure interaction for code intelligence, debugging, navigation, and git — read through the lens of an IntelliJ user (Tyler) trying to stop reaching for a full IDE. Covers comparable UX patterns, mental-model mismatches, keymap ergonomics, error/edge-case UX, and job-to-be-done prioritization.

---

## 0. Confirmed finding: the leader-key conflict is real, and worse than "unresolved" — it's silently overridden

Read directly from the worktree:

- `.vimrc` line 48: `let mapleader=","` — set early, before the plugin manager loads.
- `.vimrc` line 122-127: sources `~/.vimrc.dein` (the deployed symlink for `.vimrc.dein -> .vimrc.plug` in this repo) *after* line 48.
- `.vimrc.plug` (i.e. `.vimrc.dein`) lines 3-26: a `lua << EOF` bootstrap block for lazy.nvim, which at line 24 sets `vim.g.mapleader = " "`.

Because `.vimrc.dein` is sourced *after* `.vimrc` sets `mapleader = ","`, and Vim's "last write wins" for global variables, **the effective leader is space, not comma** — the comma assignment is dead code that creates a false mental model. This isn't a live conflict causing errors today only because `.vimrc` itself defines zero `<leader>`-prefixed mappings — all ~20 `<leader>` mappings live in `.vimrc.plug`/coc-vim section, and they're all written assuming space (e.g. `<space>a`, `<space>e`, `<space>s` for CocList, and `<leader>f`, `<leader>a`, `<leader>rn` which resolve to space-prefixed because that's the active leader by the time they're defined).

**Concrete risk**: any new mapping added to `.vimrc` (the "primary" file, which reads as authoritative because it's read first and has the visible `mapleader` declaration) that uses `<leader>` will silently bind to space, not comma, contradicting the file's own stated intent. A future maintainer reading `.vimrc` alone would reasonably expect comma-based bindings and be confused when they don't fire, or worse, accidentally shadow an existing space-prefixed coc/lazy binding.

**Recommendation for planning phase**: pick space explicitly (it already wins, and is the modern-convention default per LazyVim/AstroNvim/NvChad — see below), delete the vestigial `let mapleader=","` line, and add a single authoritative comment where leader is declared, in whichever file becomes canonical after the vimscript-vs-Lua decision.

---

## 1. Comparable UX patterns: how modern "IDE" Neovim setups structure interaction

The through-line across LazyVim, AstroNvim, NvChad, and kickstart.nvim is **not** "recreate IDE panels" — it's **"surface the same information through Neovim's native primitives (floating windows, splits, buffers, quickfix) triggered by keyboard, and make discovery a keyboard action, not a persistent visual scan."**

### 1a. Fuzzy nav — Telescope (and the fzf-lua shift)
Telescope's picker UX is a 3-pane pattern (prompt → results list → live preview) surfaced as an ephemeral floating window, not a permanent sidebar. The picker's leverage points that reduce real friction:
- **Live preview pane** — no need to open-then-check like ctrlp.vim's list-only UX; you see the file/definition before committing.
- **Composable pickers** — the same UI primitive serves file-find, live grep, LSP symbols, git status, buffers, diagnostics, etc. One interaction pattern, N data sources — this is the actual friction reduction vs. running 3 separate fuzzy-finders (ctrlp/ctrlspace/fzf.vim) with 3 different UIs and 3 sets of keybindings, which is literally the current-state problem in this repo.
- Note the ecosystem has shifted: as of LazyVim 14, **fzf-lua is now the default picker**, not Telescope, mainly for perceived speed/rendering-width complaints against Telescope (some users found Telescope's list column too narrow or laggier on large repos; fzf-lua wraps the native fzf binary for matching speed while keeping a similar preview-pane UX). Either is a legitimate "one fuzzy-finder" consolidation target — the choice is a planning-phase decision, not a UX-pattern difference; both share the prompt+list+preview interaction model this repo currently lacks as a single coherent thing.

### 1b. Debugging — nvim-dap-ui panel layout
nvim-dap-ui's model: debug "elements" (scopes/variables, call stack, breakpoints, watches, REPL/console) are independent windows grouped into named **layouts**, dockable to any screen edge, toggled as a unit. This is the closest any of the 4 areas gets to literally cloning an IDE's persistent-panel layout — and it's also the area where the community most explicitly flags the friction: a multi-pane layout assumes mouse-driven pane-switching in IDEs, but in Neovim every pane switch is a keyboard window-nav action (`<C-w>` motions), which adds real per-switch cost that doesn't exist when you just glance at an IDE's always-visible panels or click into one.
- This is why **nvim-dap-view** exists as a competing, newer approach (as of the current ecosystem): a **single-window** debug UI that time-slices between scopes/stack/watches/REPL in one buffer via tabs/toggles rather than a multi-pane split layout — explicitly trading "see everything at once" for "less window-navigation overhead." This is a genuine UX fork Tyler should be aware of during planning: nvim-dap-ui = IntelliJ-like multi-pane (familiar mental model, more nav overhead); nvim-dap-view = Neovim-native single-window (less familiar, less nav overhead). Given Tyler is actively trying to *learn* the Neovim-native workflow rather than recreate IntelliJ, nvim-dap-view's approach is worth a look, but nvim-dap-ui remains the more battle-tested/mature default with broader adapter-ecosystem documentation (relevant given the plan's own flagged DAP-maturity risk).
- Regardless of which UI, the debugging interaction model itself (breakpoint via sign-column click-equivalent keybind, step via keybinds, hover-eval via keybind or floating window) maps closely enough to IntelliJ's debugger that this is the *lowest* mental-model-mismatch area of the four — the panels differ in chrome, not in what action does what.

### 1c. Git — gitsigns.nvim (inline) vs diffview.nvim (full-view), not either/or
The current config has three overlapping git plugins (vim-fugitive, Merginal, vimagit) mapping to a similarly overlapping IntelliJ mental model (a single "Git" panel doing everything: status, diff, blame, merge). The modern Neovim-native pattern **splits by task, not by tool**:
- **gitsigns.nvim** — inline, buffer-local awareness: sign-column markers for added/changed/deleted lines, hunk navigation, and crucially **per-line/per-hunk staging directly in the buffer you're editing** (`:Gitsigns stage_hunk`, works on a visual selection for partial-hunk staging). This is *more* granular than IntelliJ's per-file/per-hunk staging in its Commit panel — a genuine capability upgrade, not just a UI change.
- **diffview.nvim** — the full-view counterpart for when you actually need a dedicated screen: a single tabpage cycling through all changed files' diffs, and a **3-way merge-conflict view** (base/ours/theirs) for actual conflict resolution — this is the closest Neovim-native equivalent to IntelliJ's merge tool.
- **neogit** (not explicitly searched in requirements but relevant) commonly fills the "commit workflow" gap (staging UI, commit message buffer, log) that fugitive's `:Gstatus` covers today.
- The idiomatic pattern is explicitly **complementary, not competing**: gitsigns for ambient awareness + line staging (replaces the "glance at gutter" + "stage this line" IntelliJ habit), diffview for full-file-diff and merge conflicts (replaces "open the Git tool window diff"), and a commit/status UI (neogit or fugitive) for the commit workflow itself. Three tools, but each owns a distinct job — unlike the current fugitive+Merginal+vimagit trio which appears to have three tools doing overlapping subsets of the same jobs.

### 1d. Code actions/refactors — popup-with-preview, not modal dialog
lspsaga.nvim and tiny-code-action.nvim (Telescope-integrated) and nvim-code-action-menu converge on the same pattern: a **floating popup listing available actions, navigable with j/k, with a diff/preview of the effect before committing** (Enter to execute). This is the Neovim-native equivalent of IntelliJ's Alt+Enter quick-fix popup — genuinely close in interaction shape (small popup, arrow/hjkl select, enter to apply), so this is a *low-mismatch* area once wired up, similar to debugging. The friction isn't the interaction pattern; it's that native `vim.lsp.buf.code_action()` alone (no plugin) has a plainer selection UI without the diff preview — plan should pick one of the popup-with-preview plugins rather than relying on the raw built-in prompt if "confidence doing a refactor without checking IntelliJ" is a goal.

---

## 2. Mental model mismatches: what to translate, not clone

| IntelliJ expectation | Underlying need | Neovim-native equivalent | Why it satisfies the need without cloning the UI |
|---|---|---|---|
| Always-visible project tree (left sidebar) | Spatial orientation: "where am I in the project," discoverability of files I don't remember the name of | Telescope/fzf-lua `find_files` + `oil.nvim` (edit-the-directory-as-a-buffer) rather than neo-tree/nvim-tree as a permanent drawer | Fuzzy-find covers "I know roughly what I want" (the majority case); oil.nvim covers "I want to browse/rename/move" via normal editing commands (dd to delete a file, yank/paste to copy) — no separate tree-navigation modal to learn. A permanent sidebar (neo-tree) is available as a fallback for the rarer "I need to see the whole shape of an unfamiliar codebase" case, but shouldn't be the default reflex the way IntelliJ's tree is, since it costs a fixed chunk of horizontal buffer space that Neovim's split model doesn't want to give up permanently. |
| Mouse-driven panel clicking (Debug tool window, Git tool window, Structure panel) | Fast context-switch between "what I'm editing" and "supporting info about it" | Toggleable floating windows / transient splits bound to single keypresses (`<leader>d` opens DAP UI, `<leader>gg` opens git status, `gO` opens symbol outline) that close as easily as they open | The need is fast access to supporting context, not permanent visibility of it. Transient windows keep the editing buffer maximized by default and pull in context only on demand — this is *faster* once the keybind is muscle memory, but requires giving up the "glance without pressing a key" affordance IntelliJ provides. This is the single biggest adjustment cost for an IntelliJ user and should be named explicitly rather than hidden. |
| Inline everything (inline diagnostics text at end of line by default, inline hints) | Immediate visibility of problems without extra action | Neovim's diagnostic virtual text (on by default in `vim.diagnostic`) + gitsigns inline hunk markers already match this one closely | Low mismatch — this is an area where Neovim's defaults already resemble IntelliJ's. Worth explicitly enabling/tuning (`vim.diagnostic.config({virtual_text = true})`) rather than assuming it, since some LazyVim-style configs favor virtual_lines or off-by-default to reduce clutter. |
| Structure/outline panel (persistent) | "What functions/classes exist in this file" | `gO` / Telescope `lsp_document_symbols` / trouble.nvim's symbol view as an on-demand popup | Same pattern as project tree: on-demand instead of persistent. Aider/trouble.nvim can pin it if Tyler decides he wants it more often than not. |
| Right-click → Refactor submenu | Discoverability of "what can I do to this symbol right now" | Code-action popup (see §1d) triggered by a single keybind, with which-key.nvim showing available leader-key groups on half-second hesitation | which-key.nvim specifically closes the *discoverability* gap that keyboard-only interfaces otherwise lose vs. a hoverable/clickable menu — this is probably the single highest-leverage discoverability plugin for an IntelliJ transplant and should be in scope regardless of the vimscript-vs-Lua outcome (a Lua plugin, but usable from an otherwise-vimscript config). |

**The general translation rule surfaced by research**: Neovim-native configs don't try to make information *permanently visible* the way IntelliJ does; they make it *one keypress away and fast to dismiss*. The UX bet is that a fluent keyboard user round-trips faster than a mouse click into a sidebar, but this bet only pays off once the keybinds are internalized — which makes discoverability tooling (which-key.nvim) and keymap consistency (see §3) directly load-bearing for how fast Tyler stops missing the IntelliJ panels.

---

## 3. Keymap ergonomics: leader-key conventions and organization

### Community convention (2026 state)
Space-as-leader is now the dominant default across LazyVim, AstroNvim, NvChad, and kickstart.nvim — not a stylistic choice unique to one distro. This matters directly for Tyler's config: the *de facto* effective leader in the current setup (space, per §0) already matches the modern convention, even though it arrived there by accident/override rather than deliberate choice.

### Common group-prefix convention under `<leader>`
Across the surveyed distros, the pattern is a mnemonic first-letter-of-category grouping, discoverable via which-key.nvim popups:

| Prefix | Category | Typical contents |
|---|---|---|
| `<leader>c` | Code | code actions, rename, format, diagnostics-related code ops |
| `<leader>d` | Debug (DAP) | toggle breakpoint, continue, step over/into/out, toggle DAP UI |
| `<leader>g` | Git | status/hunk stage/blame/diff (gitsigns + git UI) |
| `<leader>f` or `<leader><leader>`/`<leader>space` | Find (fuzzy) | find files, live grep, buffers, recent files |
| `<leader>s` | Search | symbols, workspace search (sometimes merged with `f`) |
| `<leader>x` | Diagnostics/trouble | project-wide diagnostics list, quickfix |
| `<leader>w` | Window | split/nav (already used in current config for vim-choosewin — a collision to resolve) |

### Direct collision risk against the current ~50-plugin mapping surface
Concrete overlaps found by reading `.vimrc.plug` directly that the planning phase must resolve, not just "watch for":
- `<leader>w` is already bound to `vim-choosewin` (line 401) — collides with the conventional "window" group prefix.
- `<leader>f` is already bound twice inconsistently: line 193 binds it to `:Format` (a custom command) while lines 283-284 bind it to `coc-format-selected` — these are two different bindings to the same key sequence already coexisting in the file (the second simply overwrites the first at source time), which is itself a pre-existing latent bug independent of the Lua-migration question.
- `<leader>a` is bound to `coc-codeaction-selected` (lines 296-297) and also to CocList diagnostics as `<space>a` (line 349) — since space *is* leader, `<leader>a` and `<space>a` are the literal same key sequence, meaning one of these two bindings silently loses to source order (last-wins), not both being live as the file's structure implies.
- `<leader>ac`, `<leader>z`, `<leader>rn`, `<leader>e`, `<leader>g` (fugitive Gstatus) are all single, non-grouped leader mappings from the coc/fugitive/goyo era that don't follow a category-prefix scheme at all — a which-key-style migration needs an explicit remap table, not an incremental add, precisely because the existing bindings are flat single-letters rather than nested groups.

**Recommendation for planning phase**: treat the leader-key layer as a full remap, not an additive one. Build an explicit before/after keybind table as a planning artifact (this is exactly the "keybinding-compat pass" the requirements doc already flags as a rabbit hole under fuzzy-finder consolidation — it should be scoped project-wide, not just for fuzzy-find, given the collisions found above already exist even before adding LSP/DAP/git-consolidation mappings on top).

---

## 4. Error/edge-case UX: graceful degradation vs. silent failure

This is the area where current tooling is weakest, and where Tyler's daily-driver experience will most concretely diverge from IntelliJ's "always just works because JetBrains bundles everything" model.

- **LSP server not installed/attached**: Neovim's native LSP client fails *silently* by default — if `:lsp enable` can't find a root directory match or the server binary isn't on `$PATH`, the client simply never attaches, with no user-facing error unless you run `:checkhealth vim.lsp` or notice the absence of diagnostics/gd working. This is the opposite of IntelliJ, which shows an explicit "Language server not configured" banner. **Mitigation pattern**: mason.nvim + mason-lspconfig's `ensure_installed` + `automatic_installation = true` closes this gap almost entirely by making "not installed" a transient one-time install-on-first-open event rather than a standing silent gap — this should be treated as close to mandatory for the plan, not optional polish, given the requirement that LSP features "work without falling back to IntelliJ" for 4 languages.
- **DAP adapter not configured for current filetype**: no evidence of graceful native handling — attempting to start a debug session with no adapter registered for the filetype typically errors out at the point of invocation (undefined adapter key) rather than degrading gracefully. mason-nvim-dap's `ensure_installed` covers the *installation* gap the same way mason-lspconfig does for LSP, but doesn't cover the *"no launch.json-equivalent config exists for this project"* gap — nvim-dap requires either a `.vscode/launch.json`-compatible config or a Lua-defined `dap.configurations.<filetype>` table per project/filetype. Given the plan's own flagged DAP fragility risk, the planning phase should budget explicit fallback UX: a friendly error via `vim.notify` when no configuration exists for the current filetype, rather than a raw Lua traceback, and sane default configs shipped for Go/Python at minimum (the two priority languages) so the "just works" bar is met without per-project setup on day one.
- **Treesitter parser missing for filetype**: confirmed via search — this is a known, currently-unresolved rough edge in the ecosystem itself, not something Tyler's config choices can fully fix. Failure is silent (no highlighting, no thrown error) rather than a clear "install this parser" prompt, and `nvim-treesitter` maintainers acknowledge this as a gap. **Mitigation available today**: `:checkhealth nvim-treesitter` surfaces missing parsers if run manually, and `auto_install = true` (evaluated per-buffer on filetype detection) closes most of the day-to-day gap the same way mason's `automatic_installation` does for LSP — but there's no equivalent to a friendly in-buffer notice today. This should be flagged in the plan as an accepted residual gap (fall back to regular vim syntax highlighting, which is what happens automatically when treesitter highlighting isn't active) rather than something to build custom tooling around.

**Overall pattern**: the fix for all three is the same shape — **auto-install on first use (mason.nvim family) turns "missing X" from a standing silent failure into a one-time, visible, self-healing event.** This is the single highest-leverage cross-cutting UX investment across LSP/DAP/treesitter and should be called out as a planning-phase must-have rather than assumed to fall out of "just install the plugins."

---

## 5. Job-to-be-done and reprioritization

**Functional job**: get accurate code intelligence (jump-to-def, find-refs, rename, safe refactor) and a working debugger for Go/Python without opening a second application.

**Emotional job**: confidence editing unfamiliar code without a safety net anxiety ("did that rename actually catch every reference, or did it silently miss one because coc/ale's rough edges under-deliver on the promise"), and a feeling of *control/speed* — not fighting the editor's own friction (three fuzzy-finders with unclear precedence is itself an anxiety/control problem independent of language tooling).

**Social job**: not needing to justify the tool choice to himself or anyone else — "this just works" credibility, i.e., never having a moment mid-task where the honest answer to "why are you switching to IntelliJ" is "because Neovim doesn't do X reliably yet."

### Does this reprioritize the 4 capability areas?

Yes, in a specific way — **the emotional/social jobs are most threatened by the areas with the worst error/edge-case UX today, not necessarily the areas with the flashiest missing feature.**

1. **Code intelligence & refactoring — nail first, non-negotiable.** This is the area most directly tied to the "did the tool actually work correctly" trust question (a bad rename that misses a reference is worse than no rename, because it fails silently and shows up later as a bug). Native LSP + mason auto-install is the highest-leverage, lowest-risk win here given nvim-lspconfig/native LSP maturity, and it's the prerequisite the plan's own risk section already treats as load-bearing (coc.nvim and native LSP can't cleanly coexist).
2. **Debugging — nail second, but the fragility risk (already flagged in requirements) means "good enough" should mean Go + Python solid, Rust/TS-JS acceptable-if-rough.** The DAP interaction model itself is low-mismatch (closest to IntelliJ of the four), so once an adapter is wired up correctly the UX payoff is immediate and high-confidence — but adapter setup is genuinely the most fragile plumbing of the four areas, so this is where "good enough" scoping (per the Appetite section) should flex, not where interaction-model polish should be spent.
3. **Navigation/fuzzy search — can be "good enough" faster than the other three.** Telescope or fzf-lua alone (consolidating from 3 finders to 1) delivers most of the emotional win (reduced control-anxiety from tool ambiguity) with comparatively low implementation risk and a well-worn interaction pattern. This is the one area where the *existing* redundancy itself, not a capability gap, is the primary UX problem — so the fix is mostly subtractive (delete two finders) rather than additive, which is cheap relative to the other three areas.
4. **Git integration — lowest urgency for "IDE-like" credibility, but real day-to-day friction reduction available cheaply.** IntelliJ's git tool window isn't usually the reason someone reaches for a full IDE over an editor; it's a nice-to-have consolidation (fugitive/Merginal/vimagit → gitsigns + diffview + optionally neogit) that reduces daily friction but isn't the thing standing between Tyler and closing the IntelliJ gap. Reasonable to sequence last and treat generously as "good enough" if time gets tight against the 3-6 week appetite.

**Bottom line for planning**: prioritize (1) code intelligence with mason-backed auto-install as the trust-building foundation, (2) DAP for Go/Python specifically rather than all four languages evenly, (3) fuzzy-finder consolidation as a cheap, high-relief-value early win, and (4) git UI consolidation as valuable but appropriately last if the appetite gets squeezed — consistent with the order already implied by the requirements doc's own DAP/coc risk flags, but now with an explicit UX rationale: the areas that most threaten Tyler's *confidence* in the tool (silent failure risk) should be hardened before the areas that are merely *redundant* (fuzzy-finders, git plugins).

---

## Sources

- [AstroNvim Mappings](https://docs.astronvim.com/mappings/)
- [NvChad Mappings](https://nvchad.com/docs/config/mappings/)
- [LazyVim Keymaps](https://www.lazyvim.org/configuration/keymaps)
- [What is the preferred way to setup keymaps? — LazyVim/LazyVim Discussion #3025](https://github.com/LazyVim/LazyVim/discussions/3025)
- [Leader keys and mapping keyboard sequences — DEV Community](https://dev.to/stroiman/leader-keys-and-mapping-keyboard-sequences-3ehm)
- [nvim-dap-ui — GitHub](https://github.com/rcarriga/nvim-dap-ui)
- [nvim-dap-view: A Single-Window Debug UI for Neovim](https://zenn.dev/glmlm/articles/neovim-dap-view-20260213?locale=en)
- [nvim-dap-view — GitHub](https://github.com/igorlfs/nvim-dap-view)
- [Debugging in Neovim with nvim-dap — John Tobin](https://www.johntobin.ie/blog/debugging_in_neovim_with_nvim-dap/)
- [A Guide to Debugging Applications in Neovim — Tamerlan](https://tamerlan.dev/a-guide-to-debugging-applications-in-neovim/)
- [telescope.nvim — GitHub](https://github.com/nvim-telescope/telescope.nvim)
- [LazyVim 14, some new and breaking features — Lorenzo Bettini](https://www.lorenzobettini.it/2024/12/lazyvim-14-some-new-and-breaking-features/)
- [gitsigns.nvim — GitHub](https://github.com/lewis6991/gitsigns.nvim)
- [My Neovim Git Setup: Neogit, Gitsigns, and Diffview — Michael Bao](https://medium.com/unixification/my-neovim-git-setup-ba918d261cb6)
- [How to stage individual Git hunks without leaving Neovim using gitsigns.nvim — VimTricks](https://vimtricks.wiki/posts/gitsigns-stage-hunk)
- [Working with Git inside Vim — WhyNotHugo](https://whynothugo.nl/journal/2026/01/03/working-with-git-inside-vim/)
- [Neovim git integration — Duy NG](https://tduyng.com/blog/neovim-git-tools/)
- [nvim-lspconfig — GitHub](https://github.com/neovim/nvim-lspconfig)
- [Neovim LSP docs](https://neovim.io/doc/user/lsp/)
- [mason.nvim — GitHub](https://github.com/mason-org/mason.nvim)
- [Automating LSP Installation Without mason-lspconfig.nvim](https://zenn.dev/glmlm/articles/neovim-mason-lspconfig-20250218?locale=en)
- [Debugging in Neovim — harrisoncramer.me](https://harrisoncramer.me/debugging-in-neovim/)
- [Unable to install parsers — nvim-treesitter Issue #5570](https://github.com/nvim-treesitter/nvim-treesitter/issues/5570)
- [Failure to install parsers does not throw error — nvim-treesitter Issue #7906](https://github.com/nvim-treesitter/nvim-treesitter/issues/7906)
- [neo-tree.nvim — GitHub](https://github.com/nvim-neo-tree/neo-tree.nvim)
- [Neovim file explorers — pawelgrzybek.com](https://pawelgrzybek.com/neovim-file-explorers/)
- [Code Action — lspsaga (nvimdev)](https://nvimdev.github.io/lspsaga/codeaction/)
- [tiny-code-action.nvim — GitHub](https://github.com/rachartier/tiny-code-action.nvim)
- [nvim-code-action-menu — GitHub](https://github.com/weilbith/nvim-code-action-menu)
