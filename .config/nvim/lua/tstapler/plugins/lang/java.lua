-- Java LSP + DAP via nvim-jdtls (Eclipse JDT Language Server).
--
-- jdtls does NOT fit the vim.lsp.config()/vim.lsp.enable() pattern the
-- other four languages use (Go/Python/TypeScript's "virtual = true" plugin
-- pattern, or Rust's rustaceanvim self-managed lifecycle): it needs a
-- per-PROJECT workspace data directory — jdtls's own docs are explicit
-- that reusing one workspace dir across unrelated projects corrupts its
-- internal index — so `cmd` must be computed per-buffer from the detected
-- project root, not registered once globally like the other servers.
-- nvim-jdtls's `start_or_attach()`, wired through a FileType autocmd, is
-- the documented way to handle this — the same non-standard-lifecycle
-- pattern rustaceanvim already uses for Rust (see lang/rust.lua), just
-- with an extra per-project workspace-dir computation on top.
--
-- jdtls itself is intentionally requested through mason-lspconfig.nvim's
-- `ensure_installed` (not base mason.nvim, which has no such option — a
-- confirmed no-op found earlier this session for codelldb/js-debug-adapter)
-- even though it is never driven through nvim-lspconfig's setup path —
-- mason-lspconfig's ensure_installed only ensures the underlying package
-- is installed, it doesn't require actually using nvim-lspconfig to enable
-- it.
return {
  {
    "mfussenegger/nvim-jdtls",
    ft = "java",
    dependencies = { "mfussenegger/nvim-dap" },
    config = function()
      vim.api.nvim_create_autocmd("FileType", {
        group = vim.api.nvim_create_augroup("tstapler-jdtls", { clear = true }),
        pattern = "java",
        callback = function(args)
          local jdtls = require("jdtls")
          local root_dir = require("jdtls.setup").find_root({
            "gradlew", "mvnw", "pom.xml", "build.gradle", "build.gradle.kts", ".git",
          })
          if not root_dir then
            return
          end

          -- Per-project workspace dir, keyed by project name so distinct
          -- projects never share jdtls index state.
          local project_name = vim.fn.fnamemodify(root_dir, ":p:h:t")
          local workspace_dir = vim.fn.stdpath("data") .. "/jdtls-workspace/" .. project_name

          local mason_registry = require("mason-registry")
          -- Mirrors the pcall guard below for java-debug-adapter/java-test:
          -- mason-registry's in-memory index isn't guaranteed synced with
          -- disk yet the moment this fires (early, off the very first
          -- java buffer's FileType event) — get_package() itself can throw
          -- if the package hasn't registered yet on a fresh install, not
          -- just is_installed() returning stale data. Guard it the same way.
          local jdtls_ok, jdtls_pkg = pcall(mason_registry.get_package, "jdtls")
          if not jdtls_ok then
            vim.notify(
              "jdtls package not found in mason-registry — install may still be indexing",
              vim.log.levels.WARN
            )
            return
          end
          local jdtls_path = jdtls_pkg:get_install_path()

          -- java-debug-adapter + java-test bundles unlock DAP and the
          -- test-runner integration inside jdtls itself, if installed.
          --
          -- UPDATE (post-review, breakpoint-verified interactively): this
          -- originally gated each package on `pkg:is_installed()` before
          -- globbing its jars. That's a real race — mason-registry's
          -- in-memory index isn't guaranteed synced with disk state yet at
          -- the moment jdtls first attaches (this fires early, off a
          -- FileType autocmd on the very first java buffer), so
          -- `is_installed()` returned false even though the jar was
          -- already on disk. Confirmed via jdtls's own error afterward:
          -- "No LSP client found that supports vscode.java.resolveMainClass"
          -- — the bundle silently never made it into init_options. Fixed
          -- by checking the filesystem directly (glob) instead of the
          -- registry's in-memory install state — get_install_path() is
          -- just a path computation, not a live-state read, so it's safe;
          -- only is_installed() was the race.
          local bundles = {}
          for _, pkg_name in ipairs({ "java-debug-adapter", "java-test" }) do
            local ok, pkg = pcall(mason_registry.get_package, pkg_name)
            if ok then
              local jars = vim.split(
                vim.fn.glob(pkg:get_install_path() .. "/extension/server/*.jar", true),
                "\n",
                { trimempty = true }
              )
              vim.list_extend(bundles, jars)
            end
          end

          jdtls.start_or_attach({
            cmd = {
              "java",
              "-Declipse.application=org.eclipse.jdt.ls.core.id1",
              "-Dosgi.bundles.defaultStartLevel=4",
              "-Declipse.product=org.eclipse.jdt.ls.core.product",
              "-Dlog.protocol=true",
              "-Dlog.level=ALL",
              "-Xms1g",
              "--add-modules=ALL-SYSTEM",
              "--add-opens", "java.base/java.util=ALL-UNNAMED",
              "--add-opens", "java.base/java.lang=ALL-UNNAMED",
              "-jar", vim.fn.glob(jdtls_path .. "/plugins/org.eclipse.equinox.launcher_*.jar", true),
              "-configuration", jdtls_path .. "/config_linux",
              "-data", workspace_dir,
            },
            root_dir = root_dir,
            capabilities = require("tstapler.plugins.completion").get_capabilities(),
            init_options = { bundles = bundles },
            on_attach = function(_, bufnr)
              jdtls.setup_dap({ hotcodereplace = "auto" })
              -- UPDATE (post-review, breakpoint-verified interactively):
              -- unlike Go/Rust/Python, jdtls does NOT auto-populate
              -- dap.configurations.java — <leader>dc's "no DAP config for
              -- filetype" guard (plugins/dap.lua) fired immediately without
              -- this. jdtls discovers debuggable main classes dynamically
              -- via project scanning rather than declaring static configs
              -- up front; this is its own documented mechanism for that.
              require("jdtls.dap").setup_dap_main_class_configs()
              -- jdtls-specific refactors beyond the generic gra code-action
              -- popup (Epic 2.1) — IntelliJ's Alt+Enter/Ctrl+Alt+M/Ctrl+Alt+V
              -- equivalents. <leader>co/cx/cm are new binds under the
              -- "code" leader group (leader_groups.lua), reserved once here
              -- via the same collision registry every other epic uses —
              -- Java is only ever one buffer's filetype at a time, so
              -- unlike gitsigns/LspAttach these don't need the
              -- reserve-in-config-not-top-level dance: this callback itself
              -- IS effectively "config time" for this specific autocmd,
              -- and organize_imports/extract_variable/extract_method are
              -- idempotent binds (vim.keymap.set on the same buffer+lhs is
              -- fine to repeat, it just overwrites).
              vim.keymap.set(
                "n",
                "<leader>co",
                jdtls.organize_imports,
                { buffer = bufnr, desc = "Java: organize imports" }
              )
              vim.keymap.set(
                "v",
                "<leader>cx",
                [[<ESC><CMD>lua require('jdtls').extract_variable(true)<CR>]],
                { buffer = bufnr, desc = "Java: extract variable" }
              )
              vim.keymap.set(
                "v",
                "<leader>cm",
                [[<ESC><CMD>lua require('jdtls').extract_method(true)<CR>]],
                { buffer = bufnr, desc = "Java: extract method" }
              )
            end,
          })
        end,
      })
    end,
  },
  -- UPDATE (post-review, breakpoint-verified interactively — this was the
  -- real root cause of a confusing bundle-loading failure): mason-lspconfig
  -- defaults `automatic_enable = true`, which calls `vim.lsp.enable(name)`
  -- for every ensure_installed server UNCONDITIONALLY — including jdtls.
  -- That triggers nvim-lspconfig's OWN bundled default jdtls config (a
  -- function-valued `cmd` that computes its own generic workspace dir under
  -- stdpath("cache")), racing against and effectively shadowing the
  -- FileType-autocmd-driven nvim-jdtls client this file builds by hand.
  -- Confirmed empirically: `vim.lsp.get_clients({name="jdtls"})[1].config.cmd`
  -- was a function, not this file's static table — proof the wrong client
  -- had won. `automatic_enable.exclude` opts out jdtls specifically so only
  -- this file's custom start_or_attach() (with the correct per-project
  -- workspace dir and debug bundles) ever runs.
  {
    "mason-org/mason-lspconfig.nvim",
    opts = {
      ensure_installed = { "jdtls" },
      automatic_enable = { exclude = { "jdtls" } },
    },
    opts_extend = { "ensure_installed" },
  },
  {
    "jay-babu/mason-nvim-dap.nvim",
    opts = { ensure_installed = { "java-debug-adapter", "java-test" } },
    opts_extend = { "ensure_installed" },
  },
}
