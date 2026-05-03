# History Scanning Reference

How to locate, parse, and extract hook candidates from Claude Code conversation history.

---

## File Location

```
~/.claude/projects/<slug>/<session-id>.jsonl
```

**Slug derivation**: Replace `/` with `-` in the working directory path, then strip the leading `-`.

Example: `/home/tstapler/dotfiles` → `-home-tstapler-dotfiles`

```bash
# Get slug for current directory
CWD=$(pwd)
SLUG=$(echo "$CWD" | sed 's|/|-|g')
PROJECT_DIR="$HOME/.claude/projects/$SLUG"
ls "$PROJECT_DIR"/*.jsonl 2>/dev/null
```

**Session files**: Each `.jsonl` file is one session (named by UUID). All sessions for the project live in the same directory. The global `~/.claude/history.jsonl` contains a flat summary but the per-project JSONL files have the full tool use detail needed for scanning.

---

## JSONL Schema

Each line is a JSON object. Key `type` values:

| type | Content |
|------|---------|
| `user` | User message or tool result |
| `assistant` | Assistant message (text + tool_use blocks) |
| `attachment` | Hook firing, skill listing, permission events |
| `file-history-snapshot` | File backup state |
| `permission-mode` | Session permission mode |

### User message (text)
```json
{
  "type": "user",
  "message": {
    "role": "user",
    "content": "no wait, don't delete that file"
  },
  "timestamp": "2026-05-01T12:00:00Z"
}
```

### User message (tool result)
```json
{
  "type": "user",
  "message": {
    "role": "user",
    "content": [{
      "type": "tool_result",
      "tool_use_id": "toolu_xyz",
      "content": "command output here",
      "is_error": false
    }]
  },
  "toolUseResult": {
    "stdout": "actual output",
    "stderr": "",
    "interrupted": false
  }
}
```

### Assistant tool call
```json
{
  "type": "assistant",
  "message": {
    "content": [{
      "type": "tool_use",
      "id": "toolu_xyz",
      "name": "Bash",
      "input": { "command": "rm -rf /tmp/test" }
    }]
  }
}
```

### Hook firing (attachment)
```json
{
  "type": "attachment",
  "attachment": {
    "type": "hook_success",
    "hookName": "PreToolUse:Bash",
    "hookEvent": "PreToolUse",
    "stdout": "{ ... hook output ... }",
    "exitCode": 0,
    "command": "/home/user/.claude/hooks/rtk-rewrite.sh",
    "durationMs": 24
  }
}
```

---

## Signal Extraction Logic

Parse all JSONL files in the project directory. Process events in timestamp order. Build a findings list.

### Signal 1: Explicit User Corrections

Scan `type:"user"` messages where `message.content` is a string (not array):

```python
CORRECTION_PATTERNS = [
    r'\bno[,.]?\s+(don\'t|dont|stop|wait)\b',
    r'\bwait[,.]?\s+(don\'t|dont|stop|no)\b',
    r'\bundo\s+that\b',
    r'\brevert\s+(that|this|the last)\b',
    r'\bwrong\b.*\btry again\b',
    r'\bthat\'s not what I (wanted|meant|asked)\b',
    r'\bdon\'t do that\b',
]
```

When found: look back 1-3 messages to identify *which tool call* triggered the correction. That tool name + input pattern is a hook candidate.

**Severity**: High if the tool was `Bash` or `Write`; Medium for other tools.

### Signal 2: Tool Retry Loops

Within a session, find sequences where the same `tool_name` fires with similar `input` multiple times before a successful result:

```python
# Detect retries: same tool within 5 messages, input similarity > 70%
def find_retry_loops(events):
    tool_calls = [e for e in events if is_tool_call(e)]
    for i, call in enumerate(tool_calls):
        window = tool_calls[i+1:i+4]
        for later in window:
            if later['name'] == call['name']:
                similarity = jaccard_similarity(
                    set(call['input'].get('command','').split()),
                    set(later['input'].get('command','').split())
                )
                if similarity > 0.7:
                    yield {
                        'signal': 'retry_loop',
                        'tool': call['name'],
                        'input': call['input'],
                        'count': 2,
                        'severity': 'high'
                    }
```

RTK note: `[rerun: b1]`, `[rerun: b2]` etc. in tool results are RTK retry markers specific to this environment — these indicate the hook rewrote the command and it was retried. These are NOT hook failures; they're expected behavior.

### Signal 3: Dangerous Bash Patterns

Scan all `tool_use.name == "Bash"` inputs:

```python
DANGER_PATTERNS = {
    r'rm\s+-rf': ('L1', 'block', 'rm -rf detected'),
    r'chmod\s+7': ('L1', 'block', 'chmod 777 or similar'),
    r'curl[^|]*\|[^|]*(sh|bash)': ('L1', 'block', 'curl-pipe-to-shell'),
    r'sudo\s+rm': ('L1', 'block', 'sudo rm'),
    r'\beval\s*\(': ('L2', 'warn', 'eval in command'),
    r'>\s*/etc/': ('L1', 'block', 'write to /etc/'),
    r'DROP\s+TABLE': ('L1', 'block', 'SQL DROP TABLE'),
    r'git\s+push\s+--force': ('L2', 'warn', 'force push'),
}
```

### Signal 4: Sensitive File Writes

Scan all `tool_use.name in ("Write", "Edit")` inputs for `file_path`:

```python
SENSITIVE_PATHS = [
    r'\.env$',
    r'\.env\.',
    r'credentials',
    r'secrets?\.',
    r'\.pem$',
    r'\.key$',
    r'private[_-]key',
    r'id_rsa',
    r'\.aws/credentials',
]
```

### Signal 5: Repeated File Edits

Files written/edited 3+ times in a single session often indicate rework. These aren't necessarily hook candidates, but they're workflow signals worth noting.

```python
def find_repeated_edits(session_events):
    from collections import Counter
    file_counts = Counter()
    for e in session_events:
        if is_tool_call(e) and e['name'] in ('Write', 'Edit'):
            path = e['input'].get('file_path', '')
            if path:
                file_counts[path] += 1
    return [(path, count) for path, count in file_counts.items() if count >= 3]
```

### Signal 6: Existing Hook Firings

`type:"attachment"` entries with `attachment.type == "hook_success"` tell you what hooks are *already* running. Extract these to avoid recommending duplicates:

```python
existing_hooks = set()
for event in events:
    if event.get('type') == 'attachment':
        att = event.get('attachment', {})
        if att.get('type') == 'hook_success':
            existing_hooks.add(att.get('hookName', ''))
```

---

## Findings Table Format

Output from Phase 1 scan:

```
| Pattern | Sessions | Frequency | Severity | Existing Hook? | Suggested Layer |
|---------|----------|-----------|----------|----------------|-----------------|
| rm -rf  | 3        | 7x        | High     | No             | L1 Protection   |
| .env write | 1     | 2x        | High     | No             | L1 Protection   |
| console.log added | 5 | 12x  | Medium   | No             | L2 Quality      |
| Stop after missing tests | 4 | 8x | High | No           | L3 Workflow     |
```

Score each signal:
- `frequency × severity_weight` where High=3, Medium=2, Low=1
- Sort by score descending
- Top 5 are primary recommendations; rest go in "also consider" section

---

## Scanning Scope Recommendations

| Scope | When to Use |
|-------|-------------|
| Current project only | Default — most relevant signal |
| All projects | When current project is new; look for cross-project patterns |
| Last 30 days | Filter by `timestamp` to avoid stale signals |
| Last 7 days | When workflow has changed recently |

For large projects (>10 sessions), scan in parallel — each JSONL file is independent.
