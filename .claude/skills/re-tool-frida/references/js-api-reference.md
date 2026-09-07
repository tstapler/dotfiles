# JS API Reference

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
