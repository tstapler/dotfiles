# Claude Proxy Development Guide

## Service Management

This project runs as a launchd service. To restart after making code changes:

```bash
# Graceful restart (recommended - notifies in-flight clients)
launchctl kill SIGTERM gui/$(id -u)/com.claude-proxy

# Force stop/start
launchctl bootout gui/$(id -u)/com.claude-proxy
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.claude-proxy.plist
```

Or use the legacy commands:
```bash
launchctl unload ~/Library/LaunchAgents/com.claude-proxy.plist
launchctl load ~/Library/LaunchAgents/com.claude-proxy.plist
```

### Graceful Shutdown

The proxy implements graceful shutdown handling:
- On SIGTERM/SIGINT, sets a shutdown flag
- In-flight streaming requests receive an error event with retry instructions
- New requests receive 503 Service Unavailable
- Clients automatically retry after receiving shutdown errors

## Architecture

### Providers

- **Anthropic**: Primary provider using OAuth token
- **Bedrock**: Fallback provider using AWS credentials (never goes into cooldown)

### Timeout Handling

- Bedrock requests have a 5-minute timeout (configurable via `REQUEST_TIMEOUT` env var)
- Timeouts are automatically retried on the same provider (default: 3 retries)
- Bedrock is never disabled on rate limits or timeouts

### Async I/O Performance

**Non-Blocking Boto3 Calls**:
- All boto3 calls run in a ThreadPoolExecutor (20 threads)
- Event loops never block waiting for AWS API responses
- Each worker can handle 100+ concurrent requests
- Typical request flow:
  1. Request arrives → worker event loop schedules boto3 call in thread pool
  2. Event loop continues handling other requests (non-blocking)
  3. Thread pool executes boto3 call in background
  4. When complete, callback resumes request in event loop

### Credential Refreshing

**Proactive Credential Refresh**:
- Before each Bedrock request, checks if credentials expire within 5 minutes
- Automatically refreshes credentials by recreating the boto3 client
- Works with all credential sources: AWS SSO, aws-vault, assume-role, etc.
- Logs refresh events: `🔄 Credentials expiring in Xm, refreshing proactively`
- Prevents authentication failures mid-request

**How It Works**:
1. Check credential `_expiry_time` before each API call
2. If expiring within 5 minutes → recreate client (triggers credential_process or SSO refresh)
3. Log warning at 15 minutes, refresh at 5 minutes
4. Non-blocking: credential checks run in thread pool

Your profile uses `credential_process` with aws-vault, which gets refreshed automatically when the client is recreated.

## Configuration

Environment variables (set in `com.claude-proxy.plist`):
- `CLAUDE_CODE_OAUTH_TOKEN`: OAuth token for Anthropic API
- `AWS_PROFILE`: AWS profile for Bedrock (default: Sandbox.AdministratorAccess)
- `AWS_REGION`: AWS region (default: us-west-2)
- `PROXY_PORT`: Port to run proxy on (default: 47000)
- `REQUEST_TIMEOUT`: Timeout in seconds (default: 300)
- `BEDROCK_MAX_RETRIES`: Number of retry attempts for timeouts (default: 3)
- `COOLDOWN_SECONDS`: Cooldown duration after rate limits (default: 300)
- `WORKERS`: Uvicorn worker processes (default: 1)

### Concurrency & Performance

**Multiple Workers (Default)**:
- Default: One worker per CPU core (10 workers on your system)
- Each worker uses async/await for concurrent request handling
- Each worker handles graceful shutdown independently
- Set `WORKERS=1` in plist for single-worker mode if needed

**Blocking Detection (Multi-Level)**:

1. **Event Loop Monitoring** (asyncio debug mode):
   - Detects callbacks taking >100ms
   - Logs as asyncio RuntimeWarnings in error log
   - Catches blocking operations at the event loop level
   - Most accurate detection of blocking code

2. **Request Duration Monitoring** (middleware):
   - **Slow requests** (>30s): Logged with 🐌 symbol
   - **Blocking requests** (>60s): Logged with ⚠️ symbol and ERROR level
   - All responses include `X-Request-Duration` header

These warnings indicate potential issues:
- Provider timeouts
- Network problems
- Blocking synchronous operations (code bugs)
- CPU-intensive operations in async context

Check `/tmp/claude-proxy.error.log` for both types of warnings.

## Logs

- Access logs (HTTP requests): `/tmp/claude-proxy.log`
- Application logs (with → ✓ ✗ ⏱ ↻ symbols): `/tmp/claude-proxy.error.log`

To monitor real-time activity:
```bash
tail -f /tmp/claude-proxy.error.log
```
