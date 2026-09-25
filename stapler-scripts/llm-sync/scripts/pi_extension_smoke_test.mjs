#!/usr/bin/env node
// Headless smoke test for Pi extension loading, without a TTY/TUI.
//
// Calls the real `@earendil-works/pi-coding-agent` extension loader --
// the exact function Pi's own startup path uses -- against a list of
// extension entrypoint file paths, and reports each one's load result as
// structured JSON instead of rendering a TUI. This is the implementation
// of rollout-runbook.md's "Pre-`pi_install_version`-bump smoke-test gate
// (Task 5.1.1c)", which that document flagged as not yet built.
//
// Usage:
//   node pi_extension_smoke_test.mjs <path-to-@earendil-works/pi-coding-agent/dist/index.js> <extension-path> [extension-path ...]
//
// Exit code 0 if every extension loaded with zero errors, 1 otherwise.

import { mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";

const [pkgEntry, ...extensionPaths] = process.argv.slice(2);

if (!pkgEntry || extensionPaths.length === 0) {
  console.error(
    "Usage: pi_extension_smoke_test.mjs <pi-coding-agent dist/index.js> <extension-path>...",
  );
  process.exit(2);
}

const { discoverAndLoadExtensions } = await import(path.resolve(pkgEntry));

// A scratch cwd/agentDir with nothing under it, so discovery only picks up
// the explicitly passed `extensionPaths` -- not whatever's actually
// installed under the real ~/.pi/agent/extensions on this machine.
const scratchDir = mkdtempSync(path.join(tmpdir(), "pi-ext-smoketest-"));

const result = await discoverAndLoadExtensions(extensionPaths, scratchDir, scratchDir);

const report = {
  requested: extensionPaths,
  loaded: result.extensions.map((extension) => ({
    path: extension.path,
    resolvedPath: extension.resolvedPath,
    tools: [...extension.tools.keys()],
    commands: [...extension.commands.keys()],
    handlerEvents: [...extension.handlers.keys()],
  })),
  errors: result.errors,
};

console.log(JSON.stringify(report, null, 2));

if (result.errors.length > 0) {
  process.exit(1);
}
