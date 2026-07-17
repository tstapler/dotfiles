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
  out=$(nv -c 'Lazy! sync' -c 'TSUpdateSync' \
    -c 'MasonInstall gopls basedpyright ruff vtsls' \
    -c 'sleep 30' -c 'qa')
  if echo "$out" | grep -qE 'Error detected|stack traceback|Failed to load|E5108|E5113'; then
    bad "fresh install: zero errors" "$(echo "$out" | grep -iE 'error|traceback' | grep -v remote: | head -3)"
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
echo "-- per-language LSP registration (needs real go.mod/tsconfig scratch dirs) --"
echo "   (checks ACTUAL client attach, not just vim.lsp.is_enabled() —"
echo "    is_enabled only proves the config is registered, not that the"
echo "    server binary exists/attaches; see the --fresh comment above for"
echo "    why that distinction bit us once already)"

probe_dir=$(mktemp -d)
mkdir -p "$probe_dir/go" "$probe_dir/ts"
cat > "$probe_dir/go/go.mod" <<'EOF'
module smoketest

go 1.21
EOF
echo 'package main' > "$probe_dir/go/main.go"
echo '{}' > "$probe_dir/ts/package.json"
echo 'const x = 1;' > "$probe_dir/ts/main.ts"
echo 'def f(): pass' > "$probe_dir/probe.py"
echo 'fn main() {}' > "$probe_dir/probe.rs"

lsp_probe=$(cat <<EOF
local function attach_check(file, name)
  vim.cmd("edit " .. file)
  local bufnr = vim.api.nvim_get_current_buf()
  local attached = vim.wait(10000, function()
    return #vim.lsp.get_clients({ bufnr = bufnr, name = name }) > 0
  end, 200)
  print(name .. "=" .. tostring(attached))
end
attach_check("$probe_dir/go/main.go", "gopls")
attach_check("$probe_dir/probe.py", "basedpyright")
attach_check("$probe_dir/probe.py", "ruff")
attach_check("$probe_dir/ts/main.ts", "vtsls")
EOF
)
lsp_out=$(nv -c "lua $lsp_probe" -c 'qa')
rm -rf "$probe_dir"

for pair in "gopls:Go" "basedpyright:Python" "ruff:Python (ruff)" "vtsls:TypeScript"; do
  name="${pair%%:*}"; label="${pair##*:}"
  if echo "$lsp_out" | grep -q "${name}=true"; then
    ok "$label LSP ($name) actually attaches"
  else
    bad "$label LSP ($name) actually attaches" "no client attached within 10s — server binary may not be installed (run --fresh, or check :Mason). raw: $lsp_out"
  fi
done
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
