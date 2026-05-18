# Validation Plan: Claude Proxy Error Tracking

**Project**: claude-proxy-error-tracking
**Phase**: 4 — Validation Planning
**Date**: 2026-04-16
**Next phase**: Phase 5 — Implementation (requires FRESH SESSION)

---

## Purpose

This document maps every requirement and acceptance criterion to specific test cases, ensuring complete validation coverage before claiming feature complete. Phase 4 (Validation) happens BEFORE implementation to define "done" criteria.

---

## Test Coverage Targets

| Test Level | Target Coverage | Rationale |
|------------|----------------|-----------|
| **Unit tests** | >80% code coverage | Core logic (fingerprinting, normalization, storage) must be thoroughly tested |
| **Integration tests** | 100% of integration points | Handler → storage → alert flow must work end-to-end |
| **E2E tests** | 100% of user-facing scenarios | All acceptance criteria must be verified in realistic environment |
| **Performance tests** | All success metrics validated | <2ms p99 overhead, <1% collision rate, <100MB storage |

---

## Requirements Traceability Matrix

### Requirement 1: Unique Error Type Identification and Deduplication

**Source**: `requirements.md` — Must Have (MoSCoW)

**Success Metrics** (from `plan.md`):
- <1% fingerprint collision rate (different errors grouped together)
- Same logical error produces same fingerprint across multiple occurrences

**Test Cases**:

#### TC-REQ1-001: Signature Extraction Accuracy
**Type**: Unit test
**Objective**: Verify signature extraction from diverse error messages
**Test data**:
- Bedrock ValidationException: `"Bedrock validation error: An error occurred (ValidationException) when calling the InvokeModel operation: context_management: Extra inputs are not permitted"`
- Bedrock ThrottlingException: `"Bedrock error: An error occurred (ThrottlingException) when calling the InvokeModel operation: Rate exceeded"`
- Anthropic RateLimitError: `"Rate limit exceeded for model claude-opus-4-6"`
- Generic error: `"API Error: 500 Internal Server Error"`

**Expected results**:
- ValidationException extracts: provider="bedrock", operation="InvokeModel", error_type="ValidationException", message="context_management: Extra inputs are not permitted"
- ThrottlingException extracts: provider="bedrock", operation="InvokeModel", error_type="ThrottlingException", message="Rate exceeded"
- RateLimitError extracts: provider="anthropic", operation="unknown", error_type="RateLimitError", message="Rate limit exceeded for model claude-opus-4-6"
- Generic error fallback: provider="unknown", operation="unknown", error_type="unknown", message="API Error: 500 Internal Server Error"

**Validates**: Story 1 Task 1.1 (Signature extraction)

---

#### TC-REQ1-002: Normalization Stability
**Type**: Unit test
**Objective**: Verify dynamic content is removed while preserving error semantics
**Test data**:
- Error with UUID: `"Request abc-123-def-456 failed: ValidationException"`
- Error with model ARN: `"Model arn:aws:bedrock:us-east-1:123456789:model/claude-v2 not found"`
- Error with numeric ID: `"Request ID 98765432109876543210 timed out"`
- Error with timestamp: `"Error at 2024-04-16T10:30:00Z: Connection refused"`

**Expected results**:
- UUID normalized: `"Request <UUID> failed: ValidationException"`
- ARN normalized: `"Model <MODEL_ARN> not found"`
- Long numeric ID normalized: `"Request ID <ID> timed out"`
- Timestamp preserved (not a UUID): `"Error at 2024-04-16T10:30:00Z: Connection refused"` (timestamps are semantic, not dynamic IDs)

**Validates**: Story 1 Task 1.2 (Normalization)

---

#### TC-REQ1-003: Fingerprint Determinism
**Type**: Unit test
**Objective**: Same input always produces same fingerprint
**Test data**: Same error message with different request IDs (10 samples)

**Expected results**:
- All 10 fingerprints are identical
- Fingerprint is 16-character hexadecimal string
- Fingerprint generation takes <100µs

**Validates**: Story 1 Task 1.2 (Fingerprinting)

---

#### TC-REQ1-004: Fingerprint Collision Rate
**Type**: Integration test (historical log analysis)
**Objective**: Validate collision rate <1% on real proxy errors
**Test data**: 30 days of proxy logs from `/tmp/claude-proxy.app.log`

**Expected results**:
- Extract all ERROR-level messages
- Compute fingerprints for all errors
- Calculate collision rate: (# of fingerprints with mixed error types) / (total unique fingerprints)
- Target: Collision rate <1%
- Stretch goal: <0.5%

**Validates**: Story 1 Task 1.3 (Validation on logs), Success Metric (accuracy)

---

#### TC-REQ1-005: Deduplication Correctness
**Type**: Integration test
**Objective**: Same error increments count, not creates duplicate fingerprint
**Test data**: Record same error 5 times

**Expected results**:
- First occurrence: INSERT into error_types, count=1
- Second occurrence: UPDATE error_types SET count=2
- Fifth occurrence: UPDATE error_types SET count=5
- Total rows in error_types: 1 (not 5)
- Total rows in error_occurrences: 5

**Validates**: Story 2 Task 2.2 (Storage operations), Requirement (deduplication)

---

### Requirement 2: Error Metadata Capture

**Source**: `requirements.md` — Must Have (MoSCoW)

**Success Metrics** (from `plan.md`):
- Capture provider, model, request_id, timestamp for each occurrence

**Test Cases**:

#### TC-REQ2-001: Metadata Extraction from Log Records
**Type**: Unit test
**Objective**: Extract metadata from structured log messages
**Test data**: Log message `"[abc-123] ✗ bedrock: ValidationException (model=claude-opus-4-6) - context_management: Extra inputs"`

**Expected results**:
- request_id: "abc-123"
- provider: "bedrock"
- error_type: "ValidationException"
- model: "claude-opus-4-6"
- message: "context_management: Extra inputs"

**Validates**: Story 3 Task 3.1 (Handler implementation), Requirement (metadata capture)

---

#### TC-REQ2-002: Metadata Persistence
**Type**: Integration test
**Objective**: Verify metadata stored correctly in database
**Test data**: Error with full context (provider, model, request_id, timestamp)

**Expected results**:
- error_types table: Contains provider, operation, error_type, message
- error_occurrences table: Contains request_id, model, timestamp, context JSON
- Context JSON includes extra fields (e.g., {"max_tokens": 1024, "stream": false})

**Validates**: Story 2 Task 2.2 (Storage operations), Requirement (metadata capture)

---

#### TC-REQ2-003: Metadata Query Capability
**Type**: Integration test
**Objective**: Search errors by metadata fields
**Test data**: 10 errors (5 Bedrock, 5 Anthropic, mixed models)

**Expected results**:
- `search_errors(provider="bedrock")` returns 5 errors
- `search_errors(provider="anthropic")` returns 5 errors
- `search_errors(provider="bedrock", since=<timestamp>)` returns only recent Bedrock errors
- Query execution time <50ms

**Validates**: Story 2 Task 2.2 (Storage operations), Story 5 Task 5.1 (CLI commands)

---

### Requirement 3: Persistence Layer

**Source**: `requirements.md` — Must Have (MoSCoW)

**Success Metrics** (from `plan.md`):
- Storage grows linearly with unique error types (not total error count)
- Bounded growth <100MB with 90-day retention policy
- Errors survive proxy restarts

**Test Cases**:

#### TC-REQ3-001: Database Schema Validation
**Type**: Unit test
**Objective**: Verify SQLite schema created correctly
**Test data**: Initialize ErrorTracker

**Expected results**:
- Tables exist: error_types, error_occurrences
- Indexes exist: idx_occurrences_timestamp, idx_occurrences_fingerprint, idx_error_types_provider, idx_error_types_last_seen
- WAL mode enabled: `PRAGMA journal_mode` returns "wal"
- Foreign key constraint: error_occurrences.fingerprint → error_types.fingerprint

**Validates**: Story 2 Task 2.1 (Schema design)

---

#### TC-REQ3-002: Restart Persistence
**Type**: Integration test
**Objective**: Errors survive proxy restart
**Test data**: Record 3 errors, restart proxy, query database

**Expected results**:
- After restart: All 3 errors still present in database
- Counts preserved
- No false-positive "new error" alerts (errors loaded from database on startup)

**Validates**: Requirement (persistence), Story 2 Task 2.2 (Storage operations)

---

#### TC-REQ3-003: Storage Growth Linearity
**Type**: Integration test
**Objective**: Storage scales with unique errors, not total count
**Test data**: Record 10 unique errors, each occurring 100 times (1000 total)

**Expected results**:
- error_types rows: 10 (one per unique error)
- error_occurrences rows: 1000 (one per occurrence)
- Database file size: <1MB
- Growth rate: O(unique errors) for error_types, O(occurrences) for error_occurrences

**Validates**: Success Metric (storage growth), Story 2 Task 2.2 (Storage operations)

---

#### TC-REQ3-004: Retention Policy Enforcement
**Type**: Integration test
**Objective**: Auto-pruning prevents unbounded growth
**Test data**: Insert errors with timestamps 91 days ago, run pruning

**Expected results**:
- Before pruning: error_occurrences contains old entries
- After pruning: error_occurrences older than 90 days deleted
- error_types table intact (summary data preserved)
- Storage size reduced by ~90% (assuming most data is in error_occurrences)

**Validates**: Success Metric (bounded growth), Story 2 Task 2.3 (Retention policy)

---

#### TC-REQ3-005: Storage Size After 90 Days
**Type**: Performance test (simulated)
**Objective**: Verify storage <100MB after 90 days
**Test data**: Simulate 90 days of errors (assumptions: 50 unique error types, 100 errors/day, 90-day retention)

**Expected results**:
- error_types: 50 rows × ~500 bytes = ~25KB
- error_occurrences: 9000 rows × ~1KB = ~9MB
- Total database size: <10MB (well under 100MB target)

**Validates**: Success Metric (storage growth)

---

### Requirement 4: New Error Type Alerting

**Source**: `requirements.md` — Must Have (MoSCoW)

**Success Metrics** (from `plan.md`):
- Alert within 5 seconds of first occurrence
- Cooldown prevents alert spam (max 1 alert per 5 minutes per fingerprint)

**Test Cases**:

#### TC-REQ4-001: New Error Detection
**Type**: Integration test
**Objective**: First occurrence triggers "new error" flag
**Test data**: Record error that doesn't exist in database

**Expected results**:
- `record_error()` returns `is_new=True`
- Alert triggered (notification sent)
- Second occurrence of same error returns `is_new=False`
- No alert triggered for second occurrence

**Validates**: Requirement (new error detection), Story 3 Task 3.1 (Handler implementation)

---

#### TC-REQ4-002: Alert Delivery Latency
**Type**: Performance test
**Objective**: Alert appears within 5 seconds of error occurrence
**Test data**: Trigger new error, measure time to notification

**Expected results**:
- Time from error logged to notification displayed: <5 seconds
- Typical: <1 second (synchronous delivery)
- Alert content: Title="New Error: {provider}", Message="{error_type}: {message[:100]}"

**Validates**: Success Metric (alert within 5 seconds), Story 4 Task 4.1 (Notification delivery)

---

#### TC-REQ4-003: Alert Cooldown
**Type**: Integration test
**Objective**: Cooldown prevents duplicate alerts
**Test data**: Trigger same error twice within 5 minutes

**Expected results**:
- First occurrence: Alert sent, logged to `logger.info("🔔 Alert sent: {fingerprint}")`
- Second occurrence (1 minute later): No alert, logged to `logger.debug("Alert cooldown active for {fingerprint}")`
- Third occurrence (6 minutes later): Alert sent (cooldown expired)

**Validates**: Success Metric (cooldown prevents spam), Story 4 Task 4.1 (Notification delivery)

---

#### TC-REQ4-004: Alert Failure Non-Blocking
**Type**: Integration test
**Objective**: Alert failures don't break proxy
**Test data**: Mock `subprocess.run()` to raise exception, trigger error

**Expected results**:
- Alert delivery fails → exception caught
- Error logged to stderr: `"Alert failed for {fingerprint}: {error}"`
- Proxy continues operation (no crash)
- Error still recorded in database (alert failure doesn't prevent tracking)

**Validates**: Story 4 Task 4.2 (Error handling), Known Issue #003

---

### Requirement 5: Automatic Error Capture

**Source**: Implicit requirement (logging integration must be automatic)

**Success Metrics** (from `plan.md`):
- Capture 100% of ERROR and CRITICAL level logs
- Handler failure does not break existing logging

**Test Cases**:

#### TC-REQ5-001: Automatic Capture Coverage
**Type**: Integration test
**Objective**: All ERROR+ logs are captured
**Test data**: Trigger errors in different modules (main.py, fallback.py, providers/bedrock.py)

**Expected results**:
- All errors appear in database (100% capture rate)
- Errors from all modules captured (not just main.py)
- No manual logging required (automatic via handler attachment)

**Validates**: Story 3 Task 3.2 (Handler attachment), Story 3 Task 3.3 (Live testing)

---

#### TC-REQ5-002: Handler Exception Isolation
**Type**: Unit test
**Objective**: Handler exceptions don't break logging chain
**Test data**: Mock `tracker.record_error()` to raise exception, log error

**Expected results**:
- Handler exception caught → logged to stderr
- Original error still logged to file (handler doesn't block logging)
- Proxy continues operation

**Validates**: Story 3 Task 3.1 (Handler implementation), Known Issue #004

---

#### TC-REQ5-003: Logging Overhead
**Type**: Performance test
**Objective**: Handler adds <1ms overhead to logging
**Test data**: Log 100 ERROR messages, measure with/without handler

**Expected results**:
- Without handler: baseline latency (e.g., 10ms for 100 logs)
- With handler: <11ms for 100 logs (<1ms overhead)
- Per-log overhead: <0.01ms (handler processing only, excludes database write)

**Validates**: Success Metric (performance), Story 3 Task 3.1 (Handler implementation)

---

## Story-Level Acceptance Criteria Validation

### Story 1: Core Error Fingerprinting

**Acceptance Criteria** (from `plan.md`):
- ✅ Given 30 days of historical logs, fingerprinting achieves <1% collision rate → **TC-REQ1-004**
- ✅ Same logical error produces same fingerprint across multiple occurrences → **TC-REQ1-003**
- ✅ Dynamic content (UUIDs, timestamps, request IDs) is normalized before hashing → **TC-REQ1-002**
- ✅ Fingerprint includes provider, operation, error type, and normalized message → **TC-REQ1-001**

**Additional Tests**:

#### TC-STORY1-001: Edge Case Handling
**Type**: Unit test
**Objective**: Handle malformed error messages gracefully
**Test data**:
- Empty string: `""`
- No provider: `"Error: Something went wrong"`
- Missing operation: `"bedrock: ValidationException - message"`
- Unicode characters: `"Erreur: échec de l'opération"`

**Expected results**:
- Empty string → fallback signature (provider="unknown")
- No provider → fallback to "unknown"
- Missing operation → "unknown"
- Unicode → normalized correctly (UTF-8 encoding preserved)

---

### Story 2: Persistent Storage

**Acceptance Criteria** (from `plan.md`):
- ✅ Error fingerprints persist across proxy restarts → **TC-REQ3-002**
- ✅ Storage grows linearly with unique error types (not total error count) → **TC-REQ3-003**
- ✅ Auto-pruning prevents unbounded growth (90-day retention policy) → **TC-REQ3-004**
- ✅ Query capability: search by provider, time window, fingerprint → **TC-REQ2-003**

**Additional Tests**:

#### TC-STORY2-001: Concurrent Writes
**Type**: Integration test
**Objective**: Verify no lock contention or data corruption under concurrent writes
**Test data**: 10 threads, each writing 10 errors simultaneously (100 total writes)

**Expected results**:
- All 100 errors recorded correctly
- No SQLITE_BUSY errors (WAL mode handles concurrency)
- No data corruption (ACID guarantees)
- Query returns correct count for each fingerprint

**Validates**: ADR-002 (SQLite storage), Known Issue #002

---

#### TC-STORY2-002: Database Recovery After Crash
**Type**: Integration test
**Objective**: Database remains consistent after unexpected shutdown
**Test data**: Write errors, forcefully kill process (SIGKILL), restart

**Expected results**:
- Database file not corrupted
- WAL journal replays uncommitted changes
- Committed errors present, uncommitted errors may be lost (acceptable)

**Validates**: ADR-002 (SQLite WAL mode)

---

### Story 3: Logging Integration

**Acceptance Criteria** (from `plan.md`):
- ✅ All ERROR and CRITICAL level logs are captured → **TC-REQ5-001**
- ✅ Handler extracts provider/model/request_id from log record → **TC-REQ2-001**
- ✅ Handler failure does not break existing logging → **TC-REQ5-002**
- ✅ Logging overhead <1ms for tracked errors → **TC-REQ5-003**

**Additional Tests**:

#### TC-STORY3-001: Circular Logging Prevention
**Type**: Unit test
**Objective**: Handler doesn't track its own errors (prevents infinite recursion)
**Test data**: Inject error in `record_error()` that logs at ERROR level

**Expected results**:
- Handler catches exception
- Logs to stderr (not logging module)
- No infinite recursion (recursion depth counter aborts if depth > 1)

**Validates**: Known Issue #004 (circular logging)

---

#### TC-STORY3-002: Log Format Variations
**Type**: Unit test
**Objective**: Handle diverse log formats (not just ValidationException)
**Test data**:
- Rate limit: `"Rate limit exceeded (model=claude-sonnet)"`
- Timeout: `"Request timeout after 30s (provider=bedrock)"`
- Auth error: `"Authentication failed: Invalid API key"`
- Generic error: `"An error occurred"`

**Expected results**:
- Rate limit extracted: provider="unknown", error_type="RateLimitError"
- Timeout extracted: provider="bedrock", error_type="TimeoutError"
- Auth error: provider="unknown", error_type="AuthenticationError"
- Generic error: fallback signature (provider="unknown", error_type="unknown")

**Validates**: Known Issue #005 (parsing brittleness)

---

### Story 4: Alert Delivery

**Acceptance Criteria** (from `plan.md`):
- ✅ Desktop notification appears within 5 seconds of new error → **TC-REQ4-002**
- ✅ Cooldown prevents alert spam (max 1 alert per 5 minutes per fingerprint) → **TC-REQ4-003**
- ✅ Alert includes: fingerprint, error type, provider, model → **TC-REQ4-002**
- ✅ Alert failure does not block request path → **TC-REQ4-004**

**Additional Tests**:

#### TC-STORY4-001: Alert Content Validation
**Type**: Integration test
**Objective**: Verify notification format and content
**Test data**: Trigger new ValidationException

**Expected results**:
- Notification title: "New Error: bedrock"
- Notification message: "ValidationException: context_management: Extra inputs not permitted"
- Message truncated to 100 characters if longer
- osascript command: `display notification "{message}" with title "{title}"`

---

#### TC-STORY4-002: Alert Timeout Handling
**Type**: Integration test
**Objective**: osascript timeout doesn't block handler
**Test data**: Mock `subprocess.run()` to timeout (2+ seconds)

**Expected results**:
- Timeout after 2 seconds
- Warning logged: `"Alert timeout for {fingerprint}"`
- Handler continues (doesn't block)
- Error still recorded in database

**Validates**: Known Issue #003 (osascript blocking)

---

### Story 5: Query CLI

**Acceptance Criteria** (from `plan.md`):
- ✅ List all error types sorted by count or last_seen → **TC-STORY5-001**
- ✅ Filter by provider, time window → **TC-REQ2-003**
- ✅ Show detailed occurrences for a fingerprint → **TC-STORY5-002**
- ✅ Export to JSON or CSV → **TC-STORY5-003**

**Additional Tests**:

#### TC-STORY5-001: CLI List Command
**Type**: Integration test
**Objective**: Verify `error_cli.py list` functionality
**Test data**: 10 errors in database (varied counts and timestamps)

**Expected results**:
- `error_cli.py list --sort count` displays errors sorted by count (descending)
- `error_cli.py list --sort last_seen` displays errors sorted by timestamp (descending)
- `error_cli.py list --limit 5` shows only top 5 errors
- Output format: table with columns (fingerprint, provider, error_type, count, last_seen)

---

#### TC-STORY5-002: CLI Show Command
**Type**: Integration test
**Objective**: Verify `error_cli.py show <fingerprint>` functionality
**Test data**: Error with 5 occurrences

**Expected results**:
- Displays error details (fingerprint, provider, operation, error_type, message)
- Displays summary (first_seen, last_seen, count)
- Displays recent occurrences table (timestamp, request_id, model)
- Occurrences sorted by timestamp (descending)

---

#### TC-STORY5-003: CLI Export Command
**Type**: Integration test
**Objective**: Verify `error_cli.py export` functionality
**Test data**: 10 errors in database

**Expected results**:
- `error_cli.py export --format json` outputs valid JSON (validated with `json.loads()`)
- `error_cli.py export --format csv` outputs valid CSV (opens in spreadsheet)
- JSON structure: array of error objects
- CSV structure: header row + data rows

---

## Performance Test Suite

### PT-001: Fingerprinting Performance
**Objective**: Verify <100µs per fingerprint computation
**Test data**: 1000 diverse error messages

**Expected results**:
- Average time: <50µs per fingerprint
- p99 time: <100µs per fingerprint
- No outliers >500µs

---

### PT-002: Database Write Performance
**Objective**: Verify <50ms p99 write latency
**Test data**: Insert 100 errors (mix of new and duplicate)

**Expected results**:
- Average write: <20ms
- p99 write: <50ms
- p99.9 write: <100ms

---

### PT-003: Database Read Performance
**Objective**: Verify query performance scales
**Test data**: Database with 1000 unique errors, 10,000 occurrences

**Expected results**:
- `get_error_by_fingerprint()`: <10ms
- `search_errors(provider="bedrock")`: <50ms
- `search_errors(since=<timestamp>)`: <50ms (index accelerated)
- Full table scan (`get_all_error_types()`): <200ms

---

### PT-004: End-to-End Latency
**Objective**: Verify error tracking adds <2ms p99 overhead
**Test data**: Log 100 ERROR messages with handler attached

**Expected results**:
- Baseline (no handler): measure latency
- With handler: <2ms additional overhead at p99
- Breakdown: handler processing <1ms, database write <50ms (but async, so amortized)

---

## Integration Checkpoint Validation

### Checkpoint 1: After Story 1 (Fingerprinting Validated)

**Go criteria**:
- ✅ TC-REQ1-004 passes: Collision rate <1% on 30d logs
- ✅ TC-REQ1-003 passes: Same error → same fingerprint (determinism)
- ✅ PT-001 passes: <100µs per fingerprint

**No-Go criteria**:
- ❌ Collision rate >5% → Refine normalization
- ❌ Extraction fails >10% of errors → Add fallback patterns

---

### Checkpoint 2: After Story 2 (Storage Operational)

**Go criteria**:
- ✅ TC-REQ3-001 passes: Schema created correctly
- ✅ TC-REQ1-005 passes: Deduplication works (same error increments count)
- ✅ PT-002 passes: <50ms p99 write latency

**No-Go criteria**:
- ❌ Write performance <100 writes/sec → Optimize (async writes)
- ❌ Retention policy fails → Fix before proceeding

---

### Checkpoint 3: After Story 3 (Live Error Capture)

**Go criteria**:
- ✅ TC-REQ5-001 passes: 100% of ERROR logs captured
- ✅ TC-REQ2-001 passes: Provider/model/request_id extracted correctly
- ✅ TC-REQ5-002 passes: Handler exceptions isolated

**No-Go criteria**:
- ❌ Capture rate <100% → Fix handler before Story 4
- ❌ Handler causes proxy errors → Revise exception handling

---

### Checkpoint 4: After Story 4 (End-to-End Alert Flow)

**Go criteria**:
- ✅ TC-REQ4-002 passes: Alert within 5 seconds
- ✅ TC-REQ4-003 passes: Cooldown prevents duplicates
- ✅ TC-REQ4-004 passes: Alert failure non-blocking

**No-Go criteria**:
- ❌ Alert latency >10 seconds → Move to async delivery
- ❌ Alert failures block proxy → Add more robust error handling

---

### Final Checkpoint: Complete System Integration

**Go criteria**:
- ✅ All test cases pass (unit, integration, E2E, performance)
- ✅ 48-hour production burn-in: no false-positive alerts on restart
- ✅ Storage growth <10MB after 48 hours
- ✅ p99 request latency unchanged (error tracking doesn't impact proxy performance)

**Success metrics validation**:
- ✅ Alert within 5 seconds: Measured via TC-REQ4-002
- ✅ <1% collision rate: Measured via TC-REQ1-004
- ✅ 100% capture: Measured via TC-REQ5-001
- ✅ <2ms p99 overhead: Measured via PT-004
- ✅ <100MB storage: Measured via TC-REQ3-005

---

## Test Execution Plan

### Phase 1: Unit Tests (During Implementation)
Execute immediately after implementing each component:
- Story 1 Tasks 1.1-1.2: TC-REQ1-001, TC-REQ1-002, TC-REQ1-003
- Story 2 Tasks 2.1-2.2: TC-REQ3-001, TC-REQ1-005, TC-REQ2-002
- Story 3 Task 3.1: TC-REQ2-001, TC-REQ5-002, TC-STORY3-001
- Story 4 Task 4.1: TC-STORY4-001

**Target coverage**: >80% line coverage

---

### Phase 2: Integration Tests (After Story Completion)
Execute after each story is complete:
- Story 1 complete: TC-REQ1-004 (historical log validation)
- Story 2 complete: TC-REQ2-003, TC-REQ3-002, TC-REQ3-003, TC-STORY2-001
- Story 3 complete: TC-REQ5-001, TC-STORY3-002
- Story 4 complete: TC-REQ4-001, TC-REQ4-002, TC-REQ4-003, TC-REQ4-004

---

### Phase 3: E2E Tests (After All Stories Complete)
Execute after Stories 1-4 complete:
- Story 3 Task 3.3: Full proxy integration test
- TC-REQ3-002: Restart persistence test
- TC-STORY2-002: Crash recovery test

---

### Phase 4: Performance Tests (After All Stories Complete)
Execute after all functional tests pass:
- PT-001: Fingerprinting performance
- PT-002: Database write performance
- PT-003: Database read performance
- PT-004: End-to-end latency

---

### Phase 5: Production Burn-In (48 Hours)
Execute in production environment:
- Run proxy with error tracking enabled for 48 hours
- Monitor metrics:
  - Alert accuracy (true positives vs false positives)
  - Storage growth rate (bytes per hour)
  - Performance impact (p99 latency delta)
  - Fingerprint collision rate (manual review of 10 sample groups)

---

## Test Tooling

### Unit & Integration Tests
- **Framework**: pytest
- **Coverage**: pytest-cov
- **Command**: `pytest stapler-scripts/claude-proxy/ -v --cov=error_tracker --cov-report=html`
- **Target**: >80% line coverage

### E2E Tests
- **Framework**: bash scripts + curl
- **Location**: `stapler-scripts/claude-proxy/scripts/test_error_tracking.sh`
- **Verification**: Database queries + log inspection

### Performance Tests
- **Framework**: pytest + timeit
- **Tools**: `time` command for profiling
- **Load generation**: Custom script (inject N errors, measure latency)

---

## Success Criteria Summary

**Phase 4 (Validation) is complete when**:
- ✅ All requirements mapped to test cases (traceability matrix complete)
- ✅ Test coverage targets defined (>80% unit, 100% integration/E2E)
- ✅ Integration checkpoints defined with go/no-go criteria
- ✅ Test execution plan created
- ✅ This document committed to version control

**Phase 5 (Implementation) can begin when**:
- ✅ Phase 4 complete
- ✅ FRESH SESSION opened (planning context must not contaminate implementation)
- ✅ Implementation reads `plan.md` + `validation.md` as input

**Feature is complete when**:
- ✅ All test cases pass
- ✅ All success metrics validated
- ✅ All integration checkpoints pass
- ✅ 48-hour burn-in successful
- ✅ `/quality:does-it-work` and `/code:review` pass

---

## Next Steps

**Immediate**: Commit this validation plan
```bash
git add project_plans/claude-proxy-error-tracking/implementation/validation.md
git commit -m "docs: Add validation plan for claude-proxy-error-tracking (Phase 4)"
```

**After commit**: Phase 5 — Implementation
- ⚠️ **CRITICAL**: Open FRESH SESSION (planning context must not contaminate code generation)
- Run `/code:implement` with `plan.md` + `validation.md` as input
- Implement tasks in dependency order: Story 1 → 2 → 3 → 4, Story 5 parallel after Story 2
- Execute tests as defined in Test Execution Plan
- Validate against integration checkpoints

**After implementation**: Phase 6 — QA
- Run `/quality:does-it-work` to verify implementation
- Run `/code:review` before claiming completion
- Execute 48-hour production burn-in
- Validate all success metrics achieved
