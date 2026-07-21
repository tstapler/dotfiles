# Research: Build vs. Buy — Neovim Config Base

**Question**: Should `neovim-hardening` build a config from scratch, adopt/fork a pre-built distribution, or take a hybrid approach?

**Two factors that rule options in/out, per the requirements doc**:
1. **cfgcaddy constraint** — whatever lives at `~/.config/nvim` must be plain files that `.cfgcaddy.yml` can symlink from the dotfiles repo (today: a single `.vimrc` symlinked to both `~/.vimrc` and `~/.config/nvim/init.vim`). Anything that *requires* `~/.config/nvim` to be its own independently-managed git clone conflicts with this model.
2. **Personal-customization load** — vimwiki + vim-zettel pointed at `~/personal-wiki/logseq/pages` (out of scope to improve, in scope to not break), custom per-filetype `tabstop`/`shiftwidth` settings (12+ filetypes in `.vimrc` today), personal snippets at `~/.vimsnippets` (synced via cfgcaddy to three destinations, including `.config/coc/ultisnips`), and a `,` leader key baked into a decade of muscle memory.

## Key finding that changes the calculus: distro architecture has converged

As of mid-2026, all three major distributions have **moved away from** "clone the distro's own repo into `~/.config/nvim`":

- **LazyVim**: the actual LazyVim logic is fetched by `lazy.nvim` as a plugin dependency (`{ "LazyVim/LazyVim", import = "lazyvim.plugins" }`). `~/.config/nvim` only holds a thin, user-owned starter (`init.lua`, `lua/config/*.lua`, `lua/plugins/*.lua`) copied from `LazyVim/starter`.
- **AstroNvim v4** (2024 rewrite): core logic lives in AstroCore/AstroUI/AstroLSP, imported the same way as any lazy.nvim plugin. `~/.config/nvim` holds a thin `AstroNvim/template` clone with `.git` deleted — meant to become the user's own files.
- **NvChad v2.5**: same move — "starter config" pattern, NvChad core imported as a plugin; `~/.config/nvim` holds `chadrc.lua` + user's own `lua/plugins/*.lua`.

**Implication**: the pre-research assumption in `requirements.md` ("a distro assumes it owns `~/.config/nvim` as its own git repo") is **no longer accurate for current versions** of any of the big three. The files that land at `~/.config/nvim` under all three are now small, plain, user-owned Lua files — exactly the kind of thing cfgcaddy already symlinks elsewhere (e.g. `.config/nixpkgs`, `.config/helm/starters`). The actual distro "brain" is fetched into `~/.local/share/nvim/lazy/`, which is a plugin data directory, not something cfgcaddy touches today for any plugin manager.

**One real remaining friction point**: `lazy.nvim` writes `lazy-lock.json` into `~/.config/nvim` on every `:Lazy update`, regardless of which of these options is chosen (distro or from-scratch, as long as lazy.nvim is the plugin manager). If that directory is symlinked into the tracked dotfiles repo, lockfile bumps become dotfiles diffs. This is minor and manageable (commit intentionally for reproducibility, or add to `.cfgcaddy.yml`'s `ignore` list) — not a blocker, but should be an explicit planning-phase decision either way.

**Caveat**: older tutorials/still-circulating instructions for NvChad (pre-v2.5) and AstroNvim (pre-v4) do say `git clone <distro> ~/.config/nvim` directly — that *older* model genuinely conflicts with cfgcaddy. Make sure any planning-phase adoption targets the current starter-based install path, not a stale guide.

---

## Option 1: Pre-built distributions (LazyVim / AstroNvim / NvChad)

### LazyVim
- **Maturity**: v16.0.0 shipped May 2026, repo updated June 2, 2026, active issues/discussions through July 2026. One community discussion in Feb 2026 questioned maintenance during a maintainer vacation; resolved with v15.x shipping shortly after. Net: actively maintained, occasional slow patches.
- **License**: Apache-2.0 (LazyVim repo).
- **Opinionated/customizable**: Highly opinionated defaults (leader = `<space>`, its own keymap scheme, UI chrome via bufferline/noice/etc.) but customization is a first-class, well-documented mechanism — `lua/plugins/*.lua` files merge/override specs, and an "extras" system toggles curated language/feature bundles on and off.
- **4 priority areas**: All four are first-class and well-documented. LSP via nvim-lspconfig + mason (`lang.go`, `lang.python`, `lang.rust`, `lang.typescript` extras). DAP via the `dap.core` extra (marked `recommended = true`) + per-language extras — Go gets `nvim-dap-go` wired to Delve via Mason automatically, Python gets `nvim-dap-python` wired to debugpy. Fuzzy-find via Telescope (or fzf-lua as a swappable extra). Git via gitsigns + a git extra (lazygit/neogit).
- **cfgcaddy fit**: Good, per the architecture finding above — thin starter template, plain files.
- **Personal-customization fit**: vimwiki/vim-zettel are ordinary vimscript plugins; lazy.nvim loads non-Lua plugins fine, just watch out for filetype-based lazy-loading — vimwiki has a documented history of lazy-loading incompatibilities (mis-detecting the active wiki) with lazy-loading plugin managers, so it should be set `lazy = false` or loaded eagerly rather than trusting `ft =` lazy-loading. Custom filetype tabstop/shiftwidth settings and personal snippets are just more files under `lua/config`/`after/ftplugin` — no conflict, but 100% additive work regardless of base.
- **Pros**: Most actively developed, best-documented DAP story of the three, largest "extras" catalog directly mapped to the 4 priority areas, biggest community (so answers exist for edge cases).
- **Cons**: Adopting it swaps the *current* problem (an unaudited ~50-plugin surface) for a *new* large plugin surface — LazyVim's default install pulls in many UI/QoL plugins beyond the 4 priority areas (bufferline, noice, dashboard, which-key, etc.). That cuts against the stated Success Metric of "no redundant plugins serving the same function" and a deliberately audited, minimal config — the distro reintroduces sprawl at a different level of abstraction. Every default (leader key, keymaps, UI) that doesn't match Tyler's decade of `,`-leader muscle memory has to be actively found and overridden, which is a review burden in itself.
- **Verdict**: **Viable**, not Recommended. Technically compatible with cfgcaddy (contrary to the pre-research assumption) and has the strongest DAP/LSP/extras story, but its size and opinionation work against the project's explicit "audit and prune for redundancy" goal and its "make it Tyler's" personalization requirement.

### AstroNvim v4
- **Maturity**: v4 (2024) was a full architectural rewrite around AstroCore/AstroUI/AstroLSP; actively maintained into 2026, considered one of the most polished distros available.
- **License**: MIT.
- **Opinionated/customizable**: Strong emphasis on modularity; the `astrocommunity` repo has hundreds of pre-built plugin specs (including DAP configs) that snap into the template, encouraging a "mix and match" style rather than "override the defaults" style.
- **4 priority areas**: Covered via astrocommunity packs per language (LSP, DAP, none built-in by default the way LazyVim's extras are — you opt into an astrocommunity pack per language, e.g. `pack.go`, which bundles LSP+DAP+formatting+linting together).
- **cfgcaddy fit**: Good — same thin-template architecture as LazyVim.
- **Personal-customization fit**: Similar to LazyVim; vimwiki/vim-zettel and filetype/snippet work is equally additive.
- **Pros**: Very polished, modular, strong "team config sharing" culture (astrocommunity) which happens to also work well for a personal config that wants curated language packs instead of assembling raw plugin specs.
- **Cons**: Same sprawl/opinionation concerns as LazyVim, slightly smaller community than LazyVim for troubleshooting, no meaningfully stronger case than LazyVim on the two decisive factors.
- **Verdict**: **Viable**, not Recommended — same reasoning as LazyVim; if a distro were chosen, LazyVim's larger community and clearer per-extra DAP wiring is marginally the better bet between the two.

### NvChad
- **Maturity**: v2.5 (starter-config rewrite) actively maintained; has a documented history of breaking changes between major versions (the v2.0→v2.5 move was itself a breaking rewrite of the config model).
- **License**: GPL-3.0 (notably copyleft — different from LazyVim/AstroNvim's permissive licenses; not a practical problem for a personal config that isn't redistributed, but worth flagging since the other two are MIT/Apache).
- **Opinionated/customizable**: Optimized for performance and visual polish over configurability; less of a "curated extras" story for LSP/DAP than LazyVim.
- **4 priority areas**: Weakest out-of-the-box DAP/LSP story of the three — more manual assembly required than LazyVim's extras or AstroNvim's community packs.
- **cfgcaddy fit**: Good under v2.5's starter-config model (same architecture shift as the other two); conflicts under pre-2.5 install instructions.
- **Cons**: History of breaking changes between major versions means periodic re-adaptation work even after initial setup — a maintenance tax that works against a "set it up once, dogfood for a week" goal. Weaker DAP/debugging story than LazyVim for the two priority languages (Go, Python).
- **Verdict**: **Not recommended**. No advantage over LazyVim/AstroNvim on the two decisive factors, and it's weaker specifically on DAP — the single most fragile, highest-priority requirement in this project.

---

## Option 2: kickstart.nvim as a fork/adapt base

- **Maturity**: ~30k stars, ~45k forks (unusually high fork:star ratio — a direct signal that people follow its "fork this" instructions rather than star-and-move-on). Actively committed as recently as June 2026.
- **License**: MIT.
- **Philosophy**: explicitly *not* a distro. It is "a launch point for your personal nvim configuration" — a single, heavily-commented `init.lua` (plus optional `lua/kickstart/plugins/*.lua` add-on stubs for e.g. debug/lint) meant to be read top-to-bottom, forked, and directly edited — not installed and left to auto-update. The maintainers are explicit that it is a teaching reference, not a framework: "distros are great for inspiration... create your own config."
- **cfgcaddy fit**: Excellent — trivially so. There is no "distro core" to fetch or import; every line kickstart gives you is a plain file you own outright from day one. This is functionally identical to symlinking `.vimrc` today, just split into `init.lua` + a `lua/` tree.
- **Personal-customization fit**: Excellent, for the same reason. There's no distro opinion to override — the leader key, filetype settings, wiki plugin wiring, and snippet paths are added directly into a structure Tyler fully understands, because kickstart's whole design intent is that the person reading it becomes the author.
- **Pros**: Zero cfgcaddy conflict, zero distro-opinion fighting, actively maintained as a *reference* (bug fixes/updates to the teaching pattern still land), includes a debug.lua stub already wired for nvim-dap + mason that's a legitimate starting point rather than a blank page. Much smaller surface area to audit than a full distro — aligns with the project's "prune to a minimal, audited plugin set" goal.
- **Cons**: Provides far less out-of-the-box scaffolding than LazyVim's extras for DAP/LSP per-language — Tyler (or this project's planning/implementation phases) still has to assemble and validate the Go/Python/Rust/TS-JS LSP+DAP wiring largely by hand, using kickstart's stub and LazyVim/AstroCommunity specs as reference material rather than a working default.
- **Verdict**: **Recommended** as the structural starting skeleton. It resolves both decisive factors better than any full distro, at the cost of more manual assembly work for the 4 priority areas — which the "from scratch" option below addresses using the same reference material.

---

## Option 3: From-scratch build (nvim-lspconfig, treesitter, telescope/fzf-lua, nvim-dap, gitsigns/neogit assembled directly)

- **cfgcaddy fit**: Excellent — identical reasoning to kickstart.nvim; there's no external "distro" dependency at all, just plain Lua files under a structure this project designs.
- **Personal-customization fit**: Excellent — maximum control, zero distro defaults to discover and override. The `,` leader, filetype settings, wiki integration, and snippet paths carry over unchanged in spirit from the current `.vimrc`.
- **Pros**: Full control; matches the explicit requirements-doc ask to produce a reasoned vimscript-vs-Lua recommendation rather than inherit someone else's answer; the resulting config only contains what the audit says is needed, directly satisfying "no redundant plugins" and "zero dead files" success metrics; nothing to fight.
- **Cons**: Most upfront effort of any option, particularly DAP adapter wiring — the requirements doc's own Rabbit Holes section flags DAP setup as "often the most fragile part of a modern config," and building it from zero (vs. adapting a known-working `nvim-dap-go`/`nvim-dap-python` spec) is the single biggest place this could slip the 3–6 week appetite.
- **Note**: this option and Option 2 (kickstart) are not fully distinct in practice — kickstart *is* a from-scratch build with a documented, actively-maintained skeleton and a debug.lua starting stub. The realistic version of "from scratch" for this project is "kickstart's skeleton, then assemble the rest using community-tested reference snippets" (see Option 4).
- **Verdict**: **Recommended**, effectively merged with Option 2 — use kickstart.nvim's skeleton as the literal starting point rather than writing `init.lua` bootstrapping (lazy.nvim install, base options) from a blank file, then assemble LSP/DAP/fuzzy-find/git directly rather than importing a distro's plugin bundle.

---

## Option 4: LLM-generated plugin configs vs. adapting community-tested snippets

There is a real, non-hypothetical risk in hand-writing Neovim Lua plugin specs from an LLM's training data alone, specifically for the plumbing pieces (not the personal pieces):

- **API drift risk is concrete here, not generic**: Neovim 0.11 (the version floor this project targets) introduced the native `vim.lsp.config()` / `vim.lsp.enable()` API that is displacing the older `require('lspconfig').<server>.setup{}` pattern many training corpora are saturated with. An LLM hand-writing LSP setup from memory is more likely to reach for the older, still-technically-working-via-back-compat idiom than the current idiomatic path, or to invent plausible-looking but wrong `opts` keys for fast-moving plugins (DAP adapter tables, mason `ensure_installed` package names, treesitter parser lists) where the correct value is a specific string that must match what the tool actually registers.
- **Community-tested snippets are the better source for boilerplate/plumbing**: LazyVim's `lang.go`/`lang.python`/`lang.rust`/`lang.typescript` extras, AstroCommunity's per-language packs, and kickstart.nvim's own `lua/kickstart/plugins/debug.lua` are all continuously exercised by large user bases against current plugin versions. Adapting these for the mechanical parts (Delve/debugpy adapter registration, Mason package names, treesitter `ensure_installed` lists, gitsigns default keymaps) is lower-risk and faster than reasoning them out from scratch, and doesn't forfeit any of the "from scratch" benefits above — the resulting config is still fully-owned, auditable, and distro-independent, since these are single-file references to copy and adapt, not a dependency to import.
- **Where bespoke config legitimately cannot come from any reference**, regardless of base chosen: the `,` vs `<space>` leader decision (a decade of muscle memory — no community snippet can decide this), the 12+ custom per-filetype `tabstop`/`shiftwidth` settings already encoded in `.vimrc`, the vimwiki/vim-zettel wiring to `~/personal-wiki/logseq/pages` (explicitly out-of-scope-to-improve but in-scope-to-preserve), and the personal-snippet path wiring to `~/.vimsnippets`. These are Tyler-specific facts no distro, kickstart fork, or community snippet encodes — they have to be hand-authored and reviewed in the planning/implementation phases no matter which base is chosen.
- **Verdict**: Use community-tested snippets (LazyVim extras / AstroCommunity packs / kickstart's debug.lua) as reference material for the plumbing during implementation, rather than having an LLM (or Tyler) write DAP/LSP/mason wiring from a blank page. Treat the personal-preference items above as always-bespoke, always-hand-reviewed, independent of that choice.

---

## Option 5: Fork/adapt a specific existing personal dotfiles repo

- **Example evaluated**: ThePrimeagen's `init.lua`/`.dotfiles` — arguably the most well-known personal Neovim config in the community, with multiple public forks (e.g. `enlightened/init.lua`) demonstrating the pattern is common.
- **Pros**: Concrete existence proof that "fork a specific person's config" is a viable, common pattern; can be useful as inspiration for structuring `lua/` modules or specific plugin choices.
- **Cons**: ThePrimeagen's config uses Packer, a plugin manager that has been unmaintained since 2023 — forking it directly would require swapping in lazy.nvim anyway, eliminating most of the time-savings of forking. More fundamentally, any specific individual's dotfiles encode *their* leader key, *their* keybinding scheme, and *their* plugin choices — adopting one wholesale means undoing as much personalization work as adopting a distro, just with a less-maintained, less-documented starting point and no community support channel. It offers strictly less than kickstart.nvim, which is purpose-built and actively maintained as a generic fork base, while a specific person's dotfiles are not.
- **Verdict**: **Not recommended** as the literal fork base. **Viable** only as ad hoc inspiration/reference for specific snippets during implementation (same role as the LazyVim/AstroCommunity specs in Option 4) — not as a structural starting point over kickstart.nvim.

---

## Summary Recommendation

**Hybrid, not a binary build-vs-buy choice**: use kickstart.nvim's actively-maintained, MIT-licensed, plain-file skeleton (Option 2) as the literal starting point instead of bootstrapping `init.lua` from zero — it is functionally "from scratch with a documented on-ramp" (Option 3) and both resolve the cfgcaddy and personal-customization constraints identically and better than any full distro. Then assemble the 4 priority areas (LSP, DAP, fuzzy-find, git) by adapting community-tested reference snippets from LazyVim's language extras, AstroCommunity packs, and kickstart's own debug.lua (Option 4) rather than hand-rolling adapter/mason/treesitter plumbing from an LLM's possibly-stale training data. Do not adopt LazyVim/AstroNvim/NvChad wholesale (Option 1) — they are now technically cfgcaddy-compatible (a real update to the pre-research assumption in `requirements.md`), but their scale and opinionation cut directly against this project's own success metrics (audited, non-redundant, minimal plugin set) and personalization requirement. Do not fork a specific person's dotfiles repo (Option 5) — no advantage over kickstart.nvim as a structural base, useful only as occasional reference alongside the distro specs.

**Decisive factors recap**:
- cfgcaddy: all options are now technically compatible (the "distro owns ~/.config/nvim" concern is resolved as of current distro versions) — this factor no longer rules anything out, but doesn't favor a full distro either since kickstart/from-scratch are just as compatible with zero extra indirection.
- Personal customization: this is the factor that actually discriminates — it favors kickstart/from-scratch (nothing to override) over full distro adoption (a lot to override) and over forking a stranger's dotfiles (someone else's overrides to undo).
