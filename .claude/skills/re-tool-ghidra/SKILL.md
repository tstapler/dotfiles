---
name: re-tool-ghidra
description: >
  Ghidra decompilation and analysis tool skill. Use when decompiling PE/DLL functions
  to C pseudocode, running Ghidra headless automation, writing GhidraScripts (PyGhidra
  Python 3 or Java), using FlatProgramAPI, recovering C++ types/vtables, running
  QtREAnalyzer, or generating JSON function output for downstream analysis.
  Called from code-reverse-engineering-binary (Phase 3) and code-re-qt5 (Phase 2).
tools:
  - Bash
  - Read
  - Write
model: claude-sonnet-4-6
---

# Tool: Ghidra Analysis

You are an expert in Ghidra reverse engineering and automation. You recover types,
decompile functions, write headless scripts, and document findings precisely.

## Input Contract

- `TARGET`: Path to binary (PE/DLL/ELF)
- `SESSION_DIR`: Path to `/tmp/re-work/<name>/`
- `PRIOR`: `01-static.md` and/or `02-r2-analysis.md` — read for import list and hypotheses
- (Optional) `FOCUS`: Specific function, address, or question

## Output Contract

Write `$SESSION_DIR/03-decompiled.md`. Append one-line summary to `$SESSION_DIR/findings.md`.

---

## analyzeHeadless Reference

Binary: `$GHIDRA_HOME/support/analyzeHeadless`

```bash
# Import and analyze (run once — slow)
$GHIDRA_HOME/support/analyzeHeadless \
  /tmp/ghidra-projects MyProject \
  -import <target> \
  -processor x86:LE:64:default \
  -cspec windows \
  -analysisTimeoutPerFile 300 \
  -overwrite

# Run scripts on cached project (fast — no reimport)
$GHIDRA_HOME/support/analyzeHeadless \
  /tmp/ghidra-projects MyProject \
  -process <target-filename> \
  -noanalysis \
  -scriptPath "/path/to/scripts" \
  -scriptlog /tmp/script.log \
  -postScript ExtractFunctions.py ++output /tmp/functions.json
```

**Key flags:**

| Flag | Purpose |
|------|---------|
| `-import <file>` | Import binary (add `-overwrite` to reimport) |
| `-process [file]` | Run scripts on existing project (no reimport) |
| `-noanalysis` | Skip analysis pass (use with `-process` for script-only runs) |
| `-postScript <Name> [args]` | Script runs AFTER analysis — all API available |
| `-preScript <Name> [args]` | Script runs BEFORE analysis — functions not yet defined |
| `-scriptlog <file>` | Redirect script `println()` to file (separates from Ghidra framework log) |
| `-analysisTimeoutPerFile <sec>` | Kill analysis after N seconds (set 300–600 for large DLLs) |
| `-loader-loadLibraries true` | Load imported DLLs for cross-DLL xrefs |
| `-librarySearchPaths "<p1>;<p2>"` | Where to find dependent DLLs |
| `-processor <langID>` | Force architecture: `x86:LE:64:default` for 64-bit PE |
| `-cspec <specID>` | Compiler spec: `windows` for Windows PE |
| `-deleteProject` | Delete project on exit (CI/ephemeral use) |

**Script argument passing** — use `++` prefix (not `-`) to avoid conflict with analyzeHeadless flags:
```bash
-postScript MyScript.py ++output /tmp/out.json ++verbose
```
In script: `args = getScriptArgs()` returns `["++output", "/tmp/out.json", "++verbose"]`

**Common language IDs:**
- `x86:LE:64:default` — 64-bit x86-64 (most Windows PE/DLL)
- `x86:LE:32:default` — 32-bit x86

---

## Python Scripting: PyGhidra (Recommended)

PyGhidra (Python 3) is built into Ghidra 11.x+. Uses JPype (not Jython).

```bash
pip install pyghidra
export GHIDRA_INSTALL_DIR=/opt/ghidra
```

```python
import pyghidra, json

with pyghidra.open_program("/path/to/binary.exe") as flat_api:
    program = flat_api.getCurrentProgram()
    fm = program.getFunctionManager()

    results = []
    for func in fm.getFunctions(True):
        results.append({
            "name": func.getName(),
            "address": "0x{:x}".format(func.getEntryPoint().getOffset()),
            "size": func.getBody().getNumAddresses(),
            "is_thunk": func.isThunk(),
        })

    with open("/tmp/functions.json", "w") as f:
        json.dump(results, f, indent=2)
```

**Avoid Jython (Python 2.7, EOL)** — only use for legacy scripts. PyGhidra is the correct Python 3 path.

---

## FlatProgramAPI Key Methods

In headless scripts, all FlatProgramAPI methods are callable as bare names. `currentProgram` is available directly.

### Functions

```python
# Iteration
func = getFirstFunction()
while func is not None:
    print(func.getName(), func.getEntryPoint())
    func = getFunctionAfter(func)

# Via FunctionManager (complete iterator)
fm = currentProgram.getFunctionManager()
for func in fm.getFunctions(True):   # True = forward order
    pass

# Lookup
funcs = getGlobalFunctions("CreateFileW")   # returns List[Function]
func  = getFunctionAt(toAddr(0x140001000))
func  = getFunctionContaining(toAddr(0x140001234))

# Function object methods
func.getName()                          # string name
func.getEntryPoint()                    # Address
func.getBody()                          # AddressSetView (all addrs in func)
func.getCalledFunctions(monitor)        # Set[Function] — what it calls
func.getCallingFunctions(monitor)       # Set[Function] — what calls it
func.getParameters()                    # Parameter[]
func.getReturnType()                    # DataType
func.isThunk()                          # bool
func.isExternal()                       # bool (imported DLL functions)
```

### Symbols and Imports

```python
# Symbol lookup
sym = getSymbolAt(toAddr(0x140001000))
syms = getSymbols("CreateFileW", None)   # None = global namespace

# Symbol table iteration
st = currentProgram.getSymbolTable()
for sym in st.getAllSymbols(True):
    print(sym.getName(), sym.getAddress(), sym.getSymbolType())

# Imports via ExternalManager
em = currentProgram.getExternalManager()
for lib in em.getExternalLibraryNames():       # e.g. "ws2_32.dll"
    for loc in em.getExternalLocations(lib):
        print(lib, loc.getLabel(), loc.getAddress())

# Exports
for sym in st.getAllSymbols(True):
    if sym.isExternalEntryPoint():
        print("Export:", sym.getName(), sym.getAddress())
```

### Cross-References

```python
# All callers of a function
refs = getReferencesTo(func.getEntryPoint())
for ref in refs:
    print("From:", ref.getFromAddress(), "Type:", ref.getReferenceType())

# Via ReferenceManager
rm = currentProgram.getReferenceManager()
refs = rm.getReferencesTo(addr)
refs = rm.getReferencesFrom(addr)
```

### Memory Blocks (Sections)

```python
for block in getMemoryBlocks():
    print(block.getName(),
          hex(block.getStart().getOffset()),
          block.getSize(),
          "r" if block.isRead() else "-",
          "w" if block.isWrite() else "-",
          "x" if block.isExecute() else "-")

text_block = getMemoryBlock(".text")
```

### Decompiler API

```python
from ghidra.app.decompiler import DecompInterface
from ghidra.util.task import ConsoleTaskMonitor

ifc = DecompInterface()
ifc.openProgram(currentProgram)
try:
    for func in currentProgram.getFunctionManager().getFunctions(True):
        result = ifc.decompileFunction(func, 60, ConsoleTaskMonitor())
        if result.decompileCompleted():
            c_code = result.getDecompiledFunction().getC()
            print(f"// {func.getName()} @ {func.getEntryPoint()}")
            print(c_code)
        else:
            printerr(f"Failed: {result.getErrorMessage()}")
finally:
    ifc.dispose()   # REQUIRED: releases native decompiler process
```

### JSON Output Pattern

```python
import json

# Use -scriptlog for clean capture (separates script output from Ghidra log)
# Invoke: analyzeHeadless ... -scriptlog /tmp/script.log -postScript Script.py

output = []
for func in currentProgram.getFunctionManager().getFunctions(True):
    output.append({"name": func.getName(),
                   "address": str(func.getEntryPoint())})

output_path = getScriptArgs()[0] if getScriptArgs() else "/tmp/output.json"
with open(output_path, "w") as f:
    json.dump(output, f, indent=2)
println(f"Wrote {len(output)} entries to {output_path}")
```

---

## GUI Workflow

1. File → Import → select binary
   - Language: `x86:LE:64:default` (64-bit PE) or `x86:LE:32:default`
   - Compiler Spec: `windows`
   - Options: Load External Libraries = No (avoids Wine DLL confusion)
2. Analysis → Auto Analyze → ensure **Demangler Microsoft** is checked, accept defaults
3. Navigate:
   - **Symbol Table** (Window → Symbol Table): all named functions/data
   - **Decompiler** (Window → Decompiler): C pseudocode for selected function
   - **Function Graph** (Window → Function Graph): CFG view
4. Cross-references: Right-click symbol → References → Show References To

---

## QtREAnalyzer (Qt5 targets)

```
Analysis → One Shot → QtREAnalyzer
```
Recovers `QMetaObject::d` structs → class names, signals, slots, properties.
See `code-re-qt5` for complete Qt5 workflow.

---

## Ghidra-Cpp-Class-Analyzer Plugin

For MSVC C++ RTTI/vtable recovery. Install via File → Install Extensions → add .zip.
Without it, vtables appear as `undefined8` pointer arrays. With it: recovers class names,
vtable structures, and constructor/destructor identification.

GitHub: https://github.com/astrelsky/Ghidra-Cpp-Class-Analyzer

---

## rz-ghidra (No Java, No GUI)

Embeds only Ghidra's decompiler engine in radare2/rizin:

```bash
r2pm -ci r2ghidra

r2 -q -c "aaa; s sym.main; pdgj" binary.exe | jq .
# pdg  = decompile current function (text)
# pdgj = decompile to JSON
# pdgo = decompile with offset annotations
```

Use for: fast batch decompilation, CI pipelines. Weaker than full Ghidra (no RTTI, no PDB, no analysis passes).

---

## Project Reuse (Performance)

```bash
# Import once (slow, ~30–300s)
analyzeHeadless /tmp/ghidra-projects MyProject \
  -import binary.exe -processor x86:LE:64:default -cspec windows \
  -analysisTimeoutPerFile 300 -overwrite

# Re-run scripts without reimporting (fast, ~1–5s)
analyzeHeadless /tmp/ghidra-projects MyProject \
  -process binary.exe -noanalysis \
  -postScript NewScript.py
```

---

## Gotchas

| Problem | Fix |
|---------|-----|
| Wrong project path format | Two separate args: `/home/user/ghidra myProject` NOT `/home/user/ghidra/myProject` |
| Reimport silently skipped | Add `-overwrite` |
| `getFirstFunction()` returns null in preScript | Move all extraction to postScript |
| Script args starting with `-` disappear | Use `++` prefix: `-postScript Script.py ++arg value` |
| Large PE hangs analysis | `-analysisTimeoutPerFile 300`; disable "Windows x86 PE Exception Handling" pass for speed |
| Headless/GUI calling convention mismatch | Always add `-cspec windows` for PE targets |
| `popup()`/`askFile()` crash headless | These are GUI-only; guard with try/except in headless |
| DecompInterface resource leak | Always call `ifc.dispose()` in finally block |
| Jython `currentProgram()` vs `currentProgram` | Ghidrathon uses `currentProgram()` (function call); Jython/PyGhidra use field syntax |

---

## Output Template

```markdown
# Ghidra Analysis: <target>

## Key Functions
| Name / Address | Decompiled Summary | Called By | Notes |
|---------------|--------------------|-----------|-------|

## Type Recovery
| Symbol | Type | Evidence |

## C++ Classes
| Class (vtable) | Virtual Methods | Notes |

## Import Call Chains
main → init_network → WSAConnect(192.168.1.1:9000)

## Decompiled Snippets
<key function pseudocode — addresses preserved>

## Open Questions
- [ ] Function at 0x... — behavior unknown
```

---

## Gate Artifact

`$SESSION_DIR/03-decompiled.md` with at least one decompiled function relevant to the goal.

## Related Skills

| Skill | When |
|-------|------|
| `re-tool-radare2` | Run first; confirms which functions to target in Ghidra |
| `re-tool-wine-trace` | Confirms Ghidra hypotheses with runtime observations |
| `re-tool-static-analysis` | Prerequisites: PE triage before loading into Ghidra |
| `code-re-qt5` | Qt5 workflow including QtREAnalyzer |
