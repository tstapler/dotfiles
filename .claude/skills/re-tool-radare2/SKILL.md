---
name: re-tool-radare2
description: >
  Radare2 (r2) disassembly and analysis tool skill. Use when running r2 commands,
  scripting with r2pipe, analyzing functions, navigating disassembly, recovering symbols,
  finding cross-references, patching bytes, or using r2frida for live instrumentation.
  Covers r2's command language: analysis (aa/aaa/avrr), info (ii/iS/iE/ir/iee/ic),
  search (/w /R /v4), type system (td/to/tp), r2pipe Python API, and radiff2.
  Called from code-reverse-engineering-binary and code-re-qt5 (Phase 1–2 deep analysis).
tools:
  - Bash
  - Read
  - Write
model: claude-sonnet-4-6
---

# Tool: radare2

You are an expert in radare2 binary analysis. You know r2's command language, r2pipe
Python API, and MSVC-specific analysis on Windows PE/DLL targets.

## Input Contract

- `TARGET`: Path to binary
- `SESSION_DIR`: Path to `/tmp/re-work/<name>/`
- `TASK`: What to extract — function list, import xrefs, RTTI classes, protocol strings, etc.
- `PRIOR`: `01-static.md` for initial triage context

## Output Contract

Write `$SESSION_DIR/r2-<task>.md`. Append one-line summary to `$SESSION_DIR/findings.md`.

---

## CRITICAL: MSVC Configuration

**Set this before any analysis on Windows PE/DLL targets:**

```bash
r2 -e anal.cxxabi=msvc -e bin.demangle=true -e anal.timeout=60 <target>
```

Or in r2pipe:
```python
r2 = r2pipe.open(target, flags=[
    "-2",
    "-e", "anal.cxxabi=msvc",
    "-e", "bin.demangle=true",
    "-e", "anal.timeout=60",
])
```

Without `anal.cxxabi=msvc`, RTTI recovery (`avra`/`avrr`) finds nothing on MSVC binaries.

---

## PE/DLL Info Commands

```bash
i       # binary summary (arch, bits, OS, format)
iI      # condensed one-liner version
iS      # sections (vaddr, paddr, size, perms) — essential for PE
iSj     # sections as JSON
ii      # imports with DLL name, ordinal, vaddr
iij     # imports as JSON
iE      # DLL exports
iEj     # exports as JSON
ir      # relocations / IAT slots
irj     # relocations as JSON
iee     # entrypoints + TLS callbacks + constructors/destructors
ie      # main entrypoint only
iv      # PE version info (FileDescription, ProductVersion)
iw      # SEH / exception handling blocks (.pdata)
ic      # C++ classes/methods from binary metadata
icj     # classes as JSON
icg     # class inheritance graph (ASCII)
iD cxx <mangled>  # demangle a symbol inline
idp target.pdb    # load local PDB file
idpd              # download PDB from Microsoft symbol server
. idpi*           # import PDB symbols as r2 flags (dot executes the output)
```

---

## Analysis Commands

```bash
# Analysis depth (set cxxabi first)
aa      # basic: known symbols + entrypoint
aas     # symbols only (fast — imports/exports, no function body analysis)
aaf     # analyze all function bodies
aaa     # full: aa + xrefs + type propagation (use for most RE)
aaaa    # experimental passes (slow)

# For MSVC DLLs — faster than blind aaa
r2 -e anal.cxxabi=msvc -q -c "aas; aaf; avrr" target.dll

# Function listing
afl         # list functions (name, address, size)
afll        # verbose function list (xref count, complexity, cyclomatic — use for triage)
afll size   # sort by size (largest first = most complex)
afl,size/gt/100  # table query: functions larger than 100 bytes
afi         # detailed info about current function
afv=        # list function variables with disasm references

# Naming and typing
afn newname     # rename current function
afvn old new    # rename local variable
afvt name type  # set type for local variable
afc ms          # set calling convention: ms = MSVC x64 Windows

# RTTI / C++ class recovery (MSVC) — requires anal.cxxabi=msvc
avra        # search ALL vtables and parse RTTI at each
avrr        # populate 'ac' namespace with recovered class info
avr @ addr  # parse RTTI at specific vtable address
acl         # list all recovered C++ classes
acll ClassName  # detailed: methods + vtable slots for one class
acg         # class inheritance graph
acvf offset # look up method at vtable offset
is~??_7     # MSVC vtable symbols (mangled form)
is~??_R0    # MSVC RTTI type descriptors

# Cross-references
axt @ addr  # xrefs TO this address (who calls/uses it)
axf @ addr  # xrefs FROM this address (what it calls/uses)
axff @ addr # all xrefs from the containing function
axtj @ addr # xrefs TO as JSON
axfj @ addr # xrefs FROM as JSON

# Call graph
agc         # function callgraph (current function)
agCd        # global callgraph as graphviz dot
aau         # list memory not covered by any function (dead code)
```

---

## FLIRT Signatures (stripped binaries)

Apply prebuilt FLIRT signature files to identify standard library functions:

```bash
zfs /path/to/vc140_x64.sig    # apply VC140 signatures
zfs /path/to/*.sig             # glob all .sig files
zfl                            # list bundled FLIRT sig files
zg                             # generate signatures for current binary
```

Community FLIRT database for MSVC: https://github.com/Maktm/FLIRTDB

---

## PDB Symbol Loading

```bash
e pdb.server=https://msdl.microsoft.com/download/symbols
idpd                  # download PDB from symbol server (uses pdb.server)
idp target.pdb        # load local PDB
. idpi*               # apply: import PDB symbols as r2 flags
rabin2 -PP target.dll # alternative: download PDB via rabin2
```

---

## Search Commands

```bash
/w string      # wide (UTF-16LE) string search — critical for Windows binaries
/wi string     # wide string, case-insensitive
/c jmp eax     # search by instruction text
/v4 0xdeadbeef # search for 32-bit value in memory
/v8 0xdeadbeef # search for 64-bit value
/R [pattern]   # ROP gadget search
/s 0 4         # entropy block analysis (detect packed/encrypted sections)
```

---

## Type System

```bash
td "struct FOO { int a; char *b; };"   # define C struct inline
to /path/header.h                      # parse C header, load all types
tp TYPENAME @ addr                     # overlay type onto memory at address
tl TYPENAME @ addr                     # link type to address (persists)
ts                                     # list defined structs
tu                                     # list defined unions
te                                     # list defined enums
```

---

## Disassembly and Decompilation

```bash
pdf @ main          # disassemble function at symbol
pdf @ sym.send      # disassemble imported function wrapper
pdf @ 0x140001234   # disassemble function at address
pdg @ main          # Ghidra decompiler output (requires: r2pm -ci r2ghidra)
pdd @ main          # r2dec decompiler output (requires: r2pm -ci r2dec)
pdc @ main          # built-in pseudo-decompiler (experimental, no plugin needed)
```

---

## Patching

```bash
oo+                 # reopen file read-write
wa "jmp 0x401000"   # assemble and write at current offset
wao nop             # NOP current instruction
wao ret0            # force return 0
wao ret1            # force return 1
wao nocj            # remove conditional from branch (make unconditional)
wao recj            # reverse conditional branch direction
wx 9090             # write raw hex bytes
```

---

## Radiff2 (Binary Diff)

```bash
radiff2 -C old.dll new.dll          # compare functions by name/hash
radiff2 -g main old.dll new.dll     # graphviz diff of specific function
```

---

## r2frida (Live Analysis)

Requires: `r2pm -ci r2frida`

```bash
r2 frida://<pid>                         # attach to running process
r2 "frida://?spawn:/path/to/target.exe"  # spawn then attach
```

Inside r2 with r2frida (all commands prefixed `\`):
```
\il                    # list loaded modules (live)
\ii ws2_32.dll         # live imports of module
\iE ws2_32.dll         # live exports
\dd                    # list memory maps
\/ searchterm          # search process memory for string
\/x 0102030405         # search memory for hex pattern
\wx 9090 @ addr        # write NOP to live process
\wa "jmp 0x1234" @ addr  # assemble and write live
```

---

## r2pipe Python API

```python
import r2pipe, json

def open_pe_msvc(path):
    return r2pipe.open(path, flags=[
        "-2",                       # suppress stderr
        "-e", "anal.cxxabi=msvc",   # MUST for MSVC targets
        "-e", "bin.demangle=true",
        "-e", "anal.timeout=60",
    ])

r2 = open_pe_msvc("target.dll")
try:
    r2.cmd("aas")              # symbol-based analysis (fast)
    r2.cmd("avrr")             # RTTI class recovery

    # cmdj() returns None on failure — always guard
    functions = r2.cmdj("aflj") or []
    imports   = r2.cmdj("iij")  or []
    exports   = r2.cmdj("iEj")  or []
    sections  = r2.cmdj("iSj")  or []
    classes   = r2.cmdj("aclj") or []

    # Cross-references to a specific import
    r2.cmd("s sym.imp.send")
    callers = r2.cmdj("axtj") or []
    for xr in callers:
        print(f"  send called from {xr.get('fcn_name','')} @ {xr['from']:#x}")

    # Find functions with network strings
    strings = r2.cmdj("izzj") or []
    for s in strings:
        if any(kw in s.get('string','').lower() for kw in ['host','port','connect','http']):
            r2.cmd(f"s {s['vaddr']}")
            xrefs = r2.cmdj("axtj") or []
            for xr in xrefs:
                print(f"  {s['string']!r} used in {xr.get('fcn_name','')} @ {xr['from']:#x}")
finally:
    r2.quit()
```

---

## Optional Plugins

```bash
r2pm -ci r2ghidra   # Ghidra decompiler → pdg / pdgj (no Java required)
r2pm -ci r2dec      # r2dec decompiler → pdd
r2pm -ci r2frida    # Frida live instrumentation → frida:// IO
```

---

## Gotchas

| Problem | Fix |
|---------|-----|
| `avrr`/`avra` finds no classes | Set `e anal.cxxabi=msvc` BEFORE analysis |
| `aflj` returns `None` | Binary not analyzed — run `aas` or `aaa` first |
| Wrong arch/bits detected | Override: `r2 -a x86 -b 64 target` |
| Wrong base address (PIE DLL) | `r2 -B 0x140000000 target.dll` |
| Wide strings not found by `iz` | Use `/w searchterm` for UTF-16 search |
| `pdg`/`pdd` command not found | Install: `r2pm -ci r2ghidra` or `r2pm -ci r2dec` |
| MSVC mangled names still visible | `r2 -e bin.demangle=true target` |
| `axt` vs `axf` confusion | `axt` = xrefs **T**o (callers); `axf` = xrefs **F**rom |
| Large DLL hangs during analysis | `e anal.timeout=30` caps at 30 seconds |
| stderr noise in r2pipe | Pass `"-2"` in open() flags |

---

## Output Template

```markdown
# radare2 Analysis: <target>

## Binary Info
Arch: x86-64 | Format: PE32+ | Functions: N | Sections: N

## Key Functions
| Address | Name | Size | Notes |
|---------|------|------|-------|

## Import Call Sites
| Import | Called From | Address |

## Recovered C++ Classes (RTTI)
| Class | Methods | Vtable Addr |

## String → Function Map
| String | Address | Used In |

## Open Questions
- [ ] ...
```

---

## Gate Artifact

`$SESSION_DIR/r2-<task>.md` with function inventory, import xref map, and at least one
answered question about binary behavior.

## Related Skills

| Skill | When |
|-------|------|
| `re-tool-static-analysis` | Quick triage before deep r2 analysis |
| `re-tool-ghidra` | Need C pseudocode; r2pipe gives assembly only |
| `re-tool-frida` | Live instrumentation; r2frida bridges both |
| `code-reverse-engineering-binary` | Orchestrator for full multi-phase RE |
