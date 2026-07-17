#!/usr/bin/env bash
set -euo pipefail

# e2e smoke test for MCP servers configured in ~/.claude.json. Spawns a
# fresh, scoped `claude -p` agent per server — `--strict-mcp-config` +
# `--tools ""` means each agent sees ONLY that one server's tools, so a
# pass can't be faked by falling back to a built-in tool or a different
# server. Real tool calls, real network/daemon behavior, not a mock.
#
# Usage:
#   test-mcp-servers.sh                # test every server in ~/.claude.json
#   test-mcp-servers.sh stapler-mcp    # test just the named server(s)
#   test-mcp-servers.sh -v ...         # print each agent's full JSON result

usage() {
  echo "Usage: $(basename "$0") [-v] [server...]"
  echo "  -v  verbose: print each agent's full response text"
  echo
  echo "Known servers with a real test prompt: ${!PROMPTS[*]}"
  echo "Any other server name found in ~/.claude.json gets a generic"
  echo "list-tools-and-call-one-read-only-tool prompt."
  exit 0
}

CONFIG_FILE="$HOME/.claude.json"
VERBOSE=false

# Appended to every prompt. Fuzzy grep-for-"pass"/"fail"-anywhere-in-prose
# is too fragile (the model's own prose can contain either word out of
# context) — require one single, strictly-formatted line so the parser
# below has something deterministic to match, and require it even if a
# tool call errors out, so a hung/confused agent still yields a verdict
# instead of silent prose.
RESULT_LINE_INSTRUCTION='
IMPORTANT: Whatever happens above (success, partial success, or total
failure), your LAST line of output must be exactly one of:
  RESULT: PASS
  RESULT: FAIL: <one short reason>
  RESULT: SKIP: <one short reason, e.g. missing API key>
No other line may start with "RESULT:". This line is machine-parsed.'

declare -A PROMPTS
PROMPTS[stapler-mcp]='Call stapler_list_indexed_sources first (should return quickly, even if empty — confirms the daemon starts and responds). Then call fetch_page on https://example.com and report its title. Then do a full docs-index round trip: call stapler_index_docs with url "https://example.com" and source "e2e-smoke-test", then stapler_search_docs on that source with query "example domain", then stapler_remove_indexed_source to clean it up. Note the outcome of each of these 4 calls. If BRAVE_API_KEY looks unset, skip brave_web_search and note that too rather than failing. RESULT should be PASS only if all 4 docs-index/fetch calls succeeded.'
PROMPTS[brave-search]='Call the Brave web search tool with query "rust programming language" and check whether you got at least one result with a title and URL. If it fails specifically due to a missing/invalid API key, that is a SKIP, not a FAIL.'
PROMPTS[read-website-fast]='Use the read-website tool to fetch https://example.com and check that you get back an extracted title and some content.'
PROMPTS[website-downloader]='Use the download_page tool to download https://example.com to /tmp/e2e-smoke-test-downloads (create the directory first if the tool does not do it for you) and check that a file was actually saved to disk afterward.'
PROMPTS[docs]='Call list_libraries (or the closest read-only equivalent) to confirm this docs server responds, then call search_docs (or fetch_url) with a trivial query against whatever it has indexed.'
PROMPTS[playwright]='Use browser_navigate to open https://example.com, then browser_snapshot to confirm the page loaded and has real content.'
PROMPTS[stapler-squad]='Call a read-only stapler-squad tool (e.g. list_sessions or search_sessions with an empty/trivial query) and check whether it responded without error.'

while getopts "hv" opt; do
  case "$opt" in
    v) VERBOSE=true ;;
    h) usage ;;
    *) usage ;;
  esac
done
shift $((OPTIND - 1))

if [ ! -f "$CONFIG_FILE" ]; then
  echo "ERROR: $CONFIG_FILE not found" >&2
  exit 1
fi

mapfile -t all_servers < <(python3 -c "
import json
data = json.load(open('$CONFIG_FILE'))
print('\n'.join(data.get('mcpServers', {}).keys()))
")

if [ "$#" -gt 0 ]; then
  servers=("$@")
else
  servers=("${all_servers[@]}")
fi

WORKDIR=$(mktemp -d)
trap 'rm -rf "$WORKDIR"' EXIT

echo "=== Pre-flight: claude mcp list ==="
claude mcp list 2>&1 | grep -E "✔|✗|Connected|Failed" || true
echo

declare -a summary
pass_count=0
fail_count=0
skip_count=0

for name in "${servers[@]}"; do
  echo "=== Testing '$name' ==="

  cfg_file="$WORKDIR/$name.json"
  if ! python3 -c "
import json, sys
data = json.load(open('$CONFIG_FILE'))
server = data.get('mcpServers', {}).get('$name')
if server is None:
    sys.exit(1)
json.dump({'mcpServers': {'$name': server}}, open('$cfg_file', 'w'))
"; then
    echo "SKIP: '$name' not found in $CONFIG_FILE"
    summary+=("$name: SKIP (not configured)")
    skip_count=$((skip_count + 1))
    echo
    continue
  fi

  base_prompt="${PROMPTS[$name]:-List the tools this server exposes, then call one read-only tool to confirm it actually responds.}"
  prompt="${base_prompt}
${RESULT_LINE_INSTRUCTION}"

  raw_output=$(printf '%s' "$prompt" | timeout 180 claude -p \
    --mcp-config "$cfg_file" \
    --strict-mcp-config \
    --tools "" \
    --allowedTools "mcp__${name}__*" \
    --permission-mode bypassPermissions \
    --output-format json \
    2>&1) || true

  # Always exits 0 — puts a machine-checkable ok/error marker as the FIRST
  # line of stdout instead, so this survives `set -e` regardless of
  # whether the agent's own turn ended in is_error:true (an expected,
  # legitimate outcome here, not a script bug).
  parsed=$(printf '%s' "$raw_output" | python3 -c "
import json, sys
try:
    data = json.loads(sys.stdin.read())
    marker = 'PARSE_ERROR' if data.get('is_error') else 'PARSE_OK'
    print(marker)
    print(data.get('result', ''))
except Exception as e:
    print('PARSE_ERROR')
    print(f'(unparseable agent output: {e})')
")
  parse_marker=$(printf '%s' "$parsed" | head -1)
  result_text=$(printf '%s' "$parsed" | tail -n +2)
  [ "$parse_marker" = "PARSE_OK" ] && parse_ok=0 || parse_ok=1

  if $VERBOSE; then
    echo "--- full response ---"
    echo "$result_text"
    echo "---"
  fi

  # Exactly one line is expected to start with "RESULT:" (case-insensitive,
  # allowing leading markdown bullet/bold noise like "- **RESULT:**"). Take
  # the LAST such line in case the model echoes the instruction itself
  # earlier in its reasoning/prose.
  result_line=$(printf '%s' "$result_text" | grep -iE "RESULT:" | tail -1) || true

  if [ "$parse_ok" -ne 0 ] && [ -z "$result_line" ]; then
    echo "FAIL: $name — agent errored and gave no RESULT: line"
    echo "$result_text" | head -5
    summary+=("$name: FAIL (agent error — rerun with -v for details)")
    fail_count=$((fail_count + 1))
  elif printf '%s' "$result_line" | grep -qi "RESULT:\s*FAIL"; then
    echo "FAIL: $name — $result_line"
    summary+=("$name: FAIL — $result_line")
    fail_count=$((fail_count + 1))
  elif printf '%s' "$result_line" | grep -qi "RESULT:\s*PASS"; then
    echo "PASS: $name — $result_line"
    summary+=("$name: PASS")
    pass_count=$((pass_count + 1))
  elif printf '%s' "$result_line" | grep -qi "RESULT:\s*SKIP"; then
    echo "SKIP: $name — $result_line"
    summary+=("$name: SKIP — $result_line")
    skip_count=$((skip_count + 1))
  else
    echo "UNCLEAR: $name — no RESULT: PASS/FAIL/SKIP line found, rerun with -v"
    summary+=("$name: UNCLEAR (rerun with -v)")
    fail_count=$((fail_count + 1))
  fi
  echo
done

echo "=== Summary ==="
printf '%s\n' "${summary[@]}"
echo
echo "$pass_count passed, $fail_count failed, $skip_count skipped"

[ "$fail_count" -eq 0 ]
