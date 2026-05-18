# ADR-002: Storage Backend

**Status**: Accepted
**Date**: 2026-04-16
**Context**: Phase 3 — Planning

---

## Context

Need persistent storage for error fingerprints and occurrence history to:
- Survive proxy restarts (prevent false-positive "new error" alerts)
- Enable historical trend analysis
- Support query operations (search by provider, time window, error type)
- Enforce bounded growth (retention policy)

### Requirements Driving This Decision
- Persistence: Errors must survive proxy restarts
- Query capability: Search by provider, time window, fingerprint
- Bounded growth: Storage must not grow unbounded (90-day retention policy)
- Performance: Minimal write latency impact on error path
- Operational simplicity: Solo practitioner use case (no external services)

### Research Findings
From `research/findings-architecture.md`:
- Four options considered: SQLite, JSON files, in-memory + periodic flush, append-only log
- SQLite provides full query capability with ACID guarantees
- WAL mode enables concurrent reads + 1 writer (acceptable for multi-process proxy)
- Stdlib module (zero dependencies)

---

## Decision

**Use SQLite with two-tier schema**:

### Schema Design

```sql
-- Tier 1: Deduplication (small, persistent)
CREATE TABLE error_types (
    fingerprint TEXT PRIMARY KEY,
    first_seen INTEGER NOT NULL,  -- Unix timestamp
    last_seen INTEGER NOT NULL,   -- Unix timestamp
    count INTEGER DEFAULT 1,      -- Total occurrences
    provider TEXT,
    operation TEXT,
    error_type TEXT,
    message TEXT,                 -- Normalized message (for display)
    example_full TEXT,            -- Latest full error message (raw)
    UNIQUE(fingerprint)
);

-- Tier 2: Detail (large, prunable)
CREATE TABLE error_occurrences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fingerprint TEXT NOT NULL,
    timestamp INTEGER NOT NULL,
    request_id TEXT,              -- From [request_id] in logs
    model TEXT,
    context JSON,                 -- Extra metadata (e.g., max_tokens, stream)
    FOREIGN KEY (fingerprint) REFERENCES error_types(fingerprint)
);

-- Indexes for query performance
CREATE INDEX idx_occurrences_timestamp ON error_occurrences(timestamp);
CREATE INDEX idx_occurrences_fingerprint ON error_occurrences(fingerprint);
CREATE INDEX idx_error_types_provider ON error_types(provider);
CREATE INDEX idx_error_types_last_seen ON error_types(last_seen);
```

### Configuration
- **File location**: `~/.cache/claude-proxy/error_tracker.db`
- **Journal mode**: WAL (`PRAGMA journal_mode=WAL`) — enables concurrent reads + 1 writer
- **Synchronous mode**: NORMAL (`PRAGMA synchronous=NORMAL`) — balance durability vs performance
- **Retention policy**: Delete `error_occurrences` older than 90 days (keep `error_types` intact)

---

## Rationale

### Why SQLite?

1. **Query capability**:
   - Full SQL queries enable diagnostics: `SELECT * FROM error_types WHERE provider='bedrock' AND last_seen > {timestamp}`
   - Support for CLI tool: list, search, show, export commands (Story 5)
   - Indexes accelerate common queries (by provider, time window, fingerprint)

2. **Persistence guarantees**:
   - ACID transactions: Writes are atomic (no partial updates)
   - Crash recovery: Database remains consistent after unexpected shutdown
   - WAL mode: Improves crash recovery (write-ahead log persists uncommitted changes)

3. **Performance acceptable**:
   - Write latency: 10-50ms typical (measured on macOS SSD)
   - Errors are rare: Not on hot path (only triggered when requests fail)
   - Acceptable overhead: <2ms p99 budget for error tracking, SQLite write is 10-50ms but errors occur <1% of requests
   - WAL mode reduces lock contention: Concurrent reads + 1 writer (proxy uses 10 workers)

4. **Operational simplicity**:
   - Stdlib module: `import sqlite3` — zero external dependencies
   - Standard tooling: `sqlite3` CLI for inspection and debugging
   - Single file: Easy to backup, copy, or reset (`cp error_tracker.db error_tracker.db.backup`)
   - No service management: No daemon to start, no port to configure

5. **Bounded growth**:
   - Two-tier schema separates concerns:
     - `error_types`: Small (one row per unique error), persistent
     - `error_occurrences`: Large (one row per occurrence), prunable
   - Retention policy: `DELETE FROM error_occurrences WHERE timestamp < (now - 90 days)`
   - Expected size: <10MB after 90 days (assuming 100 unique errors, 1000 occurrences)

### Schema Design Decisions

**Why two tiers?**
- **Deduplication efficiency**: `error_types` stores one row per fingerprint (summary data)
- **Query flexibility**: `error_occurrences` stores detailed history (request_id, model, context)
- **Storage growth**: Prune detailed history without losing error type summary
- **Alert logic**: Check `error_types` for "is this new?" (fast — one table lookup)

**Why JSON for context field?**
- Extensible: Can add new metadata fields without schema migration (ALTER TABLE)
- Flexibility: Different error types may have different context (Bedrock context vs Anthropic context)
- Query capability: SQLite JSON functions enable querying: `SELECT * WHERE json_extract(context, '$.model') = 'claude-opus'`

**Why Unix timestamp (INTEGER) instead of TEXT?**
- Smaller storage: 8 bytes vs 25+ bytes for ISO 8601 string
- Faster comparisons: INTEGER comparison vs string parsing
- Standard: `time.time()` in Python returns Unix timestamp directly

---

## Consequences

### Positive
- **Full query capability**: SQL enables complex diagnostics queries
- **Strong persistence**: ACID guarantees + crash recovery
- **Bounded storage**: Two-tier schema + retention policy prevents unbounded growth
- **Zero dependencies**: Stdlib module (no pip install required)
- **Standard tooling**: `sqlite3` CLI for inspection, backup, export

### Negative
- **Write latency**: 10-50ms per write (vs <1ms for in-memory)
- **Lock contention risk**: High error rates (100+ errors/sec) may cause SQLITE_BUSY errors
- **Schema migration complexity**: Adding columns requires ALTER TABLE (limited in SQLite)

### Mitigation Strategies

1. **Lock contention** (Known Issue #002):
   - WAL mode reduces contention (default in implementation)
   - Retry logic with exponential backoff on SQLITE_BUSY
   - If contention persists: Move to async writes with `asyncio.to_thread()`
   - Monitor: Track database write failures, alert if >1% failure rate

2. **Write latency**:
   - Acceptable for MVP: Errors are rare (<1% of requests), 10-50ms is acceptable overhead
   - If latency becomes issue: Use async writes (Task deferred to Phase 3 optimization)
   - Measure: Add timing metrics for database writes, track p99 latency

3. **Schema migration**:
   - Use JSON column for extensible metadata (avoid schema changes)
   - If ALTER TABLE needed: Write migration script (read old schema → write new schema)
   - Version schema: `CREATE TABLE schema_version (version INTEGER)`

4. **Storage bloat**:
   - Retention policy: Delete old occurrences on startup or periodic background task
   - Monitor: Track database file size, alert if >100MB
   - Emergency cleanup: `VACUUM` command to reclaim space after deletion

---

## Alternatives Considered

### Alternative 1: JSON Files (One File Per Fingerprint)
**Approach**: Store each error type as `errors/{fingerprint}.json` with structure:
```json
{
  "fingerprint": "a3f7c9e1d2b5f8a0",
  "first_seen": 1713283200,
  "last_seen": 1713369600,
  "count": 15,
  "occurrences": [...]
}
```

**Why rejected**:
- **No atomic updates**: Race condition on concurrent writes (proxy uses 10 workers)
  - Worker 1 reads file, increments count, writes back
  - Worker 2 reads file (gets old count), increments, writes back
  - Result: Lost update (count off by 1)
- **No query capability**: Must scan all files to search by provider or time window
  - `find errors/ -name "*.json" -exec grep -l "bedrock" {} \;` — slow for 100+ files
- **File system bloat**: One file per unique error (100 errors = 100 files)
- **No indexes**: Can't accelerate common queries

**When this would be correct**:
- Single-threaded application (no concurrent write risk)
- Very low error volume (<10 unique errors)
- Human-readable format is critical for debugging

---

### Alternative 2: In-Memory with Periodic Flush
**Approach**: Store errors in `Dict[fingerprint, ErrorRecord]` in memory, pickle/JSON dump every N minutes.

**Why rejected**:
- **Data loss on crash**: Unflushed errors disappear if proxy crashes or restarts
  - Violates "persistence layer" requirement from requirements.md
- **No persistence guarantee**: Flush interval trade-off
  - Frequent flush (every 1 min) → high I/O overhead, still lose 1 minute of data
  - Infrequent flush (every 10 min) → lose 10 minutes of data on crash
- **False-positive alerts**: After restart, in-memory state is empty → all errors appear "new"
  - Defeats purpose of tracking (prevent false-positive alerts on restart)

**When this would be correct**:
- Low-stakes logging (losing data is acceptable)
- High-performance requirement (zero write latency)
- Short-lived process (restarts are rare)

---

### Alternative 3: Append-Only Log (JSON Lines)
**Approach**: Single file with JSON lines (one line per error occurrence):
```json
{"timestamp": 1713283200, "fingerprint": "a3f7c9e1d2b5f8a0", "provider": "bedrock", ...}
{"timestamp": 1713283205, "fingerprint": "7f2a9c8e4d1b6f3a", "provider": "anthropic", ...}
```

**Why rejected**:
- **No deduplication**: Must scan entire file to count occurrences of a fingerprint
  - "Is this a new error?" requires reading all lines (O(n) for n errors)
- **No indexes**: Queries require linear scan
  - "Show me all Bedrock errors" → `grep "bedrock" errors.log` — slow for large files
- **Unbounded growth**: File grows indefinitely without rotation
  - After 90 days: 100,000 occurrences = 10MB+ file
  - Rotation requires external tool (logrotate) or custom script

**When this would be correct**:
- Audit trail (compliance requires keeping all events)
- Log aggregation pipeline (ship to external system like ELK, Splunk)
- Write-once, query externally (not queried locally)

---

### Alternative 4: External Service (Sentry, Datadog)
**Approach**: Send errors to external monitoring service for storage and analysis.

**Why rejected**:
- **Out of scope**: Requirements explicitly exclude external service integration
  - "Out of scope: Integration with external monitoring services (Datadog, etc.)"
- **Dependency overhead**: Requires API keys, network calls, account setup
- **Cost**: SaaS pricing for error tracking (may be unnecessary for solo practitioner)
- **Complexity**: Additional failure mode (network errors, API rate limits)

**When this would be correct**:
- Team environment (shared visibility)
- Need advanced features (alerting integrations, anomaly detection, user feedback)
- Already using external monitoring (consolidate all observability in one place)

---

## Validation Plan

From Task 2.1 (Design and implement SQLite schema):

1. **Schema creation**:
   - Execute CREATE TABLE statements
   - Verify: No SQL errors
   - Verify: Tables created (query `sqlite_master`)

2. **WAL mode**:
   - Execute `PRAGMA journal_mode=WAL`
   - Verify: Returns "wal" (not "delete")

3. **Indexes**:
   - Verify: Indexes created (query `sqlite_master WHERE type='index'`)
   - Test query performance: `EXPLAIN QUERY PLAN SELECT * FROM error_types WHERE provider='bedrock'`

4. **Storage operations** (Task 2.2):
   - Write error → Read back → Verify data matches
   - Write duplicate error → Verify count incremented (UPSERT logic)
   - Concurrent writes (10 threads) → Verify no corruption

5. **Retention policy** (Task 2.3):
   - Insert errors with timestamp 91 days ago
   - Run pruning: `prune_old_occurrences(max_age_days=90)`
   - Verify: `error_types` intact, `error_occurrences` deleted
   - Verify: Storage size reduced

6. **Performance benchmarks**:
   - Measure write latency: Insert 100 errors, record p50/p99/p99.9
   - Target: <50ms p99 write latency
   - Measure concurrent writes: 10 workers × 10 writes each
   - Target: Zero SQLITE_BUSY errors

---

## Implementation Impact

**Files affected**:
- `stapler-scripts/claude-proxy/error_tracker.py` (NEW) — Database schema and operations
  - Schema SQL (CREATE TABLE, CREATE INDEX, PRAGMA statements)
  - `ErrorTracker.__init__(db_path)` — Database initialization
  - `ErrorTracker.record_error(signature, context)` — UPSERT logic
  - `ErrorTracker.get_error_by_fingerprint(fingerprint)` — Lookup
  - `ErrorTracker.search_errors(provider, since, limit)` — Filtered queries
  - `ErrorTracker.prune_old_occurrences(max_age_days)` — Retention policy

**Tasks implementing this decision**:
- Task 2.1: Design and implement SQLite schema
- Task 2.2: Implement error storage operations
- Task 2.3: Implement retention policy

**Known issues related to this decision**:
- Bug 002: SQLite lock contention under high error rates
- Performance risk: Write latency may exceed 2ms budget under load

---

## References

- **Research findings**: `project_plans/claude-proxy-error-tracking/research/findings-architecture.md`
- **SQLite documentation**: https://www.sqlite.org/docs.html
- **WAL mode**: https://www.sqlite.org/wal.html
- **Python sqlite3 module**: https://docs.python.org/3/library/sqlite3.html
