local map = require("tstapler.util").map
local reserve = require("tstapler.util").reserve

-- gitsigns' hunk keymaps are registered buffer-locally inside `on_attach`,
-- which fires once per buffer. Routing those through the global safe-map
-- registry would trip its duplicate-(mode,lhs) check on every second buffer,
-- since the same lhs gets legitimately re-bound per buffer. Design choice
-- (b) from the epic brief: reserve each lhs ONCE (in `config`, below — NOT
-- at this module's top level: lazy.nvim's spec-collection pass can
-- re-evaluate a spec file's top-level code on cold start, which double-fired
-- these reserve() calls and false-tripped the duplicate-bind check; `config`
-- is guaranteed by lazy.nvim to run exactly once, the first time the plugin
-- actually loads) so the "every real keymap is at least reserved" invariant
-- holds, then use raw `vim.keymap.set` with `{ buffer = bufnr }` inside
-- `on_attach` for the actual per-buffer bind.

return {
  {
    "lewis6991/gitsigns.nvim",
    event = "BufReadPre",
    opts = {
      on_attach = function(bufnr)
        local gs = package.loaded.gitsigns
        vim.keymap.set("n", "<leader>hs", gs.stage_hunk, { buffer = bufnr, desc = "Stage hunk" })
        vim.keymap.set("n", "<leader>hr", gs.reset_hunk, { buffer = bufnr, desc = "Reset hunk" })
        vim.keymap.set("n", "<leader>hp", gs.preview_hunk, { buffer = bufnr, desc = "Preview hunk" })
        vim.keymap.set("n", "<leader>hb", function()
          gs.blame_line({ full = true })
        end, { buffer = bufnr, desc = "Blame line" })
        vim.keymap.set("n", "]c", gs.next_hunk, { buffer = bufnr, desc = "Next hunk" })
        vim.keymap.set("n", "[c", gs.prev_hunk, { buffer = bufnr, desc = "Prev hunk" })
      end,
    },
    config = function(_, opts)
      reserve("n", "<leader>hs")
      reserve("n", "<leader>hr")
      reserve("n", "<leader>hp")
      reserve("n", "<leader>hb")
      reserve("n", "]c")
      reserve("n", "[c")
      require("gitsigns").setup(opts)
    end,
  },
  {
    "tpope/vim-fugitive",
    cmd = { "Git", "G" },
    keys = {},
    config = function()
      map("n", "<leader>gg", ":Git<CR>", { desc = "Fugitive status" })
    end,
  },
}
