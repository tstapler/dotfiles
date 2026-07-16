-- leader groups: see require('tstapler.leader_groups'), the single source of truth
local map = require("tstapler.util").map

map("n", "<F3>", ":cn<CR>", { desc = "Next quickfix" })
map("n", "<S-F3>", ":cp<CR>", { desc = "Prev quickfix" })
map("n", "Y", "y$", { desc = "Yank to end of line" })

if vim.fn.executable("zsh") == 1 then
  map("n", "<F7>", ":new term://zsh<CR>", { desc = "Open zsh terminal split" })
elseif vim.fn.executable("bash") == 1 then
  map("n", "<F7>", ":new term://bash<CR>", { desc = "Open bash terminal split" })
end
