#!/bin/zsh
# Daily Slack -> Logseq synthesis, run headless by launchd (com.tstapler.slack-synthesis).
# Safe to run by hand:  ./run.sh [--yesterday|--backfill|<mode>]
#
# Auth (ANTHROPIC_BASE_URL + apiKeyHelper) comes from ~/.claude/settings.json, not this script,
# so no secrets live here. This wrapper only supplies PATH, the graph path, and a sane cwd.
set -u

MODE="${1:---yesterday}"

# Path-agnostic graph lookup: honor an inherited LOGSEQ_PATH, else default to the current graph.
export LOGSEQ_PATH="${LOGSEQ_PATH:-$HOME/Documents/notes}"

# launchd hands us a minimal PATH; add where claude + node + brew tools live.
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

# Run from the skills workspace so the slack-interactions plugin + MCP servers load.
WORKDIR="${SLACK_SYNTH_WORKDIR:-$HOME/ws/ngp-skills}"
cd "$WORKDIR" 2>/dev/null || cd "$HOME"

LOG="$HOME/Library/Logs/slack-synthesis.log"
{
  echo "===== $(date '+%F %T') start  mode=$MODE  graph=$LOGSEQ_PATH  cwd=$PWD ====="
  # --dangerously-skip-permissions: unattended runs must never block on a permission prompt.
  claude -p "/knowledge:slack-daily-synthesis $MODE" --dangerously-skip-permissions
  rc=$?
  echo "===== $(date '+%F %T') end  rc=$rc ====="
} >>"$LOG" 2>&1
