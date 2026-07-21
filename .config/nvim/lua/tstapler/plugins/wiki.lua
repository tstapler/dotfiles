return {
  {
    "tstapler/vimwiki",
    lazy = false, -- vimwiki mis-detects filetype under ft= lazy-loading
    init = function()
      vim.g.vimwiki_table_mappings = 1
      vim.g.vimwiki_list = {
        {
          path = "~/personal-wiki/logseq/pages",
          diary_path = "~/personal-wiki/logseq/journals",
          diary_rel_path = "/diary",
          auto_tags = 1,
          auto_toc = 1,
          ext = ".md",
        },
      }
    end,
  },
  {
    "michal-h21/vim-zettel",
    dependencies = { "tstapler/vimwiki" },
    init = function()
      vim.g.zettel_format = "%y-%m-%d-%H%M-%title"
    end,
  },
}
