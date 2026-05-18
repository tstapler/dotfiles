# ADR-001: Fingerprinting Algorithm

**Status**: Accepted
**Date**: 2026-04-16
**Context**: Phase 3 — Planning

---

## Context

Need to group similar errors together while distinguishing distinct error types. Three approaches considered:

1. **Status-code-first** (nginx, HAProxy) — classify by HTTP status with minimal message fingerprinting
2. **Signature extraction** (Envoy, API Gateway) — extract stable fields from structured error responses
3. **Stack-trace hashing** (Sentry-style) — hash normalized exception traces for deduplication

### Requirements Driving This Decision
- Must identify unique error types (not just status codes)
- Must correlate errors to conditions (provider, model, operation)
- Must handle third-party API errors (not internal application code)
- Must produce stable fingerprints across message variations (dynamic IDs, timestamps)

### Research Findings
From `research/findings-features.md`:
- Status-code-first provides insufficient granularity for API proxy errors
- Signature extraction is the standard pattern for API gateways (Envoy, AWS API Gateway)
- Stack-trace hashing is mismatched for proxy errors (no internal stack to trace)

---

## Decision

**Use signature extraction** with the following components:
- **Provider**: Upstream service name (e.g., "bedrock", "anthropic")
- **Operation**: API operation being called (e.g., "InvokeModel", "Converse")
- **Error type**: Exception type or error code (e.g., "ValidationException", "ThrottlingException")
- **Normalized message**: First line of error message with dynamic content removed

**Fingerprint construction**:
```python
signature = f"{provider}::{operation}::{error_type}::{normalized_message}"
fingerprint = hashlib.sha256(signature.encode()).hexdigest()[:16]
```

**Normalization rules** (apply before hashing):
```python
# Remove UUIDs
message = re.sub(r'\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b', '<UUID>', message)

# Remove model ARNs
message = re.sub(r'arn:aws:bedrock:[^:]+:[^:]+:model/[^\s]+', '<MODEL_ARN>', message)

# Remove operation names (dynamic)
message = re.sub(r'when calling the \w+ operation', 'when calling the <OPERATION>', message)

# Remove numeric IDs (conservative - only obvious IDs, not semantic numbers)
message = re.sub(r'\b[0-9]{10,}\b', '<ID>', message)  # 10+ digits likely IDs, not semantic
```

---

## Rationale

### Why Signature Extraction?

1. **Correct granularity for requirements**:
   - Status codes are too coarse: Can't distinguish `ValidationException` from `AuthenticationError` (both return 400)
   - Stack traces are too fine-grained: Same logical error at different call sites creates different fingerprints
   - Signature extraction balances precision (different errors distinguished) with stability (same error across deployments)

2. **Architectural match**:
   - Proxy errors originate from third-party APIs (Bedrock, Anthropic), not internal application code
   - Structured API responses provide extractable fields (error type, operation, message)
   - Envoy/API Gateway pattern is proven for this exact use case

3. **Stability across variations**:
   - Regex normalization removes dynamic content (UUIDs, timestamps, IDs) while preserving error semantics
   - Provider + operation + error_type anchors fingerprint to stable components
   - Message normalization handles AWS SDK quirks (operation names in error messages)

4. **Meets success metrics**:
   - Target: <1% collision rate (different errors grouped together)
   - Validation plan: Test on 30 days of historical logs (Task 1.3)
   - Conservative normalization reduces collision risk

### Example Fingerprints

**Bedrock ValidationException**:
```
Raw: "Bedrock validation error: An error occurred (ValidationException) when calling the InvokeModel operation: context_management: Extra inputs are not permitted"

Extracted:
  provider: "bedrock"
  operation: "InvokeModel"
  error_type: "ValidationException"
  message: "context_management: Extra inputs are not permitted"

Normalized message: "context_management: Extra inputs are not permitted"
(no dynamic content in this message, so unchanged)

Fingerprint: bedrock::InvokeModel::ValidationException::context_management: Extra inputs are not permitted
→ SHA256 → a3f7c9e1d2b5f8a0
```

**Bedrock ThrottlingException**:
```
Raw: "Bedrock error: An error occurred (ThrottlingException) when calling the InvokeModel operation: Rate exceeded"

Extracted:
  provider: "bedrock"
  operation: "InvokeModel"
  error_type: "ThrottlingException"
  message: "Rate exceeded"

Fingerprint: bedrock::InvokeModel::ThrottlingException::Rate exceeded
→ SHA256 → 7f2a9c8e4d1b6f3a
```

---

## Consequences

### Positive
- **High accuracy**: Distinguishes error types within same status code (ValidationException vs AuthError, both 400)
- **Proven pattern**: Envoy and AWS API Gateway use signature extraction successfully in production
- **Stable across deployments**: Code changes don't affect fingerprints (no line numbers in hash)
- **Extensible**: Easy to add new providers (Anthropic, OpenAI) with provider-specific extraction logic

### Negative
- **Manual normalization required**: Regex patterns must be tuned per provider
- **Risk of over-normalization**: Removing too much data can cause collisions (Known Issue #001)
- **Provider-specific logic**: Each provider may have different error formats requiring custom extraction

### Mitigation Strategies

1. **Collision detection** (Task 1.3):
   - Test fingerprinting on 30 days of historical logs
   - Calculate collision rate (same fingerprint, different error types)
   - Target: <1% collision rate
   - If collision rate >5%, refine normalization before proceeding to storage implementation

2. **Conservative normalization**:
   - Start with minimal normalization (only obvious dynamic data: UUIDs, long numeric IDs, ARNs)
   - Do NOT normalize all numbers (semantic values like "4096 tokens" are meaningful)
   - Document edge cases discovered during validation (Task 1.3)

3. **Fingerprint inspector tool** (Story 5):
   - CLI command to show all errors grouped by fingerprint
   - Manual review capability to detect collisions
   - Allow manual override for specific patterns if needed

4. **Fallback patterns**:
   - If extraction fails (unexpected error format), use generic signature: `{"provider": "unknown", "error_type": "unknown", "message": <full_message>}`
   - Log extraction failures at DEBUG level for investigation
   - Monitor extraction success rate (alert if <90%)

---

## Alternatives Considered

### Alternative 1: Status-Code-First (nginx pattern)
**Approach**: Primary grouping by HTTP status code (400, 500, 503), secondary grouping by upstream service.

**Why rejected**:
- Insufficient granularity for requirements ("unique error type identification")
- Can't distinguish ValidationException from AuthenticationError (both 400)
- Can't distinguish ThrottlingException from ServiceUnavailable (both 429/503)
- Doesn't capture operation context (InvokeModel vs Converse)

**When this would be correct**:
- High-throughput edge proxies where latency is critical
- Scenarios where downstream services provide their own error tracking
- Load balancing failures (connection refused, timeouts) where status code is sufficient

---

### Alternative 2: Stack-Trace Hashing (Sentry pattern)
**Approach**: Capture full exception with stack trace, normalize trace (remove variable data), hash normalized trace to create fingerprint.

**Why rejected**:
- Architectural mismatch: Proxy errors originate from third-party APIs (Bedrock, Anthropic), not internal application code
- Stack frames would capture HTTP client internals (boto3, aiohttp), not error semantics
- Same logical error (ValidationException) would group by where it's caught in proxy code, not by error type
- Higher overhead (exception capture + trace parsing) for no added value

**Example mismatch**:
```python
# Two Bedrock ValidationExceptions caught at different locations:
# 1. In providers/bedrock.py line 142
# 2. In fallback.py line 289

# Stack-trace hashing would create TWO fingerprints (different call sites)
# Signature extraction creates ONE fingerprint (same error type + message)
```

**When this would be correct**:
- Application error monitoring (Python/Node.js services with internal exceptions)
- Need to distinguish same error type from different code paths
- Errors originate from internal application logic

---

### Alternative 3: Fuzzy Similarity (Levenshtein distance)
**Approach**: Group errors with similar messages using string distance metrics (Levenshtein, cosine similarity).

**Why rejected**:
- High computational cost (O(n²) comparisons for n errors)
- Requires tuning similarity threshold (subjective, hard to validate)
- Risk of over-grouping: "Rate limit exceeded" vs "Rate exceeded" might group together despite being from different providers
- Less predictable than exact signature matching

**When this would be correct**:
- Natural language error messages with high variability
- Need to detect "similar but not identical" errors (e.g., typo variations)
- Low volume (<100 unique errors) where O(n²) is acceptable

---

## Validation Plan

From Task 1.3 (Test fingerprinting on historical logs):

1. **Extract errors from logs**:
   - Parse `/tmp/claude-proxy.app.log` for last 30 days
   - Extract all ERROR-level messages
   - Target sample size: 100+ unique errors, 1000+ total occurrences

2. **Compute fingerprints**:
   - Run signature extraction + normalization on all errors
   - Generate fingerprint for each error

3. **Calculate metrics**:
   - **Collision rate**: % of fingerprints grouping different error types
   - **Stability rate**: % of same logical errors producing same fingerprint
   - **Extraction success rate**: % of errors where signature extraction succeeded

4. **Manual review**:
   - Sample 10 fingerprint groups
   - Inspect all errors in each group
   - Verify: all errors in group are same logical type
   - Document edge cases requiring special handling

5. **Success criteria**:
   - Collision rate <1% (stretch: <0.5%)
   - Stability rate >99%
   - Extraction success rate >90%

6. **Go/No-Go decision**:
   - If collision rate >5%: Refine normalization, re-test before Story 2
   - If extraction success <80%: Add more fallback patterns, re-test
   - If edge cases discovered: Document + add special handling

---

## References

- **Research findings**: `project_plans/claude-proxy-error-tracking/research/findings-features.md`
- **Envoy error tracking patterns**: https://www.envoyproxy.io/docs/envoy/latest/configuration/observability/access_log/usage
- **AWS API Gateway error handling**: CloudWatch Logs Insights `$context.error.message` field
- **Sentry fingerprinting algorithm**: https://docs.sentry.io/product/data-management-settings/event-grouping/

---

## Implementation Impact

**Files affected**:
- `stapler-scripts/claude-proxy/error_tracker.py` (NEW) — Core fingerprinting logic
  - `extract_signature(error_message, provider, context)` function
  - `normalize_message(message)` function
  - `compute_fingerprint(signature)` function

**Tasks implementing this decision**:
- Task 1.1: Implement signature extraction
- Task 1.2: Implement normalization and fingerprinting
- Task 1.3: Test fingerprinting on historical logs (validation)

**Known issues related to this decision**:
- Bug 001: Regex normalization may over-normalize (if too aggressive, causes collisions)
- Bug 005: Provider extraction fails on unexpected log format (extraction robustness)
