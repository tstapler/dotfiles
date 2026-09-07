# Worked Examples

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
