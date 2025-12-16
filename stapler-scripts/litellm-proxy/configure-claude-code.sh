#!/bin/bash
# Configure Claude Code to use the LiteLLM proxy
# This script modifies Claude Code's settings.json directly

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# Use main proxy endpoint which routes to AWS Bedrock
# The custom_auth accepts OAuth tokens (sk-ant-oat*) for proxy authentication
# but the actual LLM calls go to Bedrock using AWS SSO credentials
PROXY_URL="http://localhost:47000"
CLAUDE_SETTINGS="${HOME}/.claude/settings.json"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Load environment
load_env() {
    if [ -f "${SCRIPT_DIR}/.env" ]; then
        source "${SCRIPT_DIR}/.env"
    fi
}

# Check if jq is available
check_jq() {
    if ! command -v jq &>/dev/null; then
        log_error "jq is required but not installed. Install with: brew install jq"
        exit 1
    fi
}

# Check if proxy config already exists in settings.json
check_existing_config() {
    if [ -f "$CLAUDE_SETTINGS" ]; then
        if jq -e '.env.ANTHROPIC_BASE_URL' "$CLAUDE_SETTINGS" &>/dev/null; then
            return 0
        fi
    fi
    return 1
}

# Add proxy config to Claude settings.json
add_to_settings() {
    check_jq

    log_info "Adding proxy configuration to $CLAUDE_SETTINGS"

    # Backup settings
    if [ -f "$CLAUDE_SETTINGS" ]; then
        cp "$CLAUDE_SETTINGS" "${CLAUDE_SETTINGS}.backup.$(date +%Y%m%d%H%M%S)"
    fi

    # Create or update settings with env.ANTHROPIC_BASE_URL
    if [ -f "$CLAUDE_SETTINGS" ]; then
        # Add env object with ANTHROPIC_BASE_URL
        local tmp=$(mktemp)
        jq --arg url "$PROXY_URL" '.env = (.env // {}) | .env.ANTHROPIC_BASE_URL = $url' "$CLAUDE_SETTINGS" > "$tmp"
        mv "$tmp" "$CLAUDE_SETTINGS"
    else
        # Create new settings file
        mkdir -p "$(dirname "$CLAUDE_SETTINGS")"
        echo "{\"env\": {\"ANTHROPIC_BASE_URL\": \"$PROXY_URL\"}}" | jq '.' > "$CLAUDE_SETTINGS"
    fi

    log_info "Configuration added successfully!"
}

# Remove proxy config from Claude settings.json
remove_from_settings() {
    check_jq

    if [ ! -f "$CLAUDE_SETTINGS" ]; then
        log_warn "Settings file not found: $CLAUDE_SETTINGS"
        return
    fi

    log_info "Removing proxy configuration from $CLAUDE_SETTINGS"

    # Backup settings
    cp "$CLAUDE_SETTINGS" "${CLAUDE_SETTINGS}.backup.$(date +%Y%m%d%H%M%S)"

    # Remove ANTHROPIC_BASE_URL from env
    local tmp=$(mktemp)
    jq 'del(.env.ANTHROPIC_BASE_URL) | if .env == {} then del(.env) else . end' "$CLAUDE_SETTINGS" > "$tmp"
    mv "$tmp" "$CLAUDE_SETTINGS"

    log_info "Configuration removed."
}

# Show current config
show_config() {
    echo "LiteLLM Proxy Claude Code Configuration (Bedrock Mode)"
    echo "======================================================="
    echo ""
    echo "Settings file: ${CLAUDE_SETTINGS}"
    echo "Proxy URL: ${PROXY_URL}"
    echo ""

    if check_existing_config; then
        echo "Status: CONFIGURED"
        echo ""
        echo "Current env settings in settings.json:"
        jq '.env // {}' "$CLAUDE_SETTINGS" 2>/dev/null || echo "  (none)"
    else
        echo "Status: NOT CONFIGURED"
    fi
    echo ""
    echo "How it works:"
    echo "  1. Claude Code sends requests to ${PROXY_URL}/v1/messages"
    echo "  2. LiteLLM routes to AWS Bedrock using your SSO credentials"
    echo "  3. OAuth token authenticates to proxy, Bedrock uses AWS credentials"
    echo ""
    echo "Prerequisites:"
    echo "  - AWS SSO login: aws-sso-util login"
    echo "  - Valid AWS profile with Bedrock access"
    echo ""
    echo "Commands:"
    echo "  ./configure-claude-code.sh install  - Add proxy to settings.json"
    echo "  ./configure-claude-code.sh remove   - Remove proxy from settings.json"
    echo "  ./configure-claude-code.sh test     - Test proxy connection"
}

# Test proxy connection
test_proxy() {
    log_info "Testing proxy connection..."

    local base_url="http://localhost:47000"

    # Health check (may return 401 since we disabled health checks)
    local health_response=$(curl -s -o /dev/null -w "%{http_code}" "${base_url}/health" 2>&1)
    if [ "$health_response" = "200" ] || [ "$health_response" = "401" ]; then
        log_info "Proxy is running (HTTP $health_response)"
    else
        log_warn "Proxy is not responding. Start it with: make start"
        return 1
    fi

    log_info "Testing Bedrock connection with a simple request..."
    # Test actual model call (use a fake OAuth token for auth)
    local response=$(curl -s "${base_url}/v1/chat/completions" \
        -X POST \
        -H "Content-Type: application/json" \
        -H "x-api-key: sk-ant-oat-test" \
        -d '{"model":"claude-haiku","messages":[{"role":"user","content":"hi"}],"max_tokens":5}' 2>&1)

    if echo "$response" | grep -q '"choices"'; then
        log_info "Bedrock connection successful!"
        echo ""
        echo "Model response received. Proxy is working correctly."
        echo ""
        echo "To use Claude Code with the proxy:"
        echo "  ANTHROPIC_BASE_URL=${PROXY_URL} claude"
    else
        log_warn "Bedrock test failed:"
        echo "$response"
        return 1
    fi
}

# Main
main() {
    local action="${1:-install}"

    case "$action" in
        install)
            load_env

            if check_existing_config; then
                log_warn "Configuration already exists in $CLAUDE_SETTINGS"
                echo "Use '$0 remove' to remove it first, or '$0 show' to view current config"
                exit 0
            fi

            add_to_settings

            echo ""
            echo -e "${BLUE}Configuration complete!${NC}"
            echo ""
            echo "Claude Code will now use the proxy at ${PROXY_URL}"
            echo ""
            echo "Start the proxy and use Claude Code:"
            echo "  make start"
            echo "  claude"
            ;;

        remove)
            remove_from_settings
            log_info "Removed proxy configuration from Claude settings"
            ;;

        show)
            load_env
            show_config
            ;;

        test)
            load_env
            test_proxy
            ;;

        *)
            echo "Configure Claude Code to use LiteLLM Proxy (Bedrock Mode)"
            echo ""
            echo "Usage: $0 {install|remove|show|test}"
            echo ""
            echo "  install - Add proxy config to Claude settings.json"
            echo "  remove  - Remove proxy config from Claude settings.json"
            echo "  show    - Show current configuration"
            echo "  test    - Test proxy connection"
            exit 1
            ;;
    esac
}

main "$@"
