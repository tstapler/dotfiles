---
name: re-tool-kaitai
description: >
  Kaitai Struct schema authoring tool skill. Use when writing .ksy specs for binary
  protocols or file formats, using the expression language (instances, bit fields,
  process transforms, valid assertions), compiling with ksc, validating with ksv,
  generating Python/Rust/C++ parsers, or debugging a failing parse.
  Called from code-reverse-engineering-binary (Phase 7) and code-re-qt5 (Phase 4–5).
  Current stable: Kaitai Struct v0.11 (2025).
tools:
  - Bash
  - Read
  - Write
model: claude-sonnet-4-6
---

# Tool: Kaitai Struct Schema Authoring

You are an expert in Kaitai Struct binary format specification. You turn empirical
observations into validated, machine-parseable specs. All field names are hypotheses
until a successful parse confirms them.

## Input Contract

- `SESSION_DIR`: Path to `/tmp/re-work/<name>/`
- `FORMAT_NAME`: Identifier for the format (e.g. `scanner_protocol`)
- `SAMPLE_FILES`: Binary samples to validate against
- `PRIOR`: `06-protocol.md` — read for field hypothesis table
- `ENDIAN`: `le` or `be`

## Output Contract

Write `$SESSION_DIR/07-<format-name>.ksy` and `07-<format-name>-notes.md`.
Append one-line summary to `$SESSION_DIR/findings.md`.

---

## Kaitai Struct DSL Reference

### Meta block

```yaml
meta:
  id: my_format          # snake_case identifier
  title: "Human Name"
  endian: le             # le or be — applies globally
  bit-endian: be         # be=MSB first, le=LSB first (for bN fields)
  encoding: UTF-8        # default string encoding
  imports:
    - /common/vlq_base128_le  # standard library import
```

### Scalar Types

| Type | Size | Notes |
|------|------|-------|
| `u1` `u2` `u4` `u8` | 1/2/4/8 bytes | unsigned; `u2le`/`u2be` override endian |
| `s1` `s2` `s4` `s8` | 1/2/4/8 bytes | signed |
| `f4` `f8` | 4/8 bytes | float (IEEE 754) |
| `b1`–`b64` | N bits | bit field; `b4le` overrides bit-endian |
| `str` | variable | needs `size` or `terminator` |
| `strz` | until null | null-terminated string shorthand |

### Repeat

```yaml
- id: items
  type: item
  repeat: eos           # until end of stream
  
- id: records
  type: record
  repeat: expr
  repeat-expr: count    # repeat count times (count = field name or expression)
  
- id: chunks
  type: chunk
  repeat: until
  repeat-until: '_.tag == 0xFF'   # _ = last parsed element
```

### String Handling

```yaml
- id: label
  type: strz                   # null-terminated
  encoding: UTF-8

- id: wide_name
  type: strz                   # v0.11: correctly finds 2-byte null for UTF-16
  encoding: UTF-16LE

- id: fixed_str
  type: str
  size: 16
  encoding: ASCII
  terminator: 0                # stop at null within the 16 bytes
  consume: true                # advance past terminator
  include: false               # exclude terminator from value
  eos-error: false             # don't error if stream ends first

- id: length_prefixed
  type: str
  size: str_len                # reads str_len bytes as string
  encoding: UTF-8
```

Encoding names are case-sensitive: `UTF-8`, `UTF-16LE`, `UTF-16BE`, `ASCII`, `ISO-8859-1`.

---

## Expression Language

Used in `size`, `repeat-expr`, `if`, `pos` (instances), `value` (instances), `valid/expr`.

### Operators

```
Arithmetic:  + - * / %
Relational:  < <= > >= == !=
Bitwise:     << >> & | ^
Logical:     and or not
Ternary:     condition ? if_true : if_false
```

### Special Variables

| Variable | Meaning |
|----------|---------|
| `_` | Current element in `repeat-until` |
| `_io` | Current stream object |
| `_root` | Root struct (top-level type) |
| `_parent` | Enclosing struct |
| `_index` | Current loop index in `repeat: expr` or `eos` |

### Method Calls

```yaml
# Integer: .to_s → decimal string
# Float: .to_i → truncate to int
# String: .length, .reverse, .substring(from, to), .to_i(radix)
# Byte array: .length, .to_s("UTF-8")
# Array: .first, .last, .size, .min, .max
```

### sizeof Operators (compile-time constants only)

```yaml
size: sizeof<u4>              # 4
size: bitsizeof<b13>          # 13
size: total - header._sizeof  # subtract fixed-size field's byte count
```

---

## Instances (Lazy Fields)

Instances live outside `seq` and are evaluated lazily (first access only).

```yaml
instances:
  # Computed value (no I/O)
  is_compressed:
    value: 'flags & 0x02 != 0'

  # Seek to absolute offset in current stream
  header:
    pos: 0
    type: file_header

  # Seek in a different stream (e.g. root stream from inside a substream)
  lookup:
    io: _root._io
    pos: table_offset
    size: table_size
    type: table_entry

  # Stream introspection
  bytes_remaining:
    value: '_io.size - _io.pos'
  at_eof:
    value: _io.eof
```

---

## Bit Fields

```yaml
meta:
  bit-endian: be        # be=MSB first (network byte order); le=LSB first

seq:
  - id: version         # 4 MSBs
    type: b4
  - id: ihl             # 4 LSBs — completes the byte
    type: b4
  - id: dscp
    type: b6
  - id: ecn             # per-field override
    type: b2le          # little-endian 2-bit field
```

Rules: `b1`=0 or 1. After a run of bN fields, next byte-aligned field auto-aligns. Bit fields cannot use `process`, `if`, or `repeat`.

---

## Process Transforms

```yaml
- id: body
  size: body_len
  process: zlib           # inflate (deflate/zlib compressed data)

- id: xored
  size: data_len
  process: xor(0xAA)      # single-byte XOR key

- id: rotated
  size: data_len
  process: rol(3)         # rotate left 3 bits; ror(n) rotates right
```

Custom transform: reference a class name as the process identifier. The class must provide a static `decode(data: bytes) -> bytes` method in the generated language's namespace.

---

## Validation (valid)

```yaml
- id: magic
  type: u4be
  valid: 0x89504E47                    # exact match

- id: version
  type: u1
  valid:
    min: 1
    max: 3

- id: type_field
  type: u1
  valid:
    any-of: [0x01, 0x02, 0x04]        # whitelist

- id: cmd
  type: u1
  enum: command_type
  valid:
    in-enum: true                      # must be a known enum value (v0.11)

- id: checksum
  type: u2
  valid:
    expr: '_ == computed_crc'          # _ = current field value
```

On failure: raises `ValidationNotEqualError`, `ValidationNotAnyOfError`, etc.
In v0.11, `valid` applies per-element on repeated fields.

---

## Standard Library Imports

```yaml
meta:
  imports:
    - /common/vlq_base128_le    # unsigned varint (LEB128, little-endian)
    - /common/vlq_base128_be    # unsigned varint (big-endian base-128)
    - /common/bytes_with_io     # byte array that exposes an _io stream handle
```

Use `bytes_with_io` when you need to parse a subfield's bytes as a new stream:

```yaml
- id: compressed
  size: comp_len
  process: zlib
  type: bytes_with_io       # .compressed._io is now a usable KaitaiStream
```

---

## ksc: Compile and Validate

```bash
# Install (Arch/Manjaro)
yay -S kaitai-struct-compiler

# Compile to Python
ksc -t python  $SESSION_DIR/07-<format>.ksy -d $SESSION_DIR/

# Compile to other targets
ksc -t rust    $SESSION_DIR/07-<format>.ksy -d $SESSION_DIR/   # NEW in v0.11
ksc -t cpp_stl $SESSION_DIR/07-<format>.ksy -d $SESSION_DIR/
ksc -t java    $SESSION_DIR/07-<format>.ksy -d $SESSION_DIR/ --java-package com.example
ksc -t all     $SESSION_DIR/07-<format>.ksy -d $SESSION_DIR/

# Check syntax only
ksc --syntax-check $SESSION_DIR/07-<format>.ksy
```

---

## Test Parse (Python)

```python
import sys, importlib.util, io
from kaitaistruct import KaitaiStream, ValidationNotEqualError, EndOfStreamError

def load_ksy_class(py_path, class_name):
    spec = importlib.util.spec_from_file_location(class_name, py_path)
    mod  = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return getattr(mod, class_name)

cls  = load_ksy_class("$SESSION_DIR/<FormatName>.py", "<FormatName>")
data = open(sys.argv[1], 'rb').read()

try:
    parsed = cls(KaitaiStream(io.BytesIO(data)))
    parsed._read()
    for i, frame in enumerate(parsed.frames):
        print(f"[{i}] type={frame.msg_type} len={frame.payload_len}")
        if i >= 5: break
except ValidationNotEqualError as e:
    print(f"Validation failed at {e.path}: expected {e.expected!r}, got {e.actual!r}")
except EndOfStreamError as e:
    print(f"Ran out of data: {e}")
```

---

## Debugging Failing Parses

1. **Web IDE first**: drag binary + .ksy to https://ide.kaitai.io — v0.11 shows partial tree with error-flagged fields and hex highlighting.

2. **Drain to see what's left**:
   ```yaml
   - id: rest
     size-eos: true
   ```

3. **Inspect current stream position** via instance:
   ```yaml
   instances:
     pos_debug:
       value: _io.pos
   ```

4. **Offset confusion in substreams**: inside a type with `size: n`, `_io.pos` is relative to the substream (0…n). Use `io: _root._io` in an instance to get root-relative position.

5. **Bit-field misalignment**: after incomplete bit-field groups, the next byte-aligned field auto-aligns. Off-by-less-than-1-byte errors usually mean an unfinished `bN` group.

---

## ImHex vs Kaitai Decision

| Use ImHex when | Use Kaitai when |
|----------------|-----------------|
| Format still unclear — need interactive exploration | Structure understood — want a reusable parser |
| Quick one-off visualization | Need Python/Rust/Java/C++ output |
| In-place encryption/decryption in pattern | Need CI-testable format definition |
| No compile step | Want to share via formats.kaitai.io |

**Workflow**: ImHex first (orient, find fields) → Kaitai (formalize, generate parsers).

---

## Complete Skeleton

```yaml
meta:
  id: target_protocol
  title: "Target Protocol — DRAFT"
  endian: le
  doc: |
    Wire protocol observed from <target>. Status: DRAFT.

seq:
  - id: frames
    type: frame
    repeat: eos

types:
  frame:
    seq:
      - id: magic
        contents: [0x??, 0x??, 0x??, 0x??]   # UPDATE from captures/stream-0.bin
      - id: payload_len
        type: u4
      - id: msg_type
        type: u1
        enum: msg_type_enum
        valid:
          in-enum: true
      - id: reserved
        type: u2
      - id: payload
        size: payload_len
        type:
          switch-on: msg_type
          cases:
            _: raw_payload

  raw_payload:
    seq:
      - id: data
        size-eos: true

enums:
  msg_type_enum:
    0x01: unknown_01    # rename as identified
```

---

## Gate Artifact

`$SESSION_DIR/07-<format>.ksy` that parses at least one sample without error, plus
`07-<format>-notes.md` with field confidence ratings.

## Related Skills

| Skill | When |
|-------|------|
| `re-tool-protocol-capture` | Must run first — provides sample binaries |
| `re-tool-frida` | More samples if captures are insufficient |
| `code-reverse-engineering-binary` | Orchestrator for full RE workflow |
