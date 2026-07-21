-- Epic 2.3, Story 2.3.1 / Task 2.3.1a: shared nvim-dap core stack.
--
-- Establishes the DAP pattern every language epic reuses: nvim-dap itself,
-- dap-ui (+ its hard dep nvim-nio), dap-virtual-text, and mason-nvim-dap as
-- the Mason bridge for DAP adapters (distinct from mason-lspconfig.nvim,
-- which only bridges LSP servers — Pattern Decisions "DAP client").
--
-- `<leader>d*` keymaps go through lazy.nvim's `keys =` force-load field
-- (Domain Glossary "lazy-loading trigger"), not a bare `vim.keymap.set` call,
-- so a breakpoint set via `<leader>db` before nvim-dap has loaded still
-- force-loads the plugin first and binds correctly (pitfalls.md §2, Story
-- 2.3.1 AC three).
--
-- reserve()-in-IIFE decision: TRIED, then DROPPED after empirical fresh-
-- install testing found a real collision — not the theoretical git.lua-style
-- one. lazy.nvim's `Spec:import` (lua/lazy/core/plugin.lua `Spec:import`)
-- does NOT `require()` each spec module (which would dedupe via
-- `package.loaded`); it `loadfile()`s and calls each module chunk directly.
-- On a genuine first-ever run — `rm -rf` of nvim-next's data/state dirs,
-- then a single headless launch — lazy.nvim clones all the newly-declared
-- plugins (nvim-dap, nvim-dap-ui, mason-nvim-dap, etc.) and then reloads the
-- full spec afterward to pick up the newly-available plugins' config, which
-- calls this module's chunk a SECOND time in the same process. A bare
-- top-level `reserve()` (or one wrapped in an IIFE run at spec-collection
-- time, which has identical timing) fires twice in that scenario and trips
-- the registry against itself:
--   E5113: .../tstapler/util.lua:10: duplicate keymap: n <leader>db
--   stack: util.lua:52 reserve -> dap.lua:59 -> dap.lua:62 (module chunk)
--     -> tstapler/init.lua:5 -> nvim/init.lua:20
-- Reproduced with `rm -rf ~/.local/share/nvim-next ~/.local/state/nvim-next
-- && NVIM_APPNAME=nvim-next nvim --headless -c 'qa'` — a plain, single,
-- ordinary startup, not a contrived double-load. Per the task brief's own
-- fallback guidance for exactly this outcome, the reserve() calls are
-- dropped; the `<leader>d*` binds still get lazy.nvim's own cross-plugin
-- `keys=` lhs-uniqueness enforcement (which errors if a DIFFERENT plugin's
-- `keys=` claims the same lhs), just not the same-file/re-execution
-- protection the safe-map registry provides elsewhere. No other file in the
-- tree declares any `<leader>d*` lhs (verified via grep), so this is a safe
-- reduction in guarantees, not an open collision.

local function continue_or_warn()
  local dap = require("dap")
  local ft = vim.bo.filetype
  local configs = dap.configurations[ft]
  if not configs or #configs == 0 then
    vim.notify("No DAP config for filetype: " .. ft, vim.log.levels.WARN)
    return
  end
  dap.continue()
end

return {
  {
    "mfussenegger/nvim-dap",
    keys = {
      { "<leader>db", function() require("dap").toggle_breakpoint() end, desc = "Toggle breakpoint" },
      { "<leader>dc", continue_or_warn, desc = "Continue/Launch" },
      { "<leader>di", function() require("dap").step_into() end, desc = "Step into" },
      { "<leader>do", function() require("dap").step_over() end, desc = "Step over" },
      { "<leader>dO", function() require("dap").step_out() end, desc = "Step out" },
      { "<leader>dr", function() require("dap").repl.open() end, desc = "REPL" },
      { "<leader>du", function() require("dapui").toggle() end, desc = "Toggle dap-ui" },
    },
  },
  {
    "rcarriga/nvim-dap-ui",
    dependencies = { "mfussenegger/nvim-dap", "nvim-neotest/nvim-nio" },
    config = function()
      local dap, dapui = require("dap"), require("dapui")
      dapui.setup()
      dap.listeners.after.event_initialized["dapui_config"] = function()
        dapui.open()
      end
      dap.listeners.before.event_terminated["dapui_config"] = function()
        dapui.close()
      end
      dap.listeners.before.event_exited["dapui_config"] = function()
        dapui.close()
      end
    end,
  },
  { "nvim-neotest/nvim-nio" },
  {
    "theHamsta/nvim-dap-virtual-text",
    dependencies = { "mfussenegger/nvim-dap" },
    opts = {},
  },
  {
    "jay-babu/mason-nvim-dap.nvim",
    dependencies = { "mason-org/mason.nvim", "mfussenegger/nvim-dap" },
    opts = {
      ensure_installed = {}, -- language files (go.lua, rust.lua, python.lua, typescript.lua) extend this via opts_extend
      handlers = {},
    },
    opts_extend = { "ensure_installed" },
  },
}
