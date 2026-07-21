local map = require("tstapler.util").map

return {
  "ibhagwan/fzf-lua",
  cmd = "FzfLua",
  keys = {},
  config = function()
    local fzf = require("fzf-lua")
    fzf.setup({})
    map("n", "<leader>ff", fzf.files, { desc = "Find files" })
    map("n", "<leader>fg", fzf.live_grep, { desc = "Live grep" })
    map("n", "<leader>fb", fzf.buffers, { desc = "Buffers" })
    map("n", "<leader>fr", fzf.oldfiles, { desc = "Recent files" })
    map("n", "<leader>fh", fzf.helptags, { desc = "Help tags" })
    map("n", "<leader>fd", fzf.diagnostics_document, { desc = "Diagnostics" })

    -- <leader>fs / <leader>fS are reserved for the LSP phase (document/workspace
    -- symbols) — a different epic. Reserve them here so the safe-map collision
    -- table catches accidental reuse before that epic lands.
    require("tstapler.util").reserve("n", "<leader>fs")
    require("tstapler.util").reserve("n", "<leader>fS")
  end,
}
