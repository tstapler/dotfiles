# Kaitai Struct DSL Reference

## Meta block

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

## Scalar Types

| Type | Size | Notes |
|------|------|-------|
| `u1` `u2` `u4` `u8` | 1/2/4/8 bytes | unsigned; `u2le`/`u2be` override endian |
| `s1` `s2` `s4` `s8` | 1/2/4/8 bytes | signed |
| `f4` `f8` | 4/8 bytes | float (IEEE 754) |
| `b1`–`b64` | N bits | bit field; `b4le` overrides bit-endian |
| `str` | variable | needs `size` or `terminator` |
| `strz` | until null | null-terminated string shorthand |

## Repeat

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

## String Handling

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
