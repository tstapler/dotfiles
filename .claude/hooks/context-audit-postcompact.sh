#!/usr/bin/env bash
# PostCompact hook — run context_audit.py against the just-compacted
# session's transcript and record a trend row in a shared SQLite db.
#
# Input (stdin, JSON): {"session_id": "...", "transcript_path": "...", "trigger": "manual"|"auto", ...}
# Pure audit/telemetry, not a gate: the actual work runs in a backgrounded
# subshell so this hook returns immediately without blocking Claude Code.

set -uo pipefail

export PATH="$PATH:$HOME/.cargo/bin"

if ! command -v jq &>/dev/null || ! command -v python3 &>/dev/null; then
  exit 0
fi

INPUT="$(cat)"

(
  TRANSCRIPT_PATH="$(echo "$INPUT" | jq -r '.transcript_path // empty')"
  TRIGGER="$(echo "$INPUT" | jq -r '.trigger // "unknown"')"
  SESSION_ID="$(echo "$INPUT" | jq -r '.session_id // "unknown"')"

  [[ -z "$TRANSCRIPT_PATH" || ! -f "$TRANSCRIPT_PATH" ]] && exit 0

  ANALYZER="$HOME/dotfiles/.claude/skills/context-audit/scripts/context_audit.py"
  [[ ! -f "$ANALYZER" ]] && exit 0

  DB_DIR="$HOME/.claude/context-audit"
  mkdir -p "$DB_DIR"

  python3 "$ANALYZER" "$TRANSCRIPT_PATH" --json \
    --sqlite "$DB_DIR/trend.db" \
    --session-id "$SESSION_ID" \
    --trigger "$TRIGGER" \
    >/dev/null 2>>"$DB_DIR/postcompact.err.log"
) &
disown

exit 0
