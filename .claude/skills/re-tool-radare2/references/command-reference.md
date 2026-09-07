# radare2 Command Reference

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

## FLIRT Signatures (stripped binaries)

Apply prebuilt FLIRT signature files to identify standard library functions:

```bash
zfs /path/to/vc140_x64.sig    # apply VC140 signatures
zfs /path/to/*.sig             # glob all .sig files
zfl                            # list bundled FLIRT sig files
zg                             # generate signatures for current binary
```

Community FLIRT database for MSVC: https://github.com/Maktm/FLIRTDB

## PDB Symbol Loading

```bash
e pdb.server=https://msdl.microsoft.com/download/symbols
idpd                  # download PDB from symbol server (uses pdb.server)
idp target.pdb        # load local PDB
. idpi*               # apply: import PDB symbols as r2 flags
rabin2 -PP target.dll # alternative: download PDB via rabin2
```

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

## Disassembly and Decompilation

```bash
pdf @ main          # disassemble function at symbol
pdf @ sym.send      # disassemble imported function wrapper
pdf @ 0x140001234   # disassemble function at address
pdg @ main          # Ghidra decompiler output (requires: r2pm -ci r2ghidra)
pdd @ main          # r2dec decompiler output (requires: r2pm -ci r2dec)
pdc @ main          # built-in pseudo-decompiler (experimental, no plugin needed)
```

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

## Radiff2 (Binary Diff)

```bash
radiff2 -C old.dll new.dll          # compare functions by name/hash
radiff2 -g main old.dll new.dll     # graphviz diff of specific function
```

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

## Optional Plugins

```bash
r2pm -ci r2ghidra   # Ghidra decompiler → pdg / pdgj (no Java required)
r2pm -ci r2dec      # r2dec decompiler → pdd
r2pm -ci r2frida    # Frida live instrumentation → frida:// IO
```
