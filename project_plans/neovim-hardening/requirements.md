# Requirements: neovim-hardening

**Date**: 2026-07-15
**Type**: migration (existing project — dotfiles repo)
**Complexity**: 4 — high-stakes / cross-cutting

## Problem Statement
Tyler's Neovim config (`.vimrc` + `.vimrc.dein`, deployed via cfgcaddy to both `~/.vimrc` and `~/.config/nvim/init.vim`) has accumulated ~50 plugins over roughly a decade, including three overlapping fuzzy-finders (ctrlp.vim, vim-ctrlspace, fzf.vim), coc.nvim + ale for completion/linting instead of native LSP, and three dead/orphaned files (`.vimrc.local`, `.vimrc.bundles.local`, `.vimrc.plug`) left over from a NeoBundle/YouCompleteMe-era setup that aren't sourced anywhere. For code intelligence, debugging, navigation, and git workflows, Tyler still reaches for IntelliJ (with a minimal 2-line `.ideavimrc`) because Neovim's current setup doesn't confidently cover those needs.

## Baseline
Today: coc.nvim + ale provide LSP-like features for Go/Rust/Python/TS-JS with known rough edges; no integrated debugger (DAP) — falls back to print-statement debugging or switching to IntelliJ; three redundant fuzzy-finders with unclear which is "the" one in daily use; git workflow spread across vim-fugitive + Merginal + vimagit; three unsourced legacy files add confusion with no functional effect. IntelliJ remains the fallback for anything code-intelligence-heavy.

## Users / Consumers
Tyler Stapler only — personal daily-driver dev environment (dotfiles repo), used across Go, Rust, Python, and TypeScript/JavaScript projects.

## Success Metrics
- Zero unsourced/dead config files remain (down from 3: `.vimrc.local`, `.vimrc.bundles.local`, `.vimrc.plug`).
- No redundant plugins serving the same function (e.g. one fuzzy-finder, not three; one git UI plugin set, not three).
- For Go, Rust, Python, and TS/JS: go-to-definition, find references, rename, and at least one cross-file-safe refactor action all work without falling back to IntelliJ.
- A working DAP-based debugger (breakpoints, step-through, variable inspection) exists for at least Go and Python (the two most likely to need it), removing the "switch to IntelliJ to debug" habit.
- Startup time does not regress vs. the current config (measure with the already-installed `vim-startuptime` before and after).
- Tyler can go a full week of daily-driver use on the new config without reverting to the old one or to IntelliJ for a task the new config claims to cover.

## Appetite
Large (3–6 weeks)
*(Scope must fit the appetite. If it doesn't fit, cut scope — do not move the deadline.)*

## Constraints
- Solo effort, evenings/weekends pace implied by "3-6 weeks" for a personal tool — no hard deadline, but scope should be cut before the timeline slips.
- Must keep working through cfgcaddy's symlink deployment model (`.cfgcaddy.yml` currently maps `.vimrc` → both `~/.vimrc` and `~/.config/nvim/init.vim`); whatever replaces it must have a clear cfgcaddy mapping.
- Must run on nvim 0.11.6 (already installed) at minimum.

## Non-functional Requirements
- **Performance SLO**: Neovim startup time must not regress vs. current baseline (benchmark via `vim-startuptime`).
- **Scalability**: N/A — single-user local tool.
- **Security classification**: Internal/personal — no special handling needed beyond not vendoring untrusted plugin sources.
- **Data residency**: Not applicable.

## Scope
### In Scope
- Research phase must produce a reasoned recommendation on **vimscript-vs-Lua**: analyze whether a full Lua rewrite (lazy.nvim + nvim-lspconfig/native LSP + treesitter + telescope) is worth it, or whether staying vimscript-based and just swapping/pruning plugins captures most of the value with less migration risk. This is an open decision, not pre-decided.
- Auditing and pruning the full existing plugin list (~50 plugins across `.vimrc.dein`) for redundancy and staleness.
- Deleting or explicitly re-integrating the three orphaned/unsourced files (`.vimrc.local`, `.vimrc.bundles.local`, `.vimrc.plug`).
- Code intelligence & refactoring: reliable LSP-backed go-to-definition, find references, rename, and safe refactors for Go, Rust, Python, TypeScript/JavaScript.
- Debugging: DAP-based breakpoint/step-through debugging, prioritized for Go and Python.
- Project/file navigation & fuzzy search: consolidate to one fuzzy-finder covering files, buffers, symbols, and live grep.
- Git integration: consolidated git status/diff/blame/merge-conflict UI (audit vim-fugitive/Merginal/vimagit overlap).
- Minor cleanup pass on `.ideavimrc` if there's easy shared value (e.g. consistent keybindings with the new Neovim config) — small effort, not a redesign of the IntelliJ/IdeaVim setup.
- Updating `.cfgcaddy.yml` link mappings if the config file layout changes (e.g. splitting into `init.lua` + `lua/` modules).

### Out of Scope
- Redesigning or expanding the IntelliJ/IdeaVim setup beyond a minor `.ideavimrc` cleanup pass.
- Non-daily-driver languages/tooling not called out above (Java, Ruby, Dart, Elixir, etc. currently referenced in coc extensions/plugins) — audit for removal if unused, but no new investment in them.
- Windows support (`.cfgcaddy.yml` has a Windows nvim mapping) — out of scope unless it falls out naturally from the Linux/macOS work.
- Zettelkasten/wiki plugins (vimwiki, vim-zettel) and distraction-free writing plugins (goyo, limelight, zenroom2) — orthogonal to the "IDE-like" goal; only touch if clearly dead weight, not to improve.

## Rabbit Holes
- **vimscript-vs-Lua decision**: could balloon if not timeboxed — research phase should produce a clear recommendation with a decision criteria (migration effort vs. capability gap), not an open-ended exploration.
- **DAP adapter setup per language** is often the most fragile part of a "modern" Neovim config (adapter installation, path discovery, per-project launch configs) — budget real time here, don't assume it's a quick plugin install.
- **coc.nvim → native LSP migration** (if the Lua rewrite is chosen) touches snippets, completion, formatting, and diagnostics simultaneously — these are easy to half-migrate and end up with a worse hybrid than the original.
- **Fuzzy-finder consolidation** touches muscle-memory keybindings across ctrlp/ctrlspace/fzf — likely to cause friction regardless of which one wins; plan for a keybinding-compat pass.
- **vim-zettel / vimwiki** integration with the personal wiki (`~/personal-wiki/logseq/pages`) is a live dependency for note-taking — do not break it while pruning, even though it's out of scope for improvement.

## Alternatives Considered
- Keep vimscript config as-is, only delete the 3 dead files and dedupe fuzzy-finders/git plugins — rejected as insufficient on its own; deferred to research as one candidate outcome of the vimscript-vs-Lua analysis rather than ruled out.
- Full switch to a pre-built Neovim distribution (LazyVim, NvChad, AstroNvim) — worth evaluating in research as a build-vs-adopt option, but Tyler's config has enough personal customization (zettel workflow, custom filetype settings, personal snippets) that full adoption may not fit; research should weigh this explicitly.

## Feasibility Risks
- DAP adapter availability/quality varies significantly by language (Go's delve integration is generally solid; verify Python's debugpy and Rust's codelldb/lldb-vscode maturity before committing).
- coc.nvim and native LSP client cannot cleanly run side-by-side for the same language servers — the vimscript-vs-Lua decision is effectively load-bearing for the whole plan, not a cosmetic choice.
- Personal wiki workflow (vimwiki/vim-zettel) depends on plugins that may not have modern Lua equivalents with feature parity.
- No existing test/CI coverage for dotfiles config correctness beyond `install.sh`/shellcheck — validation will rely on manual smoke-testing per language, not automated tests.

## Observability Requirements
Not a service — no metrics/alerts pipeline. Substitute: startup time benchmark (before/after, via `vim-startuptime`) captured in the plan, plus a manual smoke-test checklist (LSP attach, DAP breakpoint hit, fuzzy-find, git status) run per daily-driver language before merging to master.

## Risk Control
Build the new config within this feature-branch worktree (`dotfiles-harden-neovim`), isolated via `NVIM_APPNAME=nvim-next` so its plugin/Mason state never touches master's `~/.config/nvim`/`~/.local/share/nvim`. The current coc.nvim-based config on `master` stays the daily driver for any language not yet migrated.

*(Revised during Phase 4 validation — see `implementation/pre-mortem.md` and `implementation/adversarial-review.md`.)* Rather than a single big-bang swap, cutover happens **progressively per language**: once a language's native LSP/DAP setup passes its Phase smoke test (via `nvn`), that language's *real* daily-driver work shifts to `nvn` immediately — it does not wait for the other languages to finish. This deliberately trades "two live configs coexisting for several weeks" for avoiding two bigger risks the all-or-nothing approach carried: (1) a mid-migration burnout or stall permanently freezing a half-finished coc+native hybrid with no clean revert, and (2) discovering a DAP/LSP problem on a real project only after that language's coc.nvim fallback has already been torn down. The final merge to `master` happens once all in-scope languages have been progressively cut over and the full config has survived one week of combined daily-driver use. Rollback at any point is per-language: switch that language's daily work back to plain `nvim`/master (coc.nvim stays installed and functional there until its own teardown task runs) — no repo-level revert needed mid-migration. Full rollback of the whole effort, if ever needed, is `git checkout master` (or simply not merging the branch).

## Open Questions
- Does the vimscript-vs-Lua research land on a clean recommendation, or is it close enough to need a spike/prototype before deciding? (Research phase should flag this rather than force a premature decision.)
- Which specific DAP adapters are mature enough today for Go/Python/Rust/TS-JS? (Research phase.)
- Is a pre-built distro (LazyVim etc.) a better base to fork from than a from-scratch config, given the personal customizations that must be preserved? (Research phase.)
- Final fuzzy-finder and git-UI plugin choices, once redundant options are compared. (Planning phase.)
