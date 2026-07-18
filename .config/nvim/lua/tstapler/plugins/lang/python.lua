-- Python LSP + DAP (Epic 4.1, Story 4.1.1, Tasks 4.1.1a/4.1.1b):
-- basedpyright + ruff via 0.11 native vim.lsp.config()/vim.lsp.enable(), plus
-- nvim-dap-python + mason-managed debugpy with venv resolution.
--
-- Task 4.1.1c (real-project smoke test against Tyler's asdf/direnv-managed
-- project) and Task 4.1.1d (coc-pyright teardown in autocmds.lua /
-- g:coc_global_extensions) are explicitly OUT OF SCOPE here — those need a
-- real project + manual verification and land in a follow-up pass. Nothing
-- in this file touches autocmds.lua or g:coc_global_extensions; coc.nvim
-- keeps serving Python buffers until Task 4.1.1c/d land.
--
-- Second "neovim/nvim-lspconfig" fragment note — CONFIRMED COLLISION, fixed
-- with `init` instead of `config`:
--
-- plugins/lsp.lua already owns a `config` fn on this same plugin name
-- (diagnostics + LspAttach autocmd), and plugins/lang/go.lua and
-- plugins/lang/typescript.lua (sibling epics, landed concurrently with this
-- file) EACH add their own THIRD/FOURTH "neovim/nvim-lspconfig" fragment
-- with their own `config` fn (gopls / vtsls respectively). lazy.nvim does
-- NOT combine or chain multiple fragments' `config` functions the way it
-- does for `opts`/`ensure_installed` — it resolves to exactly ONE fragment's
-- `config` (lua/lazy/core/meta.lua `M:_rebuild`, which chains fragment spec
-- tables via `setmetatable(fragment.spec, {__index = super})`; the winner
-- is whichever fragment's `config` key is reached first walking the chain,
-- and empirically that was NOT the last-imported file in this repo's
-- current alphabetical import order).
--
-- Confirmed via headless NVIM_APPNAME=nvim-next fresh-install + inspecting
-- `vim.lsp.config._configs` and `vim.lsp._enabled_configs` directly: with
-- go.lua, python.lua (this file, in its original `config`-based form),
-- typescript.lua and lsp.lua all present, ONLY typescript.lua's `config`
-- ran — `vim.lsp._enabled_configs` was `{"vtsls"}` only, `basedpyright`/
-- `ruff`/`gopls` were never registered, and lsp.lua's diagnostics/LspAttach
-- autocmd never fired (`nvim_get_autocmds({group="tstapler-lsp-attach"})`
-- errored — group didn't exist). Every other language's LSP setup was
-- silently a no-op.
--
-- Fix used here: register via `init` instead of `config`. lazy.nvim always
-- runs every fragment's `init` unconditionally at startup (docs: "Init
-- functions are always executed during startup... even when the plugin
-- loading is disabled") — same mechanism plugins/lang/rust.lua already
-- relies on for `vim.g.rustaceanvim` — and, as of this fix, this file is the
-- ONLY fragment setting `init` on "neovim/nvim-lspconfig" (go.lua/
-- typescript.lua/lsp.lua all use `config`), so there's no competing `init`
-- to lose a resolution race against. `vim.lsp.config()`/`vim.lsp.enable()`
-- are pure data-registration calls with no dependency on nvim-lspconfig
-- having actually loaded yet (verified against Neovim's own
-- runtime/lua/vim/lsp.lua: `vim.lsp.config(name, cfg)` just writes into an
-- internal table; the merge with nvim-lspconfig's bundled `lsp/<name>.lua`
-- defaults happens lazily on first *read*, well after startup) — running
-- from `init` is if anything MORE correct than `config` here, since it
-- guarantees `vim.lsp.enable()`'s internal FileType autocmd is registered
-- before the very first real buffer's FileType event, avoiding the
-- classic "autocmd created mid-dispatch doesn't fire for the in-flight
-- event" race that a ft-gated (`ft = "python"`) registration would hit for
-- a `.py` file opened straight from the command line.
--
-- UPDATE (post-review, coordinator pass): the `init`-vs-`config` race
-- described above was a stopgap, not the structural fix. All four language
-- files now register their LSP setup through a uniquely-named `virtual`
-- plugin instead of adding a fragment to the shared "neovim/nvim-lspconfig"
-- plugin (see lang/go.lua's `tstapler-lang-go-lsp` for the full rationale) —
-- since the name is unique to this file, its `config` key can never be
-- silently dropped by, or silently drop, lsp.lua's or a sibling language
-- file's own fragment. lsp.lua's diagnostics/LspAttach wiring, gopls,
-- basedpyright/ruff, and vtsls now all register independently and
-- correctly — verified empirically with all four lang files present
-- together (see coordinator verification notes).
return {
  {
    "tstapler-lang-python-lsp",
    virtual = true,
    ft = "python",
    config = function()
      local capabilities = require("tstapler.plugins.completion").get_capabilities()
      local root_markers = { "pyproject.toml", "setup.py", "setup.cfg", ".git" }

      vim.lsp.config("basedpyright", {
        capabilities = capabilities,
        root_markers = root_markers,
      })
      vim.lsp.config("ruff", {
        capabilities = capabilities,
        root_markers = root_markers,
      })
      vim.lsp.enable({ "basedpyright", "ruff" })
    end,
  },
  {
    "mason-org/mason-lspconfig.nvim",
    opts = { ensure_installed = { "basedpyright", "ruff" } },
    opts_extend = { "ensure_installed" },
  },
  {
    "mfussenegger/nvim-dap-python",
    ft = "python",
    dependencies = { "mfussenegger/nvim-dap" },
    config = function()
      local debugpy_path = vim.fn.stdpath("data") .. "/mason/packages/debugpy/venv/bin/python"
      local dap_python = require("dap-python")
      dap_python.setup(debugpy_path)

      -- UPDATE (post-review, breakpoint-verified interactively): dap-python's
      -- built-in "file"/"file:args" configs (just registered above by
      -- setup()) launch via `program = "${file}"` — direct script execution,
      -- NOT `python -m` — which only adds the script's OWN directory to
      -- sys.path. Any project using absolute intra-package imports (e.g.
      -- `from mypkg.sub import x` executed from a script living inside
      -- mypkg itself) hits `ModuleNotFoundError` unless the project root is
      -- also on PYTHONPATH. Confirmed empirically: the Python fixture's
      -- main.py (`from fixture_app.lib import ...`) failed exactly this way
      -- until this fix — headless testing couldn't have caught it, since it
      -- only ever checked LSP attach/gd, never actually ran a debug session.
      -- Patch every config setup() just registered to add the project root
      -- (nearest pyproject.toml/setup.py/.git — the same root_markers
      -- basedpyright already uses) to PYTHONPATH, so the default "file"
      -- launch works for package-style projects without Tyler needing to
      -- discover or hand-pick a different config each time.
      for _, cfg in ipairs(require("dap").configurations.python or {}) do
        if not cfg.env then
          cfg.env = function()
            local bufdir = vim.fn.expand("%:p:h")
            local root = vim.fs.root(bufdir, { "pyproject.toml", "setup.py", "setup.cfg", ".git" }) or bufdir
            local existing = vim.env.PYTHONPATH
            return { PYTHONPATH = existing and (root .. ":" .. existing) or root }
          end
        end
      end

      -- Venv resolution for the debuggee interpreter (NOT the debugpy
      -- adapter interpreter above, which always runs from mason's own
      -- venv). `resolve_python` is dap-python's own documented extension
      -- point (lua/dap-python.lua `get_python_path()`): it's consulted
      -- AFTER $VIRTUAL_ENV / $CONDA_PREFIX and BEFORE dap-python's built-in
      -- venv/.venv/env/.env directory search relative to the project root.
      --
      -- Why that built-in fallback chain isn't enough on its own (Story
      -- 4.1.1's explicit poetry/pipenv acceptance criterion): poetry and
      -- pipenv both default to storing the venv OUTSIDE the project
      -- directory (e.g. ~/.cache/pypoetry/virtualenvs/<name>-<hash>), so
      -- dap-python's root-relative venv/.venv search finds nothing there —
      -- and if $VIRTUAL_ENV also isn't set (nvim launched from a shell that
      -- never ran `poetry shell`/`pipenv shell`, or asdf/direnv didn't
      -- inject it for this pane), dap-python silently falls back to the
      -- `python_path` passed to setup() above: mason's debugpy venv, i.e.
      -- effectively system Python from the debuggee's point of view. This
      -- hook asks poetry/pipenv directly before that happens.
      -- NOTE: poetry's `-C/--directory` is a global option that must precede
      -- the subcommand (`poetry -C <dir> env info --path`, NOT
      -- `poetry env info --path --directory <dir>`) — use vim.system's
      -- `cwd` opt instead of relying on that flag at all, so this doesn't
      -- depend on which poetry CLI version/flag-order Tyler has installed.
      local function run(cmd, cwd)
        local ok, result = pcall(function()
          return vim.system(cmd, { cwd = cwd, text = true }):wait()
        end)
        if not ok or result.code ~= 0 then
          return nil
        end
        local out = vim.trim(result.stdout or "")
        return out ~= "" and out or nil
      end

      dap_python.resolve_python = function()
        local venv = vim.env.VIRTUAL_ENV
        if venv and venv ~= "" then
          return venv .. "/bin/python"
        end

        local bufdir = vim.fn.expand("%:p:h")
        local root = vim.fs.root(bufdir, { "pyproject.toml", "poetry.lock", "Pipfile", ".git" }) or bufdir

        if vim.fn.filereadable(root .. "/poetry.lock") == 1 or vim.fn.filereadable(root .. "/pyproject.toml") == 1 then
          local out = run({ "poetry", "env", "info", "--path" }, root)
          if out and vim.fn.isdirectory(out) == 1 then
            return out .. "/bin/python"
          end
        end

        if vim.fn.filereadable(root .. "/Pipfile") == 1 then
          local out = run({ "pipenv", "--venv" }, root)
          if out and vim.fn.isdirectory(out) == 1 then
            return out .. "/bin/python"
          end
        end

        local local_venv = root .. "/.venv/bin/python"
        if vim.fn.executable(local_venv) == 1 then
          return local_venv
        end

        return vim.fn.exepath("python3")
      end
    end,
  },
  {
    "jay-babu/mason-nvim-dap.nvim",
    opts = { ensure_installed = { "python" } },
    opts_extend = { "ensure_installed" },
  },
}
