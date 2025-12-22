# Claude Proxy Makefile

.PHONY: help install uninstall start stop restart status logs error-logs clean deps update-token

help:
	@echo "Claude Proxy Management Commands:"
	@echo "  make install       - Install and start proxy as LaunchAgent"
	@echo "  make uninstall     - Stop and remove proxy LaunchAgent"
	@echo "  make start         - Start the proxy"
	@echo "  make stop          - Stop the proxy"
	@echo "  make restart       - Restart the proxy"
	@echo "  make status        - Check proxy status"
	@echo "  make logs          - View proxy logs"
	@echo "  make error-logs    - View error logs"
	@echo "  make clean         - Clean up logs and temp files"
	@echo "  make deps          - Install/update dependencies"
	@echo "  make update-token  - Update OAuth token in plist"
	@echo "  make dev           - Run proxy in development mode (foreground)"

# Install proxy as LaunchAgent
install: deps
	@echo "Installing Claude Proxy as LaunchAgent..."
	@if [ -z "$$CLAUDE_CODE_OAUTH_TOKEN" ]; then \
		echo "Error: CLAUDE_CODE_OAUTH_TOKEN environment variable not set"; \
		echo "Please set: export CLAUDE_CODE_OAUTH_TOKEN=sk-ant-oat-..."; \
		exit 1; \
	fi
	@sed "s|INSERT_OAUTH_TOKEN_HERE|$$CLAUDE_CODE_OAUTH_TOKEN|g" com.claude-proxy.plist > ~/Library/LaunchAgents/com.claude-proxy.plist
	@launchctl load ~/Library/LaunchAgents/com.claude-proxy.plist
	@echo "Claude Proxy installed and started"
	@echo "Proxy running at: http://localhost:47000"

# Uninstall proxy LaunchAgent
uninstall:
	@echo "Uninstalling Claude Proxy LaunchAgent..."
	@launchctl unload ~/Library/LaunchAgents/com.claude-proxy.plist 2>/dev/null || true
	@launchctl bootout gui/$$(id -u) ~/Library/LaunchAgents/com.claude-proxy.plist 2>/dev/null || true
	@rm -f ~/Library/LaunchAgents/com.claude-proxy.plist
	@echo "Claude Proxy uninstalled"

# Start the proxy
start:
	@echo "Starting Claude Proxy..."
	@launchctl load ~/Library/LaunchAgents/com.claude-proxy.plist 2>/dev/null || \
		launchctl bootstrap gui/$$(id -u) ~/Library/LaunchAgents/com.claude-proxy.plist
	@echo "Claude Proxy started"

# Stop the proxy
stop:
	@echo "Stopping Claude Proxy..."
	@launchctl unload ~/Library/LaunchAgents/com.claude-proxy.plist 2>/dev/null || \
		launchctl bootout gui/$$(id -u) ~/Library/LaunchAgents/com.claude-proxy.plist 2>/dev/null || true
	@echo "Claude Proxy stopped"

# Restart the proxy
restart: stop start
	@echo "Claude Proxy restarted"

# Check proxy status
status:
	@echo "Checking Claude Proxy status..."
	@if curl -s http://localhost:47000/health | grep -q "healthy"; then \
		echo "✅ Proxy is running and healthy"; \
		echo "Endpoint: http://localhost:47000"; \
	else \
		echo "❌ Proxy is not responding"; \
		echo "Run 'make logs' to check for errors"; \
	fi
	@echo ""
	@echo "LaunchAgent status:"
	@launchctl list | grep com.claude-proxy || echo "LaunchAgent not loaded"

# View logs
logs:
	@echo "=== Claude Proxy Logs ==="
	@tail -f /tmp/claude-proxy.log

# View error logs
error-logs:
	@echo "=== Claude Proxy Error Logs ==="
	@tail -f /tmp/claude-proxy.error.log

# Clean up logs and temp files
clean:
	@echo "Cleaning up logs and temp files..."
	@rm -f /tmp/claude-proxy.log /tmp/claude-proxy.error.log
	@echo "Cleanup complete"

# Install/update dependencies
deps:
	@echo "Installing/updating dependencies..."
	@if [ ! -d ".venv" ]; then \
		echo "Creating virtual environment..."; \
		uv venv; \
	fi
	@uv pip install -q -r requirements.txt
	@echo "Dependencies installed"

# Update OAuth token in plist
update-token:
	@if [ -z "$$CLAUDE_CODE_OAUTH_TOKEN" ]; then \
		echo "Error: CLAUDE_CODE_OAUTH_TOKEN environment variable not set"; \
		echo "Please set: export CLAUDE_CODE_OAUTH_TOKEN=sk-ant-oat-..."; \
		exit 1; \
	fi
	@echo "Updating OAuth token in LaunchAgent..."
	@sed "s|INSERT_OAUTH_TOKEN_HERE|$$CLAUDE_CODE_OAUTH_TOKEN|g" com.claude-proxy.plist > ~/Library/LaunchAgents/com.claude-proxy.plist
	@make restart
	@echo "Token updated and proxy restarted"

# Run in development mode (foreground)
dev:
	@echo "Running Claude Proxy in development mode..."
	@echo "Press Ctrl+C to stop"
	@uv run python main.py

# Test the proxy
test:
	@echo "Testing Claude Proxy..."
	@echo ""
	@echo "1. Testing health endpoint:"
	@curl -s http://localhost:47000/health | jq . || echo "Health check failed"
	@echo ""
	@echo "2. Testing with OAuth token:"
	@if [ -n "$$CLAUDE_CODE_OAUTH_TOKEN" ]; then \
		curl -X POST 'http://localhost:47000/v1/messages' \
			-H "Authorization: Bearer $$CLAUDE_CODE_OAUTH_TOKEN" \
			-H "anthropic-version: 2023-06-01" \
			-H "Content-Type: application/json" \
			-d '{"model": "claude-3-haiku-20240307", "messages": [{"role": "user", "content": "Say hello in 5 words"}], "max_tokens": 20}' \
			| jq . || echo "OAuth test failed"; \
	else \
		echo "CLAUDE_CODE_OAUTH_TOKEN not set, skipping OAuth test"; \
	fi

.DEFAULT_GOAL := help