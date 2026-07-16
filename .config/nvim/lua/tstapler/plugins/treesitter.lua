-- Treesitter (ADR-001): pinned to the frozen `master` branch, NOT `main`.
--
-- nvim-treesitter/nvim-treesitter was archived upstream on 2026-04-03 after
-- the `main` branch was rewritten to hard-require Neovim >=0.12. This config
-- targets Neovim 0.11.6 (see requirements.md + ADR-001), so `master` is the
-- only branch that loads at all. Do NOT change this to `main` — that branch
-- will not load on 0.11.6, and bumping the editor version is an explicit
-- out-of-scope decision documented in ADR-001's "Revisit trigger".
--
-- Treesitter-based folding is set here (foldmethod/foldexpr) and coexists
-- with FastFold with no special wiring beyond FastFold being present
-- (stack.md §2).

vim.opt.foldmethod = "expr"
vim.opt.foldexpr = "nvim_treesitter#foldexpr()"

return {
  {
    "nvim-treesitter/nvim-treesitter",
    branch = "master",
    build = ":TSUpdate",
    config = function()
      require("nvim-treesitter.configs").setup({
        ensure_installed = {
          "go", "rust", "python", "typescript", "tsx", "javascript",
          "lua", "vimdoc", "bash", "yaml", "json", "markdown", "markdown_inline",
        },
        auto_install = true,
        highlight = {
          enable = true,
          disable = function(lang, buf)
            -- Never attach a treesitter parser to vimwiki buffers
            -- (~/personal-wiki/logseq/pages/*.md) — protects the live wiki
            -- from an unrelated parser/highlight mismatch (pitfalls.md §3,
            -- Domain Glossary "vimwiki filetype"). Phase 7 finalizes the
            -- broader vimwiki exclusion elsewhere (autocmds.lua, wiki.lua);
            -- this is the treesitter-side guard only.
            if vim.bo[buf].filetype == "vimwiki" then
              return true
            end

            -- Size guard: skip highlighting on large generated files to
            -- avoid input lag (ADR-001 Consequences; Story 1.5.1 AC).
            local max_filesize = 100 * 1024 -- 100KB
            local ok, stats = pcall(function()
              return vim.uv.fs_stat(vim.api.nvim_buf_get_name(buf))
            end)
            if ok and stats and stats.size > max_filesize then
              return true
            end

            return false
          end,
        },
      })
    end,
  },
  {
    "nvim-treesitter/nvim-treesitter-textobjects",
    branch = "master",
    dependencies = { "nvim-treesitter/nvim-treesitter" },
  },
  {
    "Konfekt/FastFold",
  },
}
