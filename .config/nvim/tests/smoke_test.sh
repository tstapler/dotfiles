#!/usr/bin/env bash
# Integration/smoke test + startup benchmark for the tstapler nvim config.
# Formalizes the mechanical checks from
# project_plans/neovim-hardening/implementation/validation.md into one
# repeatable script — no test framework, just nvim --headless + grep.
#
# Usage:
#   .config/nvim/tests/smoke_test.sh                 # run all checks against NVIM_APPNAME (default nvim-next)
#   .config/nvim/tests/smoke_test.sh --fresh          # wipe plugin/state dirs first (slow: full reinstall)
#   .config/nvim/tests/smoke_test.sh --save-baseline  # save current startup median as the regression baseline
#   NVIM_APPNAME=nvim ./smoke_test.sh                 # test the live (post-cutover) config instead
#
# Exit 0 if every check passes, 1 otherwise.

set -u
export NVIM_APPNAME="${NVIM_APPNAME:-nvim-next}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASELINE_FILE="$SCRIPT_DIR/.startup_baseline_ms"
NVIM_CONFIG_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

FRESH=0
SAVE_BASELINE=0
for arg in "$@"; do
  case "$arg" in
    --fresh) FRESH=1 ;;
    --save-baseline) SAVE_BASELINE=1 ;;
    *) echo "unknown flag: $arg" >&2; exit 2 ;;
  esac
done

PASS=0
FAIL=0
FAILED_NAMES=()

ok()   { PASS=$((PASS+1)); printf '  \033[32mPASS\033[0m  %s\n' "$1"; }
bad()  { FAIL=$((FAIL+1)); FAILED_NAMES+=("$1"); printf '  \033[31mFAIL\033[0m  %s\n' "$1"; [ -n "${2:-}" ] && printf '        %s\n' "$2"; }

nv() { nvim --headless "$@" 2>&1; }

echo "== nvim-hardening smoke test (NVIM_APPNAME=$NVIM_APPNAME) =="
echo

if [ "$FRESH" = 1 ]; then
  echo "-- fresh install (wiping plugin/state dirs) --"
  rm -rf "$HOME/.local/share/$NVIM_APPNAME" "$HOME/.local/state/$NVIM_APPNAME"
  # Plain `-c qa` triggers lazy.nvim's auto-install but returns before it
  # finishes (async) — later checks in this same run would then race against
  # still-installing plugins/parsers. `Lazy! sync` blocks until plugin clones
  # are done; TSUpdateSync does the same for treesitter parsers. Neither one
  # waits for mason-nvim-dap's own background tool installs (delve/debugpy/
  # codelldb, kicked off independently once mason-nvim-dap.nvim loads) — mason
  # exposes no single blocking "wait for everything" command, so a bounded
  # `sleep` is the pragmatic (not perfectly deterministic) way to give those
  # a chance to finish before quitting; bump this if it's still noisy.
  #
  # IMPORTANT: mason-lspconfig.nvim's `ensure_installed` deliberately does
  # NOT auto-install when Neovim is running --headless (see its own
  # features/ensure_installed.lua: `if not platform.is_headless and
  # #ensure_installed > 0 then ...`). Confirmed empirically: after a headless
  # fresh install, all four LSP server binaries (gopls/basedpyright/ruff/
  # vtsls) were absent from mason/bin even though ensure_installed listed all
  # four correctly — only mason-nvim-dap's tools (delve/debugpy/codelldb) had
  # installed, since that installer has no such guard. In real interactive
  # use this is a non-issue (first real `nvn` launch installs them fine) —
  # but headless verification needs an explicit :MasonInstall to actually
  # exercise "do the LSP servers install", or every fresh-install check here
  # would silently pass with zero LSP servers present.
  # `sleep 30` was a blind guess at how long Mason's background installs take
  # — too short once jdtls/kotlin-language-server/java-debug-adapter/java-test
  # (JVM-sized downloads) joined the list: CI runs showed jdtls/kotlin still
  # not on disk 30s later ("no client attached — server binary may not be
  # installed"). Poll mason-registry's own is_installed() per package instead,
  # bounded at 180s total, so the wait is only as long as it needs to be.
  wait_installs='local reg = require("mason-registry")
    local pkgs = { "gopls", "basedpyright", "ruff", "vtsls", "jdtls", "kotlin-language-server", "java-debug-adapter", "java-test" }
    local deadline = vim.uv.now() + 180000
    while vim.uv.now() < deadline do
      local all_done = true
      for _, name in ipairs(pkgs) do
        local ok, pkg = pcall(reg.get_package, name)
        if not ok or not pkg:is_installed() then
          all_done = false
          break
        end
      end
      if all_done then break end
      vim.wait(3000)
    end'
  out=$(nv -c 'Lazy! sync' -c 'TSUpdateSync' \
    -c 'MasonInstall gopls basedpyright ruff vtsls jdtls kotlin-language-server java-debug-adapter java-test' \
    -c "lua $wait_installs" -c 'qa')
  # This whole command's output only exists in $out — nothing streams to the
  # terminal/CI log live (it's fully captured via command substitution) —
  # so on failure there is otherwise NO way to see what actually happened
  # beyond whatever excerpt gets printed below. Locating a generic "Error
  # detected while processing command line:" prefix and windowing around
  # it (two prior attempts, plus a naive tail) kept missing: Lazy!/
  # TSUpdateSync/MasonInstall all write async progress into the same message
  # buffer concurrently, so the actual error CODE ends up lines away from its
  # own generic header, buried in unrelated interleaved install-progress
  # noise. Grep for the error code token itself instead of the header — it's
  # emitted as one atomic write, so it survives the interleaving intact.
  echo "$out" > /tmp/.nvn_fresh_install_full.log
  if echo "$out" | grep -qE 'E[0-9]{3,5}:|stack traceback'; then
    bad "fresh install: zero errors" "$(grep -nE 'E[0-9]{3,5}:|stack traceback' /tmp/.nvn_fresh_install_full.log | head -20)"
  else
    ok "fresh install: zero errors"
  fi
  echo
fi

echo "-- config invariants --"

leader=$(nv -c 'lua io.write(vim.g.mapleader)' -c 'qa')
[ "$leader" = " " ] && ok "leader is space" || bad "leader is space" "got: [$leader]"

if grep -rn "mapleader" "$NVIM_CONFIG_DIR" --exclude-dir=tests | grep -qv '" "'; then
  bad "no comma mapleader anywhere in tree"
else
  ok "no comma mapleader anywhere in tree"
fi

opts=$(nv -c 'set number? mouse? undofile? inccommand?' -c 'qa')
if echo "$opts" | grep -q "number" && echo "$opts" | grep -q "mouse=a" \
  && echo "$opts" | grep -q "undofile" && echo "$opts" | grep -q "inccommand=nosplit"; then
  ok "options match legacy .vimrc values"
else
  bad "options match legacy .vimrc values" "$opts"
fi

tmp_go=$(mktemp --suffix=.go)
echo 'package main' > "$tmp_go"
indent=$(nvim --headless "$tmp_go" -c 'setlocal tabstop? shiftwidth? expandtab?' -c 'qa' 2>&1)
rm -f "$tmp_go"
if echo "$indent" | grep -q "tabstop=2" && echo "$indent" | grep -q "shiftwidth=2" && echo "$indent" | grep -q "expandtab"; then
  ok "go filetype: tabstop=2 expandtab"
else
  bad "go filetype: tabstop=2 expandtab" "$indent"
fi

dup=$(cat <<'EOF'
local util = require("tstapler.util")
util.map("n", "<leader>__smoketest__", function() end, {})
local ok1 = pcall(util.map, "n", "<leader>__smoketest__", function() end, {})
local ok2 = pcall(util.reserve, "n", "<leader>__smoketest__")
print("DUP_REJECTED=" .. tostring(not ok1) .. " RESERVE_SHARES=" .. tostring(not ok2))
EOF
)
dup_out=$(nv -c "lua $dup" -c 'qa')
if echo "$dup_out" | grep -q "DUP_REJECTED=true RESERVE_SHARES=true"; then
  ok "safe-map: rejects duplicate binds, reserve() shares the registry"
else
  bad "safe-map: rejects duplicate binds, reserve() shares the registry" "$dup_out"
fi

echo
echo "-- deletions / cfgcaddy cleanup --"

repo_root="$(cd "$NVIM_CONFIG_DIR/../.." && pwd)"
# Only flag FUNCTIONAL references (source/require/dofile/readfile) — bare
# textual mentions are expected in provenance comments (e.g. "ported from
# .vimrc.dein 185-189" in options.lua/autocmds.lua), not a real regression.
legacy=$(grep -rniE "(source|require|dofile|readfile)[^\n]*(vimrc\.local|vimrc\.bundles\.local|vimrc\.plug|vimrc\.dein)" "$repo_root" \
  --include='*' 2>/dev/null | grep -v '/project_plans/' | grep -v '/\.git/' | grep -v '/\.config/nvim/tests/')
if [ -z "$legacy" ]; then
  ok "legacy vimrc.* files fully deleted (no functional source/require refs)"
else
  bad "legacy vimrc.* files fully deleted (no functional source/require refs)" "$legacy"
fi

if [ -f "$repo_root/.cfgcaddy.yml" ] && grep -q "init.vim" "$repo_root/.cfgcaddy.yml"; then
  bad "cfgcaddy.yml has zero init.vim references"
else
  ok "cfgcaddy.yml has zero init.vim references"
fi

if [ -f "$NVIM_CONFIG_DIR/coc-settings.json" ]; then
  bad "coc-settings.json deleted"
else
  ok "coc-settings.json deleted"
fi

if [ -f "$repo_root/.vimrc" ] && ! grep -q "source ~/.vimrc.dein" "$repo_root/.vimrc" \
  && grep -q "plain-vim fallback only" "$repo_root/.vimrc"; then
  ok ".vimrc fallback: no dein source, has fallback header"
else
  bad ".vimrc fallback: no dein source, has fallback header"
fi

echo
echo "-- plugin tree audits --"

if grep -q "tpope/vim-surround" "$NVIM_CONFIG_DIR/lua/tstapler/plugins/editing.lua" 2>/dev/null \
  && grep -q "tpope/vim-repeat" "$NVIM_CONFIG_DIR/lua/tstapler/plugins/editing.lua" 2>/dev/null; then
  ok "vim-surround kept alongside vim-repeat"
else
  bad "vim-surround kept alongside vim-repeat"
fi

legacy_plugins=$(grep -rln "w0rp/ale\|neoinclude\|neco-syntax\|neco-vim\|neco-look\|context_filetype\|vim-autoformat\|rust-tools.nvim\|simrat39" \
  "$NVIM_CONFIG_DIR/lua/tstapler/plugins/" 2>/dev/null)
if [ -z "$legacy_plugins" ]; then
  ok "ale / coc-completion-source / rust-tools.nvim absent from plugin tree"
else
  bad "ale / coc-completion-source / rust-tools.nvim absent from plugin tree" "$legacy_plugins"
fi

if grep -rq 'mason/bin/dlv' "$NVIM_CONFIG_DIR/lua/tstapler/plugins/lang/go.lua" 2>/dev/null; then
  ok "Go DAP adapter path is hardcoded, not \$PATH-dependent"
else
  bad "Go DAP adapter path is hardcoded, not \$PATH-dependent"
fi

echo
echo "-- treesitter --"

th=$(nvim --headless "$repo_root/.config/nvim/lua/tstapler/plugins/treesitter.lua" -c 'checkhealth nvim-treesitter' -c 'w! /tmp/.nvn_smoketest_health.txt' -c 'qa' 2>&1)
if grep -qE '^\s*-\s+lua\s+.*✓' /tmp/.nvn_smoketest_health.txt 2>/dev/null; then
  ok "treesitter: lua parser installed and healthy"
else
  bad "treesitter: lua parser installed and healthy" "run with --fresh and retry; parsers may still be downloading"
fi
rm -f /tmp/.nvn_smoketest_health.txt

echo
echo "-- per-language LSP: real cross-file attach + gd navigation --"
echo "   (uses the fixture apps in tests/fixtures/ — real multi-module/"
echo "    multi-package projects, not throwaway single-file stubs. Checks"
echo "    ACTUAL client attach via vim.lsp.get_clients(), not just"
echo "    vim.lsp.is_enabled() — is_enabled only proves the config is"
echo "    registered, not that the server binary exists/attaches.)"

FIXTURES="$NVIM_CONFIG_DIR/tests/fixtures"

lsp_probe=$(cat <<EOF
-- CI run #6 showed WHY the rust gd raw-result dump was landing empty even
-- after fixing its earlier bugs: 'more' triggers a --More-- prompt once a
-- message spans enough screen lines, and headless Neovim silently drops
-- everything past that point instead of blocking (no TTY to advance it).
-- rust-analyzer's definition response, vim.inspect()'d, is comfortably
-- past that line count. Disable it for this whole probe.
vim.o.more = false
-- IMPORTANT: open each file with :edit exactly ONCE. A redundant :edit on
-- an already-open buffer (even the same unmodified file) was found to
-- detach the LSP client from that buffer — the client re-attaches to the
-- NEW buffer instance via LspAttach, but not within a few seconds, so an
-- immediately-following vim.lsp.buf.definition() call silently no-ops.
-- Confirmed empirically: wait_attach()+gd_to() as two separate functions
-- that each called :edit on the same file intermittently broke gd; folding
-- file-open into one open_once() call fixed it reliably.
local function open_once(file)
  if vim.api.nvim_buf_get_name(0) ~= file then
    vim.cmd("edit " .. file)
  end
  return vim.api.nvim_get_current_buf()
end

local function wait_client(bufnr, name, timeout, settle, wait_idle)
  local attached = vim.wait(timeout or 10000, function()
    return #vim.lsp.get_clients({ bufnr = bufnr, name = name }) > 0
  end, 200)
  print(name .. "_attached=" .. tostring(attached))
  -- vtsls/rust-analyzer report "attached" before their project/workspace
  -- graph is fully loaded — an immediate gd right after attach can silently
  -- return nothing even though the same request succeeds a few seconds
  -- later. gopls/basedpyright didn't need this at all; rust-analyzer's
  -- first-ever cold index of a workspace needed ~20s beyond attach,
  -- confirmed empirically (the raw LSP request itself was always correct —
  -- this is purely "give it time to finish indexing", not a config bug).
  vim.wait(settle or 2000)
  -- 8 real CI runs on rust-analyzer specifically: attached, correct
  -- root_dir, analyzerStatus reports a healthy loaded crate graph — but gd
  -- still deterministically empty regardless of any fixed settle delay.
  -- "crate graph loaded" (cargo metadata) and "fully indexed" (crate
  -- def-map / name resolution, needed for cross-crate go-to-def) are two
  -- separate async stages; the fixed settle can't distinguish "still
  -- indexing" from "never going to resolve". client.progress.pending is
  -- nvim's own tracking of in-flight $/progress operations (set on
  -- "begin", cleared on "end" — see runtime/lua/vim/lsp/handlers.lua) —
  -- poll it directly instead of guessing elapsed time a 5th way.
  if wait_idle and attached then
    local client = vim.lsp.get_clients({ bufnr = bufnr, name = name })[1]
    if client then
      local idle = vim.wait(timeout or 10000, function()
        return next(client.progress.pending) == nil
      end, 300)
      print(name .. "_progress_idle=" .. tostring(idle))
    end
  end
  return attached
end

local function gd(bufnr, line, col, expect_suffix, label)
  vim.api.nvim_set_current_buf(bufnr)
  vim.api.nvim_win_set_cursor(0, { line, col })
  -- CI's real raw-LSP dump (run #8) proved the rust-analyzer failure here
  -- was a genuine timing race, not a client bug or config mistake: the
  -- server answered with zero error but result = {} — it just hadn't
  -- finished indexing this workspace yet, despite wait_client()'s fixed
  -- settle delay already having elapsed. A single settle-then-try can't
  -- reliably distinguish "will never resolve" from "resolves 2s later" —
  -- retry the actual navigation attempt (the real signal we care about)
  -- instead of guessing a bigger fixed delay a 4th time.
  local ok, landed
  for _ = 1, 5 do
    vim.lsp.buf.definition()
    vim.wait(6000)
    landed = vim.api.nvim_buf_get_name(0)
    ok = landed:sub(-#expect_suffix) == expect_suffix
    if ok then
      break
    end
    vim.api.nvim_set_current_buf(bufnr)
    vim.api.nvim_win_set_cursor(0, { line, col })
  end
  print(label .. "_gd=" .. tostring(ok) .. " landed=" .. landed)
  if not ok then
    -- On failure, dump the RAW LSP response directly — this distinguishes
    -- "the server hadn't finished indexing yet" (empty/nil result, a
    -- timing problem — bump the wait_client settle window) from "the
    -- server answered correctly but vim.lsp.buf.definition() didn't
    -- navigate" (a real client-side bug, e.g. the redundant-:edit-detaches-
    -- the-client class of bug found earlier this session — see open_once()
    -- above). Guessing between these from pass/fail alone wasted three real
    -- CI round-trips on a different check; do this properly from the start.
    local clients = vim.lsp.get_clients({ bufnr = bufnr })
    local client_names = {}
    for _, c in ipairs(clients) do
      table.insert(client_names, c.name)
    end
    print(label .. "_gd_debug_clients=" .. table.concat(client_names, ","))
    if clients[1] then
      -- CI run #4 showed the clients= line print but NOT this one; run #5
      -- (after wrapping in pcall) revealed why: make_position_params()'s
      -- first arg is a WINDOW id on this Neovim version, not a bufnr — we
      -- were passing bufnr (e.g. 7), which doesn't resolve to any window
      -- ("Invalid window id: 7"). gd() already made this buffer current in
      -- window 0 above, so pass 0 (current window) instead. Fixed for run
      -- #6 — but run #6 (and #7 with 'more' disabled) both showed the dump
      -- landing as a bare "{" with nothing after: the print()/message
      -- system itself drops multi-line content in headless mode somewhere
      -- past the first line, independent of 'more'. Stop routing this
      -- through print() at all — write it straight to a file instead.
      local dump_ok, dump_err = pcall(function()
        local params = vim.lsp.util.make_position_params(0, clients[1].offset_encoding)
        local results, err = vim.lsp.buf_request_sync(bufnr, "textDocument/definition", params, 8000)
        -- CI run #11 refuted the root_dir hypothesis — it resolves to the
        -- correct Cargo workspace root in CI too, identical to local. 6
        -- straight real CI runs now: attached client, correct root_dir,
        -- zero error, deterministic "result = {}" regardless of wait time,
        -- retries, or freed-up CPU. Next real signal: rust-analyzer's own
        -- status. rust-analyzer/analyzerStatus is a custom request that
        -- reports whether its internal cargo-metadata-based crate graph
        -- actually loaded — if cargo/rustc weren't resolvable on PATH from
        -- wherever headless nvim spawned rust-analyzer, the server still
        -- attaches and answers requests, just with an empty/broken crate
        -- graph, which would produce exactly this symptom.
        local status_results = vim.lsp.buf_request_sync(
          bufnr, "rust-analyzer/analyzerStatus", { textDocument = params.textDocument }, 5000
        )
        -- Locally this is a 40KB+ blob (confirmed) — the useful part
        -- ("Workspaces:\nLoaded N packages...") is always the header, so
        -- cap it instead of dumping the whole thing into the CI log.
        local status_str = "no status client response"
        if status_results then
          for _, r in pairs(status_results) do
            if r.result then
              status_str = tostring(r.result):sub(1, 1500)
              break
            elseif r.err then
              status_str = "err: " .. vim.inspect(r.err)
            end
          end
        end
        -- Run #13's "rust-analyzer_progress_idle=" print() line never made
        -- it into the CI log at all, alongside every other plain _attached=
        -- line — turns out this whole session's "print() output vanishes
        -- in CI" mystery was never nvim's message system or 'more': GitHub
        -- Actions' own log capture collapses \r-based line overwrites
        -- (headless nvim's message redraw uses them), while bash's own
        -- $(...) capture sees the untouched raw bytes fine — which is
        -- exactly why the PASS/FAIL logic (grepping that raw $lsp_out
        -- variable) has been correct the whole time even when the CI log
        -- I can read looked broken. Route this through the file dump too.
        local progress_pending = "unknown"
        if clients[1].progress and clients[1].progress.pending then
          local tokens = {}
          for token, title in pairs(clients[1].progress.pending) do
            table.insert(tokens, tostring(token) .. "=" .. tostring(title))
          end
          progress_pending = #tokens == 0 and "none (idle)" or table.concat(tokens, ", ")
        end
        local f = io.open("/tmp/.nvn_gd_debug_" .. label .. ".log", "w")
        if f then
          f:write(
            "root_dir: " .. tostring(clients[1].config.root_dir)
            .. "\nprogress_pending: " .. progress_pending
            .. "\nresult:\n" .. vim.inspect(results)
            .. "\nerr:\n" .. vim.inspect(err)
            .. "\nanalyzerStatus:\n" .. status_str
          )
          f:close()
        end
      end)
      if not dump_ok then
        print(label .. "_gd_debug_dump_failed=" .. tostring(dump_err))
      end
    end
  end
end

local go_buf = open_once("$FIXTURES/go/app/main.go")
wait_client(go_buf, "gopls", 15000)
gd(go_buf, 13, 12, "lib/greet.go", "go")

local py_buf = open_once("$FIXTURES/python/fixture_app/main.py")
wait_client(py_buf, "basedpyright", 15000)
wait_client(py_buf, "ruff", 15000)
gd(py_buf, 10, 10, "lib.py", "python")

local ts_buf = open_once("$FIXTURES/typescript/packages/app/src/main.ts")
wait_client(ts_buf, "vtsls", 15000)
local ts_clients = vim.lsp.get_clients({ bufnr = ts_buf })
if ts_clients[1] then
  local root = ts_clients[1].config.root_dir or ""
  local nearest = root:sub(-#("typescript/packages/app")) == "typescript/packages/app"
  print("vtsls_root_is_nearest_package=" .. tostring(nearest) .. " root=" .. root)
end
gd(ts_buf, 7, 12, "lib/src/index.ts", "typescript")

-- rust-analyzer (via rustaceanvim) tends to be slower to attach on a fresh
-- workspace (compiles deps for its own analysis) — generous timeout.
--
-- UPDATE (post-review, real-CI-verified): these timeouts were tuned on a
-- local dev machine that had already run this same fixture many times
-- (warm rustup/cargo/gradle caches, fast local disk). The FIRST real
-- GitHub Actions run reproduced real failures here that never happened
-- locally — rust gd and java gd both failed even though their LSP clients
-- had already attached, because CI's network-bound cold downloads
-- (crates.io, Maven Central, GitHub release assets, no warm caches at all)
-- are meaningfully slower than anything tested locally. Bumped generously
-- rather than precisely — CI is the one place this genuinely needs slack,
-- and a few extra seconds of headroom costs nothing when the check
-- already passed almost every time.
--
-- UPDATE (4 real CI runs later): even 120s attach + 60s settle + 5x6s
-- retry still came back with a genuine "result = {}" from rust-analyzer
-- itself (proven via the file-based raw-response dump) — the server
-- answers but hasn't indexed yet, every single time, no matter how long
-- we wait. On CI's 2-core runner, gopls/basedpyright/ruff/vtsls are all
-- still attached and doing their own background work at this point,
-- competing for the same two cores rust-analyzer needs to index. Stop
-- them before starting rust — those checks already ran and recorded
-- their pass/fail, so there's nothing left for them to do.
for _, name in ipairs({ "gopls", "basedpyright", "ruff", "vtsls" }) do
  for _, c in ipairs(vim.lsp.get_clients({ name = name })) do
    c:stop(true)
  end
end
vim.wait(2000)
local rust_buf = open_once("$FIXTURES/rust/app/src/main.rs")
-- UPDATE (2nd real-CI-run data point): 90s/45s was still not enough — attach
-- passed but gd (needing actual project indexing, not just the client
-- connecting) timed out. GH Actions standard runners are 2-core/7GB, and by
-- this point in the sequence 3 other language servers (go/python/ts) are
-- still resident from earlier in this same probe — cumulative resource
-- pressure on a constrained runner, not just cold-network latency. Matching
-- jdtls's generous budget since that coped fine at this position.
wait_client(rust_buf, "rust-analyzer", 120000, 60000, true)
gd(rust_buf, 8, 14, "lib/src/lib.rs", "rust")

-- jdtls is the slowest of all six (JVM startup + Gradle project import,
-- itself needing a cold Maven Central round-trip in CI) — generous
-- timeout, same reasoning as rust-analyzer above.
local java_buf = open_once("$FIXTURES/java/src/main/java/com/example/fixture/Main.java")
wait_client(java_buf, "jdtls", 120000, 40000)
gd(java_buf, 10, 25, "fixture/Lib.java", "java")

local kotlin_buf = open_once("$FIXTURES/kotlin/src/main/kotlin/com/example/fixture/Main.kt")
wait_client(kotlin_buf, "kotlin_language_server", 90000, 30000)
gd(kotlin_buf, 8, 14, "fixture/Lib.kt", "kotlin")
EOF
)
lsp_out=$(nv -c "lua $lsp_probe" -c 'qa')

for pair in "gopls:Go" "basedpyright:Python" "ruff:Python (ruff)" "vtsls:TypeScript" "rust-analyzer:Rust" "jdtls:Java" "kotlin_language_server:Kotlin"; do
  name="${pair%%:*}"; label="${pair##*:}"
  if echo "$lsp_out" | grep -q "${name}_attached=true"; then
    ok "$label LSP ($name) actually attaches"
  else
    bad "$label LSP ($name) actually attaches" "no client attached — server binary may not be installed (run --fresh, or check :Mason)"
  fi
done

for pair in "go:Go" "python:Python" "typescript:TypeScript" "rust:Rust" "java:Java" "kotlin:Kotlin"; do
  name="${pair%%:*}"; label="${pair##*:}"
  if echo "$lsp_out" | grep -q "${name}_gd=true"; then
    ok "$label: gd jumps to the correct cross-file/cross-module definition"
  else
    debug_file="/tmp/.nvn_gd_debug_${name}.log"
    diag="$(echo "$lsp_out" | grep "${name}_gd")"
    [ -f "$debug_file" ] && diag="$diag
$(cat "$debug_file")"
    bad "$label: gd jumps to the correct cross-file/cross-module definition" "$diag"
  fi
done

if echo "$lsp_out" | grep -q "vtsls_root_is_nearest_package=true"; then
  ok "TypeScript: vtsls root_dir resolves to nearest package, not monorepo top"
else
  bad "TypeScript: vtsls root_dir resolves to nearest package, not monorepo top" "$(echo "$lsp_out" | grep "vtsls_root_is_nearest_package=")"
fi
# rustaceanvim manages rust-analyzer itself (not via vim.lsp.enable), so it's
# not checked the same way — confirmed present as a plugin spec instead.
if grep -q "mrcjkb/rustaceanvim" "$NVIM_CONFIG_DIR/lua/tstapler/plugins/lang/rust.lua" 2>/dev/null; then
  ok "Rust: rustaceanvim spec present (manages rust-analyzer itself)"
else
  bad "Rust: rustaceanvim spec present (manages rust-analyzer itself)"
fi

echo
echo "-- startup benchmark --"

times=()
for i in 1 2 3; do
  log=$(mktemp)
  nvim --headless --startuptime "$log" -c 'qa' >/dev/null 2>&1
  t=$(grep 'NVIM STARTED' "$log" | awk '{print $1}')
  [ -n "$t" ] && times+=("$t")
  rm -f "$log"
done

if [ "${#times[@]}" -eq 3 ]; then
  median=$(printf '%s\n' "${times[@]}" | sort -n | awk 'NR==2')
  echo "  runs: ${times[*]} ms   median: ${median} ms"
  if [ "$SAVE_BASELINE" = 1 ]; then
    echo "$median" > "$BASELINE_FILE"
    ok "startup benchmark (baseline saved: ${median}ms)"
  elif [ -f "$BASELINE_FILE" ]; then
    baseline=$(cat "$BASELINE_FILE")
    cmp=$(awk -v a="$median" -v b="$baseline" 'BEGIN{print (a<=b)?"1":"0"}')
    if [ "$cmp" = "1" ]; then
      ok "startup benchmark: ${median}ms <= baseline ${baseline}ms"
    else
      bad "startup benchmark: ${median}ms > baseline ${baseline}ms" "regression — check for over-eager lazy=false/VeryLazy left in from debugging"
    fi
  else
    ok "startup benchmark: ${median}ms (no baseline saved yet — run with --save-baseline)"
  fi
else
  bad "startup benchmark" "failed to capture 3 runs"
fi

echo
echo "== ${PASS} passed, ${FAIL} failed =="
if [ "$FAIL" -gt 0 ]; then
  printf 'Failed: %s\n' "${FAILED_NAMES[*]}"
  exit 1
fi
exit 0
