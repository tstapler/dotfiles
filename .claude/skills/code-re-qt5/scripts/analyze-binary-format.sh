#!/usr/bin/env bash
# Usage: ./analyze-binary-format.sh <binary-path>
# Produces: file type, header hex, sorted strings, entropy estimate, float32 triple candidates
set -euo pipefail

TARGET="${1:?Usage: $0 <binary-path>}"

echo "=== FILE TYPE ==="
file "$TARGET"
echo ""

echo "=== HEADER (first 256 bytes) ==="
xxd "$TARGET" | head -16
echo ""

echo "=== STRINGS (len >= 8, sorted unique) ==="
strings -n 8 "$TARGET" | sort -u
echo ""

echo "=== ENTROPY ESTIMATE ==="
python3 - "$TARGET" <<'PYEOF'
import sys, math, collections
data = open(sys.argv[1], 'rb').read(65536)
counts = collections.Counter(data)
total = len(data)
entropy = -sum((c/total)*math.log2(c/total) for c in counts.values() if c)
print(f"Shannon entropy (first 64KB): {entropy:.3f} bits/byte  (8.0 = random/compressed, <4.0 = structured)")
PYEOF
echo ""

echo "=== FLOAT32 TRIPLE CANDIDATES (first 10) ==="
python3 - "$TARGET" <<'PYEOF'
import sys, struct
data = open(sys.argv[1], 'rb').read()
hits = []
for i in range(0, len(data) - 12, 4):
    try:
        x, y, z = struct.unpack_from('<fff', data, i)
        if all(-10000 < v < 10000 and v == v for v in (x, y, z)):
            hits.append((i, x, y, z))
    except Exception:
        pass
for h in hits[:10]:
    print(f"  offset 0x{h[0]:08x}: ({h[1]:.3f}, {h[2]:.3f}, {h[3]:.3f})")
if not hits:
    print("  No float32 triples found in plausible range")
print(f"  Total candidates: {len(hits)}")
PYEOF
