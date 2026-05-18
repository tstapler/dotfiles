# Pitfalls Research: Error Tracking Common Failure Modes

**Project**: claude-proxy-error-tracking
**Research Dimension**: Pitfalls — Known Failure Modes
**Date**: 2026-04-16

## Research Questions

1. What causes alert fatigue in error tracking systems?
2. When do error fingerprints become unstable?
3. What drives storage bloat in production error tracking?
4. How does error logging impact latency in async Python systems?

---

## Options Surveyed

### Alert Fatigue Sources

**High-cardinality errors**: Errors with dynamic IDs, timestamps, or UUIDs in messages create unique fingerprints for logically identical issues. Each instance triggers a "new error" alert.

**Transient infrastructure failures**: Network timeouts, DNS resolution failures, and connection resets generate alert storms during outages. A 30-second AWS outage can produce hundreds of "new" timeout variants.

**Deployment churn**: Code deploys change stack traces, module paths, or function names. Fingerprints tied to exact line numbers break on every release.

**Threshold misconfiguration**: Alerting on first occurrence vs N occurrences in time window. First-occurrence alerts catch noise; threshold-based alerts delay detection of novel critical errors.

### Fingerprinting Instability Patterns

**Dynamic message content**: Error messages embedding request IDs, user IDs, timestamps, or IP addresses.
```python
# Unstable: every value creates new fingerprint
f"Failed to process request {request_id} at {timestamp}"

# Stable: pattern-based grouping
"Failed to process request: validation error"
```

**Stack trace variance**: Async frameworks (asyncio, trio) produce non-deterministic stack traces due to event loop scheduling. Same logical error appears at different call depths.

**Dependency version drift**: Library updates change internal error messages or exception hierarchies. `requests.ConnectionError` in v2.28 vs v2.31 may format differently.

**Provider-specific message formats**: Bedrock vs OpenAI vs Anthropic APIs return structurally different error bodies for the same logical failure (rate limit, auth failure).

### Storage Bloat Drivers

**Full request/response capture**: Storing complete HTTP bodies for every error instance. A single endpoint returning 5xx with 100KB responses can fill disks at 1 error/second = 8.6GB/day.

**Unbounded error instances per fingerprint**: Tracking every occurrence instead of count + sample. High-frequency errors (rate limits during load tests) generate millions of redundant rows.

**No retention policy**: Errors accumulate indefinitely. Six months of 100 errors/day = 18,000 records. With full metadata, easily 50-100MB+ for small-scale systems.

**Attachment proliferation**: Screenshots, request logs, environment dumps attached to errors. Critical for debugging but scales poorly without cleanup.

### Latency Impact Vectors

**Synchronous database writes**: Writing error metadata to SQLite on the critical path blocks request handling. 5-10ms write latency per error = 10% overhead on 50ms requests.

**Serialization overhead**: JSON encoding large error contexts (request bodies, headers, traceback) adds CPU time. 1ms serialization on every error path.

**Fingerprint computation**: Hashing stack traces or applying regex normalization on every exception. MD5 hash is ~1µs but regex-based cleanup can be 100µs-1ms.

**Alert delivery blocking**: Sending desktop notifications, webhooks, or emails synchronously in exception handlers. DNS lookup + HTTP POST = 50-200ms per alert.

**Lock contention**: Shared in-memory error registry protected by threading locks. High error rates under load cause lock contention, serializing error handling across workers.

---

## Trade-off Matrix

| Dimension | Conservative Approach | Aggressive Approach | Recommended for claude-proxy |
|-----------|----------------------|---------------------|------------------------------|
| **Alert Precision vs Recall** | Alert only on 3+ occurrences in 5 min (high precision, may miss novel errors) | Alert on first occurrence (high recall, alert spam risk) | **First occurrence with 5-minute cooldown** — novel errors are critical for solo user; cooldown prevents storms |
| **Storage Growth** | Store fingerprint + count + last_seen only (minimal disk, lose instance details) | Store all instances with full context (debugging rich, bloat risk) | **Fingerprint + count + last 5 instances** — balance debuggability with bounded growth |
| **Performance Overhead** | Async fire-and-forget logging (low latency, may lose errors on crash) | Synchronous writes with fsync (durable, adds 5-10ms/error) | **Async with queue** — proxy is latency-sensitive; queue prevents backpressure |
| **Fingerprint Stability** | Hash only exception type + top 3 stack frames (stable, high collision risk) | Hash full stack + message + context (unique, deployment fragile) | **Type + normalized message + top 5 frames** — stable across deploys, low collision |

---

## Risk and Failure Modes

### Critical Risks

**Alert fatigue from deployment churn**: Every code change shifts line numbers in stack traces. Fingerprints break, causing re-alerting on known errors after deploys.

*Mitigation*: Use relative stack frame references (function names) instead of absolute line numbers. Normalize file paths to remove package version suffixes.

**Storage bloat from high-frequency transient errors**: Rate limit errors during load spikes can generate 100+ errors/second. Without bounded instance storage, fills disk.

*Mitigation*: Cap stored instances per fingerprint (last N occurrences). Prune errors older than 30 days automatically.

**Missed critical errors due to fingerprint collisions**: Overly aggressive normalization groups distinct errors together. Example: "API Error: 400" matches validation failures, auth failures, and malformed requests.

*Mitigation*: Include provider + model + error code in fingerprint. Test fingerprint uniqueness on historical logs.

**Proxy latency spike during error storms**: Synchronous error tracking blocks request threads. Under load with errors, latency cascades.

*Mitigation*: Async error submission to background thread with bounded queue (drop on overflow rather than block).

**False positives from retries**: Retry logic causes same error to appear multiple times in short window, triggering "new error" alerts repeatedly.

*Mitigation*: Deduplicate by fingerprint + 5-minute window before alerting. Count occurrences within window.

### Operational Concerns

**Alert delivery failure**: Desktop notifications or file-based alerts may not reach user if system is off or script isn't monitored.

*Secondary path*: Write to dedicated alert log file + stdout. Check alert log on proxy startup.

**Schema evolution**: Adding metadata fields (e.g., user_agent, request_id) requires database migration. SQLite ALTER TABLE is limited.

*Design*: Use JSONB column for extensible metadata to avoid frequent schema changes.

**Fingerprint drift over time**: Message format changes from providers (e.g., AWS SDK update) silently break fingerprints. Errors appear "new" despite being old types.

*Monitoring*: Track fingerprint creation rate. Sudden spike = potential drift issue. Manual audit quarterly.

**Alert blindness**: After initial setup, user may stop checking alerts if 80%+ are false positives.

*Prevention*: Test fingerprinting on 30-day historical logs before deployment. Target <5% false positive rate.

---

## Prior Art

### Sentry Fingerprinting Rules
Sentry allows custom fingerprinting via rules DSL. Mature pattern:
```python
# Group by error type + message pattern, ignore dynamic IDs
fingerprint = [
    exception.type,
    re.sub(r'\b[0-9a-f-]{36}\b', '<UUID>', exception.message),
    stack[:5]  # Top 5 frames only
]
```
**Lesson**: Regex normalization is standard but must be tuned per error source.

### Nginx Error Levels
Nginx classifies errors into levels (debug, info, warn, error, crit). Only `error` and `crit` trigger alerts by default. Warns are logged but silent.

**Lesson**: Not all errors need alerts. Distinguish "expected errors" (rate limits) from "unexpected errors" (validation exceptions from code bugs).

### Envoy Rate-Limited Error Logging
Envoy applies per-error-type rate limiting: max N logs per minute for each fingerprint. Prevents log storms from high-frequency errors.

**Lesson**: Rate-limit error *logging* in addition to alerting. Protects disk I/O during incidents.

### Python logging.handlers.MemoryHandler
Standard library provides buffered handler that flushes on capacity or error level threshold. Async-friendly pattern for error tracking.

**Lesson**: Use stdlib buffering rather than custom queues. Well-tested, GIL-aware.

---

## Open Questions

1. **How stable are Bedrock error message formats across SDK versions?**
   *Action*: Test fingerprinting on current Bedrock error logs (from recent proxy failures). Check AWS SDK changelog for ValidationException format changes.

2. **What is acceptable error tracking latency overhead for the proxy?**
   *Action*: Benchmark current p95 latency. Define budget (e.g., "error tracking must add <2ms p99").

3. **Should error tracking be opt-in per request or always-on?**
   *Action*: If always-on, need strict latency control. If opt-in, may miss errors during early testing.

4. **What alert delivery method will Tyler actually check?**
   *Action*: Test desktop notifications on macOS (osascript). If unreliable, consider stdout + dedicated terminal window or tmux status line.

5. **How to handle fingerprint collisions post-deployment?**
   *Action*: Design fingerprint inspector tool to show grouped errors for manual review. Allow manual splitting.

---

## Recommendation

**Adopt a tiered error tracking approach with aggressive deduplication and async-first architecture:**

### Core Principles

1. **Fingerprint stability first**: Normalize dynamic content (UUIDs, timestamps, IDs) before hashing. Use exception type + top 5 stack frames + normalized message. Test on 30-day historical logs before deployment.

2. **Bounded storage**: Store last 5 instances per fingerprint + aggregate count. Prune errors older than 30 days. Separate storage for high-priority errors (mark "critical" fingerprints to keep all instances).

3. **Async error submission**: Use `asyncio.Queue` to submit errors to background task. Never block request path. Drop errors if queue full (degrade gracefully under load).

4. **Alert with cooldown**: Alert on first occurrence of new fingerprint. Then suppress alerts for same fingerprint for 5 minutes. Prevents alert storms during outages while catching novel errors fast.

5. **Separate expected from unexpected errors**: Tag rate-limit errors, auth failures, and client-side validation errors as "expected." Don't alert on first occurrence, only on unexpected errors.

### Implementation Priorities

1. **Fingerprinting function**: Build and test on existing logs first. Validate collision rate <1%.
2. **Storage schema**: SQLite with JSONB metadata column for extensibility.
3. **Async worker**: Background task consuming from queue, writing to DB.
4. **Alert delivery**: macOS desktop notification + stdout + dedicated alert log file.
5. **Admin CLI**: Tool to inspect fingerprints, view grouped errors, manually split collisions.

### Validation Tests

Before full deployment:
- Process 30 days of historical logs. Count unique fingerprints vs actual unique error types (manual review).
- Run load test with injected errors. Measure latency impact (target <2ms p99 overhead).
- Trigger 100 errors in 10 seconds. Verify single alert, not 100 alerts.
- Restart proxy with pending errors in queue. Verify no data loss (queue persistence or graceful flush on shutdown).

---

## Pending Web Searches

The following searches would strengthen this analysis if web access becomes available:

1. "error tracking alert fatigue problem" — Find case studies of teams reducing alert noise
2. "fingerprinting instability dynamic error messages" — Best practices from error tracking SaaS providers
3. "error tracking storage bloat production" — Real-world retention policies and cleanup strategies
4. "latency impact error logging Python async" — Benchmarks of async logging overhead in production systems

[TRAINING_ONLY — All recommendations based on general software engineering knowledge. Specific library versions, API behaviors, and current best practices should be verified against recent documentation and production testing.]
