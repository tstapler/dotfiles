# Hook Patterns Reference

Performance patterns, dedup implementations, and script templates for Claude Code hooks.

---

## Settings.json Hook Entry Structure

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "uv run --script ~/.claude/hooks/my-hook.py",
            "timeout": 10,
            "async": false
          }
        ]
      }
    ]
  }
}
```

**Key fields:**
- `matcher` — tool name filter evaluated *before* spawning subprocess (cheapest gate)
- `if` — secondary condition, also pre-spawn; supports shell-like expressions
- `async: true` — hook runs in background; Claude doesn't wait
- `asyncRewake: true` — async but exit code 2 interrupts Claude later
- `timeout` — seconds; default varies by hook type (command: 600s, prompt: 30s)

---

## Performance Gates — Always Apply

**Rule**: every hook entry must have either `matcher`, `if`, or both. A hook with neither fires on every event of that type.

```json
// BAD — fires on every tool use
{ "type": "command", "command": "~/.claude/hooks/check.sh" }

// GOOD — only fires for Bash tool
{ "matcher": "Bash", "hooks": [{ "type": "command", ... }] }

// BETTER — Bash + only when rm appears in command
{ "matcher": "Bash", "if": "input.command contains 'rm'", "hooks": [...] }
```

**Async decision:**

| Hook purpose | async setting |
|-------------|---------------|
| Block dangerous operation | `async: false` (must complete before tool runs) |
| Warn + allow | `async: false` if message needs to appear before the action |
| Logging, notifications | `async: true` |
| Memory capture at Stop | `async: true` |
| Context injection at UserPromptSubmit | `async: false` (inject before Claude reads prompt) |

---

## Deduplication Patterns

### Strategy 1 — Config-Level (Free, No Code)

Claude Code deduplicates identical handler strings across settings files at load time. If the same command string appears in user + project settings, it fires once.

**Action**: nothing — built in. Only matters if you have hooks in multiple settings files.

---

### Strategy 2 — Time-Window (Bug Workaround)

Use when hooks fire twice due to the `~` CWD bug (#3465) or dual plugin loading (#24115). Prevents the same event from being processed within a time window.

**Shell implementation** (add to top of any hook script):

```bash
#!/usr/bin/env bash
# Time-window deduplication: skip if same event seen within WINDOW seconds
LOCK_DIR="${XDG_RUNTIME_DIR:-/tmp}/claude-hook-locks"
mkdir -p "$LOCK_DIR"

# Hash the relevant input (stdin already consumed — hash the args or env)
EVENT_KEY="${HOOK_EVENT_NAME:-unknown}_$(echo "$@" | sha256sum | cut -c1-12)"
LOCK_FILE="$LOCK_DIR/${EVENT_KEY}.lock"
WINDOW=2

if [[ -f "$LOCK_FILE" ]]; then
    last=$(cat "$LOCK_FILE" 2>/dev/null)
    now=$(date +%s)
    if [[ $((now - last)) -lt $WINDOW ]]; then
        exit 0  # duplicate — skip silently
    fi
fi
date +%s > "$LOCK_FILE"

# ... rest of hook logic
```

**Python implementation:**

```python
import hashlib, os, time, pathlib

def is_duplicate(key: str, window_secs: int = 2) -> bool:
    lock_dir = pathlib.Path(os.environ.get("XDG_RUNTIME_DIR", "/tmp")) / "claude-hook-locks"
    lock_dir.mkdir(parents=True, exist_ok=True)
    lock_file = lock_dir / f"{hashlib.sha256(key.encode()).hexdigest()[:16]}.lock"
    now = time.time()
    if lock_file.exists():
        try:
            last = float(lock_file.read_text())
            if now - last < window_secs:
                return True
        except (ValueError, OSError):
            pass
    lock_file.write_text(str(now))
    return False
```

---

### Strategy 3 — Semantic Hash (Content Dedup)

Use when you want to avoid redundant work on logically equivalent inputs — e.g., don't re-lint a file that hasn't changed, don't re-warn about the same pattern in the same session.

The key is: `session_id + hash(relevant_input_fields)`.

`CLAUDE_SESSION_ID` is available as an environment variable in hook processes.

**Python implementation** (reads from stdin JSON):

```python
#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# ///
import hashlib, json, os, sys, pathlib

def already_seen(session_id: str, content_hash: str, state_dir: str = "/tmp/claude-hook-state") -> bool:
    pathlib.Path(state_dir).mkdir(parents=True, exist_ok=True)
    state_file = pathlib.Path(state_dir) / f"{session_id}.json"
    seen: set[str] = set()
    if state_file.exists():
        try:
            seen = set(json.loads(state_file.read_text()))
        except (json.JSONDecodeError, OSError):
            pass
    if content_hash in seen:
        return True
    seen.add(content_hash)
    state_file.write_text(json.dumps(list(seen)))
    return False

def main():
    data = json.load(sys.stdin)
    session_id = os.environ.get("CLAUDE_SESSION_ID", "unknown")
    
    # Hash the fields that determine "same event"
    tool_input = data.get("tool_input", {})
    relevant = json.dumps({
        "tool": data.get("tool_name"),
        "command": tool_input.get("command", "")[:128],  # first 128 chars of command
    }, sort_keys=True)
    content_hash = hashlib.sha256(relevant.encode()).hexdigest()[:20]
    
    if already_seen(session_id, content_hash):
        # Seen this exact event this session — skip
        print(json.dumps({"decision": "allow"}))
        sys.exit(0)
    
    # ... rest of hook logic
    print(json.dumps({"decision": "allow"}))

if __name__ == "__main__":
    main()
```

---

## UV Single-File Script Template

UV scripts avoid venv overhead — dependencies declared inline, runs immediately with `uv run --script`.

```python
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""
Hook: {name}
Event: {PreToolUse|PostToolUse|Stop|UserPromptSubmit}
Layer: {L1|L2|L3|L4}
Dedup: {None|Time-window Ns|Semantic hash on {field}}
"""
import json, sys, os

def main():
    data = json.load(sys.stdin)
    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})
    
    # Hook logic here
    
    # Allow (no output needed for simple allow)
    sys.exit(0)
    
    # OR: Block with message
    # print(json.dumps({"decision": "block", "reason": "message to Claude"}))
    # sys.exit(2)
    
    # OR: Warn (output message but allow)
    # print(json.dumps({"decision": "allow", "message": "warning text"}))

if __name__ == "__main__":
    main()
```

---

## Hook Input/Output Schema

**Input** (via stdin, all hook types):

```json
{
  "session_id": "abc123",
  "tool_name": "Bash",
  "tool_use_id": "toolu_xyz",
  "tool_input": {
    "command": "rm -rf /tmp/test"
  }
}
```

For file tools (`Write`, `Edit`):
```json
{
  "tool_name": "Write",
  "tool_input": {
    "file_path": "/home/user/project/.env",
    "content": "SECRET=..."
  }
}
```

For `UserPromptSubmit`:
```json
{
  "prompt": "deploy this to production",
  "session_id": "abc123"
}
```

**Output** (via stdout, all hook types):

```json
// Allow silently
{}

// Allow with injected context (PreToolUse only — modifies tool input)
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow",
    "updatedInput": { "command": "modified command" }
  }
}

// Warn (allow but inject message)
{ "decision": "allow", "message": "Consider X before proceeding" }

// Block (exit code 2, message fed to Claude)
{ "decision": "block", "reason": "Explanation of why this is blocked" }
```

Exit code 2 = blocking error; exit code 0 = allow; any other exit = treated as 0 with stderr logged.

---

## hookify Rule File Format

```markdown
---
name: {kebab-case}
enabled: true
event: {bash|file|stop|prompt|all}
action: {warn|block}
# Simple format:
pattern: {python-regex}
# OR Advanced format (remove pattern above):
conditions:
  - field: {command|file_path|new_text|old_text|content|transcript|prompt}
    operator: {regex_match|contains|equals|not_contains|starts_with|ends_with}
    pattern: {value}
  - field: ...  # multiple conditions = AND
---

Message body (Markdown).
Shown to Claude when rule triggers.
```

**Event to hookify field mapping:**

| hookify `event` | Claude hook type | Default field |
|-----------------|-----------------|---------------|
| `bash` | PreToolUse:Bash | `command` |
| `file` | PreToolUse:Write/Edit | `file_path`, `new_text`, `old_text`, `content` |
| `stop` | Stop | `transcript` |
| `prompt` | UserPromptSubmit | `prompt` |
| `all` | All events | depends on context |
