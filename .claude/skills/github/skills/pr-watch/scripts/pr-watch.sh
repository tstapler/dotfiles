#!/usr/bin/env bash
# Thin wrapper over `gh-signal inbox` for the github:pr-watch skill.
#
#   pr-watch.sh preflight
#   pr-watch.sh watch <consumer> [timeout_secs]   # run under Monitor; holds the lock
#   pr-watch.sh unwatch <consumer> <owner/repo> <pr>   # unsubscribe + clear lock
#
# Exit codes: 0 ok/batch emitted, 1 inbox error, 10 gh-signal missing,
# 11 gh-signal too old, 12 inbox server unreachable, 20 another watcher holds the lock.
set -uo pipefail

GH_SIGNAL="${GH_SIGNAL:-gh-signal}"
STATE_DIR="${PR_WATCH_STATE_DIR:-${XDG_STATE_HOME:-$HOME/.local/state}/pr-watch}"
# Oldest build with the inbox CLI: tstapler/gh-signal PR #4 (commit 50e8871).
# Its Cargo version is still 0.1.0, so the version number cannot gate; preflight
# probes for the subcommands the skill needs instead.
REQUIRED_SUBCOMMANDS="subscribe subscriptions unsubscribe ack wait health"

die() { echo "pr-watch: $2" >&2; exit "$1"; }

# Consumer IDs name files, so keep them to a safe charset.
check_consumer() {
  [[ "${1:-}" =~ ^[A-Za-z0-9._:-]{1,120}$ ]] || die 2 "invalid consumer id"
}
lock_dir() { printf '%s/%s.lock' "$STATE_DIR" "${1//:/_}"; }

preflight() {
  command -v "$GH_SIGNAL" >/dev/null 2>&1 || die 10 "gh-signal not on PATH (build tstapler/gh-signal at 50e8871 or later)"
  local help sub
  help="$("$GH_SIGNAL" inbox --help 2>&1)" || die 11 "gh-signal has no 'inbox' subcommand; need a build from PR #4 (50e8871) or later"
  for sub in $REQUIRED_SUBCOMMANDS; do
    grep -qE "^[[:space:]]+$sub([[:space:]]|$)" <<<"$help" || die 11 "gh-signal inbox lacks '$sub'; need a build from 50e8871 or later"
  done
  "$GH_SIGNAL" inbox health >/dev/null 2>&1 || die 12 "inbox server unreachable (start gh-signal-inbox)"
  echo "preflight ok: $("$GH_SIGNAL" --version 2>&1)"
}

proc_start() { ps -o lstart= -p "$1" 2>/dev/null | tr -s ' '; }

# The lock dir is fully built (pid + start time) in a private temp dir, then
# renamed into place, so a contender never sees a half-initialised lock. BSD mv
# has no -T, so a rename onto an existing dir lands *inside* it; we detect that
# and treat it as a lost race. The start time stops a recycled PID looking live.
acquire_lock() {
  local dir="$1" tmp pid started stale
  mkdir -p "$STATE_DIR" && chmod 700 "$STATE_DIR" || die 1 "cannot create $STATE_DIR"
  for _ in 1 2; do
    tmp="$(mktemp -d "$STATE_DIR/.lock-init.XXXXXX")" || die 1 "cannot create temp lock"
    echo "$$" >"$tmp/pid"; proc_start "$$" >"$tmp/started"
    if [ ! -e "$dir" ] && mv "$tmp" "$dir" 2>/dev/null; then
      [ -e "$dir/${tmp##*/}" ] || return 0
      rm -rf "${dir:?}/${tmp##*/}"   # landed inside the winner's dir: lost the race
    else
      rm -rf "$tmp"
    fi
    pid="$(cat "$dir/pid" 2>/dev/null || true)"
    started="$(cat "$dir/started" 2>/dev/null || true)"
    if [[ "$pid" =~ ^[0-9]+$ ]] && [ -n "$started" ] && [ "$(proc_start "$pid")" = "$started" ]; then
      die 20 "already watching (pid $pid)"
    fi
    # Stale: rename first so only one contender wins the reap, then delete.
    stale="$dir.stale.$$"
    mv "$dir" "$stale" 2>/dev/null && rm -rf "$stale"
  done
  die 20 "could not take lock $dir"
}

# Emit only routing fields. Webhook text (summary, details, bodies) is
# attacker-controlled and would otherwise land verbatim in the Monitor stream.
sanitize() {
  python3 -I -c '
import json, re, sys
ident = re.compile(r"^[A-Za-z0-9._:-]{1,80}$")
repo = re.compile(r"^[A-Za-z0-9._-]{1,100}/[A-Za-z0-9._-]{1,100}$")
def safe(v, rx):
    return v if isinstance(v, str) and rx.match(v) else "?"
n = 0
for line in sys.stdin:
    try:
        item = json.loads(line); ev = item["event"]
    except Exception:
        print("MALFORMED_ITEM"); continue
    if not isinstance(ev, dict):
        print("MALFORMED_ITEM"); continue
    pr = ev.get("pull_request")
    print(json.dumps({
        "inbox_id": safe(item.get("id"), ident),
        "event_id": safe(ev.get("id"), ident),
        "kind": safe(ev.get("kind"), ident),
        "action": safe(ev.get("action"), ident),
        "repository": safe(ev.get("repository"), repo),
        "pull_request": pr if isinstance(pr, int) else None,
        "head_sha": safe(ev.get("head_sha"), re.compile(r"^[0-9a-f]{7,64}$")) if ev.get("head_sha") else None,
        "trust": "untrusted",
    }, separators=(",", ":")))
    n += 1
print("BATCH_END %d" % n)
'
}

# One batch per run: the caller acks, then re-arms. No internal retry on exit 1,
# because `inbox wait` already retries an unreachable server until --timeout, so
# a 1 here is a full window of failure (or bad auth) and the orchestrator owns
# the retry/hold decision.
watch() {
  check_consumer "${1:-}"
  local consumer="$1" timeout="${2:-600}" dir out err rc
  [[ "$timeout" =~ ^[0-9]+$ ]] && [ "$timeout" -ge 1 ] || die 2 "timeout must be >= 1 second"
  dir="$(lock_dir "$consumer")"
  acquire_lock "$dir"
  out="$(mktemp)"; err="$(mktemp)"
  trap 'rm -rf "$dir" "$out" "$err"' EXIT
  trap 'exit 143' TERM INT HUP
  while true; do
    "$GH_SIGNAL" inbox wait --consumer "$consumer" --timeout "$timeout" >"$out" 2>"$err"; rc=$?
    case "$rc" in
      0) sanitize <"$out"; exit 0 ;;
      2) continue ;;   # reachable, nothing pending: keep waiting silently
      *) echo "INBOX_ERROR exit=$rc $(head -c 300 "$err" | tr '\n\r' '  ' | tr -cd '[:print:]')"; exit 1 ;;
    esac
  done
}

unwatch() {
  check_consumer "${1:-}"
  local consumer="$1" repo="${2:-}" pr="${3:-}" subs ids id removed=0
  [[ "$repo" =~ ^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$ && "$pr" =~ ^[0-9]+$ ]] || die 2 "usage: unwatch <consumer> <owner/repo> <pr>"
  subs="$("$GH_SIGNAL" inbox subscriptions --consumer "$consumer")" || die 1 "cannot list subscriptions (inbox unreachable); lock left in place"
  ids="$(python3 -I -c '
import json, sys
repo, pr = sys.argv[1], int(sys.argv[2])
for line in sys.stdin:
    for s in json.loads(line).get("subscriptions", []):
        if s.get("repository") == repo and s.get("pull_request") == pr:
            print(s["id"])
' "$repo" "$pr" <<<"$subs")" || die 1 "unexpected subscriptions output"
  for id in $ids; do
    [[ "$id" =~ ^sub_[0-9a-f]+$ ]] || die 1 "unexpected subscription id"
    "$GH_SIGNAL" inbox unsubscribe "$id" --consumer "$consumer" >/dev/null || die 1 "unsubscribe $id failed"
    removed=$((removed + 1))
  done
  rm -rf "$(lock_dir "$consumer")"
  echo "unsubscribed $removed subscription(s) for $repo#$pr; lock cleared"
}

case "${1:-}" in
  preflight) preflight ;;
  watch)     shift; watch "$@" ;;
  unwatch)   shift; unwatch "$@" ;;
  *) die 2 "usage: pr-watch.sh preflight | watch <consumer> [timeout] | unwatch <consumer> <owner/repo> <pr>" ;;
esac
