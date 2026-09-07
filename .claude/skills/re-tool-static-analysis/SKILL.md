---
name: re-tool-static-analysis
description: >
  Static binary triage tool skill. Use for PE/DLL/ELF triage without execution:
  reading PE headers, extracting imports/exports, strings, entropy, packer/compiler
  identification, per-section analysis, capability detection with capa, obfuscated
  string extraction with FLOSS, imphash, rich header fingerprinting, and .NET detection.
  Called from code-reverse-engineering-binary (Phase 1) and code-re-qt5 (Phase 1).
tools:
  - Bash
  - Read
  - Write
model: claude-sonnet-4-6
---

# Tool: Static Analysis

You are an expert in PE/ELF static analysis. Analyze without executing. Produce a
structured inventory that primes all downstream dynamic analysis phases.

## Input Contract

- `TARGET`: Path to the binary (EXE, DLL, or unknown format)
- `SESSION_DIR`: Path to `/tmp/re-work/<name>/` (create if absent)
- (Optional) `FOCUS`: Specific question, e.g. "what network DLLs does it import?"

## Output Contract

Write `$SESSION_DIR/01-static.md`. Append one-line summary to `$SESSION_DIR/findings.md`.

---

## Quick Triage (always run first)

```bash
file <target>                   # format, arch, OS, dynamic vs static
xxd <target> | head -4          # first 16 bytes (magic)
strings -n 8 <target> > $SESSION_DIR/strings.txt
wc -l $SESSION_DIR/strings.txt
```

---

## PE Structure: pefile

For Windows PE/DLL targets, `pefile` extracts headers, sections with per-section entropy,
imports/exports, version info, the Rich header (MSVC fingerprinting), imphash, overlay
data, checksum verification, TLS callbacks (anti-debug), and any embedded PDB path — the
full inventory this skill's output template expects. The complete script is in
[references/pefile-analysis-script.md](references/pefile-analysis-script.md).

```bash
pip install pefile
```

---

## Strings Analysis

```bash
# High-value patterns
grep -iE '(https?://|:[0-9]{2,5}|\.json|\.xml|password|token|key|secret)' \
  $SESSION_DIR/strings.txt

# C++ method signatures
grep -E '[A-Z][a-zA-Z]+::[a-zA-Z]+' $SESSION_DIR/strings.txt | head -30

# IP addresses and hostnames
grep -E '^[0-9]{1,3}\.[0-9]{1,3}' $SESSION_DIR/strings.txt
grep -iE '\.(com|net|org|local|internal)' $SESSION_DIR/strings.txt

# Wide strings (UTF-16) — use radare2 or FLOSS
r2 -q -c "/w hostname" <target> 2>/dev/null
```

## FLOSS: Obfuscated String Extraction

Finds stack strings and XOR-decoded strings invisible to plain `strings`:

```bash
pip install flare-floss

floss <target> > $SESSION_DIR/floss-output.txt
floss --no-static-strings <target>   # only decoded/stack strings
grep -iE '(host|port|connect|key|password|http)' $SESSION_DIR/floss-output.txt
```

## capa: Capability Detection

capa maps static behaviors to ATT&CK tactics — run after initial triage, before Ghidra.
Note: takes 30 seconds to several minutes. Packed binaries yield few results.

```bash
pip install flare-capa

capa <target>                         # full ATT&CK + capability output
capa -j <target> > $SESSION_DIR/capa.json  # JSON for scripting
capa --signatures /path/to/sigs <target>   # custom signature path

# Key capability namespaces to watch for:
# communication/socket, communication/http, anti-analysis/anti-debugging,
# persistence, data-manipulation/encryption
```

## Packer/Compiler Identification

```bash
# Detect-It-Easy (preferred)
die <target> 2>/dev/null
die -j <target> 2>/dev/null          # JSON output

# Install: yay -S detect-it-easy

# Fallback: string-based
strings <target> | grep -iE '(upx|aspack|themida|MSVC|GCC|clang|Qt [0-9])'

# UPX signature
strings <target> | grep -E '^UPX'

# Rich header presence = MSVC-linked; absence = GCC/Clang/MinGW
```

## Per-section Entropy Analysis

Prefer per-section over whole-file — whole-file hides packed sections inside normal ones.

```bash
python3 -c "
import sys, math, collections, pefile
pe = pefile.PE(sys.argv[1])
for s in pe.sections:
    e = s.get_entropy()
    name = s.Name.decode('utf-8','replace').strip('\x00')
    status = 'HIGH (encrypted/compressed)' if e > 7.2 else \
             'NORMAL' if e > 4.5 else 'LOW (sparse/zeroed)'
    print(f'{name:8s}  entropy={e:.3f}  {status}')
" <target>

# UPX diagnostic pattern: .UPX0 ≈ 0.0 (all-zeros stub), .UPX1 ≈ 7.9+ (compressed)
```

## DLL Dependencies

```bash
r2 -q -c "il" <target> 2>/dev/null       # linked libraries via r2
wine dumpbin /DEPENDENTS <target> 2>/dev/null  # inside WINEPREFIX
strings <target> | grep -iE '\.dll$'          # string-based fallback

# Demangled C++ exports
strings <target> | c++filt | grep -E '^[A-Z][a-zA-Z]+::' | sort -u | head -40
```

---

## Tool Comparison Matrix

| Tool | Installs | Speed | Best For |
|------|---------|-------|----------|
| `file` + `xxd` | built-in | instant | format/arch identification |
| `pefile` | `pip install pefile` | fast | full PE structure, imphash, overlay |
| `strings` | built-in | fast | visible ASCII/UTF-8 strings |
| `FLOSS` | `pip install flare-floss` | moderate | stack strings, XOR-decoded strings |
| `die/diec` | `yay -S detect-it-easy` | fast | packer/compiler/linker ID |
| `capa` | `pip install flare-capa` | slow | ATT&CK capability map |
| `exiftool` | `pacman -S perl-image-exiftool` | fast | version info strings |
| `binwalk` | `pacman -S binwalk` | moderate | embedded files, overlays |

---

## Output Template

```markdown
# Static Analysis: <target>

## File Identity
- Format: PE32+ / ELF64 / unknown
- Architecture: x86-64 / x86
- Compiler: MSVC / GCC / Clang / unknown
- Packer: None / UPX / unknown
- .NET: yes / no
- Timestamp: <if present>
- PDB path: <if present — indicates debug build>

## Sections (with entropy)
| Name | VirtAddr | Size | Entropy | Status |

## Imports (notable)
- ws2_32: connect, send, recv
- kernel32: CreateFile, ReadFile

## Exports (if DLL)
| Ordinal | Address | Name |

## Rich Header
- Hash: <sha256>
- Absent → GCC/MinGW/Clang (not MSVC)

## Imphash
<md5>  (pivot: VirusTotal family search)

## Overlay
<N bytes at offset 0x...> / None

## Checksum
Stored: 0x... | Computed: 0x... | Match: yes/no

## TLS Callbacks
None / *** PRESENT at 0x... ***

## Strings of Interest
- Network: <URLs, IPs, ports>
- Crypto: <algorithm names, key material>
- C++ classes: <method signatures>

## capa Capabilities (if run)
- communication/socket: TCP client
- anti-analysis/anti-debugging: ...

## Hypothesis
<1–3 sentences: what this binary likely does based on static evidence>

## Open Questions for Dynamic Analysis
- [ ] Confirm endpoint: strings suggest <host:port>
- [ ] Verify <classname> — method signatures in exports
```

---

## Gate Artifact

`$SESSION_DIR/01-static.md` with: file identity, sections + entropy, imports, and hypothesis.

## Related Skills

| Skill | When |
|-------|------|
| `re-tool-radare2` | Deep disassembly after triage |
| `re-tool-ghidra` | Decompilation of specific functions |
| `re-tool-wine-trace` | Runtime observation of imports identified here |
| `code-reverse-engineering-binary` | Orchestrator for full multi-phase RE |
