# RE Tool Reference

Quick-lookup commands and code snippets for `code-re-qt5`. All paths assume the RayStudio project; adjust `WINEPREFIX` and binary paths for other targets.

---

## §0 — analyze-binary-format.sh

See `scripts/analyze-binary-format.sh`. Usage:
```bash
./scripts/analyze-binary-format.sh <binary-path>
```

Produces: file type, header hex dump, sorted-unique strings, Shannon entropy estimate, float32 triple candidates.

---

## §1 — Ghidra + QtREAnalyzer Setup

```
1. Download Ghidra 11.x from https://ghidra-sre.org
2. Install QtREAnalyzer:
   - Releases: https://github.com/shenghuahe/QtREAnalyzer/releases
   - Copy .zip to $GHIDRA_HOME/Extensions/Ghidra/
   - Restart Ghidra → File → Install Extensions → enable QtREAnalyzer

3. Import DLL:
   File → Import File → select RHCore.dll
   Format: Portable Executable (PE)
   Language: x86:LE:64:default:windows  (or 32-bit if 32-bit binary)
   Options: Load External Libraries = No (avoids Wine DLL confusion)

4. Auto-analyze:
   Analysis → Auto Analyze → accept defaults, ensure "Demangler Microsoft" is checked

5. Run QtREAnalyzer:
   Analysis → One Shot → QtREAnalyzer
   Results appear in the Symbol Table and Comments

6. Find meta-objects manually if plugin misses any:
   Search → For Strings → filter "qt_static_metacall"
   Right-click → References → Show References To
   Navigate to the data XREFing qt_static_metacall — that is the QMetaObject::d struct
```

---

## §2 — Wine Relay Logging

```bash
export WINEPREFIX="$HOME/.wine-raystudio"

WINEDEBUG=+relay:ws2_32,+relay:kernel32,-all \
  wine ~/.wine-raystudio/drive_c/RayStudio/RayStudio.exe \
  2>/tmp/relay.log

# Filter for interesting calls
grep -E '(connect|send|recv|CreateFile|ReadFile|WriteFile)' /tmp/relay.log | head -100

# Watch live
tail -f /tmp/relay.log | grep -E '(connect|send|recv)'
```

**WINEDEBUG syntax**:
- `+relay:dll` — enable relay for named DLL
- `-all` — suppress all other debug channels
- Multiple DLLs: `+relay:ws2_32,+relay:kernel32`

---

## §3 — WineDbg + GDB Attach

```bash
# Terminal 1: start under winedbg
export WINEPREFIX="$HOME/.wine-raystudio"
winedbg --gdb --no-start \
  ~/.wine-raystudio/drive_c/RayStudio/RayStudio.exe

# Terminal 2: attach GDB (PORT shown in winedbg output)
gdb
(gdb) target remote localhost:PORT

# Breakpoints by symbol (if Qt5 debug symbols present)
(gdb) break Qt5Network!QTcpSocket::connectToHost
(gdb) break Qt5Core!QFile::open

# x86-64 Windows calling convention: RCX=this, RDX=arg1, R8=arg2, R9=arg3
(gdb) info registers rcx rdx r8 r9
(gdb) x/s $rdx   # print arg1 as string

(gdb) continue
```

---

## §4 — Frida Hook: ws2_32 send/recv

```python
# frida-hook-ws2.py
# Usage: python3 frida-hook-ws2.py <pid>
# Find PID: pgrep -f RayStudio.exe
# Wine processes are normal Linux processes — Frida attaches without Wine awareness.

import frida, sys

SCRIPT = """
const ws2 = Process.getModuleByName("ws2_32.dll");

const sendAddr = ws2.getExportByName("send");
Interceptor.attach(sendAddr, {
    onEnter(args) {
        const sock = args[0].toInt32();
        const len  = args[2].toInt32();
        const buf  = args[1].readByteArray(Math.min(len, 256));
        console.log("[send] sock=" + sock + " len=" + len);
        console.log(hexdump(buf, { ansi: true }));
    }
});

const recvAddr = ws2.getExportByName("recv");
Interceptor.attach(recvAddr, {
    onEnter(args) {
        this.buf    = args[1];
        this.maxlen = args[2].toInt32();
        this.sock   = args[0].toInt32();
    },
    onLeave(retval) {
        const len = retval.toInt32();
        if (len > 0) {
            console.log("[recv] sock=" + this.sock + " len=" + len);
            console.log(hexdump(this.buf.readByteArray(len), { ansi: true }));
        }
    }
});

console.log("[frida-hook-ws2] hooks installed");
""";

pid = int(sys.argv[1])
session = frida.attach(pid)
script = session.create_script(SCRIPT)
script.on('message', lambda m, d: print(m))
script.load()
sys.stdin.read()
```

```bash
# Install frida
pip install frida-tools

# Find Wine process PID
pgrep -a wine
pgrep -f RayStudio

# Run hook
python3 frida-hook-ws2.py $(pgrep -f RayStudio.exe)
```

---

## §5 — ImHex Pattern Template Skeleton

```cpp
// scanner_protocol.hexpat
// Load in ImHex: File → Load Pattern
#pragma endian little

struct FrameHeader {
    u8  magic[4];        // update after first capture
    u32 payload_len;
    u8  msg_type;
    u8  flags;
    u16 sequence;
};

struct Frame {
    FrameHeader header;
    u8          payload[header.payload_len];
};

Frame frames[while(!std::mem::eof())] @ 0x00;
```

**ImHex workflow**:
1. File → Open → select raw TCP stream binary
2. View → Pattern Editor → paste template above
3. Adjust `magic` bytes to match observed header
4. Use Entropy view (View → Entropy) to locate payload boundaries
5. Use "Find Similar" on a suspected repeated struct to count instances

---

## §6 — Kaitai Struct Skeleton

```yaml
# scanner_protocol.ksy
meta:
  id: scanner_protocol
  title: RayStudio Scanner Protocol
  endian: le

doc: |
  Wire protocol between RayStudio and Raven LiDAR scanner.
  Status: DRAFT — field names are hypotheses pending confirmation.

seq:
  - id: frames
    type: frame
    repeat: eos

types:
  frame:
    seq:
      - id: magic
        contents: [0x52, 0x41, 0x56, 0x4e]  # "RAVN" — update as needed
      - id: payload_len
        type: u4
      - id: msg_type
        type: u1
        enum: msg_type_enum
      - id: flags
        type: u1
      - id: sequence
        type: u2
      - id: payload
        size: payload_len
        type:
          switch-on: msg_type
          cases:
            'msg_type_enum::point_cloud': point_cloud_payload
            _: raw_payload

  point_cloud_payload:
    seq:
      - id: point_count
        type: u4
      - id: points
        type: point3f
        repeat: expr
        repeat-expr: point_count

  point3f:
    seq:
      - id: x
        type: f4
      - id: y
        type: f4
      - id: z
        type: f4

  raw_payload:
    seq:
      - id: data
        size-eos: true

enums:
  msg_type_enum:
    0x01: handshake
    0x02: scan_start
    0x03: scan_stop
    0x10: point_cloud
    0x20: status
    0xff: error
```

```bash
# Install: yay -S kaitai-struct-compiler  (Arch/Manjaro)
ksc -t python scanner_protocol.ksy

# Test against a capture
python3 - <<'EOF'
from scanner_protocol import ScannerProtocol
from kaitaistruct import KaitaiStream
import io

data = open('docs/re/captures/session-001.bin', 'rb').read()
parsed = ScannerProtocol(KaitaiStream(io.BytesIO(data)))
for frame in parsed.frames:
    print(f"type={frame.msg_type} seq={frame.sequence} len={frame.payload_len}")
EOF
```

---

## §7 — Float32 Triple Pattern Search

```python
#!/usr/bin/env python3
# Usage: python3 find-float-triples.py <binary-file> [min_val] [max_val]
import sys, struct

path = sys.argv[1]
lo = float(sys.argv[2]) if len(sys.argv) > 2 else -10000.0
hi = float(sys.argv[3]) if len(sys.argv) > 3 else  10000.0

data = open(path, 'rb').read()
hits = []
for i in range(0, len(data) - 12, 4):
    try:
        x, y, z = struct.unpack_from('<fff', data, i)
        if (all(lo < v < hi for v in (x, y, z)) and
                all(v == v for v in (x, y, z))):
            hits.append((i, x, y, z))
    except Exception:
        pass

print(f"Found {len(hits)} float32 triples in [{lo}, {hi}]")
for offset, x, y, z in hits[:20]:
    print(f"  0x{offset:08x}: ({x:10.4f}, {y:10.4f}, {z:10.4f})")
if len(hits) > 20:
    print(f"  ... and {len(hits)-20} more")
```

---

## §8 — Useful One-Liners

```bash
# PE DLL export table (inside nix develop)
wine dumpbin /EXPORTS RHCore.dll 2>/dev/null | head -80

# Demangled C++ symbols from a DLL
strings RHCore.dll | c++filt | grep -E '^[A-Z]' | sort -u | head -40

# Check 32 vs 64 bit
file ~/.wine-raystudio/drive_c/RayStudio/*.dll | grep -E '32|64'

# Quick entropy of whole file
python3 -c "
import sys,math,collections
d=open(sys.argv[1],'rb').read()
c=collections.Counter(d); t=len(d)
e=-sum((v/t)*math.log2(v/t) for v in c.values() if v)
print(f'{sys.argv[1]}: {e:.3f} bits/byte')
" <file>

# Watch network connections opened by Wine
ss -tnp | grep wine

# tcpdump capture (scanner's Wi-Fi AP is typically 192.168.x.x)
sudo tcpdump -i wlan0 -w /tmp/scanner.pcap host 192.168.1.1

# tcpdump on loopback (USB-redirected network)
sudo tcpdump -i lo -w /tmp/scanner-lo.pcap
```
