#!/usr/bin/env bash
# Tails macOS's unified logging system (log stream) into a flat file Alloy
# (observability stack, alloy.d/macos.alloy) can tail. Needed because /private/var/log/system.log no longer receives
# DHCP/configd/networkd/powerd output on modern macOS - those subsystems
# moved to unified logging (verified: system.log has 187 lines total, only
# syslogd's own heartbeat). $1 selects which predicate/output file to use.
set -euo pipefail

# NOT /tmp - the container can't see the host's /tmp; this directory is the one
# docker-compose.macos.yml in the observability stack bind-mounts into Alloy.
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
    usb_thunderbolt)
        OUT="$LOG_DIR/usb_thunderbolt.log"
        PREDICATE='process == "kernel" AND (eventMessage CONTAINS[c] "Thunderbolt" OR eventMessage CONTAINS[c] "USB")'
        ;;
    *)
        echo "usage: $0 {dhcp|network_config|power|usb_thunderbolt}" >&2
        exit 1
        ;;
esac

exec log stream --style syslog --predicate "$PREDICATE" --info >>"$OUT"
