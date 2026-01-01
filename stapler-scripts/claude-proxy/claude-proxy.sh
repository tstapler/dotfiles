#!/bin/bash
# Claude Proxy wrapper script
# Usage: ./claude-proxy.sh [claude command arguments]

# Run Claude Code with the proxy configured
exec env -u CLAUDE_CODE_USE_BEDROCK ANTHROPIC_BASE_URL=http://localhost:47000 claude "$@"