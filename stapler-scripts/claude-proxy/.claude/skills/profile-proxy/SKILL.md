# Claude Proxy Profiling Skill

## Purpose
Profile the Claude proxy to identify performance bottlenecks, event loop blocking, and optimization opportunities using py-spy and other profiling tools.

## When to Use
- Investigating high event loop lag (>50ms)
- Debugging slow request performance
- Validating optimization impact
- Understanding CPU vs I/O bottlenecks
- Profiling before/after code changes

## Prerequisites
```bash
# Install py-spy (requires sudo on macOS)
brew install py-spy

# Or with pip
pip install py-spy

# Install other useful profilers
pip install scalene  # Line-level profiler
pip install memray   # Memory profiler
```

## Profile Commands

### 1. Basic Flame Graph (30s sample)
```bash
# Find the main uvicorn process
PID=$(pgrep -f "uvicorn main:app" | head -1)

# Record to SVG flame graph
sudo py-spy record -o /tmp/flamegraph.svg -d 30 -p $PID

# Open in browser
open /tmp/flamegraph.svg
```

**What to look for:**
- **Wide bars at bottom** = hot paths (functions taking most time)
- **Synchronous operations** = `diskcache`, `boto3.client`, `httpx.post`
- **Event loop** = Look for `asyncio` near top (good) vs sync code (bad)

### 2. Live Top View (Like htop for Python)
```bash
sudo py-spy top -p $PID
```

**What to look for:**
- Functions with **>5% CPU** are hot paths
- `GIL` column shows Global Interpreter Lock contention
- High `Own Time` = function itself is slow (not callees)

### 3. Profile Under Load
```bash
# Terminal 1: Start load test
ab -n 10000 -c 50 -H "Authorization: Bearer $CLAUDE_CODE_OAUTH_TOKEN" \
   -H "anthropic-version: 2023-06-01" \
   -H "Content-Type: application/json" \
   -p /tmp/request.json \
   http://localhost:47000/v1/messages

# Terminal 2: Record during load
sudo py-spy record -o /tmp/under-load.svg -d 60 -p $PID
```

**Sample request body** (`/tmp/request.json`):
```json
{
  "model": "claude-haiku-4-5-20251001",
  "messages": [{"role": "user", "content": "Say hello"}],
  "max_tokens": 20
}
```

### 4. Profile Specific Scenarios

**Streaming requests:**
```bash
# Generate streaming load
for i in {1..100}; do
  curl -X POST 'http://localhost:47000/v1/messages?stream=true' \
    -H "Authorization: Bearer $CLAUDE_CODE_OAUTH_TOKEN" \
    -H "anthropic-version: 2023-06-01" \
    -H "Content-Type: application/json" \
    -d '{"model": "claude-haiku-4-5-20251001", "messages": [{"role": "user", "content": "Count to 10"}], "max_tokens": 100}' &
done

# Profile
sudo py-spy record -o /tmp/streaming.svg -d 30 -p $PID
```

**Non-streaming requests:**
```bash
# Non-streaming load
ab -n 1000 -c 50 -p /tmp/request.json \
   http://localhost:47000/v1/messages
```

**Metrics dashboard queries:**
```bash
# Generate dashboard load
for i in {1..100}; do
  curl -s http://localhost:47000/metrics > /dev/null
done &

sudo py-spy record -o /tmp/metrics.svg -d 10 -p $PID
```

### 5. Dump Current State (Non-Intrusive)
```bash
# Take snapshot without stopping process
sudo py-spy dump -p $PID

# See what each thread is doing right now
sudo py-spy dump --threads -p $PID
```

## Advanced Profiling

### Line-Level Profiling with Scalene
```bash
# More detailed than py-spy, shows line-by-line timing
scalene main.py

# Or attach to running process
sudo scalene --pid $PID --reduced-profile
```

**Advantages:**
- Shows CPU time per line
- Identifies memory allocations
- Tracks GPU usage (if applicable)

**Disadvantages:**
- Higher overhead than py-spy
- May slow down production traffic

### Memory Profiling with memray
```bash
# Track memory allocations
memray run main.py

# Attach to running process
sudo memray attach $PID --duration 30

# Generate flamegraph
memray flamegraph memray-*.bin
```

## Reading Flame Graphs

### Anatomy of a Flame Graph
```
┌─────────────────────────────────────────┐ ← Top = main entry point
│         main.py                         │
├───────────────────┬─────────────────────┤
│  fallback.py      │   metrics.py        │ ← Callees
├─────────┬─────────┼──────────┬──────────┤
│bedrock.py│anthropic│cache.set │iterkeys │ ← Bottlenecks (wide = hot)
└─────────┴─────────┴──────────┴──────────┘
```

**X-axis:** Width = % of total time (wider = more time)
**Y-axis:** Call stack depth (bottom to top)
**Color:** Random (for contrast only)

### Identifying Blocking Operations

**❌ Bad Pattern (Synchronous I/O):**
```
uvicorn.run
  └─ FastAPI.handle_request
       └─ FallbackHandler.send_message
            └─ diskcache.Cache.set        ← WIDE BAR = BLOCKING
                 └─ fcntl.flock           ← File lock!
                      └─ os.write          ← Disk I/O
```

**✅ Good Pattern (Async I/O):**
```
uvicorn.run
  └─ FastAPI.handle_request
       └─ FallbackHandler.send_message
            └─ asyncio.to_thread         ← Narrow (fast)
                 └─ [thread pool]         ← Off event loop
```

## Proxy-Specific Hot Paths

### Expected Top Functions (by time):

1. **`bedrock.py:_stream_bedrock_sync`** (20-40%)
   - Streaming responses from Bedrock
   - **Expected:** This is doing real work, should be wide

2. **`providers/anthropic.py:send_message`** (10-20%)
   - HTTP requests to Anthropic API
   - **Expected:** Network I/O, should show `httpx.post`

3. **`fallback.py:send_message`** (10-15%)
   - Provider orchestration
   - **Expected:** Should be orchestration, not computation

4. **`metrics.py:record_request_complete`** (5-10% **before Phase 1**)
   - Recording metrics
   - **Expected:** Should drop to <1% after Phase 1 optimizations

5. **`diskcache` operations** (10-20% **before Phase 1**)
   - Cache reads/writes
   - **Expected:** Should move to thread pool or disappear

### ⚠️ Red Flags (investigate if you see these):

- **`cache.iterkeys()` is wide** → Still scanning full cache (should be cached)
- **`diskcache.Lock()` appears** → File locking still happening (should be removed)
- **`boto3.client()` in hot path** → Client recreation (should be cached)
- **`json.dumps/loads` is wide** → Serialization overhead (consider msgpack)
- **`logging` is wide** → Too much logging (use lazy evaluation)

## Profiling Workflow

### Before Optimization:
```bash
# 1. Baseline profile
sudo py-spy record -o /tmp/before.svg -d 60 -p $PID

# 2. Check metrics
curl -s http://localhost:47000/metrics | jq '.lag_data[-1]'

# 3. Load test
ab -n 1000 -c 50 http://localhost:47000/health

# 4. Record max lag
```

### After Optimization:
```bash
# 1. Profile again
sudo py-spy record -o /tmp/after.svg -d 60 -p $PID

# 2. Compare lag
curl -s http://localhost:47000/metrics | jq '.lag_data[-1]'

# 3. Same load test
ab -n 1000 -c 50 http://localhost:47000/health

# 4. Compare results
```

### Side-by-Side Comparison:
```bash
# Open both flame graphs
open /tmp/before.svg /tmp/after.svg

# Visual diff:
# - Blocking operations should shrink or disappear
# - Event loop should be thinner (less blocking)
# - Thread pool operations should appear
```

## Integration with Metrics Dashboard

### Correlate Profile with Lag Spikes

1. **Note timestamp of high lag:**
   ```bash
   curl -s http://localhost:47000/metrics | jq '.lag_data[] | select(.max_ms > 100)'
   ```

2. **Profile during next spike:**
   ```bash
   # Wait for lag warning in logs
   tail -f /tmp/claude-proxy.app.log | grep "Event loop lag"

   # When you see warning, immediately profile:
   sudo py-spy record -o /tmp/spike.svg -d 5 -p $PID
   ```

3. **Analyze correlation:**
   - What operation was running during spike?
   - Is it a known hot path?
   - Can it be moved to thread pool?

## Common Bottlenecks & Solutions

| Symptom in Flame Graph | Root Cause | Solution |
|------------------------|------------|----------|
| `diskcache.Cache.set` is wide | Sync disk writes | `await asyncio.to_thread()` |
| `cache.iterkeys()` is wide | Full cache scan | Cache the result for 5s |
| `diskcache.Lock` appears | File-based locking | Use in-memory `deque` |
| `boto3.Session()` in hot path | Client recreation | Cache client, refresh proactively |
| `httpx.post` is wide | Network latency | Expected (but check connection pooling) |
| `json.dumps` is wide | Serialization overhead | Consider msgpack or reduce payload |
| Deep call stacks | Too many indirections | Flatten architecture |

## Automation Script

Create `/tmp/profile-proxy.sh`:

```bash
#!/bin/bash
set -e

PID=$(pgrep -f "uvicorn main:app" | head -1)
DURATION=${1:-30}
OUTPUT=${2:-/tmp/proxy-profile.svg}

echo "Profiling PID $PID for ${DURATION}s..."
echo "Output: $OUTPUT"

# Profile
sudo py-spy record -o "$OUTPUT" -d "$DURATION" -p "$PID"

# Show top functions
echo ""
echo "Top 10 functions by time:"
sudo py-spy top -p "$PID" -d 5 | head -20

# Check current lag
echo ""
echo "Current event loop lag:"
curl -s http://localhost:47000/metrics | jq '.current_lag_ms'

# Open flame graph
open "$OUTPUT"
```

Usage:
```bash
chmod +x /tmp/profile-proxy.sh
/tmp/profile-proxy.sh 60 /tmp/my-profile.svg
```

## Profiling Checklist

Before claiming an optimization worked:

- [ ] Profile before and after with same load
- [ ] Run load test during profiling
- [ ] Check event loop lag metrics
- [ ] Validate no regression in functionality
- [ ] Compare flame graph widths
- [ ] Check application logs for warnings
- [ ] Test under streaming and non-streaming load
- [ ] Profile all worker processes (not just one)

## Multi-Worker Profiling

Since you run 10 workers, profile all of them:

```bash
# Profile all workers
for pid in $(pgrep -f "uvicorn main:app"); do
  sudo py-spy record -o "/tmp/worker-${pid}.svg" -d 30 -p "$pid" &
done
wait

# Open all flame graphs
open /tmp/worker-*.svg
```

Look for:
- **Consistency:** All workers should show similar patterns
- **Outliers:** One worker much slower? Bad cache state or stuck request
- **Load distribution:** All workers equally busy? Or some idle?

## Resources

- [py-spy GitHub](https://github.com/benfred/py-spy)
- [Reading Flame Graphs](http://www.brendangregg.com/flamegraphs.html)
- [Python Profiling Guide](https://docs.python.org/3/library/profile.html)
- [AsyncIO Performance Tips](https://docs.python.org/3/library/asyncio-dev.html#debug-mode)

## Notes

- **Requires root:** py-spy needs sudo for process attachment
- **Low overhead:** py-spy samples (doesn't instrument), ~1% overhead
- **Production safe:** Can run in production without noticeable impact
- **Multi-language:** Works with C extensions (shows native calls)
- **Real-time:** See results immediately with `top` mode
