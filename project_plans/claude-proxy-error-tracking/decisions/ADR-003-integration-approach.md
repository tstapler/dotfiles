# ADR-003: Integration Approach

**Status**: Accepted
**Date**: 2026-04-16
**Context**: Phase 3 — Planning

---

## Context

Need to capture errors from the proxy without modifying existing error handling code. The proxy uses Python stdlib `logging` with `RotatingFileHandler`. Errors are logged with structured context: `[{request_id}] ✗ {provider}: {error_type} (model={model}) - {message}`.

### Requirements Driving This Decision
- Non-invasive: Zero changes to existing error handling code
- Automatic coverage: Capture all ERROR and CRITICAL level logs
- Reliability: Handler failures must not break existing logging
- Metadata extraction: Provider, model, request_id, timestamp

### Research Findings
From `research/findings-architecture.md`:
- Four options considered: custom logging handler, decorator, middleware, exception hook
- Logging handler is standard Python pattern for interception
- Handler exceptions can be isolated (wrapped in try/except)
- `LogRecord` provides metadata automatically (module, function, line number, timestamp)

---

## Decision

**Use custom logging handler** subclassing `logging.Handler`, filtering ERROR+ level, attached to root logger.

### Implementation Approach

```python
class ErrorTrackingHandler(logging.Handler):
    """Logging handler that tracks and deduplicates errors."""

    def __init__(self, tracker: ErrorTracker):
        super().__init__(level=logging.ERROR)
        self.tracker = tracker

    def emit(self, record: logging.LogRecord):
        """Process error log records.

        CRITICAL: Wrap in try/except to prevent breaking logging chain.
        """
        try:
            # Extract provider/model from record message
            provider, operation, error_type = self._parse_error_message(record.getMessage())

            # Extract request_id from message format: "[request_id] message"
            request_id = self._extract_request_id(record.getMessage())

            # Build signature
            signature = {
                "provider": provider,
                "operation": operation,
                "error_type": error_type,
                "message": record.getMessage()
            }

            # Record error and check if new
            fingerprint, is_new = self.tracker.record_error(signature, {
                "request_id": request_id,
                "logger": record.name,
                "filename": record.filename,
                "lineno": record.lineno,
                "timestamp": record.created
            })

            if is_new:
                self._alert_new_error(fingerprint, signature)

        except Exception as e:
            # CRITICAL: Handler exceptions must not break logging chain
            # Log to stderr to avoid circular logging
            import sys
            print(f"ERROR in ErrorTrackingHandler: {e}", file=sys.stderr)
```

### Integration Point
In `main.py` after existing logging configuration (around line 58):
```python
from error_tracker import ErrorTracker, ErrorTrackingHandler

# Initialize error tracker
error_tracker = ErrorTracker()
error_tracking_handler = ErrorTrackingHandler(error_tracker)

# Attach to root logger (captures all ERROR+ logs from all modules)
root_logger = logging.getLogger()
root_logger.addHandler(error_tracking_handler)

logger.info("Error tracking handler attached")
```

---

## Rationale

### Why Custom Logging Handler?

1. **Non-invasive**:
   - Zero changes to existing error handling code
   - Only configuration change (attach handler to logger)
   - No modification to route handlers, fallback logic, or provider code

2. **Automatic coverage**:
   - Captures all ERROR+ logs from all modules (`main.py`, `fallback.py`, `providers/*.py`)
   - Works with existing `RotatingFileHandler` setup (multiple handlers on same logger)
   - No risk of missing errors (as long as they're logged)

3. **Proven pattern**:
   - Standard Python logging architecture
   - Handler lifecycle managed by logging framework
   - Handler failures isolated (don't break logging chain)

4. **Metadata extraction**:
   - `LogRecord` provides module, function, line number, timestamp automatically
   - Error message already structured: `[{request_id}] ✗ {provider}: {error_type} (model={model}) - {message}`
   - Regex parsing extracts provider/model/request_id

5. **Compatibility**:
   - Works alongside existing handlers (`RotatingFileHandler`, `StreamHandler`)
   - No conflict with `uvicorn` access logs (separate logger)
   - No impact on log file output (handler doesn't modify logs, only observes)

### Exception Isolation Strategy

**Critical requirement**: Handler exceptions must not break proxy.

**Implementation**:
- Wrap all handler logic in try/except
- On exception: Log to stderr (NOT logging module to avoid circular logging)
- Never re-raise (let logging framework continue)

**Test cases**:
- Database write fails → handler logs to stderr, proxy continues
- Parsing error (unexpected log format) → handler logs to stderr, proxy continues
- Alert delivery fails → handler logs to stderr, proxy continues

**Verification** (Task 3.1):
```python
def test_handler_exception_isolation():
    """Verify handler exceptions don't break logging."""
    # Mock tracker.record_error() to raise exception
    with patch.object(tracker, 'record_error', side_effect=Exception("DB error")):
        logger.error("Test error")
        # Verify: Log still written to file (not blocked by handler exception)
        assert "Test error" in read_log_file()
```

---

## Consequences

### Positive
- **Minimal code changes**: Attach handler in `main.py` (10 lines), rest is new module
- **Automatic capture**: All ERROR+ logs tracked without code modifications
- **Handler exceptions isolated**: Don't break existing logging
- **Metadata-rich**: `LogRecord` provides context automatically

### Negative
- **Only captures logged errors**: If error handling forgets to log, error is missed
- **Parsing brittleness**: Depends on log message format (`[request_id] ✗ provider: ...`)
- **Circular logging risk**: If handler logs errors at ERROR level, infinite recursion possible

### Mitigation Strategies

1. **Missed errors** (if not logged):
   - Current code inspection shows all errors are logged (Task 3.1)
   - Fallback handler logs all exceptions before re-raising
   - Route handlers catch and log exceptions
   - Risk: Low (error handling is comprehensive)

2. **Parsing brittleness** (Known Issue #005):
   - Use regex with multiple fallback patterns
   - If extraction fails, use generic signature: `{"provider": "unknown", "error_type": "unknown", "message": <full_log>}`
   - Log extraction failures at DEBUG level for investigation
   - Monitor extraction success rate (alert if <90%)

3. **Circular logging** (Known Issue #004):
   - Use separate logger for tracker internals: `logging.getLogger("error_tracker.internal")`
   - Configure handler to ignore `error_tracker.internal` logger:
     ```python
     def emit(self, record):
         if record.name.startswith("error_tracker"):
             return  # Skip tracking own errors
     ```
   - Catch all exceptions and log to stderr (NOT logging module)
   - Add recursion depth counter (abort if depth > 1)

4. **Format changes**:
   - Document expected log format in handler docstring
   - Test parsing on diverse log samples (not just ValidationException)
   - Handle: rate limits, timeouts, auth errors, unknown errors
   - Add fallback for unexpected formats

---

## Alternatives Considered

### Alternative 1: Decorator Pattern
**Approach**: `@track_errors` decorator on functions that call provider APIs.

```python
@track_errors
async def call_bedrock(request):
    try:
        response = await bedrock_client.invoke_model(...)
        return response
    except Exception as e:
        # track_errors decorator captures and records exception
        raise
```

**Why rejected**:
- **Invasive**: Requires decorating 10-15 functions across multiple modules
- **Easy to forget**: New code paths may miss decorator
- **Doesn't capture library errors**: Errors in `boto3`, `aiohttp`, or other libraries not decorated
- **Maintenance burden**: Every new provider function needs decorator

**When this would be correct**:
- Selective tracking (only track specific functions)
- Need explicit control over what gets tracked
- Small codebase with few error-prone functions

---

### Alternative 2: Middleware/Wrapper Pattern
**Approach**: Wrap provider API clients with error tracking logic.

```python
class TrackedBedrockClient:
    def __init__(self, client, tracker):
        self.client = client
        self.tracker = tracker

    async def invoke_model(self, **kwargs):
        try:
            return await self.client.invoke_model(**kwargs)
        except Exception as e:
            self.tracker.record_error(extract_signature(e), ...)
            raise
```

**Why rejected**:
- **Provider-specific**: Requires separate wrapper for each provider (Bedrock, Anthropic, OpenAI)
- **Missed errors**: Doesn't capture errors outside API calls (parsing, validation, timeout handling)
- **Tight coupling**: Wrapper knows about provider client structure (must update on SDK changes)
- **Testing complexity**: Must mock provider clients and wrappers

**When this would be correct**:
- Need to intercept at API boundary (modify requests/responses)
- Few providers (1-2) with stable SDKs
- Want to enrich errors with provider-specific context before logging

---

### Alternative 3: Exception Hook (`sys.excepthook`)
**Approach**: Global uncaught exception handler.

```python
def error_tracking_exception_hook(exc_type, exc_value, exc_tb):
    tracker.record_error(extract_signature(exc_value), ...)
    sys.__excepthook__(exc_type, exc_value, exc_tb)  # Call default handler

sys.excepthook = error_tracking_exception_hook
```

**Why rejected**:
- **Only unhandled exceptions**: Only triggers if exception reaches top level (proxy would crash)
- **No context**: Can't access request_id, provider, model (exception doesn't carry this metadata)
- **Not useful for caught errors**: Proxy catches and logs errors (they never reach `sys.excepthook`)
- **Safety net only**: Doesn't capture expected error path (caught exceptions)

**When this would be correct**:
- Safety net for unexpected crashes (complement to logging handler)
- Single-threaded application (exception hook is global, not thread-safe)
- Want to capture unhandled exceptions for post-mortem analysis

---

## Validation Plan

From Task 3.1 (Implement custom logging handler):

1. **Unit tests**:
   - Mock `LogRecord` with sample error message → verify extraction succeeds
   - Mock `tracker.record_error()` → verify called with correct signature
   - Mock `tracker.record_error()` to raise exception → verify handler logs to stderr, doesn't re-raise
   - Verify circular logging prevention (handler ignores own logger)

2. **Integration tests** (Task 3.3):
   - Start proxy with handler attached
   - Trigger ValidationException (invalid request body) → verify captured in database
   - Trigger ThrottlingException (burst requests) → verify captured
   - Query database → verify fingerprints, counts, timestamps correct

3. **Parsing validation**:
   - Test parsing on diverse log samples:
     - ValidationException: `"Bedrock validation error: An error occurred (ValidationException)..."`
     - ThrottlingException: `"Bedrock error: An error occurred (ThrottlingException)..."`
     - Rate limit: `"Rate limit exceeded (model=claude-sonnet)"`
     - Timeout: `"Request timeout after 30s (provider=bedrock)"`
   - Verify extraction succeeds for all formats
   - Document fallback behavior for unknown formats

4. **Performance measurement**:
   - Benchmark handler overhead:
     - Measure: Time to process 100 ERROR logs
     - Target: <1ms per log (handler processing only, not database write)
   - Verify: Handler doesn't slow down existing logging

5. **Exception isolation**:
   - Inject errors in handler:
     - Database connection fails → verify proxy continues
     - Parsing error (malformed log message) → verify proxy continues
     - Alert delivery fails → verify proxy continues
   - Verify: All failures logged to stderr, never re-raised

---

## Implementation Impact

**Files affected**:
- `stapler-scripts/claude-proxy/error_tracker.py` (NEW) — `ErrorTrackingHandler` class
  - `__init__(tracker)`
  - `emit(record)` — Main handler logic
  - `_parse_error_message(message)` — Extract provider/operation/error_type
  - `_extract_request_id(message)` — Extract request_id from `[request_id]` prefix
  - `_alert_new_error(fingerprint, signature)` — Trigger alert on new errors

- `stapler-scripts/claude-proxy/main.py` — Handler attachment (10 lines)
  - Import `ErrorTracker` and `ErrorTrackingHandler`
  - Initialize tracker after existing logging config
  - Attach handler to root logger
  - Log "Error tracking handler attached" confirmation

**Tasks implementing this decision**:
- Task 3.1: Implement custom logging handler
- Task 3.2: Attach handler to proxy loggers
- Task 3.3: Test error capture with live proxy

**Known issues related to this decision**:
- Bug 004: Handler circular logging if tracker logs errors
- Bug 005: Provider extraction fails on unexpected log format

---

## References

- **Research findings**: `project_plans/claude-proxy-error-tracking/research/findings-architecture.md`
- **Python logging documentation**: https://docs.python.org/3/library/logging.html
- **Python logging cookbook**: https://docs.python.org/3/howto/logging-cookbook.html
- **Logging handler best practices**: https://docs.python.org/3/howto/logging.html#configuring-logging-for-a-library
