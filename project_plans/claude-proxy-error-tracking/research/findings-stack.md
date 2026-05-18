# Stack Research Findings: Error Tracking for Claude Proxy

**Project**: claude-proxy-error-tracking
**Research Dimension**: Stack — Technology Options
**Date**: 2026-04-16
**Status**: Draft (training knowledge only — web search unavailable)

---

## Executive Summary

For a lightweight Python error tracking system with deduplication, three viable approaches emerge:

1. **Stdlib-only** — hashlib for fingerprinting + SQLite for persistence + logging handlers
2. **Sentry SDK (local mode)** — industry-standard fingerprinting with optional local storage
3. **Hybrid** — custom fingerprinting with selective third-party libs (e.g., python-daemon for background alerts)

**Recommendation**: Start with stdlib-only approach for fastest implementation, with architecture that allows upgrading to Sentry SDK later if fingerprinting proves inadequate.

---

## Options Surveyed

### 1. Stdlib-Only Error Tracking

**Components**:
- **Fingerprinting**: `hashlib.sha256()` on normalized error type + message patterns
- **Persistence**: `sqlite3` built-in module
- **Alerting**: `print()` to stdout/stderr + optional file-based flag for external monitoring
- **Deduplication**: In-memory LRU cache (`functools.lru_cache` or manual dict with timestamp tracking)

**Pros**:
- Zero external dependencies
- Full control over fingerprint algorithm
- Minimal installation/deployment complexity
- Predictable performance

**Cons**:
- Manual fingerprint algorithm requires tuning (risk of collision or over-fragmentation)
- No industry-standard error grouping patterns
- Alerting limited to stdout/files (no native desktop notifications)

**Use case fit**: Ideal for urgent timeline requirement — can implement in hours, not days.

---

### 2. Sentry SDK (Local Mode)

[TRAINING_ONLY — verify latest SDK capabilities]

**Components**:
- **Fingerprinting**: Sentry's built-in grouping algorithm (considers stack trace, exception type, message patterns)
- **Persistence**: Can run in "offline" mode with local file-based envelope storage
- **Alerting**: Hooks for custom notification on new issue types
- **Deduplication**: Production-proven algorithm used by Sentry SaaS

**Pros**:
- Industry-standard error grouping (handles dynamic messages well)
- Mature fingerprinting that accounts for stack trace frames, not just error messages
- Can upgrade to Sentry hosted service later without code changes
- Rich context capture (breadcrumbs, tags, user info)

**Cons**:
- External dependency (~5MB SDK)
- More complex to configure for purely local usage (SDK defaults to sending data to Sentry)
- Overkill for simple deduplication needs
- Learning curve for SDK API

**Use case fit**: Better for long-term maintenance if error patterns prove complex.

---

### 3. Desktop Notification Libraries (macOS/Linux)

For alerting on new error types beyond stdout:

| Library | Platform Support | Dependency Weight | Notes |
|---------|-----------------|-------------------|-------|
| `plyer` | macOS, Linux, Windows | ~200KB | Cross-platform abstraction (uses `pync` on macOS, `notify-send` on Linux) [TRAINING_ONLY] |
| `pync` | macOS only | ~50KB | Native macOS notification center integration [TRAINING_ONLY] |
| `notify2` | Linux only | ~20KB | D-Bus based (requires `dbus-python`) [TRAINING_ONLY] |
| `osascript` (subprocess) | macOS only | stdlib | Shell out to AppleScript — no external dependency |
| `notify-send` (subprocess) | Linux only | stdlib | Shell out to libnotify — typically pre-installed |

**Recommendation for alerting**: Start with stdout + file flag, then add `subprocess` calls to `osascript`/`notify-send` for desktop alerts. Avoid third-party notification libraries for now (adds dependency for marginal value).

---

### 4. Error Fingerprinting Strategies

[TRAINING_ONLY — verify current best practices]

| Strategy | Stability | Collision Risk | Implementation |
|----------|-----------|----------------|----------------|
| **Exception type only** | High | High | `hash(type(exc).__name__)` |
| **Type + message prefix** | Medium | Medium | `hash(type + message[:100])` |
| **Type + stack trace top frame** | Medium | Low | `hash(type + traceback.extract_tb(tb)[0])` |
| **Sentry-style (type + stack + message pattern)** | High | Low | Normalize message (remove IDs, timestamps), hash type + normalized message + stack fingerprint |
| **Custom regex-based normalization** | Medium | Medium | Replace dynamic parts (IDs, timestamps, model names) with placeholders before hashing |

**For claude-proxy context**:
- Errors like `"Bedrock validation error: An error occurred (ValidationException) when calling the InvokeModel operation: context_management: Extra inputs are not permitted"` have stable structure but dynamic operation names.
- **Recommended approach**: Hash on `(exception_type, normalized_message, request_provider, request_model)` where normalization replaces operation names/IDs with placeholders.

**Normalization regex patterns** (to apply before hashing):
```python
# Replace Bedrock operation names
message = re.sub(r'when calling the \w+ operation', 'when calling the <OPERATION>', message)
# Replace model ARNs
message = re.sub(r'arn:aws:bedrock:[^:]+:[^:]+:model/[^\s]+', '<MODEL_ARN>', message)
# Replace request IDs
message = re.sub(r'\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b', '<UUID>', message)
```

---

### 5. Persistence Options

| Backend | Write Performance | Query Capability | Storage Growth | Setup Complexity |
|---------|------------------|------------------|----------------|------------------|
| **In-memory dict** | Instant | Limited | Unbounded (until restart) | Trivial |
| **SQLite** | ~1ms/write | Full SQL queries | Controlled (can auto-prune) | Low (stdlib) |
| **JSON file** | ~10ms/write (full rewrite) | Load entire file | Unbounded | Trivial |
| **JSON-lines (append)** | ~1ms/write | Sequential scan or external index | Unbounded | Low |

**Recommendation**: SQLite with auto-pruning (keep last N days or last M unique errors). Provides query capability for diagnostics without external dependencies.

**Schema sketch**:
```sql
CREATE TABLE errors (
    id INTEGER PRIMARY KEY,
    fingerprint TEXT NOT NULL,
    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    count INTEGER DEFAULT 1,
    exception_type TEXT,
    message TEXT,
    stack_trace TEXT,
    provider TEXT,
    model TEXT,
    metadata JSON
);
CREATE INDEX idx_fingerprint ON errors(fingerprint);
CREATE INDEX idx_last_seen ON errors(last_seen);
```

---

## Trade-off Matrix

| Dimension | Stdlib-Only | Sentry SDK | Hybrid (stdlib + notifications) |
|-----------|-------------|------------|--------------------------------|
| **Dependency weight** | 0 external deps | ~5MB SDK | ~50-200KB (if using desktop lib) |
| **Fingerprinting accuracy** | Medium (requires tuning) | High (production-proven) | Medium (manual algorithm) |
| **Alerting channels** | stdout, file | Hooks + custom | stdout, file, desktop |
| **Persistence options** | SQLite (stdlib) | File-based envelopes | SQLite (stdlib) |
| **Implementation time** | Hours | Days (learning curve) | Hours + notification testing |
| **Future extensibility** | Low (custom format) | High (Sentry compatible) | Medium (need migration path) |

---

## Risk and Failure Modes

### 1. Fingerprint Instability
**Risk**: Dynamic error messages (request IDs, timestamps, model names) cause same error type to generate different fingerprints.

**Mitigation**: Apply normalization regexes before hashing. Test against known error samples from claude-proxy logs.

**Detection**: Monitor "unique error count" metric — if growing linearly with total errors, fingerprinting is broken.

---

### 2. Alert Fatigue
**Risk**: Existing errors re-trigger "new error" alerts after proxy restart (if using in-memory persistence).

**Mitigation**: Use SQLite persistence that survives restarts. Track `first_seen` timestamp and only alert on truly new fingerprints (not seen in last N days).

**Tuning parameter**: Define "new" as "not seen in last 7 days" vs "never seen before."

---

### 3. Storage Bloat
**Risk**: SQLite database grows unbounded if all errors are persisted forever.

**Mitigation**: Implement auto-pruning: delete errors older than 90 days or keep only top 1000 most recent unique fingerprints.

**Monitoring**: Track SQLite file size; alert if exceeds 100MB (indicates pruning failure).

---

### 4. Performance Overhead
**Risk**: Synchronous error capture slows down request handling in proxy.

**Mitigation**:
- Use async SQLite writes (queue errors, flush in background thread)
- Skip fingerprinting for errors during high-load periods (circuit breaker pattern)
- Measure: add timing metrics for error capture path

**Acceptable threshold**: <5ms p99 overhead per request.

---

### 5. Fingerprint Collisions
**Risk**: Different error types hash to same fingerprint, hiding novel errors.

**Detection**: Manually inspect samples from each fingerprint group; if mixed error types, algorithm needs refinement.

**Mitigation**: Include more context in fingerprint (provider, model, stack trace) to reduce collision probability.

---

## Migration and Adoption Cost

### Integration Points with claude-proxy

[Requires reading existing code — see Open Questions]

**Likely integration patterns**:
1. **Exception handler wrapper** — Decorate route handlers with `@track_errors` that catches exceptions before response
2. **Logging handler** — Custom `logging.Handler` subclass that intercepts ERROR/CRITICAL logs
3. **Middleware** — FastAPI/Flask middleware that wraps request/response cycle

**Least invasive**: Custom logging handler (no code changes to existing handlers, just logger config).

**Most control**: Exception handler wrapper (can access request context, extract provider/model from request).

---

### Rollout Strategy

**Phase 1 (MVP — target: 1 day)**:
- Implement fingerprinting + SQLite persistence
- Add stdout alerting for new error types
- Test on existing error samples from logs

**Phase 2 (alerting — target: +1 day)**:
- Add desktop notifications via `osascript`/`notify-send`
- Add error detail lookup CLI (`error-tracker show <fingerprint>`)

**Phase 3 (query capability — target: +1 day)**:
- Add CLI for querying errors by provider, model, date range
- Add periodic summary report (e.g., daily email/Slack with new error types)

---

## Operational Concerns

### Observability
**Metrics to track**:
- Total unique error fingerprints (should be bounded)
- New error types per day (alert if >10/day, indicates instability)
- Error capture latency (p50, p99)
- SQLite file size

**Integration**: Extend existing `metrics.py` in claude-proxy to include error tracking counters.

---

### Maintenance Burden
**Stdlib approach**: Low — pure Python, no dependency updates.

**Sentry SDK approach**: Medium — need to track SDK updates, API changes.

**Verdict**: Start stdlib, migrate to Sentry only if fingerprinting proves inadequate after 1 month of production use.

---

### Testing Strategy
**Unit tests**:
- Fingerprint stability (same error → same hash)
- Normalization regex correctness
- SQLite persistence (write/read/prune)

**Integration tests**:
- End-to-end: trigger known error in proxy, verify fingerprint appears in DB
- Alert delivery: verify stdout output format

**Property-based tests** (using `hypothesis`):
- Fingerprinting should be deterministic for same input
- Normalization should not lose critical error type info

---

## Prior Art

[TRAINING_ONLY — verify current state of these projects]

### 1. Sentry (open source core)
- **Fingerprinting**: Groups by stack trace frames + exception type + message patterns
- **Deduplication**: Increments counter on existing fingerprint
- **Alerting**: Webhooks, email, Slack integrations
- **Storage**: PostgreSQL for production; file-based for SDK offline mode

**Lessons**: Fingerprinting is hard — consider stack trace, not just message. Sentry's algorithm is open source and proven.

---

### 2. Rollbar (proprietary)
- **Fingerprinting**: Similar to Sentry but more aggressive message normalization
- **Deduplication**: Time-windowed grouping (errors within 5 min grouped aggressively)
- **Alerting**: Rate-based alerts (trigger if error rate spikes)

**Lessons**: Alert on *rate changes*, not just new types. Reduces noise for existing errors.

---

### 3. Airbrake (open source origin)
- **Fingerprinting**: Exception class + file + line number
- **Deduplication**: Exact match only (less normalization)
- **Alerting**: Email, webhooks

**Lessons**: Simpler fingerprinting is more predictable but creates more false-positive "new" errors.

---

### 4. structlog (Python logging library)
- **Structured logging**: JSON logs with consistent keys
- **Processors**: Chain of functions to enrich/normalize log entries before output

**Relevance**: If claude-proxy uses `structlog`, error tracking can hook into log processing pipeline with minimal invasiveness.

---

## Open Questions

**Requires web search / codebase inspection**:

1. Does claude-proxy use `structlog`, stdlib `logging`, or custom logger?
   - **Impact**: Determines integration point (handler vs middleware vs decorator)

2. What is the current error handling pattern in route handlers?
   - **Impact**: Determines whether to wrap at handler level or use middleware

3. Are errors currently logged with structured context (provider, model)?
   - **Impact**: If yes, can extract from logs; if no, need to modify handlers

4. What is acceptable error capture latency budget?
   - **Impact**: Determines whether to use sync or async SQLite writes

5. Is there an existing metrics/monitoring system beyond `metrics.py`?
   - **Impact**: Determines whether to integrate with existing system or build standalone

---

## Pending Web Searches

Due to WebSearch unavailability, the following searches were not conducted. Verify these claims before implementation:

1. **"Python error fingerprinting libraries deduplication"**
   - Verify: Are there specialized Python libraries for error fingerprinting beyond Sentry?
   - Verify: Current best practices for message normalization patterns

2. **"lightweight error tracking Python no external service"**
   - Verify: What do other Python projects use for local error tracking?
   - Verify: Any stdlib-based reference implementations?

3. **"Sentry SDK local mode Python"**
   - Verify: Can Sentry SDK run in fully offline mode without sending data?
   - Verify: What is the SDK size and performance overhead?

4. **"Python desktop notification libraries macOS Linux"**
   - Verify: Current best cross-platform notification library
   - Verify: `plyer` vs `pync` vs `notify2` current maintenance status

---

## Recommendation

**Adopt stdlib-only approach with upgrade path to Sentry SDK.**

### Phase 1 Implementation (MVP — target: 1 day)

**Components**:
1. **Fingerprinting**:
   - Hash on `(exception_type, normalized_message, provider, model)`
   - Normalization: Apply regex patterns to remove operation names, IDs, ARNs

2. **Persistence**:
   - SQLite with schema above
   - Auto-prune: delete entries older than 90 days on startup

3. **Alerting**:
   - On new fingerprint: `print(f"[NEW ERROR] {fingerprint}: {exception_type} - {message}", file=sys.stderr)`
   - Write flag file: `/tmp/claude-proxy-new-error` (external monitoring can watch)

4. **Integration**:
   - Custom logging handler that intercepts ERROR+ logs
   - Extract provider/model from log record `extra` dict (requires adding to existing logs)

### Success Metrics
- **Within 1 week**: Catch at least 3 distinct error types from production proxy usage
- **Within 1 month**: Zero false-positive "new error" alerts for known errors (fingerprint stability)

### Decision Point: Migrate to Sentry SDK if...
- Fingerprint collision rate >5% (determined by manual inspection)
- New error types missed due to over-aggressive grouping
- Need for distributed error tracking (multiple proxy instances)

### Why This Over Alternatives
- **Vs Sentry SDK now**: Faster to implement (hours vs days), zero dependencies, meets urgent timeline
- **Vs pure in-memory**: SQLite persistence survives restarts, enables querying for diagnostics
- **Vs JSON file**: SQLite provides query capability and auto-pruning without complex file management

---

## Next Steps

1. **Inspect claude-proxy codebase** to answer Open Questions 1-3
2. **Prototype fingerprinting algorithm** against sample errors from logs (validation)
3. **Implement MVP** following Phase 1 spec above
4. **Run for 1 week** and evaluate fingerprint stability before considering Sentry migration
