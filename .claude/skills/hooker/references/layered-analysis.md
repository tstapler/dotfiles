# Layered Analysis Framework

The four control layers define *what kind of protection* a hook provides and *when* it fires relative to the action it guards.

---

## Layer Definitions

### L1 — Protection (Block Before Damage)

**Purpose**: Stop dangerous or irreversible operations before they execute.  
**Events**: `PreToolUse` only  
**Default action**: `block`  
**Failure mode if missing**: Damage happens, then you notice.

**Assign to L1 when:**
- The operation is irreversible (file deletion, overwriting credentials, production deployments)
- The pattern is clearly dangerous regardless of context
- Blocking has low false-positive risk (tight regex, specific tool)

**Examples:**
```yaml
# Block rm -rf
event: bash
action: block
pattern: rm\s+-rf

# Block writing to .env files
event: file
action: block
conditions:
  - field: file_path
    operator: regex_match
    pattern: \.env$|\.env\.

# Block curl-pipe-to-shell
event: bash
action: block
pattern: curl[^|]*\|[^|]*sh
```

**L1 performance rule**: Always use `matcher: "Bash"` or `matcher: "Write"` — L1 hooks are the ones you most want to be fast since they sit in the hot path of every tool call.

---

### L2 — Quality (Warn After Writes)

**Purpose**: Detect standards violations and surface them while the context is still warm.  
**Events**: `PostToolUse` primarily; also `PreToolUse` for patterns detectable from input  
**Default action**: `warn` (escalate to `block` only after the pattern is well-understood)  
**Failure mode if missing**: Standards drift accumulates silently across sessions.

**Assign to L2 when:**
- The pattern is detectable from file content after writing
- The issue is a quality concern, not a safety concern
- False positives are tolerable (warn is recoverable, block is not)

**Examples:**
```yaml
# Warn on console.log in source files
event: file
action: warn
conditions:
  - field: file_path
    operator: regex_match
    pattern: \.(ts|js|tsx|jsx)$
  - field: new_text
    operator: contains
    pattern: console\.log(

# Warn on TODO without ticket
event: file
action: warn
conditions:
  - field: new_text
    operator: regex_match
    pattern: TODO(?!\s*\[)
```

**L2 + dedup**: L2 hooks on file edits are high-frequency. Use semantic hash on `file_path` + `new_text[:64]` to avoid re-warning on the same content when a file is written multiple times in a session.

---

### L3 — Workflow (Completion Gates)

**Purpose**: Prevent Claude from stopping before required steps are done.  
**Events**: `Stop` primarily  
**Default action**: `block` (the whole point is to prevent stopping)  
**Failure mode if missing**: Claude declares "done" before tests pass, docs update, or commits land.

**Assign to L3 when:**
- Something must happen before a work unit is complete
- The user has repeatedly caught Claude stopping early in history scan
- There's a checklist that should be verified before any session ends

**Examples:**
```yaml
# Require test run before stopping
event: stop
action: block
conditions:
  - field: transcript
    operator: not_contains
    pattern: (pytest|npm test|go test|bun test)

# Require commit before stopping
event: stop
action: warn
conditions:
  - field: transcript
    operator: not_contains
    pattern: git commit
```

**L3 caution**: Overly aggressive L3 hooks trap Claude in infinite loops. Use `warn` before `block`. Scope conditions tightly — `not_contains` on the full transcript is a coarse signal.

---

### L4 — Intelligence (Context & Memory)

**Purpose**: Inject relevant context into prompts, capture session learnings at stop, or enhance Claude's working memory without user prompting.  
**Events**: `UserPromptSubmit`, `Stop`, `SessionStart`  
**Default action**: `warn` (used to inject context, not block)  
**Failure mode if missing**: Claude repeats work that was already done, lacks project-specific context.

**Assign to L4 when:**
- You want to automatically inject context based on what the user asks
- You want to capture session state at end (key decisions, files changed)
- The hook adds information rather than preventing actions

**Examples:**
```yaml
# Inject context when user asks about deployment
event: prompt
action: warn
conditions:
  - field: prompt
    operator: regex_match
    pattern: deploy|production|release|ship

# Always async — L4 hooks should never block
```

**L4 + async**: All L4 hooks should use `async: true`. They add value but should never gate Claude's ability to respond.

---

## Layer Decision Tree

```
Is the operation irreversible if it proceeds?
  YES → L1 (PreToolUse, block)
  NO  → continue

Is this a code/content quality issue detected from output?
  YES → L2 (PostToolUse, warn)
  NO  → continue

Does Claude stopping early cause problems?
  YES → L3 (Stop, warn/block)
  NO  → continue

Would injecting context or capturing state improve quality?
  YES → L4 (UserPromptSubmit/Stop, async warn)
  NO  → not a hook — reconsider
```

---

## Layer × Event Matrix

| Layer | PreToolUse | PostToolUse | Stop | UserPromptSubmit |
|-------|-----------|-------------|------|-----------------|
| L1 Protection | ✓ primary | — | — | — |
| L2 Quality | sometimes | ✓ primary | — | — |
| L3 Workflow | — | — | ✓ primary | — |
| L4 Intelligence | — | — | ✓ capture | ✓ primary |

---

## Severity Escalation Path

Always start at the lower-impact action and escalate only when the pattern is well-understood:

1. `warn` → observe false positive rate over 1 week
2. If FP rate < 10% → escalate to `block`
3. If FP rate > 30% → tighten the pattern, not the action
