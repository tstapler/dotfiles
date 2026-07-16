-- Epic 2.2, Story 2.2.1 / Task 2.2.1a: gopls via the Neovim 0.11 native
-- vim.lsp.config()/vim.lsp.enable() API (Domain Glossary, Pattern
-- Decisions "LSP setup API").
--
-- DEVIATION FROM THE TASK BRIEF'S LITERAL CODE (documented per instructions
-- to note deviations) — and WHY:
--
-- The brief's sample put the gopls setup inside a second
-- `{ "neovim/nvim-lspconfig", config = function() ... end }` spec table
-- declared here, alongside plugins/lsp.lua's (Epic 2.1, already committed)
-- own `"neovim/nvim-lspconfig"` spec, which already has a `config` function
-- wiring diagnostics + the `tstapler-lsp-attach` LspAttach autocmd + gd/gy
-- keymaps.
--
-- That's unsafe. Verified empirically (headless NVIM_APPNAME=nvim-next
-- probes against the live lazy.nvim source, lua/lazy/core/meta.lua
-- `Meta:_rebuild` + lua/lazy/core/loader.lua `M.config`/`M.startup`):
-- lazy.nvim merges multiple spec fragments for the same plugin name via a
-- metatable-inheritance chain, but ONLY `opts`/`cmd`/`event`/`ft`/`keys` get
-- composed across fragments (plugin.lua `M._values`, "Used for opts, cmd,
-- event, ft and keys"). Both `config` AND `init` are plain single-field
-- lookups on that chain with NO composition — whichever fragment's
-- `config`/`init` key is reached first walking the chain wins outright, and
-- every other fragment's `config`/`init` is silently dropped, no error.
-- `lua/tstapler/init.lua` imports `"tstapler.plugins"` before
-- `"tstapler.plugins.lang"`, so this is a real, live collision: as of this
-- writing, plugins/lang/typescript.lua (a sibling epic landing
-- concurrently) ALSO declares its own competing `config` fn on
-- "neovim/nvim-lspconfig" for vtsls, and a probe with both files present
-- showed lsp.lua's `tstapler-lsp-attach` augroup and gd/gy keymaps never
-- getting created — exactly the
-- "plugin_spec_keys_should_not_be_silently_overridden_across_files" failure
-- mode validation.md warns about, just on `config`/`init` instead of an
-- opts-array.
--
-- plugins/lang/python.lua (landed concurrently) hit the same collision
-- independently and worked around it by switching from `config` to `init`
-- (lazy.nvim runs every plugin's `init` unconditionally at startup,
-- loader.lua `M.startup`), reasoning that as the only fragment currently
-- using `init` on this plugin it wins by default. That's NOT a structural
-- fix, though — `init` resolves via the exact same single-winner metatable
-- chain as `config` (loader.lua `if plugin.init then plugin.init(plugin)
-- end`, one call, no fragment iteration); it only avoids the collision
-- because it's currently uncontested. python.lua's own comment predicts
-- (correctly) that go.lua/typescript.lua adopting the same `init` swap
-- would just relocate the collision rather than fix it — two more
-- "init"-claiming fragments on the same plugin name would collide with
-- python.lua's `init` and with each other the same way.
--
-- Fix used here instead: register gopls through a small `virtual = true`
-- plugin under a name nothing else declares. `virtual` is lazy.nvim's
-- documented mechanism for "spec entry with no real repo, never installed,
-- never added to the runtimepath" (lazy/types.lua; lua/lazy/core/plugin.lua
-- `M.update_state` sets `plugin._.installed = true` unconditionally for
-- virtual plugins, so there's no clone/network activity for it). Because
-- the plugin name is unique to this file, its `config` key can never be
-- silently dropped by — or silently drop — anyone else's fragment; the
-- collision is eliminated structurally rather than avoided by convention.
-- `vim.lsp.config()`/`vim.lsp.enable()` are safe to call from a lazy-loaded
-- `config` here rather than needing `init`'s "run at true startup"
-- timing: per Neovim's own runtime/lua/vim/lsp.lua, `vim.lsp.config()` just
-- writes into an internal table (the merge with nvim-lspconfig's bundled
-- `lsp/gopls.lua` defaults happens lazily on first *read*), and
-- `vim.lsp.enable()`'s FileType autocmd re-runs `doautoall FileType` for
-- already-open matching buffers once `vim.v.vim_did_enter == 1` — so
-- there's no first-buffer race even loading this late.
--
-- The mason-lspconfig.nvim entry below IS the brief's literal approach used
-- as given: it only sets `opts` (no competing `config`/`init`), and
-- `opts_extend = { "ensure_installed" }` is the correct, documented way
-- (lazy/core/plugin.lua `M._values`, the `prop .. "_extend"` list-concat
-- branch) to make lazy.nvim concatenate `ensure_installed` arrays across
-- files instead of one silently overwriting another.
return {
  {
    "tstapler-lang-go-lsp",
    virtual = true,
    ft = "go",
    config = function()
      vim.lsp.config("gopls", {
        capabilities = require("tstapler.plugins.completion").get_capabilities(),
        settings = {
          gopls = {
            gofumpt = true,
            staticcheck = true,
            usePlaceholders = true,
            completeUnimported = true,
          },
        },
        root_markers = { "go.work", "go.mod", ".git" },
      })
      vim.lsp.enable("gopls")
    end,
  },
  {
    "mason-org/mason-lspconfig.nvim",
    opts = { ensure_installed = { "gopls" } },
    opts_extend = { "ensure_installed" },
  },

  -- Epic 2.3, Story 2.3.1 / Task 2.3.1b: Go's Delve DAP adapter, the
  -- "plug-and-play" reference implementation later language epics
  -- (Rust/Python/TS-JS) follow when wiring their own DAP adapters onto the
  -- shared core in plugins/dap.lua.
  --
  -- delve's `path` is hardcoded to the mason install location rather than
  -- left as the bare "dlv" PATH lookup nvim-dap-go defaults to
  -- (pitfalls.md §2, Domain Glossary "DAP adapter") — GUI-launched Neovim
  -- instances don't reliably inherit a shell-configured PATH, so a bare
  -- command name silently fails to find the adapter in that context.
  {
    "leoluz/nvim-dap-go",
    ft = "go",
    dependencies = { "mfussenegger/nvim-dap" },
    config = function()
      require("dap-go").setup({
        dap_configurations = {
          {
            type = "go",
            name = "Debug (dlv)",
            request = "launch",
            program = "${file}",
          },
        },
        delve = {
          path = vim.fn.stdpath("data") .. "/mason/bin/dlv",
        },
      })
    end,
  },
  -- Second spec fragment for "jay-babu/mason-nvim-dap.nvim" (declared with
  -- its own `config`-free `opts` in plugins/dap.lua) — same
  -- `opts`/`opts_extend` merge pattern used throughout plugins/lang/*.lua
  -- for mason-lspconfig.nvim's `ensure_installed`.
  {
    "jay-babu/mason-nvim-dap.nvim",
    opts = { ensure_installed = { "delve" } },
    opts_extend = { "ensure_installed" },
  },
}
