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

### Working approach: frida-gadget.dll injection

```bash
# Step 1: Download frida-gadget for Windows x64
# Get from: https://github.com/frida/frida/releases
# File: frida-gadget-<version>-windows-x86_64.dll.xz
unxz frida-gadget-<version>-windows-x86_64.dll.xz
cp frida-gadget-<version>-windows-x86_64.dll frida-gadget.dll

# Step 2: Inject via DLL proxy (rename target DLL, create proxy)
# OR: patch the PE import table to add frida-gadget.dll as an import
# Use: pe-bear, CFF Explorer, or frida-inject on Windows

# Step 3: Place frida-gadget.dll next to the target EXE in the Wine prefix
cp frida-gadget.dll ~/.wine-target/drive_c/path/to/target/

# Step 4: Run target — gadget starts a listener on 127.0.0.1:27042
WINEPREFIX=~/.wine-target wine target.exe &

# Step 5: Connect from Linux host
frida -H 127.0.0.1:27042 -n target.exe
# OR in Python:
import frida
device = frida.get_device_manager().add_remote_device('127.0.0.1:27042')
session = device.attach('target.exe')
```

### Alternative: frida-gadget config file

Place `frida-gadget.config.json` next to `frida-gadget.dll`:
```json
{
  "interaction": {
    "type": "listen",
    "address": "127.0.0.1",
    "port": 27042,
    "on_load": "wait"
  }
}
```
`on_load: "wait"` pauses at DLL init — gives time to attach before code runs.

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

## Core Hook: Network Payload Capture

```python
# hook-network.py
import frida, sys, os, time

SESSION_DIR = os.environ.get('SESSION_DIR', '/tmp/re-work/target')
os.makedirs(f'{SESSION_DIR}/captures', exist_ok=True)
capture_file = open(f'{SESSION_DIR}/captures/session-{int(time.time())}.bin', 'wb')

SCRIPT = """
const ws2 = Process.getModuleByName("ws2_32.dll");

Interceptor.attach(ws2.getExportByName("send"), {
    onEnter(args) {
        const len = args[2].toInt32();
        const buf = args[1].readByteArray(Math.min(len, 4096));
        send({direction: "send", sock: args[0].toInt32(), len}, buf);
    }
});

Interceptor.attach(ws2.getExportByName("recv"), {
    onEnter(args) {
        this.buf = args[1]; this.maxlen = args[2].toInt32(); this.sock = args[0].toInt32();
    },
    onLeave(retval) {
        const len = retval.toInt32();
        if (len > 0)
            send({direction: "recv", sock: this.sock, len}, this.buf.readByteArray(len));
    }
});
console.log("[frida] hooks installed");
"""

def on_message(msg, data):
    if msg.get('type') == 'send' and data:
        d = msg['payload']
        print(f"[{d['direction']}] sock={d['sock']} len={d['len']}")
        print("  " + data[:32].hex() + ("..." if len(data) > 32 else ""))
        capture_file.write(data)
        capture_file.flush()

# Connect via gadget
device = frida.get_device_manager().add_remote_device('127.0.0.1:27042')
session = device.attach('target.exe')
script = session.create_script(SCRIPT)
script.on('message', on_message)
script.load()
print(f"[frida] capturing to {SESSION_DIR}/captures/")
sys.stdin.read()
```

---

## JS API Reference

### Module Discovery (prefer over getModuleByName — doesn't throw on missing)

```javascript
// Enumerate all loaded modules
Process.enumerateModules().forEach(m => {
    console.log(m.name, m.base, m.size);
});

// Find module by name pattern
const mod = Process.enumerateModules().find(m =>
    m.name.toLowerCase().includes('ws2'));

// Enumerate exports/imports without throwing
mod.enumerateExports().forEach(e => console.log(e.name, e.address));
mod.enumerateImports().forEach(i => console.log(i.module, i.name));
```

### ApiResolver (glob-based function discovery)

```javascript
const resolver = new ApiResolver('module');
// Find all send-like functions across all loaded DLLs
resolver.enumerateMatches('exports:ws2_32!send*').forEach(match => {
    console.log(match.name, match.address);
    Interceptor.attach(match.address, { onEnter(args) { console.log("hit"); } });
});
```

### Hook by Virtual Address (from radare2/Ghidra output)

```javascript
const base = Process.getModuleByName("target.dll").base;
const offset = 0x1234;   // VA from disassembler
Interceptor.attach(base.add(offset), {
    onEnter(args) { console.log("hit @ " + (base.add(offset))); }
});
```

### COM/vtable Hooking

```javascript
// vtable is an array of function pointers
// Read the vtable pointer, then read method pointer at index N
const obj_ptr = ptr("0x12345678");       // from relay log: 'this' pointer
const vtable  = obj_ptr.readPointer();   // vtable pointer
const method  = vtable.add(2 * Process.pointerSize).readPointer(); // method index 2

Interceptor.attach(method, {
    onEnter(args) { console.log("vtable method 2 called, this=" + args[0]); }
});
```

### NativeFunction and NativeCallback

```javascript
// Call a target function directly
const createFile = new NativeFunction(
    Module.getExportByName('kernel32.dll', 'CreateFileW'),
    'pointer',                              // return type
    ['pointer','uint32','uint32','pointer','uint32','uint32','pointer'],
    { abi: 'win64' }                        // REQUIRED for Win32 API
);

// Replace a function — CRITICAL: save NativeCallback to a variable or it's GC'd
const myImpl = new NativeCallback(function(a, b) {
    return 0;
}, 'int', ['pointer', 'int'], { abi: 'stdcall' });  // specify ABI for 32-bit

// WARNING: if you don't save myImpl, it gets garbage collected → crash
globalThis._savedCallback = myImpl;    // keep reference alive
Interceptor.replace(targetAddr, myImpl);
```

### Thread.backtrace

```javascript
Interceptor.attach(addr, {
    onEnter(args) {
        const bt = Thread.backtrace(this.context, Backtracer.FUZZY)
            .map(DebugSymbol.fromAddress)
            .join('\n');
        console.log("Backtrace:\n" + bt);
    }
});
```

### Memory Operations

```javascript
// Scan for byte pattern (with ?? wildcards)
Memory.scan(mod.base, mod.size, "52 41 56 4E ?? ?? ??", {
    onMatch(address, size) { console.log("found at " + address); },
    onComplete() { console.log("scan done"); }
});

// Allocate near a specific address (for 32-bit relative JMP trampolines)
const buf = Memory.alloc(256, { near: mod.base, maxDistance: 0x7fffffff });
```

### Stalker (Instruction-level Coverage Tracing)

Stalker traces every instruction without breakpoints — useful for recovering protocol
parser state machines.

```javascript
// Track which basic blocks are visited during a recv call
Stalker.follow(Process.getCurrentThreadId(), {
    events: { block: true, call: true, ret: false },
    onReceive(events) {
        const list = Stalker.parse(events, {
            stringify: false, annotate: false
        });
        list.forEach(event => {
            if (event[0] === 'block')
                blocksSeen.add(event[1].toString());   // event[1] = block start address
        });
    }
});

// Use to compare block coverage between different message types:
// reset blocksSeen before each recv, collect after return
```

### CModule (High-performance hooks, ~4.5x faster than JS)

```javascript
// CModule compiles C code into the target process via TinyCC
const cm = new CModule(`
#include <glib.h>
void on_message(GumInvocationContext *ic) {
    gpointer arg0 = gum_invocation_context_get_nth_argument(ic, 0);
    g_print("arg0 = %p\\n", arg0);
}
`);
Interceptor.attach(ptr("0x12345678"), cm.on_message);
```

### frida-trace CLI

```bash
# Trace all exports matching pattern
frida-trace -H 127.0.0.1:27042 -n target.exe -i "send" -i "recv" -i "connect"

# Trace by module!pattern
frida-trace -H 127.0.0.1:27042 -n target.exe -I "ws2_32.dll"

# Trace internal function by module!offset
frida-trace -H 127.0.0.1:27042 -n target.exe -a "target.dll!0x1234"

# Handler files are auto-generated in __handlers__/<module>/<function>.js
# Edit them to customize logging — they use (log, args, state) signature:
# exports.onEnter = function(log, args, state) { log("arg0=" + args[0]); }
```

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

## Output Template

```markdown
# Frida Hook Results: <target>

## Hooks Deployed
| Target | Trigger |

## Captures
| Session | Direction | Packets | Bytes | File |

## Protocol Observations
- First 4 bytes: `52 41 56 4E` ("RAVN") — likely magic
- Byte 5 = message type (values: 0x01, 0x02, 0x10)

## Raw Excerpts (32 bytes max each)

## Open Questions
- [ ] Is length inclusive or exclusive of header?
```

---

## Gate Artifact

`$SESSION_DIR/05-hooks.md` with at least one capture file and initial protocol observations.

## Related Skills

| Skill | When |
|-------|------|
| `re-tool-wine-trace` | Run first — identifies which functions carry payloads |
| `re-tool-protocol-capture` | Full Wireshark capture for stream-level context |
| `re-tool-kaitai` | Formalize structure observed in captures |
