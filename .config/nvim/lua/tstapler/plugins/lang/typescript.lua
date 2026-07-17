-- TypeScript/JavaScript LSP (+ optional-stretch DAP) — Epic 5.1, Story 5.1.1
-- (Task 5.1.1a) and stretch Story 5.1.2 (Task 5.1.2a).
--
-- vtsls is driven through the 0.11 native `vim.lsp.config()` /
-- `vim.lsp.enable()` path (Pattern Decisions: "LSP setup API"), same as
-- gopls/basedpyright and unlike rustaceanvim's self-managed lifecycle
-- (plugins/lang/rust.lua) — nvim-lspconfig just supplies vtsls's default
-- cmd/filetypes/settings, `vim.lsp.enable("vtsls")` turns it on.
--
-- Monorepo-aware root_dir (features.md §3, Story 5.1.1 AC): a monorepo can
-- have tsconfig.json/package.json at multiple depths (repo root AND each
-- package). `vim.fs.root(source, names)` walks UP from `source` and returns
-- the NEAREST ancestor directory containing any of `names` — i.e. it stops
-- at the first match walking upward from the buffer, which is exactly
-- "nearest package root", not the repo top-level. That's a synchronous
-- call; the `function(bufnr, on_dir)` wrapper below matches nvim-lspconfig's
-- 0.11 async root_dir shape (and leaves room for a future async marker
-- search) — on_dir(root) hands the resolved directory back to the client.
--
-- Coc.nvim teardown NOT done here: Task 5.1.1c (coc-tsserver teardown + full
-- coc.nvim removal, since TS/JS is the last language to migrate) is
-- explicitly out of scope for this pass — it requires Tyler's real-monorepo
-- smoke test (Task 5.1.1b) first. There is currently no coc.nvim spec
-- anywhere in this new Lua tree to touch anyway.
--
-- Treesitter: `typescript`/`tsx`/`javascript` parsers are already in
-- plugins/treesitter.lua's `ensure_installed` (Phase 1, already committed)
-- — not duplicated here.
--
-- UPDATE (post-review, coordinator pass): registering vtsls through a
-- second fragment on the shared "neovim/nvim-lspconfig" plugin silently
-- clobbered plugins/lsp.lua's diagnostics/LspAttach `config`, and collided
-- with the same fragment go.lua/python.lua each independently added for
-- gopls/basedpyright — lazy.nvim keeps exactly one `config`/`init` per
-- plugin name, no chaining. Fixed the same way lang/go.lua fixed it: a
-- uniquely-named `virtual = true` plugin, so this file's LSP setup can
-- never collide with anyone else's (see lang/go.lua's `tstapler-lang-go-lsp`
-- comment for the full empirical rationale).

return {
  {
    "tstapler-lang-typescript-lsp",
    virtual = true,
    ft = { "typescript", "javascript", "typescriptreact", "javascriptreact" },
    config = function()
      vim.lsp.config("vtsls", {
        capabilities = require("tstapler.plugins.completion").get_capabilities(),
        root_dir = function(bufnr, on_dir)
          local fname = vim.api.nvim_buf_get_name(bufnr)
          local root = vim.fs.root(fname, { "tsconfig.json", "package.json" })
          on_dir(root)
        end,
        settings = {
          -- vtsls/tsserver defaults parameterNames to "none" (unlike
          -- basedpyright, which defaults most hints on) — "literals" only
          -- hints call args that are literal values (numbers/strings/bools),
          -- which is the least noisy non-off setting; "all" hints every
          -- positional argument and gets loud fast.
          typescript = {
            inlayHints = {
              parameterNames = { enabled = "literals" },
              variableTypes = { enabled = true },
              propertyDeclarationTypes = { enabled = true },
              functionLikeReturnTypes = { enabled = true },
            },
          },
          javascript = {
            inlayHints = {
              parameterNames = { enabled = "literals" },
              variableTypes = { enabled = true },
              propertyDeclarationTypes = { enabled = true },
              functionLikeReturnTypes = { enabled = true },
            },
          },
        },
      })
      vim.lsp.enable("vtsls")
    end,
  },
  {
    "mason-org/mason-lspconfig.nvim",
    opts = { ensure_installed = { "vtsls" } },
    opts_extend = { "ensure_installed" },
  },

  -- Story 5.1.2 (STRETCH — do not block the plan), Task 5.1.2a: JS/TS
  -- debugging via vscode-js-debug, wired through nvim-dap.
  --
  -- UPDATE (post-review, interactively tested — real progress, NOT fully
  -- working, documented honestly per the plan's own "if fragile, defer" for
  -- this stretch goal rather than claiming success that isn't reliably
  -- there):
  --
  -- Three connection-layer bugs found and fixed, all confirmed via direct
  -- reproduction (headless testing cannot drive a debug session at all —
  -- none of these were catchable any other way):
  --   1. nvim-dap-vscode-js hardcodes the entrypoint as `<debugger_path>/
  --      out/src/vsDebugServer.js` (the old vscode-js-debug source-build
  --      layout); Mason's `js-debug-adapter` package ships a different,
  --      newer layout (`js-debug/src/dapDebugServer.js`).
  --   2. The plugin spawns the server with no port and reads its first
  --      stdout line as a bare port number; Mason's server requires an
  --      explicit port argument and prints a full sentence, not a bare
  --      number, when given one.
  --   3. Mason's server's default host ("localhost") resolves to the IPv6
  --      loopback (::1); the plugin connects to the IPv4 loopback
  --      (127.0.0.1) unconditionally — confirmed via the server's own
  --      "listening at ::1:<port>" log vs. the plugin's "Couldn't connect
  --      to 127.0.0.1:<port>: ECONNREFUSED" error.
  -- scripts/js-debug-adapter-wrapper.sh fixes all three: launches the real
  -- server on an explicit 127.0.0.1 port, polls until it's actually
  -- listening, then announces just the bare port number the plugin expects.
  --
  -- With all three fixed, launch telemetry fires cleanly and the
  -- "Couldn't connect"/"entrypoint does not exist"/"port is required"
  -- errors are all gone — but the breakpoint-stop-inspect cycle itself was
  -- NOT reliably reproduced: one run showed dap-ui's stack panel briefly
  -- displaying the correct paused frame (lib.ts:20, our breakpoint line);
  -- a repeat run with the identical setup disconnected within seconds with
  -- no stop at all and no error. `pwa-node` is a multi-session adapter (a
  -- bootstrap/parent session hands off to a child session for the actual
  -- Node process) — the inconsistent reproduction points at that handoff,
  -- not at anything this file controls. Left as-is rather than chasing
  -- adapter-internals further, per the plan's explicit stretch-goal
  -- timebox — the connection-layer fixes are real and worth keeping even
  -- though the feature isn't dependable yet.
  {
    "mxsdev/nvim-dap-vscode-js",
    ft = { "typescript", "javascript", "typescriptreact", "javascriptreact" },
    dependencies = { "mfussenegger/nvim-dap" },
    config = function()
      require("dap-vscode-js").setup({
        adapters = { "pwa-node" },
        debugger_cmd = { vim.fn.stdpath("config") .. "/scripts/js-debug-adapter-wrapper.sh" },
      })

      local dap = require("dap")
      for _, language in ipairs({ "typescript", "javascript", "typescriptreact", "javascriptreact" }) do
        dap.configurations[language] = {
          {
            type = "pwa-node",
            request = "launch",
            name = "Launch file",
            program = "${file}",
            cwd = "${workspaceFolder}",
          },
          {
            type = "pwa-node",
            request = "attach",
            name = "Attach to process",
            processId = require("dap.utils").pick_process,
            cwd = "${workspaceFolder}",
          },
        }
      end
    end,
  },
  -- Second spec fragment for "jay-babu/mason-nvim-dap.nvim" (declared with
  -- its own `config`-free `opts` in plugins/dap.lua, Epic 2.3.1) — same
  -- merge pattern plugins/lang/rust.lua uses for codelldb. A bare
  -- "mason-org/mason.nvim" `opts = { ensure_installed = {...} }` fragment
  -- (this file's previous approach) is a confirmed no-op: base mason.nvim
  -- implements no such option, only mason-lspconfig.nvim and
  -- mason-nvim-dap.nvim do.
  {
    "jay-babu/mason-nvim-dap.nvim",
    opts = { ensure_installed = { "js-debug-adapter" } },
    opts_extend = { "ensure_installed" },
  },
}
