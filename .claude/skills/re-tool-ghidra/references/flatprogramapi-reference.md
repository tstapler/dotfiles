# FlatProgramAPI Reference

In headless scripts, all FlatProgramAPI methods are callable as bare names. `currentProgram` is available directly.

## Functions

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

## Symbols and Imports

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

## Cross-References

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

## Memory Blocks (Sections)

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

## Decompiler API

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

## JSON Output Pattern

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
