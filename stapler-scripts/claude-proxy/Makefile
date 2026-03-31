# Claude Proxy Makefile

.PHONY: help install uninstall update start stop restart reload status logs app-logs http-logs clean deps update-token

help:
	@echo "Claude Proxy Management Commands:"
	@echo "  make install       - Install and start proxy as LaunchAgent"
	@echo "  make uninstall     - Stop and remove proxy LaunchAgent"
	@echo "  make update        - Update code, plist, and restart proxy"
	@echo "  make start         - Start the proxy"
	@echo "  make stop          - Stop the proxy"
	@echo "  make reload        - Gracefully reload (zero downtime, HUP signal)"
	@echo "  make restart       - Restart the proxy (with validation)"
	@echo "  make status        - Check proxy status"
	@echo "  make logs          - View access logs (uvicorn HTTP)"
	@echo "  make app-logs      - View application logs (fallback, providers)"
	@echo "  make http-logs     - View HTTP request logs (httpx)"
	@echo "  make clean         - Clean up logs and temp files"
	@echo "  make deps          - Install/update dependencies"
	@echo "  make update-token  - Update OAuth token in plist"
	@echo "  make dev           - Run proxy in development mode (foreground)"
	@echo "  install.sh         - Interactive installer for new users"

# Install proxy as LaunchAgent
install: deps
	@echo "Installing Claude Proxy as LaunchAgent..."
	@if [ -z "$$CLAUDE_CODE_OAUTH_TOKEN" ]; then \
		echo "Error: CLAUDE_CODE_OAUTH_TOKEN environment variable not set"; \
		echo "Please set: export CLAUDE_CODE_OAUTH_TOKEN=sk-ant-oat-..."; \
		exit 1; \
	fi
	@sed -e "s|INSERT_OAUTH_TOKEN_HERE|$$CLAUDE_CODE_OAUTH_TOKEN|g" -e "s|INSERT_WORKING_DIR_HERE|$(shell pwd)|g" com.claude-proxy.plist > ~/Library/LaunchAgents/com.claude-proxy.plist
	@launchctl load ~/Library/LaunchAgents/com.claude-proxy.plist
	@echo "Claude Proxy installed and started"
	@echo "Proxy running at: http://localhost:47000"

# Update proxy (refresh plist and restart)
update: deps
	@echo "Updating Claude Proxy..."
	@if [ -f ~/Library/LaunchAgents/com.claude-proxy.plist ]; then \
		echo "Stopping proxy..."; \
		launchctl unload ~/Library/LaunchAgents/com.claude-proxy.plist 2>/dev/null || true; \
	fi
	@echo "Updating plist..."
	@if [ -z "$$CLAUDE_CODE_OAUTH_TOKEN" ]; then \
		echo "Warning: CLAUDE_CODE_OAUTH_TOKEN not set, preserving existing token"; \
		/bin/cp -f com.claude-proxy.plist ~/Library/LaunchAgents/com.claude-proxy.plist; \
	else \
		sed -e "s|INSERT_OAUTH_TOKEN_HERE|$$CLAUDE_CODE_OAUTH_TOKEN|g" -e "s|INSERT_WORKING_DIR_HERE|$(shell pwd)|g" com.claude-proxy.plist > ~/Library/LaunchAgents/com.claude-proxy.plist; \
	fi
	@echo "Starting proxy with updated code..."
	@launchctl load ~/Library/LaunchAgents/com.claude-proxy.plist
	@sleep 4
	@echo ""
	@if curl -s http://localhost:47000/health | grep -q "healthy"; then \
		echo "✅ Claude Proxy updated and running"; \
	else \
		echo "⚠️  Proxy may not be running properly - check logs"; \
	fi

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

# Graceful reload (zero downtime with uvicorn multi-worker)
reload:
	@echo "Validating new code..."
	@uv run python -c "import main" || (echo "❌ Import failed, aborting reload"; exit 1)
	@uv run python -m pytest test_providers.py -q || (echo "❌ Tests failed, aborting reload"; exit 1)
	@echo "✅ Validation passed, sending HUP signal for graceful reload..."
	@MASTER_PID=$$(pgrep -f "uvicorn main:app" | head -1); \
	if [ -n "$$MASTER_PID" ]; then \
		kill -HUP $$MASTER_PID && echo "✅ Graceful reload initiated (PID: $$MASTER_PID)"; \
		sleep 3; \
		curl -sf http://localhost:47000/health > /dev/null && echo "✅ Proxy healthy after reload" || echo "⚠️  Health check failed"; \
	else \
		echo "⚠️  Could not find uvicorn master process, falling back to restart..."; \
		$(MAKE) restart; \
	fi

# Restart the proxy (with validation)
restart:
	@echo "Validating new code..."
	@uv run python -c "import main" || (echo "❌ Import failed, aborting restart"; exit 1)
	@uv run python -m pytest test_providers.py -q || (echo "❌ Tests failed, aborting restart"; exit 1)
	@echo "✅ Validation passed, restarting..."
	@$(MAKE) stop
	@echo "Clearing Python bytecode cache..."
	@rm -rf __pycache__ providers/__pycache__
	@$(MAKE) start
	@sleep 3
	@curl -sf http://localhost:47000/health > /dev/null && echo "✅ Proxy healthy after restart" || echo "⚠️  Health check failed"

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

# View access logs
logs:
	@echo "=== Claude Proxy Access Logs (uvicorn) ==="
	@tail -f /tmp/claude-proxy.log

# View application logs
app-logs:
	@echo "=== Claude Proxy Application Logs (fallback, providers) ==="
	@tail -f /tmp/claude-proxy.app.log

# View HTTP request logs
http-logs:
	@echo "=== Claude Proxy HTTP Request Logs (httpx) ==="
	@tail -f /tmp/claude-proxy.http.log

# Clean up logs and temp files
clean:
	@echo "Cleaning up logs and temp files..."
	@rm -f /tmp/claude-proxy.log /tmp/claude-proxy.app.log* /tmp/claude-proxy.http.log*
	@echo "Cleanup complete"

# Install/update dependencies
deps:
	@echo "Installing/updating dependencies..."
	@uv sync
	@echo "Dependencies installed"

# Update OAuth token in plist
update-token:
	@if [ -z "$$CLAUDE_CODE_OAUTH_TOKEN" ]; then \
		echo "Error: CLAUDE_CODE_OAUTH_TOKEN environment variable not set"; \
		echo "Please set: export CLAUDE_CODE_OAUTH_TOKEN=sk-ant-oat-..."; \
		exit 1; \
	fi
	@echo "Updating OAuth token in LaunchAgent..."
	@sed -e "s|INSERT_OAUTH_TOKEN_HERE|$$CLAUDE_CODE_OAUTH_TOKEN|g" -e "s|INSERT_WORKING_DIR_HERE|$(shell pwd)|g" com.claude-proxy.plist > ~/Library/LaunchAgents/com.claude-proxy.plist
	@make restart
	@echo "Token updated and proxy restarted"

# Run in development mode (foreground)
dev:
	@echo "Running Claude Proxy in development mode..."
	@echo "Press Ctrl+C to stop"
	@uv run python main.py

# Run unit tests
unit-test:
	@echo "Running unit tests..."
	@uv run python -m pytest test_providers.py -v

# Test the proxy (live integration test)
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