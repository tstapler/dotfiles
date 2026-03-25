#!/bin/bash
set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
error() {
    echo -e "${RED}Error: $1${NC}" >&2
    exit 1
}

info() {
    echo -e "${BLUE}$1${NC}"
}

success() {
    echo -e "${GREEN}$1${NC}"
}

warn() {
    echo -e "${YELLOW}$1${NC}"
}

prompt() {
    local var_name=$1
    local prompt_text=$2
    local default_value=$3
    local is_secret=${4:-false}

    if [ -n "$default_value" ]; then
        echo -n "$prompt_text [$default_value]: "
    else
        echo -n "$prompt_text: "
    fi

    if [ "$is_secret" = true ]; then
        read -s user_input
        echo  # New line after hidden input
    else
        read user_input
    fi

    if [ -z "$user_input" ] && [ -n "$default_value" ]; then
        eval "$var_name='$default_value'"
    else
        eval "$var_name='$user_input'"
    fi
}

validate_oauth_token() {
    local token=$1
    if [[ ! $token =~ ^sk-ant-oat- ]]; then
        error "Invalid OAuth token format. Must start with 'sk-ant-oat-'"
    fi
}

# Banner
echo ""
info "╔════════════════════════════════════════╗"
info "║   Claude Proxy Interactive Installer   ║"
info "╚════════════════════════════════════════╝"
echo ""

# Check macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    error "This installer only works on macOS"
fi

# Check Homebrew
if ! command -v brew &> /dev/null; then
    error "Homebrew is not installed. Install from https://brew.sh"
fi

# Check/install uv
if ! command -v uv &> /dev/null; then
    warn "uv is not installed. Installing via Homebrew..."
    brew install uv || error "Failed to install uv"
    success "✓ uv installed"
else
    info "✓ uv already installed"
fi

# Get project directory (where this script is located)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
info "Project directory: $SCRIPT_DIR"
echo ""

# Prompt for configuration
info "=== Configuration ==="
echo ""

# OAuth token (required, secret)
prompt OAUTH_TOKEN "Claude Code OAuth token (starts with sk-ant-oat-)" "" true
validate_oauth_token "$OAUTH_TOKEN"

# AWS profile
prompt AWS_PROFILE "AWS profile name" "Sandbox.AdministratorAccess" false

# AWS region
prompt AWS_REGION "AWS region" "us-west-2" false

# Proxy port
prompt PROXY_PORT "Proxy port" "47000" false

# Worker count
CPU_COUNT=$(sysctl -n hw.ncpu)
prompt WORKERS "Number of worker processes" "$CPU_COUNT" false

echo ""
info "=== Configuration Summary ==="
echo ""
echo "  OAuth Token: sk-ant-oat-***"
echo "  AWS Profile: $AWS_PROFILE"
echo "  AWS Region: $AWS_REGION"
echo "  Proxy Port: $PROXY_PORT"
echo "  Workers: $WORKERS"
echo "  Working Dir: $SCRIPT_DIR"
echo ""

# Confirm
read -p "Proceed with installation? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    error "Installation cancelled"
fi

echo ""
info "=== Installing Dependencies ==="
cd "$SCRIPT_DIR"

info "Installing Python dependencies..."
uv sync || error "Failed to install dependencies"
success "✓ Dependencies installed"

echo ""
info "=== Configuring LaunchAgent ==="

# Create plist from template
PLIST_PATH="$HOME/Library/LaunchAgents/com.claude-proxy.plist"
info "Creating LaunchAgent plist..."

sed \
    -e "s|INSERT_OAUTH_TOKEN_HERE|$OAUTH_TOKEN|g" \
    -e "s|INSERT_WORKING_DIR_HERE|$SCRIPT_DIR|g" \
    -e "s|<string>Sandbox.AdministratorAccess</string>|<string>$AWS_PROFILE</string>|g" \
    -e "s|<string>us-west-2</string>|<string>$AWS_REGION</string>|g" \
    -e "s|<string>47000</string>|<string>$PROXY_PORT</string>|g" \
    -e "s|<string>10</string>|<string>$WORKERS</string>|g" \
    com.claude-proxy.plist > "$PLIST_PATH"

success "✓ LaunchAgent plist created"

echo ""
info "=== Starting Proxy ==="

# Unload existing if present
launchctl unload "$PLIST_PATH" 2>/dev/null || true

# Load new plist
launchctl load "$PLIST_PATH" || error "Failed to load LaunchAgent"
success "✓ LaunchAgent loaded"

# Wait for startup
info "Waiting for proxy to start..."
sleep 3

# Verify health
if curl -s "http://localhost:$PROXY_PORT/health" | grep -q "healthy"; then
    echo ""
    success "╔════════════════════════════════════════╗"
    success "║   Installation Complete! ✓             ║"
    success "╚════════════════════════════════════════╝"
    echo ""
    info "Proxy URL: http://localhost:$PROXY_PORT"
    info "Dashboard: http://localhost:$PROXY_PORT/dashboard"
    info "Health Check: http://localhost:$PROXY_PORT/health"
    echo ""
    info "Management commands:"
    echo "  make restart  - Restart proxy"
    echo "  make stop     - Stop proxy"
    echo "  make logs     - View logs"
    echo "  make status   - Check status"
    echo ""
else
    warn "⚠️  Proxy started but health check failed"
    info "Check logs: tail -f /tmp/claude-proxy.app.log"
    exit 1
fi
