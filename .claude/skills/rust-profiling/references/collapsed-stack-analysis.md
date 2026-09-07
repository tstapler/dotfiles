# Step 3 — Analyze Collapsed Stacks

## Generate collapsed stacks

```bash
# From perf recording
perf script | /opt/FlameGraph/stackcollapse-perf.pl --kernel > cpu.collapsed

# Render SVG from collapsed stacks (same as cargo flamegraph, more control)
/opt/FlameGraph/flamegraph.pl --title "proextract BPA" cpu.collapsed > flamegraph.svg
```

## awk extraction from collapsed stacks

```bash
# Top leaf frames by self-sample count
awk '{n=$NF; sub(/ [0-9]+$/,""); split($0,a,";"); leaf=a[length(a)]; count[leaf]+=$NF}
     END{for(f in count) print count[f],f}' \
  cpu.collapsed | sort -rn | head -20

# Stacks touching a specific function
grep "bpa::pivot_step" cpu.collapsed | sort -t' ' -k2 -rn | head -10

# Filter to your crate only (remove stdlib + runtime noise)
grep "proextract" cpu.collapsed | sort -t' ' -k2 -rn | head -30
```

## Python percentage breakdown

```python
from collections import defaultdict
import sys

lines = [l.strip() for l in open(sys.argv[1]) if l.strip()]
total = sum(int(l.rsplit(" ", 1)[1]) for l in lines)
by_leaf = defaultdict(int)
for line in lines:
    stack, _, count = line.rpartition(" ")
    leaf = stack.split(";")[-1]
    by_leaf[leaf] += int(count)

for count, frame in sorted((-v, k) for k, v in by_leaf.items())[:20]:
    print(f"{100*-count/total:5.1f}%  {-count:6d}  {frame}")
```

```bash
python3 analyze.py cpu.collapsed
```

## Rust-specific: check for monomorphization bloat

```bash
# Symbols in the binary — large count of similar names = monomorphization
nm --demangle target/release/proextract | grep -c "fn "
cargo bloat --release --crates    # shows which crates dominate binary size
cargo bloat --release -n 30       # top 30 functions by size
```
