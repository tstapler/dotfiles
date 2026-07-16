-- which-key.nvim: surfaces the <leader> group menu (find/code/debug/git/hunk/...)
-- Group labels are sourced from lua/tstapler/leader_groups.lua — the single
-- source of truth also consumed by keymaps.lua. Never hardcode the
-- prefix -> name table here.
return {
  "folke/which-key.nvim",
  event = "VeryLazy",
  config = function()
    local groups = require("tstapler.leader_groups")

    local specs = {}
    for prefix, name in pairs(groups) do
      table.insert(specs, { "<leader>" .. prefix, group = name })
    end

    require("which-key").setup({})
    require("which-key").add(specs)
  end,
}
