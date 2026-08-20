#!/usr/bin/env bash
# Dead-man's-switch for the vaping-at-home stack. Runs outside Docker so it can
# detect the case that bit us on 2026-08-19: Docker Desktop itself quit and
# took every monitoring container down with it, silently.
set -uo pipefail

STATE_FILE="/tmp/vaping-watchdog.state"
LOG_FILE="/tmp/vaping-watchdog.log"
PROM_HEALTH_URL="http://localhost:9791/-/healthy"

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') $1" >>"$LOG_FILE"
}

notify() {
    osascript -e "display notification \"$1\" with title \"vaping-at-home\" sound name \"Basso\""
}

prev_state="unknown"
[ -f "$STATE_FILE" ] && prev_state="$(cat "$STATE_FILE")"

if ! docker info >/dev/null 2>&1; then
    cur_state="docker_down"
elif ! curl -fsS --max-time 5 "$PROM_HEALTH_URL" >/dev/null 2>&1; then
    cur_state="stack_down"
else
    cur_state="up"
fi

if [ "$cur_state" != "$prev_state" ]; then
    case "$cur_state" in
        docker_down)
            log "Docker Desktop is not running"
            notify "Docker Desktop is down - monitoring stack is not running"
            ;;
        stack_down)
            log "Docker is up but Prometheus/stack is unreachable"
            notify "vaping-at-home stack is down (Docker is up, containers aren't)"
            ;;
        up)
            log "Recovered - stack is healthy"
            notify "vaping-at-home stack is back up"
            ;;
    esac
fi

echo "$cur_state" >"$STATE_FILE"
