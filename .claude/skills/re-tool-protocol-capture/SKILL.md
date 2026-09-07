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

For device-hardware protocols where nothing shows up on a network interface, capture at
the USB/HID layer instead — see
[references/usb-hid-capture.md](references/usb-hid-capture.md). For encrypted traffic on
a Wine target, intercept at the libgnutls layer before it hits the wire — see
[references/tls-interception.md](references/tls-interception.md).

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

Once the framing is understood, a Wireshark Lua dissector makes future captures
self-annotating — see
[references/wireshark-lua-dissector.md](references/wireshark-lua-dissector.md).

---

## Stream Reassembly Edge Cases

| Problem | Symptom | Fix |
|---------|---------|-----|
| "Previous segment not captured" | Partial stream only | Recapture starting from connection |
| Checksum failure | tshark skips reassembly | `tshark -o tcp.check_checksum:FALSE` |
| Out-of-order misread as retransmit | Gaps in stream | Wireshark GitLab #15993; use `tshark -2` (two-pass) |
| Multi-PDU gap | Late PDU delivery | Increase `tcp.reassembly_table_size` in prefs |

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
