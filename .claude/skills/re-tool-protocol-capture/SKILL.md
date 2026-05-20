---
name: re-tool-protocol-capture
description: >
  Network protocol capture and analysis tool skill. Use when capturing TCP/UDP traffic,
  extracting raw streams with tshark, analyzing packet structure, identifying message
  framing, or preparing binary captures for Kaitai schema authoring. Covers tcpdump,
  tshark (JSON output, decode-as, statistics), ngrep, USB capture, and TLS interception
  via ecapture for Wine targets.
  Called from code-reverse-engineering-binary (Phase 6) and code-re-qt5 (Phase 4).
tools:
  - Bash
  - Read
  - Write
model: claude-sonnet-4-6
---

# Tool: Protocol Capture

You are an expert in network traffic capture and binary protocol analysis. Your job is to
capture traffic, extract raw payloads, and characterize message structure for schema authoring.

## Input Contract

- `INTERFACE`: Network interface (`wlan0`, `eth0`, `lo`)
- `TARGET_HOST` / `TARGET_PORT`: Endpoint (from Phase 4 trace)
- `SESSION_DIR`: Path to `/tmp/re-work/<name>/`
- `OPERATION`: User action that triggers traffic (e.g. "start a scan")
- `PRIOR`: `04-api-trace.md` and `05-hooks.md` for endpoint and protocol hints

## Output Contract

Write `$SESSION_DIR/06-protocol.md`. PCAP and streams → `$SESSION_DIR/captures/`.
Append one-line summary to `$SESSION_DIR/findings.md`.

---

## Step 1 — tshark Statistics (First-pass Triage)

Run these before extracting streams — they reveal the protocol structure at a glance.

```bash
# Protocol hierarchy (what's actually in the capture)
tshark -r session-001.pcap -q -z io,phs 2>/dev/null

# TCP conversation summary (endpoints, bytes, packets)
tshark -r session-001.pcap -q -z conv,tcp 2>/dev/null

# Expert info (retransmissions, out-of-order, errors)
tshark -r session-001.pcap -q -z expert 2>/dev/null

# Packet lengths distribution
tshark -r session-001.pcap -q -z plen,tree 2>/dev/null
```

---

## Step 2 — Capture

```bash
mkdir -p $SESSION_DIR/captures

# Targeted capture (best — minimal noise)
sudo tcpdump -i <interface> \
  host <target-host> and port <target-port> \
  -w $SESSION_DIR/captures/session-001.pcap

# Save as pcapng (preferred format — supports TLS key embedding)
sudo tcpdump -i <interface> host <target-host> \
  -w $SESSION_DIR/captures/session-001.pcapng

# Loopback (USB-redirected or local sockets)
sudo tcpdump -i lo -w $SESSION_DIR/captures/session-lo.pcap

# Stop after N packets
sudo tcpdump -i <interface> -c 200 host <target-host> \
  -w $SESSION_DIR/captures/session-001.pcap
```

### Useful tcpdump BPF Filters

```bash
# Non-standard port (e.g. port 9999)
host 192.168.1.100 and port 9999

# Any TCP with payload (no SYN/ACK/FIN-only)
host 192.168.1.100 and tcp and tcp[tcpflags] & (tcp-syn|tcp-fin|tcp-rst) == 0

# Match magic bytes at TCP payload offset 0 (e.g. "RAVN")
tcp[20:4] = 0x5241564e

# Byte at protocol offset (proto[offset:size] syntax)
tcp[20:1] = 0x01        # first byte of TCP payload = 0x01

# UDP only
host 192.168.1.100 and udp
```

---

## Step 3 — Extract Raw TCP Stream

```bash
# List all TCP streams in capture
tshark -r session-001.pcap -q -z conv,tcp 2>/dev/null | head -30

# Extract stream N as raw binary (both directions combined)
tshark -r session-001.pcap \
  -q -z follow,tcp,raw,0 \
  2>/dev/null | tail -n +7 | tr -d '\n' | xxd -r -p \
  > $SESSION_DIR/captures/stream-0.bin

# Extract stream with field filter (JSON output for scripted analysis)
tshark -r session-001.pcap \
  -T json \
  -e tcp.stream -e tcp.payload -e frame.number \
  -Y "tcp.stream==0 and tcp.payload" \
  2>/dev/null > $SESSION_DIR/captures/stream-0.json

# Force protocol decode when non-standard port is used
tshark -r session-001.pcap \
  -d tcp.port==9999,my_proto \
  -T json 2>/dev/null > ...
```

---

## Step 4 — Structural Analysis

```bash
# Entropy of raw stream
python3 -c "
import sys,math,collections
d=open(sys.argv[1],'rb').read()
c=collections.Counter(d); t=len(d)
e=-sum((v/t)*math.log2(v/t) for v in c.values() if v)
print(f'Entropy: {e:.3f} bits/byte ({len(d)} bytes)')
print('High (>7.2)=compressed/encrypted; Low (<5)=structured')
" $SESSION_DIR/captures/stream-0.bin

# Find most common 4-byte sequences (magic byte candidates)
python3 -c "
data = open('$SESSION_DIR/captures/stream-0.bin','rb').read()
from collections import Counter
cands = Counter(data[i:i+4] for i in range(0, len(data)-4, 1))
print('Top 4-byte sequences:')
for seq, n in cands.most_common(10):
    print(f'  {seq.hex()} ({n}x)')
" 

# Hex dump of first 256 bytes
xxd $SESSION_DIR/captures/stream-0.bin | head -16

# ngrep: live pattern search (regex + BPF, faster than tshark for hypothesis testing)
sudo ngrep -x -q 'RAVN' \
  host <target-host> and port <target-port>
# -x = hex output; -q = quiet; -W byline for text protocols
```

---

## TLS Interception (Wine Targets)

Wine's `secur32.dll` calls the **host system's `libgnutls.so`** via a push/pull adapter.
This means `ecapture gnutls` intercepts Wine app TLS at the libgnutls layer — no proxy,
no certificate pinning bypass needed.

```bash
# Install ecapture (eBPF-based TLS capture)
# Arch: yay -S ecapture  OR  download from: https://github.com/gojue/ecapture/releases

# Capture TLS plaintext from Wine process
sudo ecapture gnutls --pid <wine-pid> \
  -w $SESSION_DIR/captures/tls-plaintext.pcap

# Alternatively, extract session keys and embed in pcapng
SSLKEYLOGFILE=$SESSION_DIR/captures/tls-keys.log \
  WINEPREFIX=~/.wine-target wine target.exe

# Embed keys into pcapng for self-contained sharing
editcap --inject-secrets tls,$SESSION_DIR/captures/tls-keys.log \
  session-001.pcap $SESSION_DIR/captures/session-tls.pcapng
```

Note: If target uses statically-linked BoringSSL (uncommon in Win32 apps), ecapture may
not intercept — use Frida hooks on the SSL_write/SSL_read functions instead.

---

## USB / HID Capture

For hardware device protocols over USB:

```bash
# Load usbmon kernel module
sudo modprobe usbmon

# Grant capture permissions (or run as root)
sudo setfacl -m u:$USER:r /dev/usbmon*

# Find USB device bus number
lsusb | grep -i "scanner\|device-name"
# e.g. "Bus 001 Device 004" → capture on usbmon1

# Capture USB traffic
sudo tcpdump -i usbmon1 -w $SESSION_DIR/captures/usb-session.pcap

# In Wireshark/tshark: filter by device address
tshark -r usb-session.pcap -Y "usb.device_address==4" \
  -T fields -e usb.capdata 2>/dev/null | tr -d ':' | xxd -r -p \
  > $SESSION_DIR/captures/usb-payload.bin

# For HID devices: simpler — read directly
xxd /dev/hidraw0 | head -40
```

---

## Stream Reassembly Edge Cases

| Problem | Symptom | Fix |
|---------|---------|-----|
| "Previous segment not captured" | Partial stream only | Recapture starting from connection |
| Checksum failure | tshark skips reassembly | `tshark -o tcp.check_checksum:FALSE` |
| Out-of-order misread as retransmit | Gaps in stream | Wireshark GitLab #15993; use `tshark -2` (two-pass) |
| Multi-PDU gap | Late PDU delivery | Increase `tcp.reassembly_table_size` in prefs |

---

## Wireshark Lua Dissector (once structure is known)

```lua
-- minimal_dissector.lua
-- Load: tshark -X lua_script:minimal_dissector.lua -r session.pcap
local proto = Proto("myproto", "My Protocol")

local fields = {
    magic      = ProtoField.uint32("myproto.magic",   "Magic",   base.HEX),
    length     = ProtoField.uint32("myproto.length",  "Length",  base.DEC),
    msg_type   = ProtoField.uint8 ("myproto.type",    "Type",    base.HEX),
    payload    = ProtoField.bytes ("myproto.payload", "Payload"),
}
proto.fields = fields

function proto.dissector(buf, pinfo, tree)
    if buf:len() < 9 then
        pinfo.desegment_len = DESEGMENT_ONE_MORE_SEGMENT
        return
    end
    local payload_len = buf(4, 4):le_uint()
    local total = 9 + payload_len
    if buf:len() < total then
        pinfo.desegment_len = total - buf:len()
        return
    end
    pinfo.cols.protocol = "MYPROTO"
    local t = tree:add(proto, buf(0, total))
    t:add_le(fields.magic,    buf(0, 4))
    t:add_le(fields.length,   buf(4, 4))
    t:add   (fields.msg_type, buf(8, 1))
    t:add   (fields.payload,  buf(9, payload_len))
end

-- Register on port (or use heuristic checker)
DissectorTable.get("tcp.port"):add(9999, proto)
```

---

## Protocol Analysis Checklist

- [ ] Magic bytes: first 2–8 bytes of each apparent message?
- [ ] Length field: 4-byte LE/BE uint = remaining bytes? At what offset?
- [ ] Message type: 1-byte? 2-byte? What values appear?
- [ ] Header fixed size or variable?
- [ ] Payload encoding: raw binary, JSON, protobuf, TLV?
- [ ] Session handshake distinguishable?
- [ ] Endianness: `le` or `be`?
- [ ] Framing: length-prefixed, delimiter-terminated, or fixed-size records?

---

## Output Template

```markdown
# Protocol Capture: <target>

## Capture Session
- Interface: <iface> | Endpoint: <host:port> | Protocol: TCP/UDP
- PCAP: captures/session-001.pcap | Stream: captures/stream-0.bin (<N> bytes)

## Stream Properties
- Entropy: X.XX bits/byte | Framing: length-prefixed / delimiter / fixed

## Message Structure Hypothesis
| Offset | Size | Type | Examples | Hypothesis |
|--------|------|------|----------|-----------|
| 0 | 4 | magic | 52 41 56 4E | "RAVN" frame magic |
| 4 | 4 | u32le | 0x18 | payload length |
| 8 | 1 | u8 | 0x01, 0x10 | message type |

## Open Questions
- [ ] Length inclusive or exclusive of header?
```

---

## Gate Artifact

`$SESSION_DIR/06-protocol.md` with: structure hypothesis table, observed message types,
and at least one raw stream binary file.

## Related Skills

| Skill | When |
|-------|------|
| `re-tool-frida` | Individual payload capture when pcap is insufficient |
| `re-tool-kaitai` | Formalize hypothesis into validated .ksy spec |
| `re-tool-wine-trace` | Confirm endpoint before starting capture |
