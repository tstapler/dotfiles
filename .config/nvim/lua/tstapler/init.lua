require("tstapler.options")
require("tstapler.keymaps")
require("tstapler.autocmds")

require("lazy").setup({
  { import = "tstapler.plugins" },
  { import = "tstapler.plugins.lang" },
}, {
  lockfile = vim.fn.stdpath("config") .. "/lazy-lock.json",
})
