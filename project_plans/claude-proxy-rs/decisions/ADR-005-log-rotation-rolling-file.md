# ADR-005: Log Rotation — rolling-file + tracing_appender::non_blocking

**Status**: Accepted
**Date**: 2026-06-17

## Context

FR-6.5 requires size-based rotating log files:
- Application log (`/tmp/claude-proxy.app.log`): 10MB × 10 files
- HTTP log (`/tmp/claude-proxy.http.log`): 10MB × 5 files

The proxy already uses `tracing` + `tracing-subscriber` for structured logging. The naive path would be to use `tracing-appender`'s built-in `RollingFileAppender`, but that crate only supports time-based rotation (MINUTELY, HOURLY, DAILY) — not byte-size rotation.

Additionally, `tracing_appender::RollingFileAppender` blocks on writes when used directly, which would stall the async runtime on every log statement.

## Decision

Use **`rolling-file` 0.2** for size-based rotation wrapped in **`tracing_appender::non_blocking`** for async-safe writes, with multiple `fmt::Layer` instances routing events to separate files via `filter_fn` predicates.

```toml
tracing-appender = "0.2"   # non_blocking wrapper only
rolling-file = "0.2"       # size-based rotation
```

## Alternatives Considered

| Option | Rejected because |
|--------|-----------------|
| `tracing-appender` alone | Supports only time-based rotation (MINUTELY/HOURLY/DAILY/NEVER); cannot trigger on 10MB byte size (FR-6.5 requirement unmet) |
| `tracing-appender` with `max_log_files(n)` | `max_log_files` in v0.2.5 only limits the count for time-triggered rotation; still no byte-size trigger |
| Custom `MakeWriter` implementation | Significant boilerplate to reimplement what `rolling-file` provides; not justified for a side project |

## Consequences

- `tracing_appender::non_blocking(file_appender)` returns a `(Writer, WorkerGuard)` pair; the `WorkerGuard` **must be stored for the process lifetime** in `main()` — dropping it early flushes and closes the writer channel, causing log loss on shutdown
- Multiple `fmt::Layer` instances with distinct `with_filter(filter_fn(...))` predicates on `tracing_subscriber::registry()` route events to separate files simultaneously
- Route HTTP access events using `target: "http_access"` in tracing macros: `tracing::info!(target: "http_access", ...)` — the filter predicate on the HTTP layer matches this target
- `rolling-file` uses Debian naming convention: `basename`, `basename.1`, ..., `basename.N` for rotated files
- The `non_blocking` wrapper introduces a background thread and bounded channel (default 128KB buffer); this is the correct async-safe pattern for all file logging in tokio applications
