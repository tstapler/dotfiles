#!/bin/bash
# Install/uninstall auto-start service for LiteLLM proxy
# Supports both macOS (launchd) and Linux (systemd)
# Runs LiteLLM natively (not Docker) to support AWS SSO browser prompts

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LITELLM_PORT=47000
POSTGRES_PORT=47432
DATABASE_URL="postgresql://litellm:litellm@localhost:${POSTGRES_PORT}/litellm"

# Detect OS
detect_os() {
    case "$(uname -s)" in
        Darwin*) echo "macos" ;;
        Linux*)  echo "linux" ;;
        *)       echo "unknown" ;;
    esac
}

# Find uv binary (we use uv tool run to avoid PATH conflicts)
find_uv() {
    if command -v uv &>/dev/null; then
        command -v uv
    elif [ -f "$HOME/.local/bin/uv" ]; then
        echo "$HOME/.local/bin/uv"
    elif [ -f "$HOME/.cargo/bin/uv" ]; then
        echo "$HOME/.cargo/bin/uv"
    else
        echo ""
    fi
}

OS=$(detect_os)

# Start PostgreSQL container (required for LiteLLM health checks)
start_postgres() {
    echo "Starting PostgreSQL container..."
    if command -v docker &>/dev/null; then
        cd "$SCRIPT_DIR"
        docker compose up -d postgres
        # Wait for postgres to be ready
        echo "Waiting for PostgreSQL to be ready..."
        for i in {1..30}; do
            if docker compose exec -T postgres pg_isready -U litellm &>/dev/null; then
                echo "PostgreSQL is ready."
                return 0
            fi
            sleep 1
        done
        echo "Warning: PostgreSQL may not be ready yet."
    else
        echo "Warning: Docker not found. PostgreSQL must be started manually."
        echo "Run: docker compose up -d postgres"
    fi
}

# macOS launchd functions
macos_install() {
    local plist_name="com.litellm.proxy.plist"
    local plist_dest="${HOME}/Library/LaunchAgents/${plist_name}"
    local logs_dir="${HOME}/Library/Logs"

    echo "Installing LiteLLM proxy launchd service..."

    if [ ! -f "${SCRIPT_DIR}/.env" ]; then
        echo "Error: .env file not found. Run 'make setup' first."
        exit 1
    fi

    # Start PostgreSQL container first
    start_postgres

    # Find uv binary
    local uv_path=$(find_uv)
    if [ -z "$uv_path" ]; then
        echo "Error: uv not found. Install with: curl -LsSf https://astral.sh/uv/install.sh | sh"
        exit 1
    fi

    # Load environment variables for the plist
    source "${SCRIPT_DIR}/.env"

    mkdir -p "$logs_dir"

    # Generate plist with actual paths (launchd doesn't expand $HOME or env vars)
    cat > "$plist_dest" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.litellm.proxy</string>

    <key>ProgramArguments</key>
    <array>
        <string>${uv_path}</string>
        <string>tool</string>
        <string>run</string>
        <string>litellm</string>
        <string>--config</string>
        <string>${SCRIPT_DIR}/config.yaml</string>
        <string>--port</string>
        <string>${LITELLM_PORT}</string>
        <string>--num_workers</string>
        <string>4</string>
    </array>

    <key>RunAtLoad</key>
    <true/>

    <key>KeepAlive</key>
    <true/>

    <key>WorkingDirectory</key>
    <string>${SCRIPT_DIR}</string>

    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/opt/homebrew/bin:${HOME}/.local/bin:${HOME}/.cargo/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
        <key>LITELLM_MASTER_KEY</key>
        <string>${LITELLM_MASTER_KEY}</string>
        <key>ANTHROPIC_API_KEY</key>
        <string>${ANTHROPIC_API_KEY}</string>
        <key>AWS_PROFILE</key>
        <string>$(echo "${AWS_PROFILE}" | tr -d '"')</string>
        <key>AWS_REGION</key>
        <string>$(echo "${AWS_REGION:-us-west-2}" | tr -d '"')</string>
        <key>AWS_DEFAULT_REGION</key>
        <string>$(echo "${AWS_REGION:-us-west-2}" | tr -d '"')</string>
        <key>AWS_CONFIG_FILE</key>
        <string>${HOME}/.aws/config</string>
        <key>AWS_SHARED_CREDENTIALS_FILE</key>
        <string>${HOME}/.aws/credentials</string>
        <key>HOME</key>
        <string>${HOME}</string>
        <key>DATABASE_URL</key>
        <string>${DATABASE_URL}</string>
    </dict>

    <key>StandardOutPath</key>
    <string>${logs_dir}/litellm-proxy.log</string>

    <key>StandardErrorPath</key>
    <string>${logs_dir}/litellm-proxy.error.log</string>

    <key>NetworkState</key>
    <true/>
</dict>
</plist>
EOF

    launchctl load "$plist_dest"

    echo "Service installed and loaded."
    echo "Logs: $logs_dir/litellm-proxy.log"
    echo "The proxy will now start automatically on login."
    echo ""
    echo "Note: AWS SSO credentials must be refreshed manually before service starts."
    echo "Run 'aws-sso-util login' if you get authentication errors."
}

macos_uninstall() {
    local plist_dest="${HOME}/Library/LaunchAgents/com.litellm.proxy.plist"

    echo "Uninstalling LiteLLM proxy launchd service..."
    launchctl unload "$plist_dest" 2>/dev/null || true
    rm -f "$plist_dest"
    echo "Service uninstalled."
}

macos_status() {
    if launchctl list 2>/dev/null | grep -q "com.litellm.proxy"; then
        echo "Service is loaded"
        launchctl list com.litellm.proxy 2>/dev/null || true
    else
        echo "Service is not loaded"
    fi
}

# Linux systemd functions
linux_install() {
    local service_name="litellm-proxy.service"
    local service_dest="${HOME}/.config/systemd/user/${service_name}"

    echo "Installing LiteLLM proxy systemd user service..."

    if [ ! -f "${SCRIPT_DIR}/.env" ]; then
        echo "Error: .env file not found. Run 'make setup' first."
        exit 1
    fi

    # Start PostgreSQL container first
    start_postgres

    # Find uv binary
    local uv_path=$(find_uv)
    if [ -z "$uv_path" ]; then
        echo "Error: uv not found. Install with: curl -LsSf https://astral.sh/uv/install.sh | sh"
        exit 1
    fi

    mkdir -p "${HOME}/.config/systemd/user"

    # Generate service file with actual paths
    cat > "$service_dest" <<EOF
[Unit]
Description=LiteLLM Proxy (Anthropic + Bedrock Fallback)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=${SCRIPT_DIR}
EnvironmentFile=${SCRIPT_DIR}/.env
Environment="PATH=/usr/local/bin:${HOME}/.local/bin:${HOME}/.cargo/bin:/usr/bin:/bin"
Environment="DATABASE_URL=${DATABASE_URL}"
ExecStart=${uv_path} tool run litellm --config ${SCRIPT_DIR}/config.yaml --port ${LITELLM_PORT} --num_workers 4
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
EOF

    # Reload systemd and enable service
    systemctl --user daemon-reload
    systemctl --user enable litellm-proxy.service
    systemctl --user start litellm-proxy.service

    echo "Service installed and started."
    echo "View logs: journalctl --user -u litellm-proxy.service -f"
    echo ""
    echo "The proxy will now start automatically on login."
    echo "Note: For services to start at boot (before login), run:"
    echo "  sudo loginctl enable-linger $USER"
    echo ""
    echo "Note: AWS SSO credentials must be refreshed manually before service starts."
    echo "Run 'aws-sso-util login' if you get authentication errors."
}

linux_uninstall() {
    echo "Uninstalling LiteLLM proxy systemd service..."

    systemctl --user stop litellm-proxy.service 2>/dev/null || true
    systemctl --user disable litellm-proxy.service 2>/dev/null || true
    rm -f "${HOME}/.config/systemd/user/litellm-proxy.service"
    systemctl --user daemon-reload

    echo "Service uninstalled."
}

linux_status() {
    systemctl --user status litellm-proxy.service 2>/dev/null || echo "Service not found"
}

# Main
case "$1" in
    install)
        case "$OS" in
            macos) macos_install ;;
            linux) linux_install ;;
            *) echo "Unsupported OS: $OS"; exit 1 ;;
        esac
        ;;
    uninstall)
        case "$OS" in
            macos) macos_uninstall ;;
            linux) linux_uninstall ;;
            *) echo "Unsupported OS: $OS"; exit 1 ;;
        esac
        ;;
    status)
        case "$OS" in
            macos) macos_status ;;
            linux) linux_status ;;
            *) echo "Unsupported OS: $OS"; exit 1 ;;
        esac
        ;;
    *)
        echo "LiteLLM Proxy Service Installer (Native)"
        echo "Detected OS: $OS"
        echo ""
        echo "Usage: $0 {install|uninstall|status}"
        echo ""
        echo "  install   - Install and enable auto-start service"
        echo "  uninstall - Remove auto-start service"
        echo "  status    - Check service status"
        echo ""
        echo "Note: LiteLLM runs natively (not in Docker) to support AWS SSO browser prompts."
        exit 1
        ;;
esac
