local map = require("tstapler.util").map

return {
  {
    "junegunn/goyo.vim",
    cmd = "Goyo",
    keys = {},
    init = function()
      map("n", "<leader>z", ":Goyo<CR>", { desc = "Toggle Goyo distraction-free mode" })
    end,
  },
  { "junegunn/limelight.vim", cmd = { "Limelight", "LimelightToggle" } },
  { "amix/vim-zenroom2", cmd = "Goyo" },
  {
    "vim-pandoc/vim-pandoc",
    ft = "pandoc",
    init = function()
      vim.g["pandoc#syntax#codeblocks#embeds#langs"] = { "ruby", "iteratehaskell=lhaskell", "bash=sh", "python", "shell=sh" }
      vim.g["pandoc#syntax#conceal#blacklist"] = { "block", "codeblock_start", "codeblock_delim" }
      vim.g["pandoc#keyboard#use_default_mappings"] = 1
      vim.g["pandoc#formatting#mode"] = "sA"
      vim.g["pandoc#folding#level"] = 2
      vim.g["pandoc#folding#mode"] = "relative"
      vim.g["pandoc#after#modules#enabled"] = { "tablemode", "unite" }
      vim.g["pandoc#completion#bib#mode"] = "citeproc"
      vim.g["pandoc#folding#fold_yaml"] = 0
      vim.g["pandoc#spell#default_langs"] = { "en_us" }
      vim.g["pandoc#syntax#colorcolumn"] = 1
    end,
  },
  { "vim-pandoc/vim-pandoc-syntax", ft = "pandoc" },
  { "vim-pandoc/vim-pandoc-after", ft = "pandoc" },
  { "rhysd/vim-grammarous", cmd = "GrammarousCheck" },
  { "jamessan/vim-gnupg", event = "BufReadCmd *.gpg,*.asc,*.pgp" },
}
