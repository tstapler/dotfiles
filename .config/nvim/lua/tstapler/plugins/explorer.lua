local map = require("tstapler.util").map

return {
  "stevearc/oil.nvim",
  lazy = false,
  opts = {},
  keys = {},
  config = function(_, opts)
    require("oil").setup(opts)
    map("n", "-", "<CMD>Oil<CR>", { desc = "Open parent directory" })
    map("n", "<C-e>", function()
      require("oil").toggle_float()
    end, { desc = "Toggle oil explorer" })
  end,
}
