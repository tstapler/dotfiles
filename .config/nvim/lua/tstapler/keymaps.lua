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

-- Diagnostic navigation/float — NOT LSP-specific (vim.diagnostic works with
-- no client attached), so these are plain global binds here rather than
-- buffer-local LspAttach binds like plugins/lsp.lua's <leader>cr/<leader>cf.
-- <leader>cd lives in the "code" leader group; [d/]d are the vim-idiomatic
-- bracket-motion pair for diagnostic navigation, unprefixed to match e.g.
-- ]c/[c for gitsigns hunks.
map("n", "<leader>cd", vim.diagnostic.open_float, { desc = "Line diagnostics" })
map("n", "]d", function()
  vim.diagnostic.jump({ count = 1, float = true })
end, { desc = "Next diagnostic" })
map("n", "[d", function()
  vim.diagnostic.jump({ count = -1, float = true })
end, { desc = "Prev diagnostic" })
