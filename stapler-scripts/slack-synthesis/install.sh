#!/bin/zsh
# Idempotent installer for the daily Slack -> Logseq synthesis launchd agent.
# Re-run any time after editing run.sh or the plist; it re-loads cleanly.
#
# Repeatable pattern for other skill-based crons: copy this directory, change LABEL,
# the plist's ProgramArguments slash-command, and the schedule.
set -euo pipefail

SCRIPT_DIR="${0:A:h}"
LABEL="com.tstapler.slack-synthesis"
DEST="$HOME/Library/LaunchAgents/$LABEL.plist"
LOG="$HOME/Library/Logs/slack-synthesis.log"
DOMAIN="gui/$(id -u)"

mkdir -p "$HOME/Library/LaunchAgents" "$HOME/Library/Logs"
chmod +x "$SCRIPT_DIR/run.sh"

# Render the plist with this machine's paths.
sed -e "s|__RUN_SH__|$SCRIPT_DIR/run.sh|g" \
    -e "s|__LOG__|$LOG|g" \
    "$SCRIPT_DIR/$LABEL.plist" > "$DEST"

# Reload idempotently (bootout is a no-op the first time).
launchctl bootout "$DOMAIN/$LABEL" 2>/dev/null || true
launchctl bootstrap "$DOMAIN" "$DEST"
launchctl enable "$DOMAIN/$LABEL"

echo "Installed $LABEL"
echo "  plist : $DEST"
echo "  runs  : 09:10 daily -> claude /knowledge:slack-daily-synthesis --yesterday"
echo "  graph : \$LOGSEQ_PATH (default ~/Documents/notes)"
echo "  log   : $LOG"
echo
echo "Run now : launchctl kickstart -k $DOMAIN/$LABEL"
echo "Status  : launchctl print $DOMAIN/$LABEL | head"
echo "Disable : launchctl bootout $DOMAIN/$LABEL"
