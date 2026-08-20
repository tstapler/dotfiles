#!/usr/bin/env bash
# Tails macOS's unified logging system (log stream) into a flat file promtail
# can scrape. Needed because /private/var/log/system.log no longer receives
# DHCP/configd/networkd/powerd output on modern macOS - those subsystems
# moved to unified logging (verified: system.log has 187 lines total, only
# syslogd's own heartbeat). $1 selects which predicate/output file to use.
set -euo pipefail

# NOT /tmp - promtail's container mounts a named volume over its own /tmp
# (see promtail_positions in docker-compose.yml), which shadows the host's
# /tmp and would make files written there invisible to promtail.
LOG_DIR="$HOME/Library/Logs/vaping-unified-logs"
mkdir -p "$LOG_DIR"

case "$1" in
    dhcp)
        OUT="$LOG_DIR/dhcp.log"
        PREDICATE='eventMessage CONTAINS[c] "DHCP" OR eventMessage CONTAINS[c] "bootp"'
        ;;
    network_config)
        OUT="$LOG_DIR/network_config.log"
        PREDICATE='process == "configd" AND (eventMessage CONTAINS[c] "Interface" OR eventMessage CONTAINS[c] "Network" OR eventMessage CONTAINS[c] "SCNetworkReachability")'
        ;;
    power)
        OUT="$LOG_DIR/power.log"
        PREDICATE='process == "powerd" AND (eventMessage CONTAINS[c] "Sleep" OR eventMessage CONTAINS[c] "Wake" OR eventMessage CONTAINS[c] "hibernation")'
        ;;
    *)
        echo "usage: $0 {dhcp|network_config|power}" >&2
        exit 1
        ;;
esac

exec log stream --style syslog --predicate "$PREDICATE" --info >>"$OUT"
