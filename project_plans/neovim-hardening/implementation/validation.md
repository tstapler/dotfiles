# Validation Plan: neovim-hardening

**Date**: 2026-07-15

## Happy Path Scenario
Given the Phase 1 shared infrastructure (lazy.nvim, safe-map registry, treesitter, statusline/explorer/finder/git) is loaded under `NVIM_APPNAME=nvim-next`, when Tyler opens a real `go.mod` project's `.go` file, presses `grn` to rename a variable and uses `<leader>db`/`<leader>dc` to set a breakpoint and launch the debugger, then gopls renames the variable package-wide, Delve stops at the breakpoint with dap-ui showing the variable scope, and `:checkhealth vim.lsp` shows exactly one active client for the buffer — proving the full LSP+DAP+nav+git vertical works end-to-end without IntelliJ, the pattern every later language phase replicates.

## Requirement → Verification Mapping

### Phase 1: Shared infrastructure

| Requirement/Story | Verification Mechanism | Check Name | Type | Scenario |
|---|---|---|---|---|
| Story 1.1.1: init.lua bootstrap | `rm -rf ~/.local/share/nvim-next ~/.local/state/nvim-next && NVIM_APPNAME=nvim-next nvim --headless -c 'qa' 2>&1 \| grep -iE 'error\|E[0-9]{3}'` (expect empty) | `bootstrap_should_start_with_zero_errors_on_fresh_install` | Mechanical | Happy path |
| Story 1.1.1: `:Lazy` UI availability | Manual: launch `nvn`, run `:Lazy` | `lazy_ui_should_open_via_command` | Manual | Happy path |
| Story 1.1.1: leader set before lazy | `nvim --headless -c 'lua print(vim.g.mapleader)' -c 'qa'` prints a single space | `leader_should_be_space_before_lazy_loads` | Mechanical | Happy path |
| Story 1.1.1: no comma leader anywhere | `grep -rn "mapleader" .config/nvim/` — confirm no `,` value remains | `mapleader_should_not_be_comma_anywhere_in_tree` | Mechanical | Happy path |
| Story 1.2.1: options ported | `nvim --headless -c 'set number? mouse? undofile? inccommand?' -c 'qa'`, grep output for expected values | `options_should_match_legacy_vimrc_values` | Mechanical | Happy path |
| Story 1.2.2: Go indent autocmd | Open `.go` file, `:setlocal tabstop? shiftwidth? expandtab?` | `go_file_should_use_tabstop_2_expandtab` | Mechanical | Happy path |
| Story 1.2.2: vimwiki filetype race | Manual: open real `~/personal-wiki/logseq/pages/*.md`, `:set filetype?` | `wiki_page_should_resolve_filetype_vimwiki_not_mkd` | Manual | Happy path |
| Story 1.2.2 / pitfalls §3: wiki dir absent | Manual: temporarily rename `~/personal-wiki`, launch `nvn` fresh, check `:messages` for zero errors (wiki.lua loads vimwiki eagerly, `lazy=false`) | `wiki_dir_absent_should_not_error_on_fresh_machine` | Manual | Error/degraded — closes adversarial-review CONCERN #4 |
| Story 1.3.1: safe-map duplicate rejection | Temporarily register two `map("n","<leader>f",...)` calls, launch headless, grep `:messages`/stderr for `duplicate keymap: n <leader>f` | `safe_map_should_reject_duplicate_bind_when_two_plugins_claim_same_lhs` | Mechanical | Error/degraded (validates the failure-injection path) |
| Story 1.3.1: single resolution after full config load | `nvim --headless -c 'verbose nmap <leader>f' -c 'qa'` — exactly one "Last set from" line | `safe_map_should_resolve_each_key_to_exactly_one_binding_after_full_config_loads` | Mechanical | Happy path |
| Story 1.3.1: `reserve()` shares collision table with `map()` | Give a lazy `keys=` entry (via `reserve()`) the same lhs as an existing `map()` call, confirm startup errors | `reserve_should_register_lazy_keys_in_same_collision_table` | Mechanical | Error/degraded |
| Story 1.3.2: `Y` yanks to EOL | Manual: press `Y` in normal mode on a line | `Y_should_yank_to_end_of_line` | Manual | Happy path |
| Story 1.3.2: `<F7>` terminal | Manual: press `<F7>` with zsh available | `F7_should_open_zsh_terminal_split_when_zsh_available` | Manual | Happy path |
| Story 1.3.2: `leader_groups.lua` single source of truth | `grep -n "leader_groups" keymaps.lua which-key.lua` — both reference the module, no hardcoded duplicate table | `leader_groups_rename_should_propagate_to_keymaps_comment_and_whichkey_without_second_edit` | Mechanical | Happy path |
| Story 1.4.1: which-key popup | Manual: press `<leader>`, wait ~0.5s, confirm f/c/d/g/h groups shown | `whichkey_should_show_leader_groups_popup_after_hesitation` | Manual | Happy path |
| Story 1.5.1: Go parser + checkhealth | Open `.go` file, `:InspectTree`; `nvim --headless -c 'checkhealth nvim-treesitter' -c 'qa'` grep for `go` OK | `go_treesitter_parser_should_render_parse_tree_and_pass_checkhealth` | Mechanical + Manual | Happy path |
| Story 1.5.1: large-file guard | Manual: open a 60k-line generated file, confirm treesitter highlight is skipped, no input lag | `treesitter_should_skip_highlighting_on_large_generated_file` | Manual | Error/degraded (size-guard fallback) |
| Story 1.5.1 / pitfalls §3: vimwiki markdown-parser conflict | Manual: open real wiki page, confirm no `no parser for 'vimwiki'` error, no markdown parser attaches | `vimwiki_buffer_should_not_attach_markdown_parser` | Manual | Error/degraded — closes a confirmed nvim-treesitter#6720-class regression |
| Story 1.6.1: legacy files deleted | `grep -rn "vimrc.local\|vimrc.bundles.local\|vimrc.plug\|vimrc.dein" .` (zero hits outside plan docs); `ls` each path expects "No such file" | `legacy_files_should_be_fully_deleted_with_no_remaining_references` | Mechanical | Happy path |
| Story 1.6.2: cfgcaddy `init.vim` entries removed | `grep -n "init.vim" .cfgcaddy.yml` — zero matches | `cfgcaddy_yml_should_have_zero_init_vim_references_after_cleanup` | Mechanical | Happy path |
| Task 1.6.2a: dir-vs-file linking check | Touch a temp file under `.claude/skills/`, check if `~/.claude/skills/` reflects it without re-running cfgcaddy install; record result | `cfgcaddy_directory_vs_file_linking_should_be_determined_empirically` | Mechanical | Happy path (investigation) |
| pitfalls §6 / adversarial-review CONCERN #2: second-machine deploy | Manual: fresh disposable container/VM, clone dotfiles, run cfgcaddy install cold, launch `nvim`, confirm Mason auto-installs, `rustup component add rust-analyzer` succeeds, treesitter `auto_install` fires, absent `~/personal-wiki` doesn't error, `:checkhealth` is clean | `second_machine_fresh_cfgcaddy_deploy_should_reproduce_working_config` | Manual | Error/degraded — closes adversarial-review CONCERN #2 |
| Story 1.6.3: coc-settings.json deleted | `ls .config/nvim/coc-settings.json` expects "No such file" | `coc_settings_json_should_not_exist_after_deletion` | Mechanical | Happy path |
| Story 1.6.3 / pitfalls §1: snippet inventory before removal | Manual: list `~/.vimsnippets`, confirm inventory distinguishes personal vs. vendored UltiSnips-format snippets | `personal_ultisnips_snippets_should_be_inventoried_before_coc_snippets_removed` | Manual | Error/degraded (data-loss prevention) |
| Story 1.6.4: `.vimrc` fallback trimmed | `grep -n "source ~/.vimrc.dein"` (expect none); grep for fallback header comment (expect present) | `vimrc_fallback_should_have_no_dein_source_and_fallback_header` | Mechanical | Happy path |
| Story 1.7.1: lualine + gruvbox, airline gone | Manual: open any file, confirm lualine mode/branch/filename/diagnostics; `exists(':AirlineToggle')` == 0 | `lualine_should_render_with_gruvbox_and_airline_fully_removed` | Manual + Mechanical | Happy path |
| Story 1.7.2: oil.nvim | Manual: press `-`, confirm oil buffer opens; `<C-e>` toggles; `exists(':NERDTreeToggle')` == 0 | `oil_should_open_parent_dir_as_buffer_on_dash_keypress` | Manual | Happy path |
| Story 1.7.3: fzf-lua | Manual: `<leader>ff` opens picker+preview in a git repo; `<leader>fg` live-greps; `exists(':CtrlP')` == 0 | `fzf_lua_file_picker_should_open_with_live_preview_on_leader_ff` | Manual | Happy path |
| Story 1.7.4: gitsigns + fugitive | Manual: edit tracked file, confirm hunk sign, `<leader>hs` stages, `]c`/`[c` nav, `:Git` opens status; `exists(':Merginal')` == 0 | `gitsigns_should_mark_hunk_and_stage_on_leader_hs` | Manual | Happy path |
| Story 1.7.5: surround + repeat | Manual: `ysiw"` then `.`, confirm surround applies and repeat works | `surround_and_repeat_should_both_function_together` | Manual | Happy path |
| pitfalls §4: repeat/surround coupling | `grep` plugin specs — `vim-repeat` spec present whenever `vim-surround` spec present (both-or-neither) | `vim_repeat_pruned_without_surround_should_be_flagged_as_regression` | Mechanical | Error/degraded — closes a named pitfalls.md hazard |

### Phase 2: Go LSP + DAP pilot

| Requirement/Story | Verification Mechanism | Check Name | Type | Scenario |
|---|---|---|---|---|
| Story 2.1.1: Mason UI, no clients pre-enable | Manual: `:Mason` opens; `:checkhealth vim.lsp` shows no attached clients | `mason_ui_should_open_with_no_attached_lsp_clients_before_server_enabled` | Manual | Happy path |
| Story 2.1.1: LspAttach keymaps wired once | Manual (cross-referenced/verified concretely in Story 2.2.1's checks below) | `lspattach_keymaps_should_wire_once_when_client_attaches` | Manual | Happy path |
| Story 2.1.1: not-yet-migrated filetype keeps working under coc | Manual: open `.rs`/`.py`/`.ts` file before that language's phase lands, confirm coc still attaches/provides features, `:checkhealth vim.lsp` shows zero native clients | `not_yet_migrated_filetype_should_still_use_coc_with_zero_native_clients` | Manual | Error/degraded — the critical non-regression state the adversarial-review BLOCKER fix depends on |
| Task 2.3.3a: coc-go torn down after real-project smoke test passes, gopls sole client | Manual: `.go` file after teardown, `:lua print(vim.b.coc_enabled)` is false, no coc diagnostics, gopls is sole client | `go_coc_extension_should_be_disabled_after_teardown_with_gopls_sole_client` | Manual | Happy path |
| adversarial-review CONCERN #1: Mason install failure | Manual: disable network (block github in `/etc/hosts` or drop the interface), fresh `:MasonInstall gopls`, confirm Mason UI surfaces a clear failed state within a bounded timeout (not a silent hang) | `mason_install_failure_should_surface_clear_error_not_silent_hang` | Manual | Error/degraded — closes adversarial-review CONCERN #1 |
| Task 2.1.1c: ale/coc-source plugins absent | `grep -rn "w0rp/ale\|neoinclude\|neco-syntax\|neco-vim\|neco-look\|context_filetype\|vim-autoformat" lua/tstapler/plugins/` — zero matches | `ale_and_coc_completion_source_plugins_should_be_absent_from_plugin_tree` | Mechanical | Happy path |
| Story 2.2.1: gopls single client + rename | Manual: `go.mod` project, `grn` on variable, confirm package-wide rename; `:checkhealth vim.lsp` shows exactly one client | `go_lsp_should_show_single_active_client_and_rename_package_wide_when_grn_pressed` | Manual | Happy path |
| Story 2.2.1: single-file fallback | Manual: bare `.go` file with no `go.mod`/`.git`, confirm gopls attaches without crash, `vim.notify` warns about degraded cross-file features | `gopls_should_attach_in_single_file_mode_without_crash_when_go_mod_absent` | Manual | Error/degraded |
| Story 2.2.1: Go LSP smoke section | Manual: run `gd`/`grr`/`grn`/`K` checklist end-to-end | `go_smoke_test_lsp_section_should_pass_end_to_end` | Manual | Happy path |
| Story 2.3.1: DAP breakpoint + dap-ui | Manual: `<leader>db` breakpoint, `<leader>dc` launch, confirm stop, dap-ui variable scope, step-over, continue | `go_dap_breakpoint_should_stop_and_dapui_should_show_variable_scope` | Manual | Happy path |
| Story 2.3.1: debug-nearest-test | Manual: run nvim-dap-go debug-nearest-test, confirm stop inside test | `go_test_debug_nearest_should_stop_at_breakpoint_inside_test` | Manual | Happy path |
| Story 2.3.1 / pitfalls §2: breakpoint set before DAP loads | Manual: fresh `nvn` session, press `<leader>db` before any DAP command has run, confirm force-load and correct bind | `dap_breakpoint_set_before_plugin_loads_should_still_bind_via_forced_load` | Manual | Error/degraded — closes a named lazy-loading DAP hazard |
| Story 2.3.1 / pitfalls §2: adapter path hardcoded | `grep` `dap.lua`/`lang/go.lua` for the `dlv` adapter `command` — must be `stdpath("data").."/mason/bin/dlv"`, not bare `"dlv"` | `dap_adapter_path_should_be_hardcoded_not_dollar_path_dependent` | Mechanical | Error/degraded — guards against PATH-inheritance failures in GUI launchers |
| Story 2.3.2: full Go smoke test | Manual: run all five Observability Plan sections on a real Go project under `nvn` | `go_full_smoke_test_all_five_sections_should_pass` | Manual | Happy path |
| Story 2.3.2: Go pilot startup benchmark | `NVIM_APPNAME=nvim-next nvim --startuptime /tmp/nvim-next-phase2.log` x3, compare median to `/tmp/nvim-baseline.log` | `go_pilot_startup_time_should_not_regress_vs_baseline` | Mechanical | Happy path |

### Phase 3: Rust LSP + DAP

| Requirement/Story | Verification Mechanism | Check Name | Type | Scenario |
|---|---|---|---|---|
| Story 3.1.1: rust-analyzer single client + rename | Manual: `Cargo.toml` project, `grn` on struct field, confirm crate-wide rename; one client | `rust_lsp_should_show_single_client_and_rename_across_crate_when_grn_pressed` | Manual | Happy path |
| Story 3.1.1: codelldb debugging | Manual: `:RustLsp debuggables`, pick binary, confirm stop + dap-ui scopes | `rust_dap_should_stop_at_breakpoint_via_rustlsp_debuggables` | Manual | Happy path |
| Story 3.1.1 / pitfalls §2: rust-analyzer via rustup not mason | `rustup component list --installed \| grep rust-analyzer` present; `~/.local/share/nvim-next/mason/bin/rust-analyzer` absent | `rust_analyzer_should_originate_from_rustup_not_mason` | Mechanical | Error/degraded — guards against toolchain/version drift |
| Task 3.1.1c: coc-rust-analyzer torn down | Manual: after 3.1.1b passes, remove `coc-rust-analyzer` + set `b:coc_enabled=false` for rust, reopen `.rs`, confirm one client, no coc diagnostics | `rust_coc_should_be_torn_down_only_after_smoke_test_passes_with_single_client_remaining` | Manual | Happy path |
| adversarial-review CONCERN #3: per-phase startup re-check | 3x `--startuptime` run after Phase 3 lands, compare median to baseline | `rust_pilot_startup_time_should_not_regress_vs_baseline` | Mechanical | Happy path (gap-closing — closes adversarial-review CONCERN #3) |
| Task 3.1.1a: rust-tools.nvim absent | `grep -rn "rust-tools.nvim\|simrat39"` — zero matches (archived-plugin audit) | `rust_tools_nvim_should_be_absent_from_plugin_tree` | Mechanical | Happy path |

### Phase 4: Python LSP + DAP

| Requirement/Story | Verification Mechanism | Check Name | Type | Scenario |
|---|---|---|---|---|
| Story 4.1.1: basedpyright single client + rename | Manual: `.venv` project, `grn` on function, confirm project-wide rename, one client | `python_lsp_should_show_single_client_and_rename_across_project_when_grn_pressed` | Manual | Happy path |
| Story 4.1.1: debugpy under project venv | Manual: breakpoint + active `.venv`, launch debug, confirm interpreter is venv's not system Python, stops at breakpoint | `python_dap_should_run_under_project_venv_interpreter_not_system_python` | Manual | Happy path |
| Story 4.1.1 / pitfalls §2: non-standard venv location | Manual: poetry/pipenv project with venv outside project dir, confirm `resolve_python()`/`pythonPath` picks correct interpreter, verify with `/path/to/python -m debugpy --version` | `python_venv_outside_project_should_resolve_via_custom_resolver_not_system_python` | Manual | Error/degraded — closes a named silent-wrong-interpreter hazard |
| pitfalls §2: `python3-venv` system package footgun | `python3 -m venv --help` exits 0 before troubleshooting Mason debugpy install failures | `python3_venv_module_should_be_present_before_mason_debugpy_install` | Mechanical | Error/degraded — distinguishes a system-package gap from a Mason bug |
| Task 4.1.1d: coc-pyright torn down | Manual: after 4.1.1c passes, remove `coc-pyright` + set `b:coc_enabled=false` for python, reopen `.py`, confirm basedpyright+ruff clients, no coc diagnostics | `python_coc_should_be_torn_down_only_after_smoke_test_passes_with_single_client_remaining` | Manual | Happy path |
| adversarial-review CONCERN #3: per-phase startup re-check | 3x `--startuptime` run after Phase 4 lands, compare median to baseline | `python_pilot_startup_time_should_not_regress_vs_baseline` | Mechanical | Happy path (gap-closing) |

### Phase 5: TypeScript/JavaScript LSP (+ stretch DAP)

| Requirement/Story | Verification Mechanism | Check Name | Type | Scenario |
|---|---|---|---|---|
| Story 5.1.1: vtsls single client + references | Manual: pnpm monorepo `.ts` file, `grr` on function, confirm references across package, one client | `tsjs_lsp_should_show_single_client_and_list_references_across_package_when_grr_pressed` | Manual | Happy path |
| Story 5.1.1 / features.md §3: monorepo root resolution | Manual: monorepo with `tsconfig.json` at multiple depths, confirm vtsls `root_dir` picks nearest package, not repo top | `tsjs_monorepo_root_should_resolve_to_nearest_package_not_repo_top` | Manual | Error/degraded |
| Task 5.1.1c: coc-tsserver torn down + coc.nvim fully removed (last language) | Manual: after 5.1.1b passes, teardown + remove `coc.nvim` spec entirely, confirm `exists(':CocInfo')`==0, coc.nvim absent from `:Lazy`, vtsls sole client | `tsjs_coc_should_be_fully_removed_as_last_language_with_single_vtsls_client_remaining` | Manual | Happy path |
| Task 5.1.1c: dead per-language autocmds cleaned up | `grep -n "coc_enabled" autocmds.lua` — zero remaining references after coc.nvim removal | `dead_per_language_coc_enabled_autocmds_should_be_removed_after_coc_fully_uninstalled` | Mechanical | Happy path |
| adversarial-review CONCERN #3: per-phase startup re-check | 3x `--startuptime` run after Phase 5 lands, compare median to baseline | `tsjs_pilot_startup_time_should_not_regress_vs_baseline` | Mechanical | Happy path (gap-closing) |
| Story 5.1.2 (stretch): pwa-node DAP or explicit deferral | Manual: Node script + breakpoint, launch `pwa-node` config, confirm stop OR confirm documented deferral with `vim.notify` fallback and no half-working state | `tsjs_dap_should_stop_at_breakpoint_via_pwa_node_or_be_explicitly_deferred` | Manual | Happy path (non-blocking stretch) |

### Phase 6: Git UI consolidation (conditional)

| Requirement/Story | Verification Mechanism | Check Name | Type | Scenario |
|---|---|---|---|---|
| Story 6.1.1: neogit + diffview compose with gitsigns | Manual: repo with merge conflict, `:DiffviewOpen` shows 3-way view; neogit stages hunks + writes commit message | `neogit_and_diffview_should_compose_with_gitsigns_if_added` | Manual | Happy path (conditional on felt need) |
| Story 6.1.1: documented skip if not needed | Manual: if fugitive+gitsigns proved sufficient during Phases 2-5 dogfooding, confirm a one-line documented reason for skipping | `neogit_diffview_should_be_skipped_with_documented_reason_if_not_needed` | Manual | Happy path (valid alternate branch) |

### Phase 7: Cleanup, verification, cutover

| Requirement/Story | Verification Mechanism | Check Name | Type | Scenario |
|---|---|---|---|---|
| Story 7.1.1: `.ideavimrc` minor cleanup bound | `grep -n 'mapleader=" "' .ideavimrc`; diff line-count added ≤ ~6 | `ideavimrc_should_set_space_leader_and_stay_within_minor_cleanup_bound` | Mechanical | Happy path |
| Story 7.2.1: wiki filetype + no markdown parser | Manual: real wiki file, `:set filetype?`==vimwiki, `:InspectTree` shows no markdown parser, wikilinks follow on `<CR>`, no parser error | `wiki_page_should_use_native_vimwiki_syntax_with_no_markdown_parser_attached` | Manual | Happy path |
| Story 7.2.1: non-wiki markdown parity | Manual: open a non-wiki scratch `.md` file, confirm markdown treesitter DOES attach (exclusion is wiki-scoped, not global) | `non_wiki_markdown_scratch_file_should_still_get_treesitter_markdown_highlighting` | Manual | Happy path |
| adversarial-review CONCERN #4: wiki dir absent, final gate | Manual: rename `~/personal-wiki` away, launch `nvn` fresh, confirm zero startup errors before declaring Phase 7 done | `wiki_dir_absent_on_fresh_machine_should_start_nvn_with_zero_errors` | Manual | Error/degraded — closes adversarial-review CONCERN #4 (final gate, mirrors check #8) |
| Story 7.3.1: full plugin ported/replaced/pruned mapping | Mechanical: diff `.vimrc.dein` list against new tree; grep confirms explicitly-named pruned set (coc.nvim, ale, ctrlp.vim, vim-ctrlspace, fzf.vim, ctrlsf.vim, Merginal, vimagit, vim-airline, NERDTree, Shougo/*, vim-autoformat, vim-polyglot, etc.) is absent | `old_plugin_list_should_map_fully_to_ported_replaced_or_pruned` | Mechanical | Happy path |
| Story 7.3.1 / pitfalls §4: ctrlspace session-persistence gap | Manual: confirm session/workspace persistence usage is either confirmed unused, or a replacement (mksession autosave/persistence.nvim) is in place before deleting vim-ctrlspace | `ctrlspace_session_persistence_gap_should_be_resolved_before_deletion` | Manual | Error/degraded — closes Unresolved Question #4 |
| Task 7.3.1b: ambiguous low-signal plugins | Manual: for emmet-vim/starlark.vim/vim-kubernetes/vim-base64/hexmode/snippet-source plugins, confirm usage decision recorded (ported or pruned + logged in `REMOVED-PLUGINS.md`) | `ambiguous_low_signal_plugins_should_be_ported_only_if_muscle_memory_confirms_usage` | Manual | Happy path |
| Success Metric: no redundant plugins | `grep` plugin spec directory for known-redundant function classes (fuzzy finders, git-status UIs) — exactly one per class (plus optional neogit/diffview) | `no_redundant_plugin_should_serve_same_function_across_final_tree` | Mechanical | Happy path |
| Task 7.4.1a / pitfalls §6: lazy-lock.json committed | `git check-ignore .config/nvim/lazy-lock.json` (non-zero exit — not ignored); `git ls-files .config/nvim/lazy-lock.json` (present) | `lazy_lock_json_should_be_committed_not_gitignored` | Mechanical | Happy path |
| Success Metric: full week of daily-driver use | Manual: track a full week of `nvn` daily use across all four languages; log any fallback-to-master/IntelliJ incidents; zero required | `week_long_dogfood_should_complete_with_zero_reverts_to_master_or_intellij` | Manual | Happy path |
| Story 7.4.1 / Migration Plan: cutover reversibility | See **Cutover Reversibility Check** in Verification Protocol below | `cutover_should_be_reversible` | Manual | Error/degraded (rollback path) |
| adversarial-review CONCERN #5: future nvim upgrade / TSUpdate reminder | `grep` the cutover checklist / plan for a line instructing "after any future nvim version bump, run `:TSUpdate` and re-run the smoke-test checklist"; confirm present | `future_nvim_upgrade_should_trigger_documented_tsupdate_and_smoke_test_reminder` | Mechanical | Error/degraded — closes adversarial-review CONCERN #5 (doc-gap) |
| pitfalls §5: lazy.nvim spec-merge `keys` array override | For any plugin whose `keys=` array is contributed to by more than one file (e.g. DAP keys extended per-language), confirm `opts_extend` is set or the effective merged `keys` array actually contains every file's entries (inspect via `:Lazy` / `require('lazy.core.plugin').spec`) | `plugin_spec_keys_arrays_should_not_be_silently_overridden_across_files` | Mechanical | Error/degraded — closes a named lazy.nvim footgun |

---

## Verification Protocol

### Startup benchmark
- **Baseline (before Phase 1 starts)**: on master's current config, `nvim --startuptime /tmp/nvim-baseline.log`, 3 runs, record the final "NVIM STARTED" total for each; use the median.
- **Re-check points**: after Phase 2 (Go pilot sign-off, Task 2.3.2a), after Phase 3 (Rust), after Phase 4 (Python), after Phase 5 (TS/JS), and once more at final cutover (Task 7.4.1a/b) — not just once at the end of the Go pilot (this closes adversarial-review CONCERN #3, which flagged that Phases 3-6 had no re-check task).
- **Command per re-check**: `NVIM_APPNAME=nvim-next nvim --startuptime /tmp/nvim-next-phaseN.log`, 3 runs, median total.
- **Regression threshold**: new-config median total must be **≤** the master baseline median (Success Metric, requirements.md). No percentage slack — the baseline is the bar.
- **First response to a regression**: check for over-eager `lazy = false` / `event = "VeryLazy"` left in from debugging that session's story (pitfalls.md §5) before assuming a plugin itself is slow; convert to a proper `ft`/`cmd`/`keys` trigger before proceeding to the next phase.

### Smoke-test checklist per phase
Run under `nvn` before calling any language story done (per Observability Plan in plan.md):
1. **LSP**: open a real file of the language → `:checkhealth vim.lsp` shows exactly ONE client attached; `gd` jumps to definition; `grr` lists references; `grn` renames across files; `K` shows hover.
2. **DAP** (Go, Python; Rust via codelldb; TS/JS optional-stretch): set a breakpoint, launch debug, confirm it stops, inspect a variable in dap-ui, step over, continue to exit.
3. **Fuzzy-find**: `<leader>ff` opens files with live preview; `<leader>fg` live-greps.
4. **Git**: edit a tracked file → gitsigns shows the hunk in the sign column; `<leader>hs` stages it; `:Git` (fugitive) opens status.
5. **No-duplicate-keymap**: config loads with zero errors (safe-map registry throws on any duplicate `(mode,lhs)`).
6. **Startup benchmark re-check** (see above) — added explicitly to every phase's smoke test, not just Go's.
7. **Not-yet-migrated-language regression check** (Phases 2-4 only): open a file in a language whose phase hasn't landed yet, confirm coc.nvim still serves it and `:checkhealth vim.lsp` shows zero native clients for that buffer.

### Cutover reversibility check — `cutover_should_be_reversible`
1. Confirm pre-merge: master's `~/.local/share/nvim` (its coc/lazy runtime state) has received zero writes from `nvn` testing — spot-check `ls -la ~/.local/share/nvim/mason` / `~/.local/share/nvim/lazy` predates this project's work, versus `~/.local/share/nvim-next` holding all the new Mason binaries and plugin checkouts. This is the empirical proof that `NVIM_APPNAME=nvim-next` isolation actually held throughout development, not just a design intention (pitfalls.md §7).
2. Merge `dotfiles-harden-neovim` → `master`, run cfgcaddy install, launch plain `nvim`. Confirm `~/.config/nvim/init.vim` is gone, `~/.config/nvim/init.lua` + `lua/**` + `lazy-lock.json` exist, plugins/Mason tools install from the committed lockfile, `:checkhealth` is clean.
3. Rehearse rollback: revert the merge (or `git checkout master~1`) in `~/dotfiles`, re-run cfgcaddy install, relaunch `nvim`. Confirm the `init.vim` symlink is restored and the old coc.nvim config launches cleanly and immediately — proving the rollback is clean at the runtime-state level (step 1), not just the config-source level.
4. Both directions (cutover and rollback) must complete with zero manual repair steps beyond `git` + `cfgcaddy install` + a normal `nvim` launch.

---

## Test/Check Stack
- **Mechanical**: `:checkhealth`, `:LspInfo`/`:checkhealth vim.lsp`, `nvim --headless` scripted invocations piped through `grep`, `git check-ignore`/`git ls-files`, static `grep -rn` audits of plugin-spec files and `.cfgcaddy.yml`, `--startuptime` benchmark runs.
- **Manual**: Tyler performs an editor interaction (keypress, command, breakpoint) under `NVIM_APPNAME=nvim-next nvim` and observes the result against the plan's Given-When-Then criteria.

## Coverage Summary
- **All 29 stories in plan.md** (Phases 1-7): each has at least one mapped verification case above — 29/29 (100%).
- **All Success Metrics from requirements.md**: zero dead files (#`legacy_files_should_be_fully_deleted...`), no redundant plugins (#`no_redundant_plugin_should_serve_same_function...` + #`old_plugin_list_should_map_fully...`), gd/refs/rename/refactor per language without IntelliJ (#`go_lsp_...`, `rust_lsp_...`, `python_lsp_...`, `tsjs_lsp_...`), DAP for Go + Python (#`go_dap_...`, `python_dap_...`), startup no-regression (per-phase `*_startup_time_should_not_regress_vs_baseline` checks), full week of daily-driver use (#`week_long_dogfood_should_complete_with_zero_reverts...`) — all mapped.
- **79 total verification cases**: 31 mechanical, 48 manual.
- **22 error/degraded-path checks**, including 6 that directly close open items from adversarial-review.md's CONCERNS list (Mason install failure, second-machine fresh deploy, per-phase startup re-check gap ×4 phases, wiki-dir-absent on fresh machine ×2, future-nvim-upgrade/TSUpdate doc reminder) and 6 that close named hazards from research/pitfalls.md (§1 snippet loss before coc-snippets removal, §2 DAP breakpoint-before-load binding, §2 hardcoded adapter path, §2 rust-analyzer-via-rustup drift guard, §2 python3-venv system package footgun, §2 non-standard venv resolution, §3 vimwiki/treesitter parser conflict, §4 vim-repeat/vim-surround coupling, §4 ctrlspace session-persistence gap, §5 lazy.nvim `keys` array merge footgun).
