#!/usr/bin/env bash
# Bridges a real incompatibility between mxsdev/nvim-dap-vscode-js and
# Mason's js-debug-adapter package, found while interactively verifying the
# TS/JS DAP stretch goal (Story 5.1.2):
#
# nvim-dap-vscode-js's `start_debugger()` (lua/dap-vscode-js/utils.lua)
# spawns the debug server with NO port argument and reads its first stdout
# chunk, trims the trailing newline, and uses that ENTIRE string as "the
# port" — this matches the OLD vscode-js-debug build (`out/src/
# vsDebugServer.js`), which self-picks a random free port and prints just
# the bare port number to stdout when launched with no args.
#
# Mason's js-debug-adapter package ships a newer, differently-laid-out
# build (`js-debug/src/dapDebugServer.js`) that (a) requires an EXPLICIT
# port argument — it does not self-pick one — and (b) when given one,
# prints a full sentence ("Debug server listening at ::1:<port>") rather
# than a bare number. Passing that sentence to nvim-dap as if it were a
# port number fails outright.
#
# This wrapper: picks a random port itself, starts the real debug server
# with that port (stdout silenced, so its own "listening at" sentence never
# reaches nvim-dap's reader), polls until the port actually accepts
# connections, THEN prints only the bare port number to stdout (satisfying
# the plugin's stdout-scraping contract). Printing before confirming the
# server was actually listening was tried first and failed with
# ECONNREFUSED — nvim-dap's connection attempt raced node's own startup
# time.
#
# Wired via typescript.lua's `debugger_cmd` (which nvim-dap-vscode-js's own
# docs say "takes precedence over both node_path and debugger_path").
#
# Known limitation, accepted as-is (stretch goal, per the plan's own
# "timebox; if it fights, defer" guidance): if nvim-dap force-kills this
# wrapper (SIGKILL, which cannot be trapped), the backgrounded node child
# is orphaned rather than cleaned up. Harmless in practice — each session
# picks a fresh random port — but a long-running dev session that starts
# and force-kills many debug sessions will accumulate orphaned node
# processes over time.

set -uo pipefail

DATA_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/${NVIM_APPNAME:-nvim}"
DEBUG_SERVER="$DATA_DIR/mason/packages/js-debug-adapter/js-debug/src/dapDebugServer.js"

PORT=${1:-$(shuf -i 20000-30000 -n 1)}

# dapDebugServer.js's default host ("localhost") resolves to the IPv6
# loopback (::1) on this machine, but nvim-dap/nvim-dap-vscode-js connect
# to the IPv4 loopback (127.0.0.1) unconditionally — confirmed empirically
# ("Debug server listening at ::1:<port>" in the server's own log vs
# "Couldn't connect to 127.0.0.1:<port>: ECONNREFUSED" from the plugin).
# dapDebugServer.js takes an explicit second positional host argument
# (`Usage: dapDebugServer.js [port|socket path=8123] [host=localhost]`) —
# passing 127.0.0.1 explicitly closes the gap.
node "$DEBUG_SERVER" "$PORT" 127.0.0.1 >/dev/null 2>&1 &
NODE_PID=$!
trap 'kill "$NODE_PID" 2>/dev/null' EXIT TERM

for _ in $(seq 1 50); do
  if (: <"/dev/tcp/127.0.0.1/$PORT") 2>/dev/null; then
    break
  fi
  sleep 0.1
done

echo "$PORT"
wait "$NODE_PID"
