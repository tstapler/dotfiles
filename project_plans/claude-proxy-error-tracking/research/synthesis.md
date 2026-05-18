# Research Synthesis: Claude Proxy Error Tracking

**Created**: 2026-04-16
**Status**: Phase 2 complete — ready for Phase 3 (Planning)

---

## Decision Required

Select technology stack, architecture, and implementation approach for error tracking system with deduplication, metadata capture, persistence, and new-error alerting in claude-proxy.

---

## Context

claude-proxy currently lacks structured error tracking. Recent Bedrock API changes introduced new error types (e.g., `ValidationException: context_management: Extra inputs not permitted`) that blocked proxy usage. Manual log inspection is insufficient for correlating errors to conditions (provider, model, request patterns). Need automated system that:

- Identifies unique error types via fingerprinting
- Captures metadata (provider, model, operation)
- Persists historical error data
- Alerts when novel error types appear

**Constraints**:
- Must integrate with existing Python codebase (`stapler-scripts/claude-proxy/*.py`)
- Solo practitioner — operational simplicity critical
- Urgency — proxy currently blocked
- Lightweight dependencies preferred

**Success metric**: Alert on new error type within seconds of occurrence, enabling rapid diagnosis and preventing extended downtime.

---

## Options Considered

### Technology Stack

| Option | Dependency Weight | Fingerprinting Accuracy | Implementation Time | Extensibility |
|--------|-------------------|-------------------------|---------------------|---------------|
| **Stdlib-only** | 0 external deps | Medium (requires tuning) | Hours | Low (custom format) |
| **Sentry SDK** | ~5MB SDK | High (production-proven) | Days (learning curve) | High (SaaS compatible) |
| **Hybrid** (stdlib + notifications) | ~50-200KB (if using desktop lib) | Medium (manual algorithm) | Hours + testing | Medium |

### Error Classification Approaches

| Pattern | Granularity | Overhead | Fit for Proxy Errors |
|---------|-------------|----------|---------------------|
| **Status-code-first** (nginx) | Low (per-status) | Minimal | ❌ Too coarse (can't distinguish ValidationException from AuthError) |
| **Signature extraction** (Envoy, API Gateway) | High (per-error-type) | Moderate (JSON parsing on error path) | ✅ Optimal for structured API errors |
| **Stack-trace hashing** (Sentry) | Very high (per-call-site) | High | ❌ Mismatched (proxy errors from third-party, not internal stack) |

### Storage Backends

| Backend | Write Latency | Query Capability | Storage Growth | Operational Complexity |
|---------|--------------|------------------|----------------|------------------------|
| **SQLite** | 10-50ms | Full SQL | Controlled (auto-prune) | Low (stdlib, WAL mode) |
| **JSON files** | 5-20ms | None (scan all files) | Unbounded | Low but fragile (race conditions) |
| **In-memory + flush** | 0ms | High (in-memory) | Ephemeral (data loss on crash) | Low |
| **Append-only log** | 2-10ms | Poor (linear scan) | Unbounded | Low |

### Integration Approaches

| Approach | Invasiveness | Coverage | Effort |
|----------|-------------|----------|--------|
| **Custom logging handler** | Non-invasive (config only) | High (all logged errors) | ~50 lines |
| **Decorator** | Invasive (decorate 10-15 functions) | Selective (easy to miss new code) | ~20 lines + decorating |
| **Middleware** | Moderate (wrap provider clients) | High (uniform capture) | Provider-specific |
| **Exception hook** (`sys.excepthook`) | Non-invasive | Only unhandled (proxy would crash) | Trivial |

### Alerting Mechanisms

| Mechanism | Latency | Reliability | Platform |
|-----------|---------|-------------|----------|
| **macOS Notification Center** | 50-100ms (sync) | High (if GUI logged in) | macOS only |
| **File signal + watcher** | 5ms + watcher | High (decoupled) | Cross-platform (requires external watcher) |
| **Stdout with prefix** | <1ms | Medium (easy to miss) | Universal |
| **Async queue** | <1ms | High (non-blocking) | Universal (adds threading complexity) |

---

## Dominant Trade-off

**Fingerprint stability vs precision**: Aggressive normalization (removing IDs, timestamps, model names) increases stability across message variations but risks collision (different errors grouped together). Conservative normalization preserves distinction but creates fingerprint drift on every deploy or provider SDK update.

**Secondary tension**: Performance vs durability. Synchronous SQLite writes guarantee persistence but add 10-50ms latency on error path (acceptable since errors are rare). Async writes eliminate latency but risk data loss on crash.

**Third tension**: Dependency weight vs implementation speed. Stdlib-only approach is fastest to deploy (hours) but requires fingerprint algorithm tuning. Sentry SDK provides production-proven fingerprinting but adds 5MB dependency and days of learning curve.

---

## Recommendation

**Choose**: Stdlib-only implementation with signature extraction, SQLite storage, custom logging handler, and macOS notifications.

**Because**:

1. **Urgency requirement**: Stdlib approach can be implemented in hours vs days (no external dependency setup, no API learning curve). Proxy is currently blocked — speed to resolution is critical.

2. **Error source match**: Signature extraction (Envoy/API Gateway pattern) is the correct model for proxy errors. Stack-trace hashing is mismatched (no internal stack to trace), and status-code-first lacks granularity (can't distinguish `ValidationException` from `AuthenticationError` within same 400 status).

3. **Solo practitioner context**: SQLite provides full query capability (essential for diagnostics) without external service setup. Custom logging handler is non-invasive (no code changes to error handlers) and automatic (captures all logged errors).

4. **Upgrade path**: Stdlib fingerprinting validates the approach quickly. If collision rate >5% or grouping proves inadequate, migration to Sentry SDK is straightforward (same integration point — logging handler, compatible storage schema).

**Accept these costs**:

- **Fingerprint tuning required**: Manual regex-based normalization needs testing on historical logs to balance stability and collision rate. Will require iteration.
- **Platform lock-in for alerts**: macOS notifications work only on GUI session. Acceptable for solo user; would need rework for team or server deployment.
- **Operational burden**: Custom code means no vendor support. Monitoring fingerprint stability and storage growth is manual responsibility.

**Reject these alternatives**:

- **Sentry SDK now**: Implementation time (days) conflicts with urgent timeline. Dependency overhead (~5MB) unnecessary for MVP validation. Adopt only if fingerprint collision rate exceeds 5% after 1 month of production use.
- **Status-code-first**: Insufficient granularity. Requirements explicitly state "unique error type identification" — status codes do not distinguish error types within same code (all 400s grouped together).
- **Stack-trace hashing**: Architectural mismatch. Proxy errors originate from third-party APIs (Bedrock, Anthropic), not internal application code. Stack frames would capture HTTP client internals, not error semantics.
- **JSON file storage**: No atomic updates (race condition risk), no indexes (slow queries), no query capability (must scan all files for "show me all Bedrock errors this week").
- **In-memory storage**: Data loss on crash violates "persistence layer" requirement. Historical data essential for trend analysis and reducing false-positive "new error" alerts after restarts.

---

## Implementation Plan Summary

**Phase 1 (MVP — target: 1 day)**:
1. **Fingerprinting**: Hash on `(provider, operation, error_type, normalized_message)` with regex normalization (remove UUIDs, timestamps, IDs)
2. **Storage**: SQLite two-tier schema (error_types for deduplication, error_occurrences for metadata) with 90-day retention policy
3. **Integration**: Custom `logging.Handler` subclass that intercepts ERROR+ logs, extracts provider/model from `LogRecord.extra`
4. **Alerting**: Synchronous macOS notification via `osascript` on new fingerprint (5-minute cooldown to prevent alert storms)

**Phase 2 (operational maturity — target: +2 days)**:
1. **Query CLI**: Search errors by provider, time window, error type
2. **Retention policy**: Auto-prune error_occurrences >30 days on startup
3. **Alert rate limiting**: Max 1 alert per 5 minutes per fingerprint
4. **Admin tool**: Fingerprint inspector to manually review grouped errors and detect collisions

**Phase 3 (optimization — if needed)**:
1. **Async alert queue**: Move 50-100ms notification delivery off request path (only if latency becomes observable issue)
2. **Fingerprint normalization tuning**: Reduce collision rate based on production data
3. **Rate-change detection**: Alert on 10x spike in known error type frequency (trending)

---

## Open Questions Before Committing

The following questions require code inspection or prototyping before Phase 3 (Planning):

1. **[ ] Does claude-proxy use `structlog`, stdlib `logging`, or custom logger?**
   - Blocks: Integration approach (handler attachment point)
   - Required action: Read `stapler-scripts/claude-proxy/main.py` and `metrics.py`

2. **[ ] Are errors currently logged with provider/model context?**
   - Blocks: Whether handler can extract metadata from logs or if error handling code needs modification
   - Required action: Grep for `logger.error` patterns in `providers/bedrock.py`

3. **[ ] What is current error handling pattern in route handlers?**
   - Blocks: Whether to use middleware, decorator, or handler-only approach
   - Required action: Read error handling code in `main.py` (likely FastAPI exception handlers)

4. **[ ] What is acceptable error tracking latency overhead?**
   - Blocks: Decision on sync vs async writes
   - Required action: Benchmark current p95 request latency, define budget (e.g., "error tracking must add <2ms p99")

5. **[ ] Fingerprinting stability on actual error logs?**
   - Blocks: Regex normalization patterns (must test on real errors)
   - Required action: Extract 30 days of error logs, run fingerprint prototype, measure collision rate (target <1%)

**Spike work before planning**:
- Prototype fingerprinting algorithm on sample Bedrock errors from recent proxy failures
- Validate regex normalization patterns remove dynamic data without losing error type distinction
- Measure baseline SQLite write latency on target system (macOS filesystem)

---

## Sources

This synthesis draws from:
- `project_plans/claude-proxy-error-tracking/research/findings-stack.md`
- `project_plans/claude-proxy-error-tracking/research/findings-features.md`
- `project_plans/claude-proxy-error-tracking/research/findings-architecture.md`
- `project_plans/claude-proxy-error-tracking/research/findings-pitfalls.md`

---

## Signature Extraction Pattern (Recommended)

**Example from Bedrock ValidationException**:

Raw error:
```json
{
  "detail": "Bedrock validation error: An error occurred (ValidationException) when calling the InvokeModel operation: context_management: Extra inputs are not permitted"
}
```

Extracted signature components:
```python
provider: "bedrock"
operation: "InvokeModel"
error_type: "ValidationException"
message: "context_management: Extra inputs are not permitted"
```

Fingerprint:
```
bedrock::InvokeModel::ValidationException::context_management: Extra inputs not permitted
→ SHA256 hash → a3f7c9e1d2b5f8a0 (16-char prefix)
```

**Normalization rules** (apply before fingerprinting):
```python
# Remove operation names (dynamic)
message = re.sub(r'when calling the \w+ operation', 'when calling the <OPERATION>', message)
# Remove UUIDs
message = re.sub(r'\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b', '<UUID>', message)
# Remove model ARNs
message = re.sub(r'arn:aws:bedrock:[^:]+:[^:]+:model/[^\s]+', '<MODEL_ARN>', message)
# Remove numeric IDs
message = re.sub(r'\b\d+\b', '<NUM>', message)
```

---

**Next step**: Proceed to Phase 3 (Planning) with `/plan:feature`. Planning phase will:
- Inspect claude-proxy codebase to answer Open Questions 1-3
- Design detailed implementation plan based on this synthesis
- Create ADRs for key architectural decisions (fingerprinting algorithm, storage schema, alert delivery)
