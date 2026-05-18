# ADR-004: Alert Delivery Mechanism

**Status**: Accepted
**Date**: 2026-04-16
**Context**: Phase 3 — Planning

---

## Context

Need to notify user of new error types within seconds of first occurrence. The system must distinguish "new errors" (never seen before) from "known errors" (already tracked). User is a solo practitioner on macOS, working at desk with GUI session active.

### Requirements Driving This Decision
- **Speed**: Alert within 5 seconds of new error occurrence
- **Precision**: Only alert on novel error types (no spam for known errors)
- **Reliability**: Alert failure must not block proxy operation
- **Visibility**: User must see alert immediately (not buried in logs)

### Research Findings
From `research/findings-architecture.md` and `research/findings-pitfalls.md`:
- Four options considered: macOS Notification Center, file signal + watcher, stdout prefix, async queue
- Desktop notifications provide immediate visibility
- Cooldown period prevents alert fatigue during error storms
- Synchronous delivery acceptable for MVP (errors are rare, 50-100ms overhead acceptable)

---

## Decision

**Use macOS Notification Center** via `osascript` subprocess with 5-minute cooldown per fingerprint. Synchronous delivery (block for up to 2s timeout) acceptable for MVP. Upgrade to async queue if latency becomes observable issue.

### Implementation Approach

```python
class ErrorTracker:
    def __init__(self):
        self.alert_cache = {}  # fingerprint → last_alert_timestamp

    def send_desktop_notification(self, fingerprint: str, signature: dict):
        """Send macOS notification for new error.

        Cooldown: Skip if same fingerprint alerted within 5 minutes.
        """
        # Check cooldown
        last_alert_time = self.alert_cache.get(fingerprint, 0)
        if time.time() - last_alert_time < 300:  # 5 minutes
            logger.debug(f"Alert cooldown active for {fingerprint}")
            return

        # Build notification message
        title = f"New Error: {signature['provider']}"
        message = f"{signature['error_type']}: {signature['message'][:100]}"

        # Send via osascript (timeout 2s)
        try:
            subprocess.run([
                'osascript', '-e',
                f'display notification "{message}" with title "{title}"'
            ], timeout=2, check=True, capture_output=True)

            logger.info(f"🔔 Alert sent: {fingerprint} ({signature['provider']} {signature['error_type']})")

            # Record alert time
            self.alert_cache[fingerprint] = time.time()

        except subprocess.TimeoutExpired:
            logger.warning(f"Alert timeout for {fingerprint} (notification may not display)")
        except Exception as e:
            logger.error(f"Alert failed for {fingerprint}: {e}")
```

### Alert Cooldown Strategy
- **Per-fingerprint**: Each unique error has independent cooldown
- **Duration**: 5 minutes (300 seconds)
- **Purpose**: Prevents alert spam during error storms while catching novel errors quickly
- **Storage**: In-memory dict (cache) — survives session but resets on proxy restart

**Example behavior**:
```
Time    Event                               Action
00:00   ValidationException first seen      → Alert sent
00:01   ValidationException occurs again    → No alert (cooldown active)
00:04   ValidationException occurs again    → No alert (cooldown active)
00:06   ValidationException occurs again    → Alert sent (cooldown expired)
00:06   ThrottlingException first seen      → Alert sent (different fingerprint)
```

---

## Rationale

### Why macOS Notification Center?

1. **Immediate visibility**:
   - Desktop notifications appear prominently (top-right corner on macOS)
   - User sees alert immediately if at desk
   - No need to actively monitor logs or terminal

2. **Zero dependencies**:
   - `osascript` built-in on macOS
   - No external watcher process required
   - No Python libraries to install

3. **Acceptable latency**:
   - Synchronous delivery: 50-100ms typical
   - Errors are rare: Not on hot path (only when requests fail)
   - Error rate: <1% of total requests → 50-100ms blocking is acceptable
   - Alternative: If latency becomes issue, upgrade to async queue (deferred to Phase 3)

4. **Solo practitioner fit**:
   - macOS-only acceptable for single-user setup
   - User works at desk with GUI session (not SSH-only)
   - No team coordination required (no Slack, email, PagerDuty)

5. **Cooldown prevents spam**:
   - 5-minute cooldown per fingerprint prevents alert fatigue
   - Transient outages (100 errors in 1 minute) trigger 1 alert, not 100
   - Novel errors still caught quickly (different fingerprint = no cooldown)

### Notification Format

**Title**: `"New Error: {provider}"`
- Short and scannable
- Provider name immediately visible (Bedrock, Anthropic)

**Message**: `"{error_type}: {message[:100]}"`
- Error type (ValidationException, ThrottlingException)
- First 100 characters of message (preview)
- Full details available via query CLI

**Example notifications**:
```
Title:   New Error: bedrock
Message: ValidationException: context_management: Extra inputs are not permitted
```

```
Title:   New Error: anthropic
Message: RateLimitError: Rate limit exceeded for model claude-opus-4-6
```

### Cooldown Rationale

**Why 5 minutes?**
- Short enough: Novel errors caught quickly (5-minute delay acceptable)
- Long enough: Prevents spam during transient outages
- Tunable: Can be configured (environment variable or config file)

**Why per-fingerprint?**
- Different errors are independent (ValidationException vs ThrottlingException)
- One error storm shouldn't suppress alerts for unrelated errors

**Why in-memory cache?**
- Simple: No persistent storage required
- Fast: Dictionary lookup is O(1)
- Acceptable: Cooldown resets on proxy restart (rare event)

---

## Consequences

### Positive
- **Simple implementation**: ~30 lines (alert function + cooldown check)
- **Zero dependencies**: osascript is built-in
- **Immediate visibility**: User sees alert immediately
- **Cooldown prevents spam**: 5-minute window prevents alert fatigue

### Negative
- **macOS-only**: No Linux/Windows support (requires GUI session)
- **Synchronous latency**: 50-100ms blocking on alert delivery
- **Requires GUI session**: Doesn't work over SSH or when logged out
- **Cooldown resets on restart**: In-memory cache doesn't survive restarts

### Mitigation Strategies

1. **Platform lock-in** (macOS-only):
   - Acceptable for MVP: Solo practitioner on macOS
   - If Linux support needed: Add `notify-send` fallback (subprocess pattern same as osascript)
   - If Windows support needed: Add `powershell` fallback (`New-BurntToastNotification`)
   - Document platform requirement in README

2. **Synchronous latency** (Known Issue #003):
   - Timeout: 2 seconds (aggressive, prevents long blocking)
   - Test osascript failure gracefully: `timeout → warning logged, proxy continues`
   - If latency becomes observable issue: Upgrade to async queue (Phase 3 optimization)
   - Measure: Add timing metrics for alert delivery, track p99 latency

3. **Requires GUI session**:
   - Document limitation: "Alerts only appear when logged into macOS GUI"
   - Fallback: stdout logging (`logger.info("🔔 Alert sent")`) always works
   - Alternative: Use file-based signal (`touch /tmp/new-error-alert`) for headless operation

4. **Cooldown resets on restart**:
   - Acceptable: Proxy restarts are rare (only on deploy or crash)
   - If cooldown persistence needed: Store in SQLite (`CREATE TABLE alert_cooldowns`)
   - Cost/benefit: Not worth complexity for MVP (restarts are rare)

---

## Alternatives Considered

### Alternative 1: File Signal + External Watcher
**Approach**: Write `NEW_ERROR` to `/tmp/proxy-alerts.txt`, external watcher (e.g., `fswatch` + script) polls and triggers alert.

**Why rejected**:
- **Complexity**: Requires two processes (proxy + watcher)
- **Maintenance**: External watcher must be running (systemd service, launchd plist)
- **No visibility advantage**: osascript provides same notification with simpler architecture
- **Debugging harder**: Two processes to debug instead of one

**When this would be correct**:
- Need cross-platform support (watcher can use platform-specific notification APIs)
- Alert delivery must be async (watcher decouples proxy from notification latency)
- Multiple proxy instances (shared alert file)

---

### Alternative 2: Stdout with Prefix
**Approach**: Print `[NEW_ERROR]` line to stdout, user monitors logs or pipes to alert tool.

**Why rejected**:
- **Easy to miss**: Scrollback in terminal (user may not see)
- **No prominence**: Text in logs doesn't grab attention like desktop notification
- **Requires active monitoring**: User must be watching terminal or set up external tool

**When this would be correct**:
- Headless server (no GUI session)
- Log aggregation pipeline (ship to external system like ELK, Splunk)
- User prefers terminal-based workflow (tmux status line, terminal notifications)

---

### Alternative 3: Async Queue + Background Thread
**Approach**: Main thread writes alert to `queue.Queue`, background thread drains and sends notifications.

```python
class ErrorTracker:
    def __init__(self):
        self.alert_queue = queue.Queue()
        self.alert_thread = threading.Thread(target=self._alert_worker, daemon=True)
        self.alert_thread.start()

    def _alert_worker(self):
        while True:
            fingerprint, signature = self.alert_queue.get()
            self.send_desktop_notification(fingerprint, signature)

    def alert_new_error(self, fingerprint, signature):
        self.alert_queue.put((fingerprint, signature))  # Non-blocking
```

**Why deferred (not rejected)**:
- **Complexity**: Threading adds lifecycle management (shutdown, join)
- **Unnecessary for MVP**: Synchronous delivery acceptable (errors are rare, 50-100ms overhead acceptable)
- **Premature optimization**: Implement only if latency becomes observable issue

**When to implement** (Phase 3 optimization):
- If p99 latency on error path exceeds 2ms budget
- If osascript blocking causes observable degradation
- If alert delivery failures impact proxy availability

---

## Validation Plan

From Task 4.1 (Implement macOS notification delivery):

1. **Unit tests**:
   - Mock `subprocess.run()` → verify osascript called with correct arguments
   - Verify notification format: title, message
   - Verify cooldown logic: second alert within 5 minutes skipped
   - Verify cooldown expiry: alert after 6 minutes succeeds

2. **Integration tests** (Task 4.2):
   - Trigger new error → verify notification appears
   - Trigger same error again within 5 min → verify no notification
   - Trigger same error after 6 min → verify notification appears
   - Trigger different error → verify notification appears (independent cooldown)

3. **Failure handling**:
   - osascript timeout → verify warning logged, proxy continues
   - osascript error (binary not in PATH) → verify error logged, proxy continues
   - osascript crash → verify proxy doesn't crash

4. **Latency measurement**:
   - Measure time from `send_desktop_notification()` call to return
   - Target: <100ms p99
   - If exceeds 100ms: Investigate (osascript slow? DNS lookup?)

5. **End-to-end validation**:
   - Run proxy with error tracking enabled
   - Trigger ValidationException → verify desktop notification appears
   - Check notification content: title, message match expected format
   - Verify: Notification disappears after user dismisses or timeout (system behavior)

---

## Implementation Impact

**Files affected**:
- `stapler-scripts/claude-proxy/error_tracker.py` — Alert delivery functions
  - `send_desktop_notification(fingerprint, signature)` — Main alert logic
  - `alert_cache` — In-memory cooldown tracking (dict)

**Tasks implementing this decision**:
- Task 4.1: Implement macOS notification delivery
- Task 4.2: Add alert logging and fallback

**Known issues related to this decision**:
- Bug 003: osascript failure blocks error handler (timeout mitigation)

---

## Future Enhancements (Out of Scope for MVP)

If requirements change or limitations discovered during operation:

1. **Cross-platform support**:
   - Detect OS: `platform.system()` → "Darwin" (macOS), "Linux", "Windows"
   - macOS: osascript (current implementation)
   - Linux: `notify-send` (libnotify)
   - Windows: `powershell -Command "New-BurntToastNotification"`

2. **Async delivery**:
   - Use `asyncio.Queue` + background task
   - Move 50-100ms osascript call off request path
   - Only implement if latency becomes observable issue

3. **Multiple alert channels**:
   - Desktop notification (current)
   - Slack webhook (if team environment)
   - Email (if headless operation)
   - Configure via environment variables

4. **Alert enrichment**:
   - Include error count in notification (e.g., "ValidationException: 5 occurrences")
   - Deep link to query CLI (e.g., `open claude-proxy://error/<fingerprint>`)
   - Attach recent error occurrences (request_id, model)

5. **Persistent cooldown**:
   - Store cooldowns in SQLite (`CREATE TABLE alert_cooldowns`)
   - Survive proxy restarts
   - Only implement if restarts are frequent

---

## References

- **Research findings**: `project_plans/claude-proxy-error-tracking/research/findings-architecture.md`
- **Research findings**: `project_plans/claude-proxy-error-tracking/research/findings-pitfalls.md` (alert fatigue)
- **macOS notification documentation**: `man osascript`, AppleScript display notification
- **Python subprocess documentation**: https://docs.python.org/3/library/subprocess.html
