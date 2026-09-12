import assert from "node:assert/strict";
import test from "node:test";

import dotfilesHooks, {
  compactBashCommand,
  isPrLifecycleCommand,
} from "./index.ts";

test("detects only gh PR lifecycle commands", () => {
  assert.equal(isPrLifecycleCommand("gh pr create --draft"), true);
  assert.equal(isPrLifecycleCommand("GH_HOST=example gh pr ready 42 && gh pr merge 42"), true);
  assert.equal(isPrLifecycleCommand("echo 'gh pr merge'"), true);
  assert.equal(isPrLifecycleCommand("gh pr view 42"), false);
});

test("uses an RTK rewrite before cmdcrush", async () => {
  const calls = [];
  const pi = {
    async exec(command, args) {
      calls.push([command, args]);
      return command === "rtk"
        ? { code: 0, stdout: "rtk git status\n", stderr: "" }
        : { code: 1, stdout: "", stderr: "" };
    },
  };

  assert.equal(await compactBashCommand(pi, "git status"), "rtk git status");
  assert.deepEqual(calls, [["rtk", ["rewrite", "git status"]]]);
});

test("falls back to cmdcrush when RTK is unavailable", async () => {
  const pi = {
    async exec(command) {
      if (command === "rtk") throw new Error("spawn ENOENT");
      return { code: 0, stdout: "/usr/local/bin/cmdcrush\n", stderr: "" };
    },
  };

  assert.equal(
    await compactBashCommand(pi, "find . -type f -print"),
    "/usr/local/bin/cmdcrush -- bash -c 'find . -type f -print'",
  );
});

test("falls back to cmdcrush for substantial commands", async () => {
  const pi = {
    async exec(command) {
      if (command === "rtk") return { code: 1, stdout: "", stderr: "" };
      return { code: 0, stdout: "/usr/local/bin/cmdcrush\n", stderr: "" };
    },
  };

  assert.equal(
    await compactBashCommand(pi, "find . -type f -print"),
    "/usr/local/bin/cmdcrush -- bash -c 'find . -type f -print'",
  );
});

test("shell-quotes apostrophes in cmdcrush fallback commands", async () => {
  const pi = {
    async exec(command) {
      if (command === "rtk") return { code: 1, stdout: "", stderr: "" };
      return { code: 0, stdout: "/bin/cmdcrush\n", stderr: "" };
    },
  };
  assert.equal(
    await compactBashCommand(pi, "printf '%s' a-command-with-output"),
    "/bin/cmdcrush -- bash -c 'printf '\"'\"'%s'\"'\"' a-command-with-output'",
  );
});

test("does not rewrite trivial, heredoc, or already wrapped commands", async () => {
  const pi = { async exec() { throw new Error("must not execute"); } };
  assert.equal(await compactBashCommand(pi, "pwd"), "pwd");
  assert.equal(await compactBashCommand(pi, "cat <<EOF\nx\nEOF"), "cat <<EOF\nx\nEOF");
  assert.equal(await compactBashCommand(pi, "rtk git status"), "rtk git status");
});

test("registers Pi lifecycle hooks and blocks a PR lifecycle command once", async () => {
  const handlers = new Map();
  const commands = new Map();
  const pi = {
    on(name, handler) { handlers.set(name, handler); },
    registerCommand(name, command) { commands.set(name, command); },
    async exec() { return { code: 1, stdout: "", stderr: "" }; },
  };

  dotfilesHooks(pi);
  assert.deepEqual(
    [...handlers.keys()].sort(),
    ["session_compact", "session_start", "tool_call"],
  );
  assert.equal(commands.has("magic-compact"), true);

  const event = { toolName: "bash", input: { command: "gh pr merge 42" } };
  const first = await handlers.get("tool_call")(event, { signal: undefined });
  const second = await handlers.get("tool_call")(event, { signal: undefined });
  assert.equal(first.block, true);
  assert.match(first.reason, /review gate/i);
  assert.equal(second, undefined);
});
