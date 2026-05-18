# Research Findings: Features — Error Classification Patterns

**Subtopic**: Features dimension for claude-proxy-error-tracking
**Research Date**: 2026-04-16
**Status**: Complete (training knowledge — see Pending Web Searches section)

---

## Executive Summary

Proxy and gateway systems use three primary error classification strategies:

1. **Status-code-first** (nginx, HAProxy) — classify by HTTP status with minimal message fingerprinting
2. **Signature extraction** (Envoy, API Gateway services) — extract stable fields from structured error responses
3. **Stack-trace hashing** (Sentry-style) — hash normalized exception traces for deduplication

For claude-proxy, **signature extraction** is recommended: extract provider error codes, operation names, and error types from structured API responses, then hash these stable components to create error fingerprints. This balances granularity (distinguishes ValidationException from ThrottlingException) with stability (ignores request-specific details like timestamps).

---

## Options Surveyed

### 1. Status-Code-First (nginx, HAProxy)

**How it works**:
- Primary grouping by HTTP status code (400, 500, 503, etc.)
- Secondary grouping by upstream destination or route
- Minimal message content inspection
- Example: nginx `error_log` with log levels and upstream references

**Characteristics**:
- Very low overhead — simple counter increments
- Poor granularity — "400 Bad Request" is too broad for API proxies
- Fast implementation — no parsing required
- Limited metadata — primarily counts and rates

**When it's appropriate**:
- High-throughput edge proxies where latency is critical
- Scenarios where downstream services provide their own detailed error tracking
- Load balancing failures (connection refused, timeouts)

### 2. Signature Extraction (Envoy, AWS API Gateway)

**How it works**:
- Parse structured error responses (JSON, gRPC status details)
- Extract stable identifiers:
  - Error type/code (e.g., `ValidationException`, `error.type.validation`)
  - Service operation (e.g., `InvokeModel`, `CreateBucket`)
  - Provider-specific error codes (e.g., Bedrock error codes, AWS SDK exceptions)
- Construct signature from these fields
- Hash signature for deduplication

**Example from Envoy** [TRAINING_ONLY — verify]:
```
Error signature components:
- response_code: 400
- response_code_details: "ValidationException"
- upstream_cluster: "bedrock-us-east-1"
- route_name: "/v1/messages"
```

**Example from AWS API Gateway** [TRAINING_ONLY — verify]:
- CloudWatch Logs Insights queries group by `$context.error.message`
- X-Ray traces capture exception types and error segments
- Grouping by `errorType` in structured logs

**Characteristics**:
- Moderate overhead — JSON parsing on error path only
- High granularity — distinguishes error types within same status code
- Requires provider-specific extraction logic
- Metadata-rich — captures context without storing full request

**When it's appropriate**:
- API proxies fronting multiple backend services
- Systems with structured error responses (JSON APIs, gRPC)
- Need to distinguish provider-specific error types

### 3. Stack-Trace Hashing (Sentry, Rollbar, Bugsnag)

**How it works**:
- Capture full exception with stack trace
- Normalize trace:
  - Remove variable data (timestamps, request IDs, user IDs)
  - Extract file paths and line numbers
  - Preserve function call chain
- Hash normalized trace to create fingerprint
- Group exceptions by fingerprint
- Store first/last occurrence, count, example

**Sentry fingerprinting** [TRAINING_ONLY — verify]:
```python
# Default: hash of (exception_type, stack_trace_frames)
# Custom: user-defined grouping rules
fingerprint = ['{{ default }}', 'custom-grouping-key']
```

**Characteristics**:
- High overhead — requires exception capture and parsing
- Very high granularity — same error type at different call sites grouped separately
- Excellent for application code errors (Python tracebacks)
- Overkill for proxying third-party API errors (no internal stack to trace)

**When it's appropriate**:
- Application error monitoring (not proxy errors)
- Python/Node.js services with internal exceptions
- Need to distinguish same error type from different code paths

---

## Trade-off Matrix

| Dimension | Status-Code-First | Signature Extraction | Stack-Trace Hashing |
|-----------|-------------------|----------------------|---------------------|
| **Granularity** | Low (per-status) | High (per-error-type) | Very High (per-call-site) |
| **Overhead** | Minimal | Moderate | High |
| **Metadata richness** | Low | High | Very High |
| **Stability** | Very stable | Stable (if fields chosen well) | Fragile (line numbers change) |
| **Implementation complexity** | Low | Moderate | High |
| **Provider-specific logic** | None | Required | Minimal |
| **Grouping accuracy** | Over-groups | Balanced | Over-splits |
| **Fit for proxy errors** | Poor | Excellent | Poor |

**Scoring for claude-proxy requirements**:

| Requirement | Status-Code | Signature | Stack-Trace |
|-------------|-------------|-----------|-------------|
| Unique error type identification | ❌ Too coarse | ✅ Yes | ⚠️ Over-splits |
| Deduplication | ❌ Over-groups | ✅ Accurate | ⚠️ Fragile |
| Provider/model metadata | ⚠️ Manual | ✅ Extracted | ✅ Captured |
| New error detection | ❌ Noisy | ✅ Precise | ⚠️ Too sensitive |
| Low overhead | ✅ Minimal | ✅ Acceptable | ❌ High |

---

## Risk and Failure Modes

### Signature Extraction Risks

**1. Fingerprint instability**:
- **Risk**: Including request-specific data (IDs, timestamps) in signature causes duplicate grouping
- **Mitigation**: Explicitly define stable fields; exclude dynamic content
- **Example**:
  - ❌ Include: `"Request ID abc-123 failed"`
  - ✅ Include: `"ValidationException: context_management: Extra inputs not permitted"`

**2. Provider API changes**:
- **Risk**: Upstream error format changes break extraction logic
- **Mitigation**: Version extraction logic per provider; fallback to message-based fingerprinting
- **Example**: AWS SDK major version upgrade changes exception structure

**3. Metadata explosion**:
- **Risk**: Capturing too much context (full request/response) causes storage bloat
- **Mitigation**: Define metadata schema with fixed fields (provider, model, operation); store counts, not full payloads

**4. Over-grouping related errors**:
- **Risk**: Using only error type loses important distinctions (e.g., ValidationException on different fields)
- **Mitigation**: Include error message in signature (after normalization); use hierarchical grouping

### Status-Code Risks

**1. Insufficient signal**:
- **Risk**: All 400 errors grouped together; cannot distinguish ValidationException from AuthenticationError
- **Impact**: Cannot prioritize fixes; new error types go undetected

### Stack-Trace Risks

**1. Proxy context mismatch**:
- **Risk**: Stack traces inside proxy code are meaningless (error originated in provider service)
- **Impact**: All provider errors group by proxy exception handling location

**2. Noise from library internals**:
- **Risk**: HTTP client library frames dominate stack; errors group by library version, not error type

---

## Migration and Adoption Cost

### Implementation Effort

**Status-Code-First**: 1-2 hours
- Increment counters keyed by status code + provider
- Emit alert on new status/provider pair
- Zero parsing required

**Signature Extraction**: 4-8 hours
- Define signature schema (error_type, operation, provider, model)
- Implement provider-specific extractors (Bedrock, Anthropic, etc.)
- Hash signature components
- Store metadata + counts
- Alert on new fingerprint

**Stack-Trace Hashing**: 16+ hours
- Integrate exception capture library (Sentry SDK or custom)
- Configure fingerprinting rules
- Filter/normalize traces
- High ongoing maintenance (fingerprint tuning)

### Operational Complexity

**Status-Code**:
- Single counter storage (in-memory dict or metrics)
- No parsing failures to handle
- Limited querying capability

**Signature Extraction**:
- Structured storage (SQLite or JSON)
- Parsing failures degrade to fallback fingerprint
- Rich querying (by provider, error type, time window)

**Stack-Trace**:
- Full exception storage
- Library version dependencies
- Fingerprint tuning required per error type

---

## Operational Concerns

### Performance Impact

**Signature Extraction**:
- **Hot path**: None (only runs on error responses)
- **Error path**: JSON parsing + field extraction + hash (~0.1-1ms per error)
- **Storage I/O**: Async write to SQLite or periodic flush (non-blocking)

**Alerting**:
- **New fingerprint detection**: In-memory set lookup (O(1))
- **Notification delivery**: Async (does not block proxy response)

### Storage Growth

**Fingerprint table**:
- Row per unique error type (expected: 10-100 types)
- Columns: fingerprint_hash, error_type, provider, model, first_seen, last_seen, count, example_message
- Growth: Sub-linear (new error types rare after initial burn-in)

**Time-series data** (optional):
- Row per error occurrence (if detailed querying needed)
- Growth: Linear with error rate
- Mitigation: Retention policy (e.g., keep 30 days, aggregate to hourly counts after 7 days)

### Alert Fatigue

**Scenario**: Transient provider issues cause burst of new error types
**Mitigation strategies**:
1. **Cooldown period**: Suppress alerts for same fingerprint within N minutes
2. **Threshold gating**: Only alert if error occurs >5 times in 5 minutes (avoids one-off flakes)
3. **Provider maintenance mode**: Temporarily disable alerts for known-unstable provider

---

## Prior Art

### Nginx Error Handling

**Approach**: Status-code-first with `error_log` directives
**Granularity**: Log level (error, warn, crit) + upstream name
**Deduplication**: None (log streaming, external analysis required)
**Fit**: ❌ Too basic for API proxy error types

### Envoy Proxy

**Approach**: Signature extraction via access logs and stats
**Key patterns** [TRAINING_ONLY — verify]:
- `upstream_cluster` + `response_code` + `response_flags`
- Stats dimensions: `envoy.cluster.<name>.upstream_rq_<status>`
- Access log filters can extract gRPC status codes and messages

**Deduplication**: Via metrics aggregation (Prometheus/StatsD)
**Fit**: ✅ Excellent model for claude-proxy (similar problem space)

### AWS API Gateway

**Approach**: Structured logging with CloudWatch Logs Insights
**Key patterns**:
- `$context.error.message` — error message from backend
- `$context.error.messageString` — API Gateway error
- `$context.integrationErrorMessage` — integration failure details

**Deduplication**: Manual via CloudWatch Insights queries
**Fit**: ✅ Demonstrates value of structured error fields

### Kong API Gateway

**Approach**: Plugins for error handling (e.g., `request-termination`, `response-transformer`)
**Key patterns** [TRAINING_ONLY — verify]:
- Log aggregation plugins (Datadog, Splunk)
- Custom error response transformations
- Rate limiting on error status codes

**Deduplication**: External (via log aggregation service)
**Fit**: ⚠️ Plugin architecture overkill for single-user proxy

### Sentry (Application Monitoring)

**Approach**: Stack-trace hashing with custom fingerprinting
**Strengths**:
- Excellent for application code errors
- Rich UI for error browsing and trending
- Issue grouping with merge/split capability

**Fit**: ❌ Over-engineered for proxy errors (no internal stack to trace)
**Lesson**: Fingerprinting must match error source (application vs third-party API)

---

## Open Questions

### 1. Fuzzy Grouping vs Exact Match

**Question**: Should similar error messages be grouped together?

**Example**:
- Error A: `ValidationException: context_management: Extra inputs not permitted`
- Error B: `ValidationException: context_management: Required input missing`

**Options**:
- **Exact match**: Separate fingerprints (recommended for initial implementation)
- **Fuzzy similarity**: Group by error type prefix (requires tuning, risk of over-grouping)

**Recommendation**: Start with exact match; add fuzzy grouping only if alert volume is unmanageable.

### 2. Error Message Normalization Depth

**Question**: How much of the error message should be included in fingerprint?

**Options**:
1. **Error type only**: `ValidationException` (over-groups)
2. **Type + operation**: `ValidationException:InvokeModel` (balanced)
3. **Type + operation + message**: `ValidationException:InvokeModel:Extra inputs not permitted` (precise)

**Trade-off**: Precision vs stability (messages may have variable data)

**Recommendation**: Use option 3 with normalization (strip IDs, timestamps, quotes).

### 3. Historical Trend Detection

**Question**: Should the system detect increases in known error types, or only alert on novel fingerprints?

**Scope decision**: Requirements specify "new error type alerting" — trending is out of scope for MVP.

**Future consideration**: Add rate-change detection in Phase 2 (requires time-series storage).

---

## Recommendation

### Primary Approach: Signature Extraction

Implement error fingerprinting based on Envoy/API Gateway patterns:

**Signature components**:
1. **Error type**: Extracted from structured response (e.g., `ValidationException`, `ThrottlingException`)
2. **Operation**: API operation being called (e.g., `InvokeModel`, `Converse`)
3. **Provider**: Upstream provider name (e.g., `bedrock`, `anthropic`)
4. **Model**: Model ID if available (e.g., `claude-opus-4-6`)
5. **Normalized message**: First line of error message with IDs/timestamps stripped

**Fingerprint construction**:
```python
signature = f"{provider}::{operation}::{error_type}::{normalized_message}"
fingerprint_hash = hashlib.sha256(signature.encode()).hexdigest()[:16]
```

**Metadata storage**:
- Fingerprint hash (primary key)
- Full signature components (for display)
- First seen timestamp
- Last seen timestamp
- Occurrence count
- Example full error (latest occurrence)

**Alerting logic**:
- Maintain in-memory set of known fingerprints (loaded from storage at startup)
- On new fingerprint: log alert, optionally send desktop notification
- Cooldown: 5 minutes per fingerprint to avoid duplicate alerts

**Integration point**:
- Intercept error responses in `providers/*.py` error handling
- Extract signature, compute fingerprint, update storage
- Non-blocking (async write or fire-and-forget)

### Why Not Status-Code-First?

Insufficient granularity. Requirements specify "unique error type identification" — status codes do not distinguish `ValidationException` from `AuthenticationError` (both return 400).

### Why Not Stack-Trace Hashing?

Mismatch with error source. Stack traces are meaningful for application code errors, not third-party API errors. Proxy stack frames (HTTP client, request handlers) are not the error origin.

### Implementation Complexity

- **Provider-specific extraction**: Requires logic per provider (Bedrock, Anthropic, etc.)
- **Mitigation**: Start with generic JSON error parser; add provider-specific overrides as needed
- **Fallback**: If extraction fails, fingerprint entire error message (graceful degradation)

### Phased Rollout

**Phase 1** (MVP):
- Extract error type + message from Bedrock responses (immediate pain point)
- Store fingerprints in SQLite
- Log alert to stdout on new fingerprint

**Phase 2** (iteration):
- Add Anthropic provider extraction
- Desktop notification via `osascript` (macOS) or `notify-send` (Linux)
- Query interface (list errors by provider, time range)

**Phase 3** (polish):
- Fingerprint normalization tuning (reduce false positives)
- Rate-change detection (alert on 10x spike in known error)
- Retention policy (archive old fingerprints)

---

## Pending Web Searches

The following searches would validate and extend training knowledge:

1. **"nginx error classification patterns logging"**
   - Verify: nginx error_log directive capabilities
   - Check: Modern nginx versions support structured logging formats (JSON)

2. **"API gateway error fingerprinting deduplication"**
   - Find: Real-world examples of signature extraction schemas
   - Check: AWS API Gateway CloudWatch Logs Insights error grouping patterns

3. **"error signature extraction from stack traces"**
   - Verify: Sentry fingerprinting algorithm details
   - Find: Open-source implementations (Python)

4. **"Envoy proxy error tracking patterns"**
   - Check: Envoy access log format variables for error details
   - Find: Example Envoy configurations for error classification

**Priority**: Search #2 (API gateway patterns) would provide most value — direct analogs to claude-proxy problem space.

---

## Appendix: Example Error Signatures

### Bedrock ValidationException

**Raw error**:
```json
{
  "detail": "Bedrock validation error: An error occurred (ValidationException) when calling the InvokeModel operation: context_management: Extra inputs are not permitted"
}
```

**Extracted signature**:
```
provider: bedrock
operation: InvokeModel
error_type: ValidationException
message: "context_management: Extra inputs are not permitted"
```

**Fingerprint**: `bedrock::InvokeModel::ValidationException::context_management: Extra inputs not permitted`

### Bedrock ThrottlingException

**Raw error**:
```json
{
  "detail": "Bedrock error: An error occurred (ThrottlingException) when calling the InvokeModel operation: Rate exceeded"
}
```

**Extracted signature**:
```
provider: bedrock
operation: InvokeModel
error_type: ThrottlingException
message: "Rate exceeded"
```

**Fingerprint**: `bedrock::InvokeModel::ThrottlingException::Rate exceeded`

### Generic API 400

**Raw error** (unstructured):
```json
{
  "error": "Invalid request parameters"
}
```

**Fallback signature**:
```
provider: anthropic
operation: unknown
error_type: http_400
message: "Invalid request parameters"
```

**Fingerprint**: `anthropic::unknown::http_400::Invalid request parameters`

---

**End of findings.**
