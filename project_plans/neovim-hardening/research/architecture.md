# Architecture Research: Neovim Hardening

Agent 3 (Architecture) — SDD Phase 2 research for `neovim-hardening`.

## 0. Current-state facts (grounding)

- `.vimrc` (226 lines, vimscript): options, mappings, ~20 filetype autocmds, sources
  `~/.vimrc.dein` if present, then sources `~/.vim/local/*` for machine-local overrides.
  Has scattered `has('nvim')` branches (terminal mapping, `inccommand`) — it is a genuinely
  shared vim+nvim file today, not just nominally.
- `.vimrc.dein` (565 lines, vimscript): despite the filename, bootstraps **lazy.nvim** (not
  dein) inside two `lua << EOF ... EOF` heredocs, declares ~50 plugins in one `lazy.setup({...})`
  table (lines 29-179), then has ~380 lines of plugin-specific vimscript config *below* the
  plugin list (lines 184-565) — e.g. coc.nvim's own config block is ~170 lines (190-364),
  physically 150-300 lines away from its one-line plugin declaration at line 36. This
  spec/config separation is the file's core maintainability defect, not the plugin count itself.
- `.config/nvim/` in the repo currently contains **only** `coc-settings.json` — no `init.lua`,
  no `lua/` tree exists yet. This is a from-scratch layout decision, not a refactor of an
  existing Lua tree.
- Dead files confirmed harmless to delete: `.vimrc.local` and `.vimrc.bundles.local` are
  pre-dein/NeoBundle-era vimscript (YouCompleteMe, neocomplete, NeoBundle plugin declarations);
  neither is `source`d anywhere in `.vimrc` or `.vimrc.dein`. `.vimrc.plug` (not fully read, but
  per requirements.md is vim-plug era) is likewise unsourced. Safe to delete outright.
- `.ideavimrc` is 2 lines: `set surround` / `set commentary`. Trivial; not a redesign target.
- **cfgcaddy semantics** (confirmed via the tool's own README, `tstapler/cfgcaddy`): by default,
  cfgcaddy mirrors every file in the dotfiles repo to the same relative path under
  `linker_dest` ($HOME) *unless* it matches an `ignore:` glob. The explicit `links:` block in
  `.cfgcaddy.yml` is only needed for **exceptions** — renames, multi-destination fan-out, or
  OS-conditional paths. This resolves an apparent discrepancy: `.vimrc` has no explicit
  `links:` entry pointing at `~/.vimrc` — it doesn't need one, because default mirroring
  already produces `~/.vimrc`. The *explicit* entries are the two extra renames:
  `.vimrc → .config/nvim/init.vim` (Linux/Darwin) and the Windows equivalent. So the "shared
  vimscript file" constraint in requirements.md is real and currently active, not vestigial.
- Directory-as-one-unit linking already has precedent in this exact `.cfgcaddy.yml`:
  `.config/nixpkgs`, `.mixxx/controllers`, `.claude/skills`, `.claude/agents`, `.claude/commands`
  are all linked as bare directory `src:` entries (or via default mirroring), not enumerated
  file-by-file. Splitting nvim config into a `lua/` tree is not a new pattern for this tool.
- Side-finding: `.cfgcaddy.yml`'s `.vimsnippets` multi-dest entry links to
  `.vim/bundle/.dein/stapler-snips` — an actual dein.vim path, distinct from the
  lazy.nvim-via-`.vimrc.dein` setup that's actually in use. This is itself a small piece of
  migration debt (a previous dein→lazy.nvim migration that didn't clean up cfgcaddy). Worth
  pruning in the same pass as the three dead vimscript files, once confirmed nothing still
  reads that path.

## 1. File/module layout pattern

**Community standard for 2025-2026** (kickstart.nvim, LazyVim, and the broad devlog/blog
consensus converge on this): `init.lua` as a thin bootstrap, plus a `lua/<namespace>/` tree:

```
.config/nvim/
  init.lua                      -- lazy.nvim bootstrap + require("tstapler")
  lua/tstapler/
    init.lua                    -- requires options/keymaps/autocmds, then lazy.setup(...)
    options.lua                 -- vim.opt.* (ports .vimrc's Options block)
    keymaps.lua                 -- non-plugin-specific vim.keymap.set (ports .vimrc's Mappings block)
    autocmds.lua                -- filetype settings (ports .vimrc's ~20 au FileType blocks)
    plugins/
      lsp.lua                   -- nvim-lspconfig + mason + mason-lspconfig
      dap.lua                   -- nvim-dap + nvim-dap-go/python + dap-ui + mason-nvim-dap
      completion.lua            -- nvim-cmp/blink.cmp + snippet engine
      treesitter.lua
      finder.lua                -- the single consolidated fuzzy-finder (telescope or fzf-lua)
      git.lua                   -- the single consolidated git UI
      wiki.lua                  -- vimwiki + vim-zettel (vimscript plugins, config via vim.g)
      ui.lua                    -- statusline, colorscheme
      editing.lua               -- surround, comment, autopairs, etc.
```

`lazy.setup({ { import = "tstapler.plugins" }, ... })` auto-loads every file under
`plugins/` — adding a new plugin file requires zero edits to `init.lua`.

**Why this matters at ~25-30-plugin scale (post-pruning)**: the current `.vimrc.dein`
already exhibits the failure mode a single-file Lua config would just re-encode in a new
syntax — plugin *declaration* and plugin *configuration* live hundreds of lines apart. A
module-per-concern layout fixes this by construction: a plugin's `lazy.nvim` spec table and
its `opts`/`config` function live in the same file, often the same table. Swapping coc.nvim
for native LSP becomes "delete/rewrite `plugins/lsp.lua`," not a scroll-and-grep exercise
across a 565-line file. This is the single biggest maintainability lever available in this
migration, independent of the vimscript-vs-Lua decision (see §3) — even a vimscript-retained
option benefits from *some* form of this separation, though vimscript lacks `require()` and
can't get it as cleanly.

Do **not** go granular to one-file-per-plugin (50+ tiny files) — group by functional concern
instead. One-per-plugin adds navigation overhead without a corresponding benefit once plugins
are already grouped by concern; reserve per-file granularity for plugins complex enough to
need it on their own (LSP and DAP will likely want to stay split further internally, e.g.
`lsp/servers.lua`, `dap/go.lua`, `dap/python.lua`, if they grow to warrant it — cross that
bridge only if `plugins/lsp.lua` or `plugins/dap.lua` actually gets unwieldy).

## 2. cfgcaddy integration

**Recommendation: link `.config/nvim` as one directory unit, relying on cfgcaddy's default
mirror behavior — add no new explicit `links:` entry.** None of `.config/nvim/init.lua` or
`.config/nvim/lua/**` match any existing `ignore:` pattern (no `*.lua` exclusion exists), so
default mirroring already produces the correct `~/.config/nvim/init.lua` and
`~/.config/nvim/lua/tstapler/*.lua` paths with zero new config. This is not a novel ask of the
tool — it already treats `.config/nixpkgs`, `.claude/skills`, `.claude/agents`, etc. as
directory-level units in this same `.cfgcaddy.yml`.

**Required cfgcaddy changes** (this part is not optional, it's a conflict-avoidance fix):
delete the two existing explicit rename entries that point `.vimrc` at nvim's init path —
```yaml
  - src: .vimrc
    dest: .config/nvim/init.vim
    os: "Linux Darwin"
  ...
  - src: .vimrc
    dest: "%userprofile%\\AppData\\Local\\nvim\\init.vim"
    os: "Windows"
```
Once the new tree provides its own `init.lua`, leaving these in place would create a stale
`~/.config/nvim/init.vim` symlink to `.vimrc` sitting *alongside* the new `init.lua` —
Neovim's own startup rule is that if both `init.vim` and `init.lua` exist in the config
directory it treats this as an error condition (or at best undefined precedence depending on
version). This must be removed in the same change that adds the new tree, not as a followup.

Splitting into multiple Lua files does **not** complicate cfgcaddy's per-file link model,
because cfgcaddy's model is already directory-capable, not strictly per-file — the model this
migration should worry about is the opposite: whether cfgcaddy's directory linking makes ONE
symlink for the whole directory (new files added later "just work" without rerunning the
installer) or walks the tree at install-time and links each file individually (new files
require rerunning `bootstrap-dotfiles.sh`/cfgcaddy before nvim can see them). The README
fetch did not settle this definitively. **Recommend a cheap empirical check before relying on
it**: touch a new file inside an existing directory-linked path already in
`.cfgcaddy.yml` (e.g. `.claude/skills/`) and check whether it appears under `~/.claude/skills/`
without rerunning cfgcaddy. If it's file-level (not whole-directory), add "rerun cfgcaddy
install" as an explicit step whenever a new `plugins/*.lua` file is added during this
migration — cheap to document, expensive to debug blind (a plugin file that silently isn't
even present on disk in `$HOME` looks identical to a lazy-loading bug, see §4).

Keep the existing standalone `.config/nvim/coc-settings.json` link entry only for as long as
coc.nvim survives in any form (see §3); delete it in the same commit that removes coc.nvim
entirely.

## 3. Migration strategy: vimscript vs. Lua — architectural options

**Option A — Shared vimscript core + Lua-only IDE layer, `has('nvim')`-gated.**
Keep `.vimrc` mostly as-is (options/mappings/autocmds stay vimscript, still shared with plain
vim), keep the `lua << EOF ... EOF` heredoc bootstrap for lazy.nvim, swap coc.nvim+ale for
nvim-lspconfig+mason+nvim-dap *inside* the existing heredoc pattern, gated by `has('nvim')`.
- *Migration/integration complexity*: low for the file-layout question (no restructuring), but
  this does **not** reduce the actual hardest work — the coc→native-LSP swap (requirements.md's
  named rabbit hole) is exactly as large and exactly as risky whether it lives in a heredoc or
  a `lua/` tree. It only avoids solving the maintainability problem in §1.
- *Risk*: heredoc-embedded Lua has no module system (no `require()`, no per-file lazy-loading
  of your *own* config code), poor tooling support (a single giant `lua << EOF` block doesn't
  get its own LSP/treesitter treatment as cleanly as real `.lua` files), and doesn't scale to
  the amount of new LSP/DAP/treesitter config this migration adds. This option papers over the
  current file's core defect rather than fixing it — it's the "band-aid," not a real option
  for a migration explicitly scoped to be "large" (3-6 weeks).

**Option B — Full Lua rewrite; vim gets a frozen legacy snapshot.**
Build the `lua/tstapler/` tree from scratch for Neovim only. Leave `.vimrc` exactly as it is
today (or trim only the neovim-specific stray comments), so plain `vim` keeps getting exactly
today's experience via cfgcaddy's default mirror to `~/.vimrc`, untouched by this migration.
Neovim stops reading `.vimrc` entirely — remove the two `.vimrc → init.vim` rename entries
from `.cfgcaddy.yml` (§2) and let `init.lua`/`lua/**` mirror independently.
- *Migration/integration complexity*: medium. Two config surfaces to reason about
  permanently (vimscript for bare vim, Lua for neovim), but they're now fully decoupled —
  changing one can never regress the other. Wiki plugins (vim-zettel/vimwiki, see §5) need to
  be re-declared in the new Lua tree, but this is a mechanical, low-risk port (§5).
- *Risk*: low, by design — this is the risk-control option. `master` branch stays fully
  functional the entire time (per requirements.md's Risk Control section), and if anything goes
  wrong, "the old file still works for vim" is not even relevant to nvim's cutover risk since
  they're already fully split.

**Option C — Full Lua rewrite; drop vim support entirely.**
Same Lua tree as Option B, but delete `.vimrc` (or reduce it to a two-line "unsupported, see
nvim" stub) rather than freezing it. One canonical config, one language, forever.
- *Migration/integration complexity*: lowest long-term (no permanent dual-language
  maintenance), but requires confirming plain `vim` (not `nvim`) is genuinely unused in
  Tyler's daily workflow before deleting its config — this migration's own constraints assume
  nvim 0.11.6 as the baseline runtime and never call out a plain-vim use case as a
  requirement or success metric.
- *Risk*: low technically, but carries a small "did I just break something I forgot I use"
  risk if plain `vim` turns out to be invoked anywhere (bare SSH sessions to boxes without
  nvim, `sudoedit`, `git commit` if `$EDITOR`/`core.editor` resolves to `vim` rather than
  `nvim` in some context, etc.).

**Recommendation: Option C as the target, with an explicit, cheap pre-check before
committing to it — fall back to Option B if the check fails.**

Decision criteria (not just preference):
1. **Usage check** — grep shell history / `git config --get core.editor` /
   `echo $EDITOR $VISUAL` across the machines this repo is deployed to for evidence of bare
   `vim` invocation in the last few months. If it's genuinely zero (most likely, given `nvim`
   is the pinned baseline and there's no plain-vim item anywhere in requirements.md's scope),
   take Option C — delete `.vimrc`'s vim-only branches and stop the dual-maintenance burden
   for good.
2. **If bare vim shows up anywhere** (even as a rare SSH-without-nvim fallback), take Option B
   instead — the cost of freezing today's `.vimrc` as a legacy file is near-zero (it's not
   touched again), and it removes the small residual risk of Option C for a case that does
   exist.
3. **Option A is never the right call for this migration** given the explicit "Large (3-6
   weeks)" appetite and the requirement that the research phase produce a *reasoned*
   recommendation rather than defer the hard part — Option A defers exactly the part
   requirements.md flags as the load-bearing risk (§6) without buying any real safety in
   exchange.

This recommendation should be validated/confirmed in Phase 3 (planning) with a two-minute
usage check rather than re-litigated as an open research question — the check is cheap and
turns a preference into a fact.

## 4. Migration-specific failure modes

**A. coc.nvim + native LSP both registered for the same filetype.**
*What breaks*: duplicate diagnostics (two sets of signs/virtualtext for the same line),
duplicate completion sources fighting over `<Tab>`/`<CR>`, and silently "wrong" `gd`/`gr`
behavior (see D). This is requirements.md's named Feasibility Risk, and it is concrete, not
theoretical (see §6 for why they can't coexist even in principle).
*Detection*: `:LspInfo` (or `:checkhealth vim.lsp`) shows a client attached for the buffer
**and** `:CocInfo` / `call coc#rpc#ready()` is true for the same buffer/filetype.
*Mitigation*: treat this as an atomic, per-filetype cutover, never a lingering hybrid — the
same commit that adds `gopls` to `mason-lspconfig`'s `ensure_installed` must also remove
`coc-go` from `g:coc_global_extensions` (or, if doing it all at once, remove `coc.nvim`
entirely from the plugin spec). Never leave both installed *and* enabled for the same
filetype past a single work session.

**B. Lazy-loading misconfiguration — plugin silently never loads.**
*What breaks*: a feature is just... absent, with no error, because the `event`/`ft`/`cmd`
trigger in the lazy.nvim spec never fires for the way the plugin is actually used.
*Detection*: `:Lazy` UI shows the plugin's load state; `:Lazy profile` shows which load
events actually fired; a manual smoke-test checklist per plugin (open a file of the relevant
type, run one command the plugin provides, confirm it's not `E492: Not an editor command`)
run before considering a plugin "migrated."
*Mitigation*: for anything safety-critical during the transition (LSP, DAP, treesitter),
prefer broad triggers (`lazy = false`, `VeryLazy`, `BufReadPre`) over narrow, guessed
triggers, and only tighten to precise `ft`/`cmd`/`keys` triggers after the smoke test
confirms it works — optimize load time last, correctness first.

**C. Treesitter parser/query version mismatches.**
*What breaks*: broken syntax highlighting/folding (folding matters here — `Konfekt/FastFold`
is already in the current plugin list) or fatal Lua errors on buffer open, when a parser
grammar's ABI drifts from what the installed `nvim-treesitter` revision or Neovim 0.11.6's
bundled treesitter runtime expects.
*Detection*: `:checkhealth nvim-treesitter`; error text mentioning parser/query
incompatibility on file open.
*Mitigation*: pin `nvim-treesitter` via lazy.nvim's lockfile (`lazy-lock.json`, committed to
the repo) rather than floating `main`; treat `:TSUpdate` as a deliberate, reviewed action tied
to a config change, not something that runs unattended.

**D. Keymap collisions between old and new plugin sets during transition.**
*What breaks*: e.g. `vim-ctrlspace`'s `<C-Space>` fighting a new finder's binding, or — the
sharpest version of this — coc's `nmap gd <Plug>(coc-definition)` and a new
`vim.keymap.set('n', 'gd', vim.lsp.buf.definition, ...)` both trying to own `gd`; whichever
runs **last** during config load silently wins, with no error, and it *looks* like a bug in
the new plugin rather than a stale binding from the old one.
*Detection*: `:verbose nmap gd` (repeat for every keymap that matters: `gr`, `gy`, `gi`,
`K`, `<leader>rn`, `<leader>f`, etc.) shows exactly which script/line last set the mapping —
run this for every keymap the old and new systems both touch before calling a migration step
"done."
*Mitigation*: delete the old plugin's keymap block in the **same commit** that adds the new
plugin's keymap block for that function — never let both exist simultaneously even
transiently within the branch's history. Ownership of a keybinding is 1:1 with whichever
plugin is currently active for that function, never dual-bound "just in case."

## 5. Personal wiki dependency: vim-zettel + vimwiki

Both are pure-vimscript plugins with no Lua rewrite and none needed. They are indifferent to
whether the surrounding config is vimscript or Lua — the only two things they need are (a) a
plugin-manager entry (lazy.nvim already manages them fine either way — the current entries are
literally `'tstapler/vimwiki'` (Tyler's own fork) and `'michal-h21/vim-zettel'`, unchanged in a
Lua tree) and (b) their `g:` variables set before/at load. Today those are set in vimscript
(`.vimrc.dein` lines 368-374: `g:zettel_format`, `g:vimwiki_list` pointing at
`~/personal-wiki/logseq/pages`). In a Lua config this is a 1:1 mechanical port —
`vim.g.zettel_format = "..."` / `vim.g.vimwiki_list = { {...} }` — either inline in
`lua/tstapler/plugins/wiki.lua` or in that spec's `init = function() ... end`. Zero semantic
risk, zero compat shim required.

The one adjacent risk (not a Lua-vs-vimscript issue) is the `.vimsnippets` cfgcaddy multi-dest
entry pointing at a dein-specific path (`.vim/bundle/.dein/stapler-snips`, see §0) — confirm
nothing in the wiki/snippets workflow actually depends on that stale path before pruning it.

## 6. LSP data flow: native (nvim-lspconfig/mason) vs. coc.nvim — making the coexistence risk concrete

**Native flow:**
1. `mason.nvim` installs/manages LSP server **binaries** (`gopls`, `pyright`/`basedpyright`,
   `rust-analyzer`, `vtsls`/`tsserver`) into `~/.local/share/nvim/mason/bin`, independent of
   any system package manager.
2. `mason-lspconfig.nvim` bridges mason's binary names to lspconfig's server names and, on
   Neovim 0.11+, can call the native `vim.lsp.enable({...})` API so servers auto-start on a
   matching filetype — a declarative shift away from the older per-server
   `require('lspconfig').gopls.setup{}` calls.
3. On attach, an `LspAttach` autocmd wires keymaps **once, globally**
   (`vim.lsp.buf.definition`, `.references`, `.rename`, `.code_action`, etc.) rather than
   duplicating keymap logic per server.
4. Diagnostics are native: `vim.diagnostic.config()` controls signs/virtualtext/underline
   uniformly across every attached server, via Neovim's own `vim.diagnostic` API.
5. Completion is a *separate* concern layered on top (nvim-cmp/blink.cmp), wired via
   `capabilities` passed into the server config — easy to forget as a step (server attaches
   fine, hover/gd work, but completion silently stays basic because capabilities were never
   advertised).

**coc.nvim's current flow (fundamentally different plumbing, not just older syntax):**
1. coc.nvim is a single Node.js host process. "Extensions" (`coc-go`, `coc-pyright`,
   `coc-rust-analyzer`, `coc-tsserver`, etc. — the ~18 entries in `g:coc_global_extensions`)
   are installed and managed **by coc itself** (`:CocInstall`, stored under
   `~/.config/coc/extensions`) — a closed package ecosystem parallel to, and
   non-interoperable with, mason/lspconfig.
2. Those extensions wrap/embed the actual language servers and talk to coc's Node process
   over its own internal RPC — diagnostics, completion, go-to-def, and rename all flow through
   coc's own vimscript/Node plumbing (`CocAction`, `coc#pum#*`, `<Plug>(coc-definition)`, all
   visible throughout `.vimrc.dein` lines 190-364), a **completely separate code path** from
   `vim.lsp.buf.*` / `vim.diagnostic.*` — not two implementations of the same API, two
   unrelated systems that happen to solve the same problem.
3. **This is exactly why coexistence is dangerous, concretely**: if `gopls` is registered
   both as coc's `coc-go` extension *and* as a native mason/lspconfig server for the `go`
   filetype, two independent LSP client processes attach to the same buffer. Each pushes its
   own diagnostics (duplicate signs), each can claim the same keymap (`gd` bound to both
   `<Plug>(coc-definition)` and an `LspAttach`-wired `vim.lsp.buf.definition` — see §4D for
   which wins), and both try to drive the same completion popup (coc's `coc#pum#visible()`
   omnifunc-driven flow vs. nvim-cmp's LSP source) fighting over `<Tab>`/`<CR>`. There is no
   supported partial state — "half coc, half native LSP" for a single filetype is not a
   degraded-but-working mode, it's actively broken. This is why requirements.md calls the
   vimscript-vs-Lua decision "load-bearing for the whole plan": the cutover must be atomic —
   either whole-repo at once, or filetype-by-filetype with strict removal of the old
   extension the same commit the new server is added (§4A) — never a lingering hybrid.
