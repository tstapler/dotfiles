#!/usr/bin/env bash
# cmdcrush-hook-version: 1
# PreToolUse:Bash hook — compress command output before it reaches context.
#
# Strategy: try rtk's per-command rewrite first (its git/gh/aws/etc-aware
# substitutions produce smaller output at the source), and only fall back to
# generically wrapping the whole command in `cmdcrush -- bash -c '...'` when
# rtk has no equivalent. Imports rtk's registry via `rtk rewrite` instead of
# reimplementing it here, so rtk's registry stays the single source of truth
# for per-command compaction (see rtk's own hook, .claude/hooks/rtk-rewrite.sh
# in the rtk repo, for the exit-code contract this mirrors).
#
# Exit code protocol from `rtk rewrite`:
#   0 + stdout  Rewrite found, no deny/ask rule matched -> auto-allow
#   1           No RTK equivalent -> fall through to cmdcrush wrap
#   2           Deny rule matched -> pass through (native deny handles it)
#   3 + stdout  Ask rule matched -> rewrite but let Claude Code prompt

set -euo pipefail

# Hooks may run with a minimal PATH that doesn't source shell startup files
# (where `~/.cargo/bin` normally gets added) — append it defensively so
# `cmdcrush` resolves regardless of how this hook was invoked.
export PATH="$PATH:$HOME/.cargo/bin"

CMDCRUSH_BIN="${CMDCRUSH_BIN:-cmdcrush}"

if ! command -v jq &>/dev/null; then
  exit 0
fi

INPUT=$(cat)
CMD=$(echo "$INPUT" | jq -r '.tool_input.command // empty')

if [ -z "$CMD" ]; then
  exit 0
fi

# Heredocs/here-strings don't survive being re-quoted into a single
# `bash -c '...'` argument safely — skip rather than risk corrupting the
# command (same limitation rtk's own hook documents).
case "$CMD" in
  *'<<'*) exit 0 ;;
esac

# Already wrapped/rewritten — avoid double-wrapping.
case "$CMD" in
  "rtk "*|"$CMDCRUSH_BIN "*|"cmdcrush "*) exit 0 ;;
esac

ORIGINAL_INPUT=$(echo "$INPUT" | jq -c '.tool_input')

# Try rtk's per-command compaction first, if rtk is available. rtk's own
# registry already decides which commands are worth touching (e.g. it leaves
# `pwd`/`echo` alone), so this runs before any triviality heuristic — a short
# command like `git status` is exactly the case rtk exists to compact.
if command -v rtk &>/dev/null; then
  EXIT_CODE=0
  REWRITTEN=$(rtk rewrite "$CMD" 2>/dev/null) || EXIT_CODE=$?

  case $EXIT_CODE in
    0)
      if [ "$CMD" != "$REWRITTEN" ]; then
        UPDATED_INPUT=$(echo "$ORIGINAL_INPUT" | jq --arg cmd "$REWRITTEN" '.command = $cmd')
        jq -n --argjson updated "$UPDATED_INPUT" '{
          "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
            "permissionDecisionReason": "rtk auto-rewrite",
            "updatedInput": $updated
          }
        }'
        exit 0
      fi
      ;;
    2)
      exit 0
      ;;
    3)
      UPDATED_INPUT=$(echo "$ORIGINAL_INPUT" | jq --arg cmd "$REWRITTEN" '.command = $cmd')
      jq -n --argjson updated "$UPDATED_INPUT" '{
        "hookSpecificOutput": {
          "hookEventName": "PreToolUse",
          "updatedInput": $updated
        }
      }'
      exit 0
      ;;
  esac
fi

# No rtk-specific rewrite applied. Before falling back to generic cmdcrush
# wrapping, skip commands unlikely to produce enough output to be worth an
# extra subprocess spawn — cmdcrush's own --floor-bytes would pass these
# through anyway, so wrapping them just adds overhead with no benefit.
read -r first_word _ <<<"$CMD"
case "$first_word" in
  cd|pwd|echo|export|alias|unalias|which|type|true|false|exit|source|.|set|unset|umask|history|jobs|fg|bg|wait|clear|pushd|popd|dirs)
    exit 0
    ;;
esac
if [ "${#CMD}" -lt 20 ]; then
  exit 0
fi

CMDCRUSH_PATH=$(command -v "$CMDCRUSH_BIN" 2>/dev/null) || exit 0

# Use the resolved absolute path: the rewritten command runs in Claude Code's
# Bash tool environment, not this hook script's process, so the PATH
# extension above (or any PATH this script happens to have) doesn't carry
# over to it.
WRAPPED="$CMDCRUSH_PATH -- bash -c $(printf '%q' "$CMD")"
UPDATED_INPUT=$(echo "$ORIGINAL_INPUT" | jq --arg cmd "$WRAPPED" '.command = $cmd')

jq -n --argjson updated "$UPDATED_INPUT" '{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow",
    "permissionDecisionReason": "cmdcrush output compaction",
    "updatedInput": $updated
  }
}'
