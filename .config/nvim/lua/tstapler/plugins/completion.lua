-- blink.cmp (Epic 2.1, Task 2.1.1b): completion engine + capabilities helper.
--
-- This file serves two purposes at once:
--   1. It's a lazy.nvim plugin-spec module, imported via
--      `import = "tstapler.plugins"` in init.lua.
--   2. It's `require`-able directly by any language epic's plugin file as
--      `require("tstapler.plugins.completion").get_capabilities()` to get
--      the LSP capabilities table blink.cmp advertises, which MUST be
--      merged into every `vim.lsp.config()` call so completion isn't stuck
--      on basic/no-completion (Domain Glossary "capabilities").
--
-- IMPORTANT shape note (found by testing against the real lazy.nvim
-- source, lua/lazy/core/plugin.lua Spec:normalize + lua/lazy/core/util.lua
-- is_list): a table like `{ spec, get_capabilities = fn }` (one array
-- element + one extra hash key) is NOT auto-detected as a spec list.
-- `is_list()` counts total pairs and requires every integer index up to
-- that count to be populated; a lone hash key alongside index 1 makes it
-- return false, so normalize() falls through to its "treat as a single
-- plugin spec" branch and crashes trying to call `:find()` on `spec[1]`
-- (which is a table, not a plugin-name string) — confirmed via a fresh
-- `NVIM_APPNAME=nvim-next` headless run ("attempt to call method 'find'
-- (a nil value)" in lazy/core/fragments.lua).
--
-- The fix: don't wrap the spec in an outer array at all. Return the plugin
-- spec table itself as the module's return value (index 1 = the plugin
-- name string, exactly like plugins/explorer.lua's single-spec return,
-- which also carries several extra non-array keys safely) and hang
-- `get_capabilities` directly off that same table. lazy.nvim's import sees
-- a normal single spec (spec[1] is a string); `require(...)` callers see a
-- table with a callable `get_capabilities` field.
--
-- Contract for downstream language epics (Go/Rust/Python/TS-JS):
--   require("tstapler.plugins.completion").get_capabilities()
--
-- Snippet expand/jump (replacing the old coc-snippets <C-l>/<C-j> binds):
-- blink.cmp's own `opts.keymap` table is the idiomatic way to set these,
-- NOT a manual map()/reserve() call through the safe-map registry — these
-- are insert-mode-only, completion-menu-scoped bindings that blink.cmp
-- manages internally, not general buffer/global keymaps. The `"default"`
-- preset already binds <Tab>/<S-Tab> to snippet_forward/snippet_backward
-- (with graceful fallback when no snippet session is active), which is
-- exactly the "sensible keys" replacement asked for, so no override is
-- specified here.

local M = {
  "saghen/blink.cmp",
  version = "*",
  opts = {
    keymap = { preset = "default" },
  },
}

function M.get_capabilities()
  return require("blink.cmp").get_lsp_capabilities()
end

return M
