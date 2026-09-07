# pefile Analysis (Windows PE/DLL)

```bash
pip install pefile   # if not installed
```

```python
import pefile, json, sys, hashlib

pe = pefile.PE(sys.argv[1])

# --- Headers ---
print("Machine:     ", hex(pe.FILE_HEADER.Machine))
print("TimeDateStamp:", pe.FILE_HEADER.TimeDateStamp)
print("Subsystem:   ", pe.OPTIONAL_HEADER.Subsystem)
print("ImageBase:   ", hex(pe.OPTIONAL_HEADER.ImageBase))
print("Is64:        ", pe.FILE_HEADER.Machine == 0x8664)

# --- .NET detection ---
if pe.OPTIONAL_HEADER.DATA_DIRECTORY[14].VirtualAddress != 0:
    print("*** .NET binary (managed) ***")

# --- Sections with per-section entropy ---
print("\nSections:")
for s in pe.sections:
    name    = s.Name.decode('utf-8','replace').strip('\x00')
    entropy = s.get_entropy()
    print(f"  {name:8s}  vaddr={hex(s.VirtualAddress):10s}  "
          f"size={s.SizeOfRawData:8d}  entropy={entropy:.2f}")

# --- Imports ---
if hasattr(pe, 'DIRECTORY_ENTRY_IMPORT'):
    print("\nImports:")
    for entry in pe.DIRECTORY_ENTRY_IMPORT:
        dll = entry.dll.decode('utf-8','replace')
        names = [imp.name.decode() if imp.name else f"ord_{imp.ordinal}"
                 for imp in entry.imports if imp.name or imp.ordinal]
        print(f"  {dll}: {', '.join(names[:8])}")

# --- Exports ---
if hasattr(pe, 'DIRECTORY_ENTRY_EXPORT'):
    print("\nExports:")
    for sym in pe.DIRECTORY_ENTRY_EXPORT.symbols:
        name = sym.name.decode() if sym.name else f"ord_{sym.ordinal}"
        print(f"  {sym.ordinal:5d}  {hex(sym.address):10s}  {name}")

# --- Version info (FileDescription, ProductName, etc.) ---
if hasattr(pe, 'FileInfo'):
    for fi in pe.FileInfo:
        for st in fi:
            if hasattr(st, 'StringTable'):
                for entry in st.StringTable:
                    for k, v in entry.entries.items():
                        print(f"  {k.decode()}: {v.decode()}")

# --- Rich header (compiler fingerprinting, MSVC only) ---
if pe.RICH_HEADER:
    rh_hash = pe.get_rich_header_hash()
    print(f"\nRich header hash (sha256): {rh_hash}")
    print("Rich header entries (tool_id, count):")
    for entry in pe.RICH_HEADER.entries:
        print(f"  comp_id={hex(entry[0]):#010x}  count={entry[1]}")
    # Note: absent Rich header → GCC/Clang/MinGW binary (not MSVC)

# --- Import hash (family clustering) ---
try:
    print(f"\nImphash: {pe.get_imphash()}")
except Exception:
    pass

# --- Overlay (data after last section — packing indicator) ---
overlay = pe.get_overlay()
if overlay:
    print(f"\nOverlay: {len(overlay)} bytes at offset {pe.get_overlay_data_start_offset():#x}")

# --- Checksum verification ---
print(f"\nChecksum stored:   {hex(pe.OPTIONAL_HEADER.CheckSum)}")
print(f"Checksum computed: {hex(pe.generate_checksum())}")
if pe.OPTIONAL_HEADER.CheckSum != pe.generate_checksum():
    print("  *** CHECKSUM MISMATCH — binary modified or packed ***")

# --- TLS Callbacks (anti-debug) ---
if hasattr(pe, 'DIRECTORY_ENTRY_TLS'):
    tls = pe.DIRECTORY_ENTRY_TLS.struct
    if tls.AddressOfCallBacks != 0:
        print(f"\n*** TLS CALLBACKS at {hex(tls.AddressOfCallBacks)} ***")
        print("  These run before DllMain — common anti-debug / initialization vector")

# --- PDB path (debug build artifact) ---
if hasattr(pe, 'DIRECTORY_ENTRY_DEBUG'):
    for d in pe.DIRECTORY_ENTRY_DEBUG:
        if hasattr(d.entry, 'PdbFileName'):
            print(f"\nPDB path: {d.entry.PdbFileName.decode('utf-8','replace')}")
```
