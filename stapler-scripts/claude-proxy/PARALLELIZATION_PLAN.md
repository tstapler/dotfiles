# Parallelization & Event Loop Optimization Plan

## Current Bottlenecks (from metrics)

**Event Loop Lag Pattern:**
- Regular spikes: 200-430ms
- Pattern: Periodic (every request)
- Cause: Synchronous disk I/O in hot paths

**Blocking Operations Identified:**
1. `diskcache.Lock()` - File locking (metrics.py:66)
2. `cache.iterkeys()` - Full cache scan (metrics.py:152, 164)
3. `cache.set()` - Synchronous writes on every request
4. `cache.get()` - Synchronous reads on credential checks

## Phase 1: Quick Wins (Immediate - 2hr)

### 1.1 Move Cache Operations to Thread Pool
**Impact:** 70% lag reduction
**Complexity:** Medium

```python
# Before (BLOCKS):
self.cache.set(key, value)

# After (NON-BLOCKING):
await asyncio.to_thread(self.cache.set, key, value)
```

**Files to update:**
- `metrics.py` - All cache operations
- `fallback.py` - Cooldown cache
- `providers/bedrock.py` - Credential cache
- `providers/anthropic.py` - Model cache

### 1.2 Remove File Locking for Recent Errors
**Impact:** Eliminate 50-100ms spikes
**Complexity:** Low

```python
# Replace diskcache.Lock with in-memory deque
from collections import deque
recent_errors = deque(maxlen=20)  # Thread-safe for append/pop
```

### 1.3 Cache Dashboard Stats (Don't Recompute)
**Impact:** Eliminate cache.iterkeys() overhead
**Complexity:** Low

```python
# Compute stats once per minute in background task
asyncio.create_task(update_stats_periodically())
```

## Phase 2: Architecture Improvements (1 day)

### 2.1 Replace diskcache with aiocache
**Impact:** Full async, 90% lag reduction
**Complexity:** High

```python
from aiocache import Cache
from aiocache.serializers import JsonSerializer

cache = Cache(
    Cache.MEMORY,  # Or Cache.REDIS for multi-process
    serializer=JsonSerializer(),
    ttl=3600
)

# Fully async:
await cache.set(key, value)
value = await cache.get(key)
```

**Pros:**
- Native async/await
- No disk I/O
- Multi-backend (memory, redis, memcached)

**Cons:**
- Loses persistence (use Redis for persistence)
- Need to handle multi-worker coordination

### 2.2 In-Memory Cache with Periodic Persistence
**Impact:** Best of both worlds
**Complexity:** Medium

```python
# Hot path: in-memory (no blocking)
from cachetools import TTLCache
memory_cache = TTLCache(maxsize=1000, ttl=300)

# Background: persist to disk every 60s
async def persist_cache():
    while True:
        await asyncio.sleep(60)
        await asyncio.to_thread(disk_cache.update, memory_cache)
```

## Phase 3: Horizontal Scaling (2 days)

### 3.1 Shared State via Redis
**Impact:** Enable multi-machine scaling
**Complexity:** High

```python
import aioredis

redis = await aioredis.from_url("redis://localhost")
await redis.set("cooldown:anthropic", time.time() + 300)
```

**Benefits:**
- Shared cooldowns across workers/machines
- Atomic operations (INCR, EXPIRE)
- Pub/sub for metrics aggregation

### 3.2 Metrics Aggregation Service
**Impact:** Remove metrics overhead from request path
**Complexity:** High

```python
# Request handler: fire and forget
await metrics_queue.put(event)

# Background worker: batch write every 1s
async def metrics_aggregator():
    while True:
        batch = []
        for _ in range(100):
            batch.append(await metrics_queue.get())
        await batch_write_metrics(batch)
```

## Phase 4: Advanced Optimizations (3-5 days)

### 4.1 HTTP Connection Pooling
```python
httpx.AsyncClient(
    limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
    timeout=httpx.Timeout(300.0)
)
```

### 4.2 Request Coalescing
Deduplicate identical in-flight requests:
```python
# If same request already in-flight, wait for it
inflight_requests = {}
if request_hash in inflight_requests:
    return await inflight_requests[request_hash]
```

### 4.3 Worker Affinity
Route requests to same worker for cache locality:
```python
# In nginx/load balancer
hash $request_body consistent;  # Route by request hash
```

## Implementation Priority

**Week 1 - Quick Wins:**
1. ✅ Thread pool offload cache ops (2hr)
2. ✅ Remove file locking (1hr)
3. ✅ Cache dashboard stats (1hr)

**Week 2 - Architecture:**
4. ⬜ Migrate to aiocache (1 day)
5. ⬜ Redis for shared state (1 day)

**Week 3 - Advanced:**
6. ⬜ Metrics aggregation service (2 days)
7. ⬜ Connection pooling (1 day)

## Metrics & Success Criteria

**Current State:**
- Max lag: 430ms
- Avg lag: ~50ms (estimated from chart)
- P95 lag: ~300ms

**Target State (Phase 1):**
- Max lag: <50ms
- Avg lag: <5ms
- P95 lag: <20ms

**Target State (Phase 2+):**
- Max lag: <10ms
- Avg lag: <1ms
- P95 lag: <5ms

## Profiling & Validation

### Before Changes:
```bash
# Profile with py-spy
py-spy record -o profile.svg -d 60 -p $(pgrep -f uvicorn)

# Monitor lag in real-time
curl http://localhost:47000/metrics | jq .current_lag_ms
```

### After Each Phase:
- Run load test (100 concurrent requests)
- Compare event loop lag metrics
- Validate no functionality regression
