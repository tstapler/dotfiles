---
name: re-tool-frida
description: >
  Frida dynamic instrumentation tool skill. Use when hooking functions in a running
  process, capturing raw payload bytes from send/recv, intercepting function arguments
  or return values, using Stalker for coverage tracing, or CModule for high-performance
  hooks. NOTE: Direct Frida attachment to Wine processes crashes — use frida-gadget.dll
  injection instead (documented below).
  Called from code-reverse-engineering-binary (Phase 5) and code-re-qt5 (Phase 3c).
tools:
  - Bash
  - Read
  - Write
model: claude-sonnet-4-6
---

# Tool: Frida Instrumentation

You are an expert in Frida dynamic instrumentation. You know the JS API, gadget injection
for Wine processes, high-performance hook patterns, and the NativeCallback GC pitfall.

## Input Contract

- `TARGET_PID` or `TARGET_NAME`: Process identifier
- `SESSION_DIR`: Path to `/tmp/re-work/<name>/`
- `FOCUS`: What to hook — network buffers, file I/O, specific exports, or VA
- `PRIOR`: `04-api-trace.md` for call sequence context

## Output Contract

Write `$SESSION_DIR/05-hooks.md`. Raw captures → `$SESSION_DIR/captures/`.
Append one-line summary to `$SESSION_DIR/findings.md`.

---

## CRITICAL: Wine Process Attachment

**`frida.attach(pid)` crashes on Wine processes** (GitHub issue #3339 — not fixed).
Direct attachment hits "Unable to locate the libc" and kills the target.

Use `frida-gadget.dll` injection instead: build/copy the gadget next to the target EXE
in the Wine prefix, launch the target so the gadget starts a listener on
`127.0.0.1:27042`, then attach from the Linux host over that port. Full step-by-step
(including the gadget config JSON for delayed start) is in
[references/wine-gadget-injection.md](references/wine-gadget-injection.md).

---

## Setup

```bash
pip install frida-tools   # installs frida, frida-ps, frida-trace, frida-ls-devices

frida --version
python3 -c "import frida; print(frida.__version__)"

# List processes (use after gadget is loaded)
frida-ps -H 127.0.0.1:27042     # via gadget
```

---

## Core Workflow

1. Attach (direct on Linux targets, gadget injection on Wine — see above).
2. Hook the relevant boundary — network send/recv, a specific export, or a VA found by
   radare2/Ghidra. A full worked example (hooking `ws2_32.dll` send/recv and writing
   captures to disk) is in [references/examples.md](references/examples.md), along with
   the `$SESSION_DIR/05-hooks.md` output template.
3. For deeper introspection — module/export discovery, `ApiResolver`, vtable/COM hooking,
   `NativeFunction`/`NativeCallback`, backtraces, `Memory.scan`, `Stalker` coverage
   tracing, `CModule` for high-performance hooks, and the `frida-trace` CLI — see
   [references/js-api-reference.md](references/js-api-reference.md).

---

## Gotchas

| Problem | Fix |
|---------|-----|
| Crashes with "Unable to locate libc" | Direct Wine attach — use frida-gadget.dll instead |
| NativeCallback silently GC'd → crash | Save to `globalThis._savedXxx` to keep reference |
| 32-bit stdcall corrupts stack | Specify `{ abi: 'stdcall' }` in NativeCallback/NativeFunction |
| Module not found on getModuleByName | DLL not yet loaded; hook after load or use Process.enumerateModules() |
| High-frequency hooks flood message queue | Batch with `send()` arrays or use CModule |
| frida-trace handler signature wrong | Handler uses `(log, args, state)` not raw `(this, args)` |
| `Process.setExceptionHandler` try/catch fails | Known limitation — catch block inside exception handler crashes; use Stalker instead |

---

## Gate Artifact

`$SESSION_DIR/05-hooks.md` with at least one capture file and initial protocol observations.

## Related Skills

| Skill | When |
|-------|------|
| `re-tool-wine-trace` | Run first — identifies which functions carry payloads |
| `re-tool-protocol-capture` | Full Wireshark capture for stream-level context |
| `re-tool-kaitai` | Formalize structure observed in captures |
