-- Note: Konfekt/FastFold is already declared by the treesitter epic in
-- treesitter.lua — intentionally not duplicated here.
return {
  { "tpope/vim-surround", event = "VeryLazy" },
  { "tpope/vim-commentary", event = "VeryLazy" },
  -- Hard dependency of vim-surround's `.` repeat support (pitfalls.md §4) —
  -- keep even though it does little on its own.
  { "tpope/vim-repeat", event = "VeryLazy" },
  { "tpope/vim-speeddating", event = "VeryLazy" },
  { "tpope/vim-abolish", event = "VeryLazy" },
  { "mbbill/undotree", cmd = "UndotreeToggle" },
  {
    "ojroques/vim-oscyank",
    branch = "main",
    init = function()
      vim.g.oscyank_term = "default"
      vim.api.nvim_create_autocmd("TextYankPost", {
        callback = function()
          if vim.v.event.operator == "y" and vim.v.event.regname == "+" then
            vim.cmd("OSCYankReg +")
          end
        end,
      })
    end,
  },
  { "dhruvasagar/vim-table-mode", cmd = "TableModeToggle" },
  { "godlygeek/tabular", cmd = "Tabularize" },
  { "christoomey/vim-sort-motion", event = "VeryLazy" },
  { "christoomey/vim-titlecase", event = "VeryLazy" },
  { "triglav/vim-visual-increment", event = "VeryLazy" },
  { "chrisbra/NrrwRgn", cmd = { "NR", "NW", "NRV", "NRM" } },
  { "dstein64/vim-startuptime", cmd = "StartupTime" },
}
