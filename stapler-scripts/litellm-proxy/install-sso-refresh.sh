#!/bin/bash
# Install/uninstall AWS SSO credential refresh service
# Runs aws-sso-util login periodically to keep credentials fresh
# If session is valid, refreshes silently. If expired, opens browser.

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Refresh interval in seconds (4 hours = 14400)
# SSO sessions typically last 8-12 hours, so refreshing every 4 hours keeps us ahead
REFRESH_INTERVAL=14400

# Detect OS
detect_os() {
    case "$(uname -s)" in
        Darwin*) echo "macos" ;;
        Linux*)  echo "linux" ;;
        *)       echo "unknown" ;;
    esac
}

# Find aws-sso-util
find_aws_sso_util() {
    if command -v aws-sso-util &>/dev/null; then
        command -v aws-sso-util
    elif [ -f "$HOME/.local/bin/aws-sso-util" ]; then
        echo "$HOME/.local/bin/aws-sso-util"
    else
        echo ""
    fi
}

OS=$(detect_os)

# macOS launchd functions
macos_install() {
    local plist_name="com.aws.sso-refresh.plist"
    local plist_dest="${HOME}/Library/LaunchAgents/${plist_name}"
    local logs_dir="${HOME}/Library/Logs"

    echo "Installing AWS SSO refresh launchd service..."

    local sso_util_path=$(find_aws_sso_util)
    if [ -z "$sso_util_path" ]; then
        echo "Error: aws-sso-util not found. Install with: pip install aws-sso-util"
        exit 1
    fi

    mkdir -p "$logs_dir"

    # Generate plist - runs every REFRESH_INTERVAL seconds
    cat > "$plist_dest" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.aws.sso-refresh</string>

    <key>ProgramArguments</key>
    <array>
        <string>${sso_util_path}</string>
        <string>login</string>
        <string>--all</string>
    </array>

    <key>RunAtLoad</key>
    <true/>

    <key>StartInterval</key>
    <integer>${REFRESH_INTERVAL}</integer>

    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/opt/homebrew/bin:${HOME}/.local/bin:/usr/bin:/bin</string>
        <key>HOME</key>
        <string>${HOME}</string>
    </dict>

    <key>StandardOutPath</key>
    <string>${logs_dir}/aws-sso-refresh.log</string>

    <key>StandardErrorPath</key>
    <string>${logs_dir}/aws-sso-refresh.error.log</string>
</dict>
</plist>
EOF

    launchctl load "$plist_dest"

    echo "SSO refresh service installed."
    echo "Logs: $logs_dir/aws-sso-refresh.log"
    echo ""
    echo "The service will:"
    echo "  - Run immediately on load"
    echo "  - Refresh every $(( REFRESH_INTERVAL / 3600 )) hours"
    echo "  - Open browser only if SSO session has fully expired"
}

macos_uninstall() {
    local plist_dest="${HOME}/Library/LaunchAgents/com.aws.sso-refresh.plist"

    echo "Uninstalling AWS SSO refresh service..."
    launchctl unload "$plist_dest" 2>/dev/null || true
    rm -f "$plist_dest"
    echo "Service uninstalled."
}

macos_status() {
    if launchctl list 2>/dev/null | grep -q "com.aws.sso-refresh"; then
        echo "Service is loaded"
        launchctl list com.aws.sso-refresh 2>/dev/null || true
    else
        echo "Service is not loaded"
    fi
}

# Linux systemd functions
linux_install() {
    local service_dest="${HOME}/.config/systemd/user/aws-sso-refresh.service"
    local timer_dest="${HOME}/.config/systemd/user/aws-sso-refresh.timer"

    echo "Installing AWS SSO refresh systemd service..."

    local sso_util_path=$(find_aws_sso_util)
    if [ -z "$sso_util_path" ]; then
        echo "Error: aws-sso-util not found. Install with: pip install aws-sso-util"
        exit 1
    fi

    mkdir -p "${HOME}/.config/systemd/user"

    # Service file (one-shot, triggered by timer)
    cat > "$service_dest" <<EOF
[Unit]
Description=AWS SSO Credential Refresh

[Service]
Type=oneshot
ExecStart=${sso_util_path} login --all
Environment="PATH=/usr/local/bin:${HOME}/.local/bin:/usr/bin:/bin"
EOF

    # Timer file
    cat > "$timer_dest" <<EOF
[Unit]
Description=AWS SSO Credential Refresh Timer

[Timer]
OnBootSec=1min
OnUnitActiveSec=${REFRESH_INTERVAL}s
Persistent=true

[Install]
WantedBy=timers.target
EOF

    systemctl --user daemon-reload
    systemctl --user enable aws-sso-refresh.timer
    systemctl --user start aws-sso-refresh.timer
    # Run once immediately
    systemctl --user start aws-sso-refresh.service || true

    echo "SSO refresh service installed."
    echo "View logs: journalctl --user -u aws-sso-refresh.service"
    echo ""
    echo "The service will:"
    echo "  - Run 1 minute after boot"
    echo "  - Refresh every $(( REFRESH_INTERVAL / 3600 )) hours"
    echo "  - Open browser only if SSO session has fully expired"
}

linux_uninstall() {
    echo "Uninstalling AWS SSO refresh service..."

    systemctl --user stop aws-sso-refresh.timer 2>/dev/null || true
    systemctl --user disable aws-sso-refresh.timer 2>/dev/null || true
    rm -f "${HOME}/.config/systemd/user/aws-sso-refresh.service"
    rm -f "${HOME}/.config/systemd/user/aws-sso-refresh.timer"
    systemctl --user daemon-reload

    echo "Service uninstalled."
}

linux_status() {
    echo "Timer status:"
    systemctl --user status aws-sso-refresh.timer 2>/dev/null || echo "Timer not found"
    echo ""
    echo "Last run:"
    systemctl --user status aws-sso-refresh.service 2>/dev/null || echo "Service not found"
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
        echo "AWS SSO Credential Refresh Service"
        echo "Detected OS: $OS"
        echo ""
        echo "Usage: $0 {install|uninstall|status}"
        echo ""
        echo "  install   - Install periodic SSO refresh (every 4 hours)"
        echo "  uninstall - Remove SSO refresh service"
        echo "  status    - Check service status"
        echo ""
        echo "Note: If SSO session is valid, refresh is silent."
        echo "      If expired, a browser window will open for re-auth."
        exit 1
        ;;
esac
