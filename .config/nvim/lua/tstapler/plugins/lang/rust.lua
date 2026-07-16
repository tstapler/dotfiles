-- Rust LSP + DAP (Epic 3.1, Task 3.1.1a): rustaceanvim.
--
-- rustaceanvim owns rust-analyzer's entire LSP lifecycle itself (its own
-- internal `vim.lsp.start()` call, keyed off `ft = "rust"`) — it is NOT
-- driven through nvim-lspconfig's `setup{}` or the 0.11 native
-- `vim.lsp.config()/enable()` path (Pattern Decisions: "LSP setup API").
-- Do NOT add a parallel `require('lspconfig').rust_analyzer.setup{}` or
-- `vim.lsp.enable("rust_analyzer")` call anywhere — that would race a second
-- client into existence for the same buffer, violating the "exactly one
-- client per buffer per filetype" invariant (Domain Glossary "LSP client").
--
-- rust-analyzer itself is intentionally NOT mason-managed: it comes from
-- `rustup component add rust-analyzer` (a one-time, machine-level step
-- outside this repo — pitfalls.md §2, Pattern Decisions "rust-analyzer
-- install") so its version stays matched to the active toolchain instead of
-- drifting from whatever mason last pinned.
--
-- codelldb (the DAP adapter rustaceanvim drives via `:RustLsp debuggables`)
-- IS mason-managed, but mason-nvim-dap (the DAP-side Mason bridge) isn't in
-- the tree yet — it lands with the shared DAP core in Epic 2.3.1, a later,
-- separate task not part of this batch. Until then, request codelldb via
-- bare mason.nvim `ensure_installed`, the tool-agnostic base mechanism that
-- works standalone regardless of which later epic wires the DAP-adapter
-- plumbing on top of it. This is a second spec fragment for the same
-- "mason-org/mason.nvim" plugin already declared in plugins/lsp.lua —
-- lazy.nvim merges same-name spec fragments across files, deep-merging
-- `opts` (list-valued keys concatenated via `opts_extend`) while keeping the
-- `config` function already defined in plugins/lsp.lua.
return {
  {
    "mrcjkb/rustaceanvim",
    version = "^6",
    ft = "rust",
    init = function()
      vim.g.rustaceanvim = {
        server = {
          capabilities = require("tstapler.plugins.completion").get_capabilities(),
        },
      }
    end,
  },
  {
    "mason-org/mason.nvim",
    opts = { ensure_installed = { "codelldb" } },
    opts_extend = { "ensure_installed" },
  },
}
