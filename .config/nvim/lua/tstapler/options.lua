-- Editor options ported from the legacy .vimrc / .vimrc.plug / .vimrc.dein.
-- Vim-only compatibility branches (t_Co, ttymouse, inccommand existence guard,
-- shell detection) are intentionally dropped — see Epic 1.2 in
-- project_plans/neovim-hardening/implementation/plan.md.

vim.opt.mouse = "a"
vim.opt.showcmd = true
vim.opt.magic = true
vim.opt.wildmenu = true
vim.opt.wildmode = "longest:list,full"
vim.opt.incsearch = true
vim.opt.number = true
vim.opt.laststatus = 2
vim.opt.autoread = true
vim.opt.listchars = { eol = "$", tab = ">-", trail = "~", extends = ">", precedes = "<" }
vim.opt.undodir = vim.fn.expand("~/.undodir/")
vim.opt.undofile = true
vim.opt.signcolumn = "yes"
vim.opt.updatetime = 300
vim.opt.hidden = true
vim.opt.backup = false
vim.opt.writebackup = false
vim.opt.inccommand = "nosplit"
