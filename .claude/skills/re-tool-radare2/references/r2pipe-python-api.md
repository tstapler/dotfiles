# r2pipe Python API

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
