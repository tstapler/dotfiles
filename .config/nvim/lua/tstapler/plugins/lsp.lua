-- Native LSP core (Epic 2.1, Story 2.1.1): mason + nvim-lspconfig scaffolding.
--
-- No language server is enabled yet in this story — that's per-language work
-- in plugins/lang/*.lua (Epic 2.2+). This file only wires the parts every
-- future server needs: mason for installing tools, the LspAttach keymap
-- scaffolding, and diagnostic display config. coc.nvim and its per-language
-- extensions stay fully installed and untouched (see plan.md Epic 2.1 goal);
-- teardown is deferred to Story 2.3.3.

local map = require("tstapler.util").map
local reserve = require("tstapler.util").reserve

-- LspAttach fires once per (buffer, client) pair, so across a session it
-- fires repeatedly — the exact same hazard gitsigns' on_attach hit in Phase 1
-- (see plugins/git.lua). Fix: reserve each NEW (mode,lhs) exactly once, at
-- `config` time (lazy.nvim guarantees `config` runs exactly once per plugin
-- load — never at this file's top level, since lazy.nvim's spec-collection
-- pass can re-evaluate a spec file's top-level code on a cold start and
-- would double-fire a top-level reserve()/map() call), then bind the real
-- per-buffer keymaps with raw vim.keymap.set + { buffer = bufnr } inside the
-- LspAttach callback itself.
--
-- <leader>fs / <leader>fS are ALREADY reserved by plugins/finder.lua (Phase
-- 1 fzf-lua spec deliberately pre-reserved them for this exact story) — do
-- NOT reserve() them again here, only bind them with raw vim.keymap.set
-- below. gd / gy / <leader>cr / <leader>cf / <leader>ci are new in this
-- story, so they get reserve()'d once.
--
-- <leader>c* here is the "code" leader group (leader_groups.lua) — rename,
-- format, and inlay-hint toggle are genuinely LSP-dependent (no-op without
-- an attached client), so they're bound buffer-locally via LspAttach like
-- gd/gy, not as always-present global binds. Diagnostic navigation/float
-- (<leader>cd, [d/]d) are NOT LSP-specific — vim.diagnostic works without
-- any client attached — so those live in keymaps.lua as plain global binds
-- instead, not gated behind this autocmd.
local function on_lsp_attach(args)
  local bufnr = args.buf
  local client = vim.lsp.get_client_by_id(args.data.client_id)

  local function opts(desc)
    return { buffer = bufnr, desc = desc }
  end

  -- 0.11 native defaults (grn, gra, grr, gri, grt, gO, K) are left alone —
  -- they're Neovim built-ins already, no binding needed here.
  vim.keymap.set("n", "gd", vim.lsp.buf.definition, opts("LSP: goto definition"))
  vim.keymap.set("n", "gy", vim.lsp.buf.type_definition, opts("LSP: goto type definition"))
  vim.keymap.set("n", "<leader>fs", function()
    require("fzf-lua").lsp_document_symbols()
  end, opts("LSP: document symbols"))
  vim.keymap.set("n", "<leader>fS", function()
    require("fzf-lua").lsp_live_workspace_symbols()
  end, opts("LSP: workspace symbols"))

  vim.keymap.set("n", "<leader>cr", vim.lsp.buf.rename, opts("LSP: rename"))
  vim.keymap.set("n", "<leader>cf", function()
    vim.lsp.buf.format({ async = true })
  end, opts("LSP: format buffer"))

  if client and client:supports_method("textDocument/inlayHint") then
    vim.lsp.inlay_hint.enable(true, { bufnr = bufnr })
    vim.keymap.set("n", "<leader>ci", function()
      local enabled = vim.lsp.inlay_hint.is_enabled({ bufnr = bufnr })
      vim.lsp.inlay_hint.enable(not enabled, { bufnr = bufnr })
    end, opts("LSP: toggle inlay hints"))
  end
end

return {
  {
    "mason-org/mason.nvim",
    opts = {},
    config = function(_, opts)
      require("mason").setup(opts)

      -- Task 2.1.1d: surface install failures instead of a silent hang.
      --
      -- Verified against mason.nvim's actual source (lua/mason-core/installer/
      -- InstallRunner.lua): on install failure the *package* emits
      -- "install:failed" and the *registry* emits "package:install:failed",
      -- both with (package, result) — `result` is the failed mason.Result,
      -- tostring()-able for a human-readable error. This matches the event
      -- name the task brief guessed, no substitution needed.
      local ok, mason_registry = pcall(require, "mason-registry")
      if ok then
        mason_registry:on("package:install:failed", function(pkg, result)
          vim.notify(
            string.format(
              "Mason failed to install %s: %s (check network connectivity / GitHub rate limits)",
              pkg.name,
              tostring(result)
            ),
            vim.log.levels.ERROR
          )
        end)
      end
    end,
  },
  {
    "mason-org/mason-lspconfig.nvim",
    dependencies = { "mason-org/mason.nvim", "neovim/nvim-lspconfig" },
    -- No ensure_installed yet — per-language epics (2.2 Go, Rust, Python,
    -- TS-JS) add their own server names here.
    opts = {},
  },
  {
    "neovim/nvim-lspconfig",
    config = function()
      -- ux.md §2: enable diagnostics explicitly rather than relying on
      -- Neovim's own defaults. virtual_text=false here: plugins/diagnostics.lua
      -- (tiny-inline-diagnostic.nvim) owns the actual inline rendering — see
      -- that file for why this key can't be safely set from two places.
      vim.diagnostic.config({ virtual_text = false, signs = true })

      reserve("n", "gd")
      reserve("n", "gy")
      -- <leader>fs / <leader>fS already reserved by plugins/finder.lua.
      reserve("n", "<leader>cr")
      reserve("n", "<leader>cf")
      reserve("n", "<leader>ci")

      vim.api.nvim_create_autocmd("LspAttach", {
        group = vim.api.nvim_create_augroup("tstapler-lsp-attach", { clear = true }),
        callback = on_lsp_attach,
      })
    end,
  },
  -- Story 2.1.2: code-action popup, overriding native `gra`.
  {
    "rachartier/tiny-code-action.nvim",
    event = "LspAttach",
    opts = {},
    config = function(_, opts)
      require("tiny-code-action").setup(opts)

      -- `gra` is Neovim 0.11's own built-in default and was deliberately
      -- NOT registered via map()/reserve() above (Task 2.1.1a note) — this
      -- is the first-ever registration of (n, "gra") in the collision
      -- table, so no duplicate-bind error fires here.
      local code_action = require("tiny-code-action").code_action
      map("n", "gra", code_action, { desc = "Code action (popup)" })
      map("n", "<leader>a", code_action, { desc = "Code action (popup)" })
    end,
  },
}
