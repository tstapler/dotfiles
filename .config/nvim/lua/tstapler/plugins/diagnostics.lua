-- Compact inline diagnostics (IntelliJ-gap-analysis quick win #2): replaces
-- Neovim's default multi-line virtual_text diagnostic rendering with a
-- single-line, less noisy inline message — ux.md §1/features.md §4 flagged
-- the default renderer as a felt gap against IntelliJ's compact gutter
-- annotations.
--
-- virtual_text is explicitly disabled in plugins/lsp.lua's
-- vim.diagnostic.config() call (not here) — this plugin and the native
-- renderer both draw on the same line and fight visually if both are on,
-- and vim.diagnostic.config() is a single global table with no per-file
-- merge safety (unlike lazy.nvim's opts_extend), so exactly one place needs
-- to own that key. lsp.lua sets virtual_text=false once, unconditionally,
-- at its own config time; this plugin doesn't need to touch it again.
return {
  "rachartier/tiny-inline-diagnostic.nvim",
  event = "LspAttach",
  opts = {},
}
