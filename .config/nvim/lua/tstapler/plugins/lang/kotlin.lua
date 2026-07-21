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
-- UPDATE (post-review, real-CI-and-local-verified): kotlin-language-server
-- is itself a JVM program, launched under whatever `java` resolves first
-- on PATH. Confirmed via lsp.log a real crash on this machine's default
-- JDK: `java.lang.IllegalArgumentException: 25.0.2` — the bundled Kotlin
-- compiler (2.1.0) this server ships can't parse a JDK 25-style version
-- string at all, an upstream compatibility gap, not a config mistake (Java
-- itself, via jdtls, works fine under the exact same JDK 25 — this is
-- specific to kotlin-language-server's older bundled compiler). Point it
-- at a known-compatible JDK if one is findable, otherwise fall back to
-- whatever's on PATH (no worse than before this fix).
local function find_compatible_java_home()
  -- actions/setup-java sets JAVA_HOME_<version>_X64 for every JDK version
  -- installed in a workflow — CI's .github/workflows/nvim.yml installs 21,
  -- which this compiler handles fine.
  for _, v in ipairs({ "21", "17", "11" }) do
    local env_home = vim.env["JAVA_HOME_" .. v .. "_X64"]
    if env_home and vim.fn.isdirectory(env_home) == 1 then
      return env_home
    end
  end
  -- Common Linux distro JVM install paths, for local dev machines with no
  -- setup-java-style env vars (this repo's own dev machine has this one).
  for _, v in ipairs({ "21", "17", "11" }) do
    local path = "/usr/lib/jvm/java-" .. v .. "-openjdk"
    if vim.fn.isdirectory(path) == 1 then
      return path
    end
  end
  return nil
end

return {
  {
    "tstapler-lang-kotlin-lsp",
    virtual = true,
    ft = "kotlin",
    config = function()
      local java_home = find_compatible_java_home()
      vim.lsp.config("kotlin_language_server", {
        capabilities = require("tstapler.plugins.completion").get_capabilities(),
        root_markers = { "settings.gradle.kts", "settings.gradle", "pom.xml", ".git" },
        cmd_env = java_home and { JAVA_HOME = java_home } or nil,
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
