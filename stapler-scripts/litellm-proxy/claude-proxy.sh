#!/bin/bash
# Run Claude Code with LiteLLM proxy configured via environment variables
# Usage: ./claude-proxy.sh [claude args...]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LITELLM_PORT="${LITELLM_PORT:-47000}"

# Source .env if it exists
if [[ -f "$SCRIPT_DIR/.env" ]]; then
    source "$SCRIPT_DIR/.env"
fi

# Check if proxy is running
if ! curl -s "http://localhost:$LITELLM_PORT/health" >/dev/null 2>&1; then
    echo "Warning: LiteLLM proxy doesn't appear to be running on port $LITELLM_PORT"
    echo "Start it with: cd $SCRIPT_DIR && make start"
    echo ""
    read -p "Continue anyway? [y/N] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Run claude with proxy environment variables
# Unset CLAUDE_CODE_USE_BEDROCK to use standard Anthropic API through proxy
exec env \
    -u CLAUDE_CODE_USE_BEDROCK \
    ANTHROPIC_BASE_URL="http://localhost:$LITELLM_PORT" \
    claude "$@"
