# Wine Gadget Injection (Full Steps)

`frida.attach(pid)` crashes on Wine processes (GitHub issue #3339 — not fixed).
Direct attachment hits "Unable to locate the libc" and kills the target.

## Working approach: frida-gadget.dll injection

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

## Alternative: frida-gadget config file

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
