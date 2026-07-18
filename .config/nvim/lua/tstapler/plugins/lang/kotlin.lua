-- Kotlin LSP via kotlin-language-server (kotlin_language_server in
-- nvim-lspconfig's server registry). Unlike Java's jdtls, this server has
-- no per-project workspace-directory requirement, so it fits the same
-- 0.11 native vim.lsp.config()/vim.lsp.enable() "virtual plugin" pattern
-- Go/Python/TypeScript already use — see lang/go.lua's
-- "tstapler-lang-go-lsp" comment for the full empirical rationale on why
-- a uniquely-named virtual plugin, not a second fragment on the shared
-- "neovim/nvim-lspconfig" plugin.
--
-- DAP: NOT wired here. Kotlin compiles to JVM bytecode, so in principle
-- the same java-debug-adapter Java uses (lang/java.lua) could attach to a
-- running/launched Kotlin process — but nvim-jdtls's DAP integration
-- (setup_dap, debuggables discovery) is Java-project-shaped and doesn't
-- understand Kotlin source directly, and there's no equivalent
-- Kotlin-native tooling with comparable maturity in the Neovim ecosystem.
-- Left unimplemented rather than shipping something unverified — same
-- "stretch goal, document the gap honestly" call already made for TS/JS
-- DAP (lang/typescript.lua) — worth revisiting only if this becomes an
-- actual daily-driver need.
return {
  {
    "tstapler-lang-kotlin-lsp",
    virtual = true,
    ft = "kotlin",
    config = function()
      vim.lsp.config("kotlin_language_server", {
        capabilities = require("tstapler.plugins.completion").get_capabilities(),
        root_markers = { "settings.gradle.kts", "settings.gradle", "pom.xml", ".git" },
      })
      vim.lsp.enable("kotlin_language_server")
    end,
  },
  {
    "mason-org/mason-lspconfig.nvim",
    opts = { ensure_installed = { "kotlin_language_server" } },
    opts_extend = { "ensure_installed" },
  },
}
