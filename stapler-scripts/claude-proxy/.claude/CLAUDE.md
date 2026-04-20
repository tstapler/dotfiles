# Claude Proxy Development Guide

## Service Management

This project runs as a launchd service. To restart after making code changes:

```bash
# Recommended: Use the Makefile
make restart

# Or manually with graceful shutdown (notifies in-flight clients)
launchctl kill SIGTERM gui/$(id -u)/com.claude-proxy
```

Additional Makefile commands:
```bash
make start       # Start the service
make stop        # Stop the service
make status      # Check if running
make logs        # View access logs (uvicorn)
make app-logs    # View application logs (fallback, providers)
make http-logs   # View HTTP request logs (httpx)
```

### Graceful Shutdown

The proxy implements graceful shutdown handling:
- On SIGTERM/SIGINT, sets a shutdown flag
- In-flight streaming requests receive an error event with retry instructions
- New requests receive 503 Service Unavailable
- Clients automatically retry after receiving shutdown errors

### Bedrock-Specific Workarounds

**Thinking Budget Tokens Issue** ([Issue #8756](https://github.com/anthropics/claude-code/issues/8756)):
- **Applies to**: AWS Bedrock provider only
- **Problem**: Claude Code defaults to `MAX_THINKING_TOKENS=31999`, which:
  - Often exceeds `max_tokens` causing validation errors
  - Consumes output budget, truncating tool responses (file edits)
  - Triggers Bedrock's burndown throttling with 4096 limit
- **Solution**: Bedrock provider automatically validates thinking tokens:
  - If `budget_tokens > max_tokens` and `max_tokens < 1024`: Disables thinking
  - If `budget_tokens > max_tokens` and `max_tokens >= 1024`: Caps to `max_tokens`
  - If `budget_tokens < 1024`: Increases to minimum 1024
- **Anthropic provider**: Receives original request (no modification)
- Logged as warning: `Bedrock: Capping thinking.budget_tokens...`
- Can be removed once Claude Code fixes the default

**SSE Event Forwarding** (Fixed 2026-01-23):
- **Problem**: Original Bedrock implementation only forwarded 2 out of 7 SSE event types
  - Only forwarded: `content_block_delta`, `message_stop`
  - Dropped: `message_start`, `content_block_start`, `content_block_stop`, `message_delta`, `ping`
  - Caused Claude Code "No assistant message found" errors on short Haiku responses
- **Solution**: Now forwards ALL event types from Bedrock, matching Anthropic provider behavior
- **Implementation**: Changed from selective event filtering to `yield f"data: {json.dumps(chunk)}\n\n"`
- **Refactoring**: Extracted shared logic into `_prepare_bedrock_body()` and `_handle_bedrock_error()` helper methods

**Request Body Cleaning** (Fixed 2026-02-20):
- **Problem**: Claude Code sends Bedrock/Claude Code-specific fields that cause validation errors
  - Tool fields: `defer_loading`, `input_examples`, `custom`, `cache_control` cause validation errors
  - Message content: `tool_reference` type not supported in tool results by either Anthropic API or Bedrock
  - Top-level fields: `output_config`, `context_management` cause validation errors (Anthropic API only)
  - Errors: `tools.X.custom.defer_loading: Extra inputs are not permitted`, `messages.X.content.0.tool_result.content.0: Input tag 'tool_reference' found using 'type' does not match any of the expected tags`
  - See: [Claude Code Issue #11678](https://github.com/anthropics/claude-code/issues/11678)
- **Solution**: Both providers clean request body before sending
- **Implementation**:
  - **Shared method** `_clean_message_content()` (in base Provider class):
    - Filters message content to only include supported types: `text`, `image`, `document`, `search_result`
    - Removes unsupported types like `tool_reference` from tool results
    - Used by both Anthropic and Bedrock providers
  - **Anthropic provider** `_clean_request_body()`:
    - Removes unsupported fields from tool definitions
    - Calls shared `_clean_message_content()` for message cleaning
    - Removes Bedrock-specific top-level fields:
      - `output_config`: Bedrock-only field for [effort parameter](https://docs.aws.amazon.com/bedrock/latest/userguide/model-parameters-anthropic-claude-messages.html) (Claude Opus 4.5 with `effort-2025-11-24` beta)
      - `context_management`: Bedrock-specific field for context caching ([Issue #21612](https://github.com/anthropics/claude-code/issues/21612))
  - **Bedrock provider** `_prepare_bedrock_body()`:
    - Removes unsupported fields from tool definitions
    - Calls shared `_clean_message_content()` for message cleaning
- **Impact**: Prevents 400 validation errors when using tools and advanced features with both providers

## Architecture

### Providers

- **Anthropic**: Primary provider using OAuth token
- **Bedrock**: Fallback provider using AWS credentials (never goes into cooldown)

### Beta Features

The proxy automatically forwards `anthropic-beta` headers to both providers:
- **Anthropic API**: Header is passed through as-is
- **Bedrock**: Header is converted to `anthropic_beta` array in request body with model-specific filtering
  - Only beta flags supported by Bedrock are included
  - Beta flags are filtered based on model compatibility (e.g., `computer-use` only for Claude 3.7 Sonnet)
  - Unsupported or incompatible flags are filtered out and logged
  - Reference: [AWS Bedrock Claude Documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/model-parameters-anthropic-claude-messages-request-response.html)
- Supports comma-separated beta features (e.g., `context-1m-2025-08-07,token-efficient-tools-2025-02-19`)

**Supported Bedrock Beta Features**:
| Beta Feature | Beta Header | Compatible Models |
|--------------|-------------|-------------------|
| Computer use | `computer-use-2025-01-24` | Claude 3.7 Sonnet |
| Tool use | `token-efficient-tools-2025-02-19` | Claude 3.7 Sonnet and Claude 4+ |
| Interleaved thinking | `Interleaved-thinking-2025-05-14` | Claude 4+ models |
| 128K output tokens | `output-128k-2025-02-19` | Claude 3.7 Sonnet |
| Developer mode (raw thinking) | `dev-full-thinking-2025-05-14` | Claude 4+ models (requires account team approval) |
| 1 million tokens | `context-1m-2025-08-07` | Claude Sonnet 4 |
| Context management | `context-management-2025-06-27` | Claude Sonnet 4.5 and Claude Haiku 4.5 |
| Effort | `effort-2025-11-24` | Claude Opus 4.5 |
| Tool search tool | `tool-search-tool-2025-10-19` | Claude Opus 4.5 |
| Tool use examples | `tool-examples-2025-10-29` | Claude Opus 4.5 |

**Model-Specific Filtering**:
The proxy automatically filters beta features based on the model being used. For example:
- Request with `claude-haiku-4-5-20251001` + `computer-use-2025-01-24` → filtered out (only compatible with Claude 3.7 Sonnet)
- Request with `claude-haiku-4-5-20251001` + `context-management-2025-06-27` → included (compatible with Haiku 4.5)
- Request with `claude-sonnet-4-20250514` + `context-1m-2025-08-07` → included (compatible with Sonnet 4)

Filtered features are logged at debug level:
- `Filtering unsupported beta flags for Bedrock: [...]` - Beta feature not recognized by Bedrock
- `Filtering model-incompatible beta flags for MODEL: [...]` - Beta feature not compatible with this model

Example client request:
```
anthropic-beta: oauth-2025-04-20,context-1m-2025-08-07
```

Bedrock receives only the supported flag:
```python
{"anthropic_beta": ["context-1m-2025-08-07"]}
```

### Error Handling

- **4xx errors (ValidationError)**: Returned with original status code, not retried
- **429 errors (RateLimitError)**: Triggers cooldown on Anthropic provider, automatic fallback to Bedrock
- **Timeout errors**: Retried on same provider (Bedrock only, up to BEDROCK_MAX_RETRIES times)
- **5xx errors**: Logged and returned as 500 Internal Server Error

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
- Before each Bedrock request, checks credential expiry status
- Automatically refreshes credentials using aws-sso-lib Python library
- Opens browser for SSO authentication when tokens expire
- Works with all credential sources: AWS SSO (via aws-vault), assume-role, etc.
- Detects and handles expired credentials gracefully
- Provides clear instructions when manual SSO login is required

**Performance Caching**:
- Uses diskcache to reduce expensive boto3 credential checks
- Credential validity cached for 30 seconds (avoids checking on every request)
- SSO configuration cached for 1 hour (rarely changes)
- Cache shared across all worker processes via `/tmp/claude-proxy-bedrock-cache`
- Significantly reduces overhead with multiple concurrent requests

**Credential States**:
1. **Already expired**: Opens browser for SSO login
   - `🔐 AWS SSO session expired. Opening browser for login...`
   - `✓ SSO login completed successfully`
2. **Expiring soon** (< 5 min): Proactive refresh
   - `🔄 Credentials expiring in Xm, refreshing proactively`
3. **Valid** (> 15 min): No action needed
   - `Credentials valid for X minutes`

**Error Handling**:
When Bedrock requests fail due to credential issues, the proxy:
- Detects "security token expired" errors from AWS
- Logs actionable commands to fix the issue
- Returns clear error messages to Claude Code
- Example: `❌ AWS credentials expired. Run: aws-vault exec Sandbox.AdministratorAccess -- aws sts get-caller-identity`

**Manual Refresh**:
If you see authentication errors, refresh your SSO session:
```bash
# Test credentials
aws-vault exec Sandbox.AdministratorAccess -- aws sts get-caller-identity

# Or use your aws-claude alias
aws-claude
```

**How It Works**:
1. Check credential `_expiry_time` before each API call
2. If expired or expiring within 5 minutes → use aws-sso-lib to refresh SSO token cache
3. aws-sso-lib opens browser for authentication and updates `~/.aws/sso/cache/`
4. aws-vault credential_process reads refreshed tokens from cache
5. Non-blocking: credential checks run in thread pool

The proxy uses aws-sso-lib to programmatically refresh AWS SSO tokens by opening the browser for authentication. This directly updates the SSO token cache (`~/.aws/sso/cache/`) that aws-vault's credential_process reads, ensuring seamless credential refresh.

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

Check `/tmp/claude-proxy.app.log` for both types of warnings.

## Logs

**Log Files** (automatically rotated):
- **Application logs** (with → ✓ ✗ ⏱ ↻ symbols): `/tmp/claude-proxy.app.log`
  - Fallback logic, provider switching, errors
  - 10MB per file, 10 backups (100MB total)
- **HTTP request logs** (httpx/httpcore): `/tmp/claude-proxy.http.log`
  - Low-level HTTP requests/responses
  - 10MB per file, 5 backups (50MB total)
- **Access logs** (uvicorn HTTP): `/tmp/claude-proxy.log`
  - Endpoint access, status codes
  - Managed by uvicorn

**Request ID Tracking**:
- Every request gets a unique 8-character ID (e.g., `b69743ce`)
- Request ID is returned in `X-Request-ID` response header
- All log entries include `[request_id]` prefix for easy correlation
- Example log flow for a single request:
  ```
  [b69743ce] → /v1/messages stream=true
  [b69743ce] Request: model=claude-sonnet-4-5, max_tokens=4096, stream=True
  [b69743ce] ✓ Starting streaming response
  ```

**Monitoring**:
```bash
# Application activity (recommended)
tail -f /tmp/claude-proxy.app.log

# Follow a specific request by ID
grep "b69743ce" /tmp/claude-proxy.app.log

# HTTP request details
tail -f /tmp/claude-proxy.http.log

# Endpoint access
tail -f /tmp/claude-proxy.log
```

## Future Work / Research TODOs

Items identified from tool evaluations and architecture reviews. Not blocking current operation.

### Compression (claw-compactor / FusionEngine)

- [ ] **Investigate CacheAligner concept** — headroom's CacheAligner aligns compressed content to Anthropic prompt cache boundaries so compression and caching compound (the 90% cache read discount only activates when prefixes are stable). Check if FusionEngine has any cache-boundary awareness: inspect `_engine.stage_names` at startup and grep claw-compactor source for "cache" or "prefix". If absent, consider a lightweight post-compression pass that stabilizes prefixes before forwarding.
  - Reference: [headroom CacheAligner](https://github.com/chopratejas/headroom), [[Knowledge Synthesis - 2026-04-16]]
  - Priority: Medium — compounding effect could meaningfully reduce costs for long sessions

- [ ] **Evaluate headroom Python SDK for non-proxy paths** — tools that make direct Anthropic API calls (bypassing this proxy) currently get no compression. headroom's Python SDK (`from headroom import compress`) could be used in those paths. Assess whether any tools in `~/Documents/personal-wiki/tools/` call the API directly.
  - Priority: Low — proxy covers all Claude Code traffic

### Session Learning (`headroom learn` concept)

- [ ] **Investigate `headroom learn` for MEMORY.md automation** — headroom reads conversation history from Claude Code, finds failure patterns, and writes corrections to CLAUDE.md. This is exactly the "automated session-end hook to populate MEMORY.md" gap called out in STAPLER.md. Study the implementation before building a custom version.
  - Reference: [headroom learn docs](https://github.com/chopratejas/headroom), STAPLER.md "Known gaps" section
  - Priority: High — MEMORY.md is currently empty; this gap actively degrades session quality

### Re-evaluation Triggers

- [ ] Re-evaluate headroom for adoption when it reaches 1.0 (currently 0.x/beta)
- [ ] Re-evaluate if claw-compactor becomes unmaintained or FusionEngine compression ratios degrade
