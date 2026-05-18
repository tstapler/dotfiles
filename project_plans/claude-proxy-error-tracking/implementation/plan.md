# Implementation Plan: Claude Proxy Error Tracking

**Project**: claude-proxy-error-tracking
**Phase**: 3 — Planning complete
**Date**: 2026-04-16
**Next phase**: Phase 4 — Validation (`/quality:test-planner`)

---

## Epic Overview

### User Value Proposition
Enable rapid diagnosis of novel proxy failures by automatically detecting and alerting on new error types, preventing extended downtime and reducing manual log inspection overhead.

### Success Metrics
- **Primary**: Alert within 5 seconds of first occurrence of a new error fingerprint
- **Accuracy**: <1% fingerprint collision rate (different errors grouped together)
- **Coverage**: Capture 100% of logged errors from all providers (Anthropic, Bedrock)
- **Performance**: <2ms p99 overhead on error path (errors are rare, not hot path)
- **Storage**: Bounded growth <100MB with 90-day retention policy

### Scope

**In scope**:
- Error fingerprinting with signature extraction (provider + operation + error_type + normalized_message)
- SQLite persistence with two-tier schema (error_types + error_occurrences)
- macOS desktop notifications via `osascript` with 5-minute cooldown
- Custom logging handler integration (non-invasive, automatic capture)
- Query CLI for diagnostics (search by provider, time window, error type)

**Out of scope** (per requirements):
- Real-time dashboard UI (use existing `/dashboard` endpoint)
- External monitoring service integration (Datadog, Sentry)
- SLO/SLA enforcement or trending alerts
- Automatic error remediation

### Constraints
- Python stdlib-only implementation (zero external dependencies for MVP)
- Must not block request path (async writes or sync with acceptable latency)
- macOS-only alerting acceptable (solo practitioner use case)
- Integrate with existing `logging` infrastructure
- Must survive proxy restarts (persistent storage)

---

## Codebase Insights (Open Questions Answered)

### 1. Logging Infrastructure
**Answer**: Stdlib `logging` with `RotatingFileHandler`
- Found in `main.py` lines 21-58
- Separate log files: `/tmp/claude-proxy.app.log` (application), `/tmp/claude-proxy.http.log` (HTTP requests)
- Uses standard `logger = logging.getLogger(__name__)` pattern

### 2. Error Context Availability
**Answer**: Yes, errors logged with structured context
- Format: `[{request_id}] ✗ {provider}: {error_type} (model={model}) - {message}`
- Provider name, model, request_id all captured
- Found in `fallback.py` lines 132-147

### 3. Error Handling Pattern
**Answer**: Exception-based with custom types
- Custom exceptions: `RateLimitError`, `ValidationError`, `TimeoutError`, `AuthenticationError`, `ModelUnsupportedError`
- Fallback handler orchestrates retries and provider switching
- Route handlers catch and log with request context
- Found in `main.py` lines 899-924

### 4. Sample Bedrock Error Format
```
Bedrock validation error: An error occurred (ValidationException) when calling the InvokeModel operation: context_management: Extra inputs are not permitted
```
**Extraction confirmed**:
- Provider: "bedrock"
- Operation: "InvokeModel"
- Exception type: "ValidationException"
- Message: "context_management: Extra inputs are not permitted"

---

## Architecture Decisions

The following ADRs document key technical decisions:

- **ADR-001**: `decisions/ADR-001-fingerprinting-algorithm.md` — Signature extraction using provider + operation + error_type + normalized_message (vs stack-trace hashing)
- **ADR-002**: `decisions/ADR-002-storage-backend.md` — SQLite with two-tier schema and 90-day retention policy (vs JSON files or in-memory)
- **ADR-003**: `decisions/ADR-003-integration-approach.md` — Custom logging handler with ERROR level filter (vs decorator or middleware)
- **ADR-004**: `decisions/ADR-004-alert-delivery.md` — macOS notifications via `osascript` with 5-minute cooldown (vs stdout or file signals)

---

## Story Breakdown

### Story 1: Core Error Fingerprinting [1 week]

**User value**: Automatic deduplication of similar errors, enabling "new vs known" detection

**Acceptance criteria**:
- Given 30 days of historical logs, fingerprinting achieves <1% collision rate
- Same logical error produces same fingerprint across multiple occurrences
- Dynamic content (UUIDs, timestamps, request IDs) is normalized before hashing
- Fingerprint includes provider, operation, error type, and normalized message

**Tasks**:

#### Task 1.1: Implement signature extraction [3h]
**Objective**: Parse error messages to extract stable signature components

**Context boundary**:
- Files: `stapler-scripts/claude-proxy/error_tracker.py` (NEW), `test_error_tracker.py` (NEW)
- Lines: ~150 lines (signature extraction function + tests)
- Concepts: Regex-based parsing, error message structure

**Implementation approach**:
1. Create `extract_signature(error_message, provider, request_context)` function
2. Parse Bedrock format: `"{provider} {classification}: An error occurred ({exception_type}) when calling the {operation} operation: {message}"`
3. Return dict with provider, operation, error_type, message fields
4. Handle edge cases (missing fields, malformed messages)

**Validation strategy**:
- Unit test with sample Bedrock ValidationException → verify extraction
- Test ThrottlingException, rate limit errors, timeout errors
- Test malformed messages → verify graceful fallback

**INVEST check**: ✅ Independent (no external dependencies), Negotiable (regex patterns flexible), Valuable (enables fingerprinting), Estimable (3h), Small (single function), Testable (unit tests)

---

#### Task 1.2: Implement normalization and fingerprinting [3h]
**Objective**: Normalize dynamic content and generate stable hash fingerprints

**Context boundary**:
- Files: `error_tracker.py` (normalization + hashing functions), `test_error_tracker.py` (tests)
- Lines: ~120 lines (normalize_message + compute_fingerprint + tests)
- Concepts: Regex normalization patterns, SHA256 hashing

**Implementation approach**:
1. Create `normalize_message(message)` with regex patterns:
   - UUIDs → `<UUID>`
   - Model ARNs → `<MODEL_ARN>`
   - Numeric IDs → `<NUM>`
   - Operation names → `<OPERATION>`
2. Create `compute_fingerprint(signature)` → SHA256 hash first 16 chars
3. Test determinism (same input → same output)

**Validation strategy**:
- Same error with different request IDs → same fingerprint
- Different errors → different fingerprints
- Benchmark: <100µs per fingerprint

**INVEST check**: ✅ Independent, Negotiable (normalization patterns tunable), Valuable (core deduplication logic), Estimable (3h), Small (two functions), Testable (unit tests)

---

#### Task 1.3: Test fingerprinting on historical logs [2h]
**Objective**: Validate fingerprinting accuracy on real proxy errors

**Context boundary**:
- Files: `scripts/validate_fingerprints.py` (NEW)
- Lines: ~80 lines (log parsing + analysis script)
- Concepts: Log file parsing, collision detection, manual review

**Implementation approach**:
1. Extract errors from `/tmp/claude-proxy.app.log` (last 30 days)
2. Compute fingerprints for all errors
3. Calculate collision rate (same fingerprint, different error types)
4. Calculate stability rate (same logical error, different fingerprints)
5. Manual review of 10 sample fingerprint groups

**Validation strategy**:
- Target: <1% collision rate, >99% stability rate
- Document edge cases requiring special handling
- Verify diverse error types captured (not just ValidationException)

**INVEST check**: ✅ Independent (depends on 1.1-1.2 complete), Negotiable (analysis approach flexible), Valuable (validates core assumption), Estimable (2h), Small (analysis script), Testable (manual review)

---

### Story 2: Persistent Storage [1 week]

**User value**: Historical error data enables trend analysis and reduces false-positive "new error" alerts after restarts

**Acceptance criteria**:
- Error fingerprints persist across proxy restarts
- Storage grows linearly with unique error types (not total error count)
- Auto-pruning prevents unbounded growth (90-day retention policy)
- Query capability: search by provider, time window, fingerprint

**Tasks**:

#### Task 2.1: Design and implement SQLite schema [2h]
**Objective**: Create two-tier schema for deduplication and detailed storage

**Context boundary**:
- Files: `error_tracker.py` (schema + init)
- Lines: ~100 lines (schema SQL + initialization logic)
- Concepts: SQLite schema design, foreign keys, indexes

**Implementation approach**:
1. Define `error_types` table (fingerprint PK, first_seen, last_seen, count, metadata)
2. Define `error_occurrences` table (id PK, fingerprint FK, timestamp, context JSON)
3. Create indexes on timestamp, fingerprint, provider
4. Enable WAL mode: `PRAGMA journal_mode=WAL`
5. Create database at `~/.cache/claude-proxy/error_tracker.db`

**Validation strategy**:
- Schema creation succeeds
- WAL mode enabled (query `PRAGMA journal_mode`)
- Indexes created (query `sqlite_master`)

**INVEST check**: ✅ Independent (depends on Story 1), Negotiable (schema fields adjustable), Valuable (enables persistence), Estimable (2h), Small (schema definition), Testable (schema inspection)

---

#### Task 2.2: Implement error storage operations [3h]
**Objective**: CRUD operations for error tracking

**Context boundary**:
- Files: `error_tracker.py` (ErrorTracker class), `test_error_tracker.py` (storage tests)
- Lines: ~200 lines (class + methods + tests)
- Concepts: SQLite transactions, UPSERT, foreign key constraints

**Implementation approach**:
1. Create `ErrorTracker` class with `__init__(db_path)`
2. Implement `record_error(signature, context)` → returns `(fingerprint, is_new)`
   - UPSERT error_types (update count/last_seen if exists)
   - INSERT error_occurrences
   - Return is_new=True if first occurrence
3. Implement `get_error_by_fingerprint(fingerprint)` → dict
4. Implement `search_errors(provider, since, limit)` → list[dict]

**Validation strategy**:
- Record error → returns fingerprint
- Record same error again → updates count, not duplicate
- New error returns is_new=True
- Search filters work correctly

**INVEST check**: ✅ Independent, Negotiable (API design flexible), Valuable (core storage logic), Estimable (3h), Small (single class), Testable (unit tests with temp database)

---

#### Task 2.3: Implement retention policy [2h]
**Objective**: Auto-prune old error occurrences to prevent storage bloat

**Context boundary**:
- Files: `error_tracker.py` (pruning function)
- Lines: ~50 lines (pruning logic + tests)
- Concepts: Time-based cleanup, SQLite DELETE

**Implementation approach**:
1. Create `prune_old_occurrences(max_age_days=90)` method
2. DELETE FROM error_occurrences WHERE timestamp < (now - max_age_days)
3. Keep error_types intact (summary data)
4. Run on startup or periodic background task

**Validation strategy**:
- Insert errors with old timestamps (91 days ago)
- Run pruning
- Verify error_types present, error_occurrences deleted
- Storage size bounded

**INVEST check**: ✅ Independent, Negotiable (retention period configurable), Valuable (prevents unbounded growth), Estimable (2h), Small (single function), Testable (unit test with synthetic data)

---

### Story 3: Logging Integration [3 days]

**User value**: Automatic error capture without modifying existing error handling code

**Acceptance criteria**:
- All ERROR and CRITICAL level logs are captured
- Handler extracts provider/model/request_id from log record
- Handler failure does not break existing logging
- Logging overhead <1ms for tracked errors

**Tasks**:

#### Task 3.1: Implement custom logging handler [3h]
**Objective**: Intercept ERROR+ logs and extract error information

**Context boundary**:
- Files: `error_tracker.py` (ErrorTrackingHandler class)
- Lines: ~150 lines (handler + parsing methods)
- Concepts: logging.Handler subclass, exception handling, regex parsing

**Implementation approach**:
1. Create `ErrorTrackingHandler(logging.Handler)` with level=ERROR
2. Implement `emit(record)` method:
   - Parse `record.getMessage()` to extract provider, operation, error_type
   - Extract request_id from `[{request_id}]` prefix
   - Build signature dict
   - Call `tracker.record_error(signature, context)`
   - If is_new → alert
3. Wrap in try/except → log to stderr on failure (prevent circular logging)

**Validation strategy**:
- Trigger ValidationException → handler captures
- Handler exception → error logged to stderr, proxy continues
- Verify provider/model extraction from real log messages
- Benchmark: <1ms handler overhead

**INVEST check**: ✅ Independent (depends on Stories 1-2), Negotiable (parsing patterns flexible), Valuable (enables automatic capture), Estimable (3h), Small (single handler class), Testable (unit tests with mock LogRecord)

---

#### Task 3.2: Attach handler to proxy loggers [1h]
**Objective**: Register handler with existing logging infrastructure

**Context boundary**:
- Files: `main.py` (startup configuration)
- Lines: ~10 lines (handler attachment)
- Concepts: Logger configuration, handler registration

**Implementation approach**:
1. Import ErrorTracker and ErrorTrackingHandler
2. Initialize tracker after existing logging config (line 58)
3. Attach handler to root logger: `root_logger.addHandler(handler)`
4. Log "Error tracking handler attached" confirmation

**Validation strategy**:
- Proxy starts without errors
- Trigger test error → verify captured in database
- Check logs for "Error tracking handler attached" message

**INVEST check**: ✅ Independent (depends on 3.1), Negotiable (attachment point flexible), Valuable (activates tracking), Estimable (1h), Small (config change), Testable (integration test)

---

#### Task 3.3: Test error capture with live proxy [2h]
**Objective**: End-to-end validation of error tracking

**Context boundary**:
- Files: `scripts/test_error_tracking.sh` (NEW)
- Lines: ~50 lines (bash script)
- Concepts: Integration testing, curl requests, database queries

**Implementation approach**:
1. Start proxy
2. Trigger ValidationException (invalid request body)
3. Trigger ThrottlingException (burst requests)
4. Query database for captured errors
5. Verify fingerprints, counts, timestamps

**Validation strategy**:
- 100% of triggered errors appear in database
- Duplicate errors increment count (no duplicate fingerprints)
- Provider/model/request_id correctly extracted

**INVEST check**: ✅ Independent (depends on 3.2), Negotiable (test scenarios flexible), Valuable (validates integration), Estimable (2h), Small (test script), Testable (automated verification)

---

### Story 4: Alert Delivery [2 days]

**User value**: Immediate notification of new error types enables rapid response

**Acceptance criteria**:
- Desktop notification appears within 5 seconds of new error
- Cooldown prevents alert spam (max 1 alert per 5 minutes per fingerprint)
- Alert includes: fingerprint, error type, provider, model
- Alert failure does not block request path

**Tasks**:

#### Task 4.1: Implement macOS notification delivery [2h]
**Objective**: Send desktop notifications via `osascript`

**Context boundary**:
- Files: `error_tracker.py` (notification function)
- Lines: ~80 lines (alert logic + cooldown cache)
- Concepts: Subprocess execution, cooldown logic, error handling

**Implementation approach**:
1. Create `send_desktop_notification(fingerprint, signature)` method
2. Check cooldown: skip if alerted within 5 minutes
3. Build notification: title=`"New Error: {provider}"`, message=`"{error_type}: {message[:100]}"`
4. Execute: `subprocess.run(['osascript', '-e', 'display notification...'], timeout=2)`
5. Record alert time in cache

**Validation strategy**:
- Trigger new error → notification appears
- Trigger same error within 5 min → no notification
- Trigger same error after 6 min → notification appears
- Measure latency: <100ms

**INVEST check**: ✅ Independent (depends on Story 3), Negotiable (notification format flexible), Valuable (user visibility), Estimable (2h), Small (single function), Testable (integration test)

---

#### Task 4.2: Add alert logging and fallback [1h]
**Objective**: Log alert attempts and handle failures gracefully

**Context boundary**:
- Files: `error_tracker.py` (alert function error handling)
- Lines: ~30 lines (logging + exception handling)
- Concepts: Exception handling, non-blocking errors

**Implementation approach**:
1. Wrap `subprocess.run()` in try/except
2. On success: `logger.info(f"🔔 Alert sent: {fingerprint}")`
3. On timeout: `logger.warning(f"Alert timeout for {fingerprint}")`
4. On error: `logger.error(f"Alert failed for {fingerprint}: {e}")`
5. Never re-raise (non-blocking)

**Validation strategy**:
- Normal case → alert sent, log message
- osascript timeout → warning logged, proxy continues
- osascript error → error logged, proxy continues

**INVEST check**: ✅ Independent (depends on 4.1), Negotiable (logging format flexible), Valuable (operational visibility), Estimable (1h), Small (error handling), Testable (mock subprocess failure)

---

### Story 5: Query CLI [2 days]

**User value**: Diagnostics tool for investigating error patterns

**Acceptance criteria**:
- List all error types sorted by count or last_seen
- Filter by provider, time window
- Show detailed occurrences for a fingerprint
- Export to JSON or CSV

**Tasks**:

#### Task 5.1: Implement CLI query commands [3h]
**Objective**: Command-line tool for error analysis

**Context boundary**:
- Files: `scripts/error_cli.py` (NEW)
- Lines: ~200 lines (CLI with subcommands)
- Concepts: argparse, SQLite queries, table formatting

**Implementation approach**:
1. Create argparse with subcommands: list, show, search
2. `list` — display all errors sorted by count or last_seen
3. `show <fingerprint>` — display error details + recent occurrences
4. `search --provider <name> --since <time>` — filtered search
5. Format output as table (simple print or use tabulate if available)

**Validation strategy**:
- `error_cli.py list` → displays errors
- `error_cli.py search --provider bedrock` → shows only Bedrock
- `error_cli.py show <fingerprint>` → shows details

**INVEST check**: ✅ Independent (depends on Story 2, independent of 3-4), Negotiable (CLI UX flexible), Valuable (diagnostics capability), Estimable (3h), Small (single CLI script), Testable (manual testing)

---

#### Task 5.2: Add export functionality [2h]
**Objective**: Export error data for external analysis

**Context boundary**:
- Files: `scripts/error_cli.py` (export subcommand)
- Lines: ~80 lines (JSON + CSV export)
- Concepts: JSON serialization, CSV DictWriter

**Implementation approach**:
1. Add `export --format json|csv` subcommand
2. Query all error_types
3. If JSON: `json.dumps(errors, indent=2)`
4. If CSV: `csv.DictWriter` with error fields
5. Output to stdout (user redirects to file)

**Validation strategy**:
- `error_cli.py export --format json > errors.json` → valid JSON
- `error_cli.py export --format csv > errors.csv` → valid CSV
- Verify: Opens in spreadsheet

**INVEST check**: ✅ Independent (depends on 5.1), Negotiable (export format flexible), Valuable (external analysis), Estimable (2h), Small (export function), Testable (validate JSON/CSV format)

---

## Known Issues

### Bug 001: 🐛 [Fingerprinting]: Regex normalization may over-normalize [SEVERITY: Medium]
**Description**: Aggressive regex normalization (removing all numeric IDs) may group distinct errors together if error messages differ only by numbers.

Example:
- "Maximum tokens 4096 exceeded" → "Maximum tokens <NUM> exceeded"
- "Maximum tokens 8192 exceeded" → "Maximum tokens <NUM> exceeded" (collision!)

**Mitigation strategies**:
1. Use conservative normalization (only UUIDs/request IDs, not all numbers)
2. Add fingerprint inspector CLI to detect collisions
3. Allow manual fingerprint override for specific patterns
4. Monitor collision rate (alert if >1%)

**Files likely affected**:
- `error_tracker.py` — `normalize_message()` function

**Prevention approach**:
- Test on diverse error samples (Task 1.3)
- Document edge cases
- Include collision detection in validation script

**Related tasks**: Task 1.2 (normalization), Task 1.3 (validation)

---

### Bug 002: 🐛 [Storage]: SQLite lock contention under high error rates [SEVERITY: Low]
**Description**: Multiple concurrent errors may cause SQLite write contention if error rate exceeds ~100 errors/second. Proxy uses 10 workers (multi-process), each writing to shared database.

**Mitigation strategies**:
1. Use WAL mode (allows concurrent reads + 1 writer)
2. Implement retry with exponential backoff on SQLITE_BUSY
3. Use async writes with `asyncio.to_thread()`
4. If contention persists: per-worker buffer + periodic flush

**Files likely affected**:
- `error_tracker.py` — `record_error()` function

**Prevention approach**:
- Load test with 100+ errors/sec
- Add metrics for write failures
- Document acceptable error rate threshold

**Related tasks**: Task 2.2 (storage operations)

---

### Bug 003: 🐛 [Alerting]: osascript failure blocks error handler [SEVERITY: Medium]
**Description**: If `osascript` subprocess hangs or fails, error handler may block logging for up to 2 seconds (subprocess timeout).

**Mitigation strategies**:
1. Run osascript in separate thread pool (non-blocking)
2. Use aggressive timeout (2s)
3. Use `subprocess.run(..., timeout=2, check=False)` to ignore errors
4. Catch all exceptions without re-raising

**Files likely affected**:
- `error_tracker.py` — `send_desktop_notification()` function

**Prevention approach**:
- Test with osascript disabled (binary not in PATH)
- Add metrics for alert delivery failures
- Document fallback behavior

**Related tasks**: Task 4.1 (notification delivery), Task 4.2 (error handling)

---

### Bug 004: 🐛 [Integration]: Handler circular logging if tracker logs errors [SEVERITY: High]
**Description**: If `ErrorTrackingHandler.emit()` triggers an error that gets logged at ERROR level, infinite recursion could occur.

**Mitigation strategies**:
1. Use separate logger: `logging.getLogger("error_tracker.internal")`
2. Configure handler to ignore `error_tracker.internal` logger
3. Catch all exceptions and log to stderr (not logging module)
4. Add recursion depth counter (abort if depth > 1)

**Files likely affected**:
- `error_tracker.py` — `ErrorTrackingHandler.emit()` method

**Prevention approach**:
- Test: Inject error in `record_error()` → verify no infinite loop
- Use try/except with stderr fallback (as shown in Task 3.1)
- Add guard: `if record.name.startswith("error_tracker"): return`

**Related tasks**: Task 3.1 (handler implementation)

---

### Bug 005: 🐛 [Parsing]: Provider extraction fails on unexpected log format [SEVERITY: Medium]
**Description**: Error message parsing assumes format: `"[{request_id}] ✗ {provider}: {error_type} (model={model}) - {message}"`. If format changes or error comes from different code path, extraction fails.

**Mitigation strategies**:
1. Use regex with multiple fallback patterns
2. If extraction fails, use generic signature: `{"provider": "unknown", "error_type": "unknown", "message": <full_log>}`
3. Log extraction failures at DEBUG level
4. Add metrics for extraction success rate (alert if <90%)

**Files likely affected**:
- `error_tracker.py` — `_parse_error_message()` method in handler

**Prevention approach**:
- Test parsing on diverse log samples (rate limits, timeouts, auth errors)
- Document expected format + fallback behavior
- Handle: multiple error types, not just ValidationException

**Related tasks**: Task 3.1 (handler implementation), Task 3.3 (integration testing)

---

## Dependency Visualization

```
Story 1: Core Fingerprinting
   ├─ Task 1.1: Signature extraction (independent)
   ├─ Task 1.2: Normalization/hashing (depends on 1.1)
   └─ Task 1.3: Validation on logs (depends on 1.2)

Story 2: Persistent Storage
   ├─ Task 2.1: Schema design (depends on Story 1 complete)
   ├─ Task 2.2: Storage operations (depends on 2.1)
   └─ Task 2.3: Retention policy (depends on 2.2)

Story 3: Logging Integration
   ├─ Task 3.1: Handler implementation (depends on Story 1, Story 2)
   ├─ Task 3.2: Handler attachment (depends on 3.1)
   └─ Task 3.3: Live testing (depends on 3.2)

Story 4: Alert Delivery
   ├─ Task 4.1: Notification implementation (depends on Story 3)
   └─ Task 4.2: Logging/fallback (depends on 4.1)

Story 5: Query CLI
   ├─ Task 5.1: CLI commands (depends on Story 2, independent of 3-4)
   └─ Task 5.2: Export functionality (depends on 5.1)
```

**Critical path**: Story 1 → Story 2 → Story 3 → Story 4 (total: 2.5 weeks)
**Parallel work**: Story 5 can start after Story 2 completes

---

## Integration Checkpoints

### After Story 1: Fingerprinting Validated
**Verifiable**: Run `validate_fingerprints.py` on 30 days of logs

**Expected results**:
- <1% collision rate
- >99% stability rate
- Documented edge cases

**Go/No-Go**: If collision rate >5%, refine normalization before Story 2

---

### After Story 2: Storage Operational
**Verifiable**: Database inspection + storage tests

**Expected results**:
- Database at `~/.cache/claude-proxy/error_tracker.db`
- Schema matches design
- Write/read/update cycle works
- Retention policy functions

**Go/No-Go**: If write performance <100 writes/sec, optimize before Story 3

---

### After Story 3: Live Error Capture
**Verifiable**: Trigger errors, query database

**Expected results**:
- 100% of ERROR logs captured
- Provider/model/request_id extracted correctly
- Handler exceptions isolated

**Go/No-Go**: If capture rate <100%, fix handler before Story 4

---

### After Story 4: End-to-End Alert Flow
**Verifiable**: Trigger new error, verify notification

**Expected results**:
- Desktop notification within 5 seconds
- Cooldown prevents duplicate alerts
- Alert failure non-blocking

**Go/No-Go**: If alert latency >10 seconds, move to async delivery

---

### Final: Complete System Integration
**Verifiable**: 48-hour production burn-in

**Expected results**:
- No false-positive alerts on restart
- Alert accuracy: 100% recall, 0% false negatives
- Storage growth: <10MB after 48 hours
- Performance: p99 latency unchanged

---

## Testing Strategy

### Unit Tests (pytest)
**Coverage target**: >80%

**Test modules**:
- `test_error_tracker.py` — Fingerprinting, normalization, storage
  - Signature extraction from diverse messages
  - Normalization preserves error type
  - Same error → same fingerprint
  - Database write/read/update cycle
  - Retention policy deletes old data

**Run**: `pytest stapler-scripts/claude-proxy/test_error_tracker.py -v --cov=error_tracker`

---

### Integration Tests
**Coverage**: End-to-end with real database

**Scenarios**:
- Error logged → handler captures → database write → query retrieves
- New error triggers alert → cooldown prevents duplicate
- Multiple workers writing concurrently → no corruption
- Proxy restart → errors persist → no false-positive alerts

**Run**: `pytest stapler-scripts/claude-proxy/test_error_tracker_integration.py -v`

---

### E2E Tests (bash)
**Coverage**: Real proxy with error tracking enabled

**Script**: `scripts/test_error_tracking.sh`

**Scenarios**:
- Trigger ValidationException → verify captured
- Trigger ThrottlingException → verify captured
- Query database → verify data present

---

### Performance Tests
**Coverage**: Latency and storage scalability

**Scenarios**:
1. Baseline latency (tracking disabled)
2. Error path overhead (100 errors → measure latency)
3. Storage growth (1000 unique errors → verify <50MB)
4. Concurrent writes (10 workers × 10 errors/sec → verify no lock contention)

**Tools**: `wrk` or `locust`, `time` for profiling

**Acceptance**: <2ms p99 overhead on error path

---

## Success Criteria

### Functional Requirements
- ✅ Unique fingerprint per error type (provider + operation + error_type + message)
- ✅ Deduplication: Same error increments count
- ✅ Metadata capture: provider, model, request_id, timestamp
- ✅ Persistence: Survives proxy restarts
- ✅ New error alerting: Desktop notification within 5 seconds
- ✅ Alert cooldown: Max 1 per 5 minutes per fingerprint

### Non-Functional Requirements
- ✅ Performance: <2ms p99 overhead on error path
- ✅ Reliability: Handler failures isolated
- ✅ Storage: <100MB after 90 days
- ✅ Accuracy: <1% fingerprint collision rate
- ✅ Coverage: 100% of ERROR+ logs captured

### Operational Requirements
- ✅ Query CLI functional
- ✅ Retention policy enforced (90-day auto-pruning)
- ✅ Logging integration non-invasive
- ✅ Documentation: README with setup, usage, troubleshooting

---

## Next Steps

**Immediate**: Phase 4 — Validation planning
- Run `/quality:test-planner` to create `validation.md`
- Map test cases to requirements line-by-line
- Define test coverage requirements

**After validation**: Phase 5 — Implementation
- **CRITICAL**: Open fresh session (planning context must not contaminate implementation)
- Run `/code:implement` with `plan.md` + `validation.md` as input
- Implement tasks in dependency order (Story 1 → 2 → 3 → 4, Story 5 parallel after Story 2)

**After implementation**: Phase 6 — QA
- Run `/quality:does-it-work` to verify implementation
- Run `/code:review` before claiming completion
