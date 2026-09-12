import assert from "node:assert/strict";
import test from "node:test";

import ponytail from "./index.ts";

test("Pi ponytail starts off and remains available on demand", async () => {
  const handlers = new Map();
  const commands = new Map();
  const pi = {
    on(name, handler) { handlers.set(name, handler); },
    registerCommand(name, command) { commands.set(name, command); },
    appendEntry() {},
  };
  ponytail(pi);

  let status;
  const ctx = {
    sessionManager: { getBranch: () => [] },
    ui: { setStatus(_key, value) { status = value; }, notify() {} },
  };
  handlers.get("session_start")({}, ctx);
  assert.equal(status, undefined);
  assert.equal(handlers.get("before_agent_start")({ systemPrompt: "BASE" }), undefined);

  await commands.get("ponytail").handler("full", ctx);
  assert.equal(status, "ponytail:full");
  assert.match(
    handlers.get("before_agent_start")({ systemPrompt: "BASE" }).systemPrompt,
    /minimum|simplest|YAGNI/i,
  );
});
