# Architecture Research Findings
## Claude Proxy Error Tracking System

**Research dimension**: Architecture — integration approaches, storage backends, alerting delivery
**Date**: 2026-04-16
**Status**: Draft — based on training knowledge (WebSearch unavailable)

---

## Executive Summary

Researched integration patterns, storage backends, and alerting mechanisms for a lightweight Python error tracking system. **Recommendation**: SQLite-backed storage with custom logging handler integration and async signal-based alerts. This balances persistence needs with minimal operational overhead.

---

## Options Surveyed

### 1. Integration Approaches

#### Option A: Custom Logging Handler
**Pattern**: Subclass `logging.Handler`, attach to existing loggers, intercept ERROR/CRITICAL records.

**Pros**:
- Non-invasive — no code changes to existing error handling
- Automatic capture of all logged errors
- Structured metadata via `LogRecord` attributes (funcName, module, lineno)

**Cons**:
- Only captures logged errors (explicit `logger.error()` calls)
- Missed errors if exception handling doesn't log
- Handler execution is synchronous in logging path

**Implementation sketch**:
```python
class ErrorTrackingHandler(logging.Handler):
    def emit(self, record: LogRecord):
        if record.levelno >= logging.ERROR:
            error_fingerprint = compute_fingerprint(record)
            store_error(fingerprint, metadata=extract_metadata(record))
            if is_new_error(fingerprint):
                alert_new_error(fingerprint, record)
```

#### Option B: Decorator Pattern
**Pattern**: `@track_errors` decorator on functions that call provider APIs.

**Pros**:
- Explicit control over what gets tracked
- Can capture request/response context easily
- No logging infrastructure dependency

**Cons**:
- Invasive — requires decorating many functions
- Easy to forget on new code paths
- Doesn't capture errors in library code

#### Option C: Middleware/Wrapper
**Pattern**: Wrap provider API calls with error tracking logic.

**Pros**:
- Central interception point (e.g., wrap Bedrock client)
- Captures all provider errors uniformly
- Can inject provider/model metadata easily

**Cons**:
- Provider-specific implementation needed
- Missed errors outside API calls (parsing, validation)
- Tight coupling to provider client structure

#### Option D: Exception Hook (`sys.excepthook`)
**Pattern**: Global uncaught exception handler.

**Pros**:
- Catches all unhandled exceptions automatically
- Zero code changes
- Safety net for missed errors

**Cons**:
- Only unhandled exceptions (proxy would likely crash)
- No context about where error came from
- Not useful for caught-and-logged errors

---

### 2. Storage Backends

#### Option A: SQLite (File-Based)
**Pattern**: Single-file database with schema for error types, occurrences, metadata.

**Schema sketch**:
```sql
CREATE TABLE error_types (
    fingerprint TEXT PRIMARY KEY,
    first_seen INTEGER NOT NULL,
    last_seen INTEGER NOT NULL,
    count INTEGER DEFAULT 1,
    error_message TEXT,
    stack_trace TEXT,
    category TEXT  -- e.g., "bedrock_validation", "rate_limit"
);

CREATE TABLE error_occurrences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fingerprint TEXT NOT NULL,
    timestamp INTEGER NOT NULL,
    provider TEXT,
    model TEXT,
    context JSON,  -- request details, response snippet
    FOREIGN KEY (fingerprint) REFERENCES error_types(fingerprint)
);

CREATE INDEX idx_occurrences_time ON error_occurrences(timestamp);
CREATE INDEX idx_occurrences_provider ON error_occurrences(provider);
```

**Pros**:
- Full query capability (search by provider, time window, error type)
- Atomic writes, ACID guarantees
- No size limits in practice (up to TBs)
- Standard tooling (`sqlite3` CLI for debugging)
- Lightweight (single stdlib dependency)

**Cons**:
- File I/O latency (10-50ms writes typical)
- Requires file path configuration
- SQLite locking under high concurrency (not an issue for single-process proxy)

**Write pattern**: Use WAL mode (`PRAGMA journal_mode=WAL`) for better concurrency. [TRAINING_ONLY — verify WAL default in Python's sqlite3 module]

#### Option B: JSON File per Error Type
**Pattern**: `errors/{fingerprint}.json` with structure `{first_seen, last_seen, count, occurrences: []}`

**Pros**:
- Human-readable
- No schema management
- Easy to inspect/debug

**Cons**:
- No atomic updates (race conditions on concurrent writes)
- No indexing (must scan all files for queries)
- File system bloat (one file per unique error)
- Slow queries ("find all errors from Bedrock this week")

#### Option C: In-Memory with Periodic Flush
**Pattern**: `Dict[fingerprint, ErrorRecord]` in memory, pickle/JSON dump every N minutes.

**Pros**:
- Zero latency during proxy requests
- Simple implementation

**Cons**:
- Data loss on crash (unflushed errors disappear)
- No persistence guarantee
- Flush interval trade-off (frequent = I/O overhead, infrequent = loss risk)
- No historical queries (only current session data)

**Verdict**: Inappropriate for "persistence layer" requirement.

#### Option D: Append-Only Log
**Pattern**: Single file with JSON lines (`{timestamp, fingerprint, metadata}\n`).

**Pros**:
- Simple append (fast writes)
- No corruption risk
- Easy log rotation

**Cons**:
- Slow deduplication (must read entire file to find existing errors)
- No indexes (linear scan for queries)
- Grows indefinitely without rotation

**Use case**: Good for audit trail, poor for "new error detection" (requires full scan).

---

### 3. Alerting Delivery Mechanisms

#### Option A: macOS Notification Center (via `osascript`)
**Pattern**: Shell out to AppleScript to trigger notification.

```python
subprocess.run([
    'osascript', '-e',
    f'display notification "{error_msg}" with title "New Error in claude-proxy"'
])
```

**Pros**:
- Native macOS integration
- User sees it immediately (if at desk)
- Zero dependencies

**Cons**:
- Platform-specific (macOS only)
- Synchronous subprocess call (10-100ms)
- No notification if user not logged in
- Rate limiting by system (grouped notifications)

#### Option B: File-Based Signal
**Pattern**: Write `NEW_ERROR` to a watched file (e.g., `/tmp/proxy-alerts.txt`). External watcher (e.g., `fswatch` + script) polls and triggers alert.

**Pros**:
- Decouples alert delivery from proxy process
- Async (proxy writes and continues)
- Platform-agnostic file write

**Cons**:
- Requires external watcher setup
- Complexity (two-process system)
- File I/O still blocks briefly

#### Option C: Stdout with Prefix
**Pattern**: Print `[NEW_ERROR]` line to stdout. User monitors logs or pipes to alert tool.

**Pros**:
- Zero dependencies
- Works in any environment (SSH, Docker, systemd)
- Integrates with existing log aggregation

**Cons**:
- Easy to miss (scrollback)
- Requires active log monitoring
- No visual prominence

#### Option D: Python `logging` with Custom Handler for Alerts
**Pattern**: Emit alert via separate `AlertHandler` that sends desktop notification, email, or webhook.

**Pros**:
- Reuses logging infrastructure
- Can add multiple alert channels (SMTP, Slack, etc.) without changing core code
- Async if handler uses thread pool

**Cons**:
- Still requires handler implementation (same as Option A)

#### Option E: Signal/Queue + Background Thread
**Pattern**: Main thread writes alert to `queue.Queue`, background thread drains and sends notifications.

**Pros**:
- Truly async (zero latency in request path)
- Can batch alerts (e.g., "5 new errors in last minute")
- Handles slow alert channels gracefully

**Cons**:
- Threading complexity
- Thread lifecycle management (shutdown, join)
- Queue size limits (if unbounded, memory risk)

---

## Trade-off Matrix

| Dimension | Option | Latency | Persistence | Query Capability | Complexity | Failure Mode |
|---|---|---|---|---|---|---|
| **Integration** | Logging Handler | Low (µs) | N/A | N/A | Low | Missed unlogged errors |
| | Decorator | Low | N/A | N/A | Medium | Forgot to decorate |
| | Middleware | Low | N/A | N/A | Medium | Provider-specific |
| | Exception Hook | None | N/A | N/A | Low | Only uncaught |
| **Storage** | SQLite | 10-50ms | Strong | High (SQL) | Low | Locking (rare) |
| | JSON Files | 5-20ms | Weak (race) | None | Low | Corruption on crash |
| | In-Memory | 0ms | None | High (in-mem) | Low | Data loss on crash |
| | Append-Only | 2-10ms | Strong | Poor | Low | Bloat without rotation |
| **Alerting** | macOS Notif | 50-100ms | N/A | N/A | Low | Platform lock-in |
| | File Signal | 5ms + watcher | N/A | N/A | Medium | External dependency |
| | Stdout | <1ms | N/A | N/A | Low | Easy to miss |
| | Async Queue | <1ms | N/A | N/A | Medium | Thread management |

---

## Risk and Failure Modes

### Storage Risks

1. **SQLite Locking**: Under heavy load, writes block. **Mitigation**: Single-threaded proxy unlikely to hit this; use WAL mode if needed.
2. **Disk Space Exhaustion**: `error_occurrences` table grows unbounded. **Mitigation**: Retention policy (delete occurrences >30 days, keep error_types).
3. **Schema Migration**: Adding columns requires migration logic. **Mitigation**: Start with extensible JSON column for future metadata.
4. **File Path Misconfiguration**: SQLite file in wrong directory (permissions, missing dir). **Mitigation**: Fail fast on startup, create directory if missing.

### Integration Risks

1. **Logging Handler Not Attached**: If logger not configured, no tracking. **Mitigation**: Attach handler in proxy startup code with verification log.
2. **Handler Exception Breaks Logging**: If handler crashes, entire logging system fails. **Mitigation**: Wrap handler `emit()` in try/except, log handler errors separately.
3. **Circular Logging**: Handler logs its own errors, triggering infinite loop. **Mitigation**: Handler uses different logger name (e.g., `error_tracker.internal`) not tracked.

### Alerting Risks

1. **Alert Fatigue**: If many new errors fire rapidly, notification spam. **Mitigation**: Rate limit (max 1 alert per 5 minutes per fingerprint).
2. **Silent Failure**: Notification command fails (e.g., `osascript` not in PATH), no feedback. **Mitigation**: Log alert delivery failures.
3. **Blocking Alert Delivery**: Synchronous notification blocks proxy request. **Mitigation**: Use async queue pattern for alerts.

---

## Migration and Adoption Cost

### Integration

**Logging Handler approach** (recommended):
- **Code changes**: ~50 lines (handler class + attachment in startup)
- **Migration path**: Add handler to existing loggers, no changes to error handling code
- **Testing**: Verify handler attached, trigger test error, confirm storage write

**Decorator approach** (alternative):
- **Code changes**: ~20 lines decorator + decorating 10-15 functions
- **Migration path**: Incremental (decorate high-value functions first)
- **Risk**: Easy to miss new code paths

### Storage

**SQLite approach** (recommended):
- **Setup**: Create DB file on first run (3 CREATE TABLE statements)
- **Migration**: None initially; future schema changes need ALTER TABLE or recreate
- **Operational**: Backup strategy (copy .db file), retention policy script

**JSON files approach** (not recommended):
- **Setup**: Create `errors/` directory
- **Migration**: Easy to add fields (just write new keys)
- **Operational**: File cleanup script, manual deduplication

### Alerting

**macOS Notification approach** (recommended for solo practitioner):
- **Setup**: Zero (osascript is built-in)
- **Migration**: None
- **Operational**: User must be logged into macOS GUI session

**Async queue approach** (if latency critical):
- **Setup**: ~30 lines (queue, background thread, shutdown logic)
- **Migration**: None
- **Operational**: Ensure thread shutdown on proxy exit

---

## Operational Concerns

### Monitoring the Tracker Itself

- **Health check**: Periodic query to SQLite (e.g., `SELECT COUNT(*) FROM error_types`) to ensure DB not corrupted
- **Storage growth**: Track DB file size, alert if >100MB (indicates bloat or missing retention)
- **Alert delivery**: Log alert attempts, detect silent failures

### Performance Impact

**Baseline proxy latency budget**: ~50-200ms per request (Bedrock API call dominates).

**Error tracking overhead**:
- Logging handler: <1ms (memory operations only until error occurs)
- SQLite write on error: 10-50ms (acceptable — errors are rare, not hot path)
- Alert delivery (sync): 50-100ms (macOS notification) — **blocks request if in handler**

**Mitigation**: Use async queue for alerts to move 50-100ms out of request path.

### Debugging and Introspection

**SQLite advantages**:
- Standard CLI: `sqlite3 error_tracker.db "SELECT * FROM error_types ORDER BY last_seen DESC LIMIT 10;"`
- Export to CSV: `.mode csv` + `.output errors.csv` + query
- Schema inspection: `.schema`

**Query examples**:
```sql
-- New errors in last 24 hours
SELECT * FROM error_types WHERE first_seen > strftime('%s', 'now', '-1 day');

-- Top errors by count
SELECT error_message, count FROM error_types ORDER BY count DESC LIMIT 5;

-- All Bedrock errors
SELECT et.* FROM error_types et
JOIN error_occurrences eo ON et.fingerprint = eo.fingerprint
WHERE eo.provider = 'bedrock';
```

---

## Prior Art

### Sentry (Open Source Error Tracking)

**Architecture**:
- Fingerprinting: SHA1 hash of (exception type + stack trace + message normalized)
- Storage: PostgreSQL (events table + issues table for deduplication)
- Alerting: Webhooks, email, integrations (Slack, PagerDuty)

**Lessons**:
- Fingerprinting stability is hard (message variations cause fingerprint drift)
- Two-tier storage (issue summary + individual events) enables both deduplication and query depth
- Alert rules need thresholds (e.g., "alert on >10 occurrences in 5 minutes")

**Applicability**: Sentry SDK has "local mode" but still heavyweight. Fingerprinting approach is sound — hash of (error type + normalized message + code location).

### Nginx Error Tracking [TRAINING_ONLY — verify]

**Pattern**:
- Logs errors to file with severity levels
- `error_log` directive supports custom log formats
- No built-in deduplication (handled by external log aggregators like ELK)

**Lesson**: Separate concerns — logging vs deduplication vs alerting. Nginx focuses on fast logging, delegates deduplication.

### Envoy Proxy Error Stats [TRAINING_ONLY — verify]

**Pattern**:
- Metrics exported (counter per error type)
- No persistence (in-memory only)
- Prometheus scrapes and stores time-series data

**Lesson**: For operational metrics, external time-series DB (Prometheus) handles persistence. For error tracking with alerting, need local storage.

---

## Open Questions

1. **Fingerprinting algorithm stability**: Should dynamic error messages (e.g., "Model X not found" where X varies) be normalized before hashing?
   - **Prototype needed**: Test fingerprinting on known error variations from proxy logs.

2. **Retention policy**: Keep all error_types forever or prune low-count errors after N days?
   - **Recommendation**: Keep error_types indefinitely (small data), prune error_occurrences >30 days.

3. **Alert batching**: If 5 new errors appear in 30 seconds, send 1 notification or 5?
   - **Recommendation**: Batch by time window (e.g., "3 new errors detected" every 5 minutes).

4. **Async vs sync alert delivery**: Is 50-100ms blocking acceptable for rare errors?
   - **Recommendation**: Start with sync (simpler), add async queue if latency becomes issue.

5. **SQLite file location**: Store in proxy repo (`claude-proxy/errors.db`) or separate data directory?
   - **Recommendation**: Configurable path with default `~/.claude-proxy/error_tracker.db`.

---

## Recommendation

### Integration Approach
**Custom Logging Handler** — non-invasive, automatic capture, integrates with existing logging infrastructure.

### Storage Backend
**SQLite with two-tier schema** (error_types for deduplication + error_occurrences for detail):
- Balances query capability, persistence, and operational simplicity
- Proven reliability (ACID, widely used)
- Low dependency cost (stdlib)

### Alerting Mechanism
**Synchronous macOS Notification (Phase 1) → Async Queue (Phase 2 if needed)**:
- Start simple (direct `osascript` call in handler)
- Measure latency impact on real errors
- Add async queue only if >50ms blocking becomes observable issue

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│ claude-proxy (main.py)                                       │
│                                                               │
│  ┌──────────────┐      ┌─────────────────┐                  │
│  │ Provider API │─────>│ Error Raised    │                  │
│  │ Call         │      │ (Exception)     │                  │
│  └──────────────┘      └────────┬────────┘                  │
│                                  │                           │
│                                  v                           │
│                         ┌─────────────────┐                 │
│                         │ logger.error()  │                 │
│                         └────────┬────────┘                 │
│                                  │                           │
│                                  v                           │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ ErrorTrackingHandler (logging.Handler)                 │ │
│  │                                                         │ │
│  │  1. Compute fingerprint (hash of type+msg+location)    │ │
│  │  2. Query SQLite: SELECT ... WHERE fingerprint=?       │ │
│  │  3. If new: INSERT, send alert                         │ │
│  │  4. If existing: UPDATE count, last_seen               │ │
│  │  5. INSERT error_occurrence (metadata: provider, model)│ │
│  └────────────┬───────────────────────────┬───────────────┘ │
│               │                           │                  │
│               v                           v                  │
│  ┌──────────────────────┐   ┌─────────────────────────┐    │
│  │ error_tracker.db     │   │ macOS Notification      │    │
│  │ (SQLite)             │   │ (osascript)             │    │
│  │                      │   │                         │    │
│  │ - error_types        │   │ "New Error: Bedrock     │    │
│  │ - error_occurrences  │   │  validation failed"     │    │
│  └──────────────────────┘   └─────────────────────────┘    │
└───────────────────────────────────────────────────────────┘
```

### Implementation Phases

**Phase 1: Core tracking (80% of value)**
- SQLite schema creation
- Logging handler with fingerprinting
- Basic INSERT/UPDATE logic
- Synchronous macOS notification on new error

**Phase 2: Operational maturity**
- Retention policy script (prune old occurrences)
- Query CLI tool (search errors by provider, time)
- Alert rate limiting (max 1 per 5 min per fingerprint)

**Phase 3: Performance optimization (if needed)**
- Async alert queue
- Batch writes (buffer multiple errors, write every 5s)
- Read-only connection for queries (avoid lock contention)

---

## Pending Web Searches

If WebSearch becomes available, validate/expand these areas:

1. "Python SQLite WAL mode performance async writes" — confirm WAL is beneficial
2. "Python logging handler exception handling best practices" — avoid breaking logging chain
3. "Sentry fingerprinting algorithm details" — improve fingerprint stability
4. "macOS notification center rate limiting behavior" — understand system throttling
5. "Python queue.Queue vs asyncio.Queue for alert delivery" — choose async pattern

---

## Appendix: Fingerprinting Algorithm Sketch

```python
import hashlib
import re

def compute_fingerprint(record: logging.LogRecord) -> str:
    """
    Generate stable fingerprint for error deduplication.

    Strategy:
    - Normalize dynamic parts (IDs, timestamps, numbers)
    - Hash: error type + normalized message + code location
    """
    error_type = record.exc_info[0].__name__ if record.exc_info else "LoggedError"
    message = record.getMessage()

    # Normalize message: replace UUIDs, numbers, quotes
    normalized = re.sub(r'\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b',
                        '<UUID>', message)
    normalized = re.sub(r'\b\d+\b', '<NUM>', normalized)
    normalized = re.sub(r'["\']([^"\']+)["\']', r'<STR>', normalized)

    # Include code location (module + function)
    location = f"{record.module}.{record.funcName}"

    fingerprint_input = f"{error_type}|{normalized}|{location}"
    return hashlib.sha256(fingerprint_input.encode()).hexdigest()[:16]
```

**Example**:
```
Input:  ValidationException: Model 'claude-v2' not found in region us-west-2
Output: a3f7c9e1d2b5f8a0  (stable across region/model variations)

Input:  ValidationException: Model 'claude-3' not found in region us-east-1
Output: a3f7c9e1d2b5f8a0  (same fingerprint)
```

---

**Status**: Draft — ready for synthesis phase
**Next step**: Integrate with stack/features/pitfalls findings into synthesis.md
