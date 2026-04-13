# Claude Proxy Makefile

.PHONY: help install uninstall update start stop restart reload status logs app-logs http-logs clean deps update-token bench bench-compare bench-watch test-instance

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
	@echo ""
	@echo "Benchmarking:"
	@echo "  make bench         - Run compression benchmark (dry-run, no API calls)"
	@echo "  make bench-compare - Compare port 47000 vs port 47001 side-by-side"
	@echo "  make bench-watch   - Live /metrics terminal dashboard"
	@echo "  make test-instance - Start a test proxy on port 47001"
	@echo ""
	@echo "Model Configuration:"
	@echo "  make validate-models    - Validate Bedrock model mappings"
	@echo "  make list-models        - List all available models (Bedrock + Anthropic)"
	@echo "  make regenerate-configs - Regenerate model config files"
	@echo ""
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

# Graceful reload (zero downtime: canary smoke test → HUP → worker cycle)
reload:
	@echo "Validating new code..."
	@uv run python -c "import main" || (echo "❌ Import failed, aborting reload"; exit 1)
	@uv run python -m pytest test_providers.py -q || (echo "❌ Tests failed, aborting reload"; exit 1)
	@echo "✅ Tests passed, starting canary on :47001..."
	@OAUTH_TOKEN=$$(if [ -n "$$CLAUDE_CODE_OAUTH_TOKEN" ]; then echo "$$CLAUDE_CODE_OAUTH_TOKEN"; else /usr/libexec/PlistBuddy -c "Print :EnvironmentVariables:CLAUDE_CODE_OAUTH_TOKEN" ~/Library/LaunchAgents/com.claude-proxy.plist 2>/dev/null; fi); \
	MASTER_PID=$$(pgrep -f "uvicorn main:app" | head -1); \
	PROXY_PORT=47001 WORKERS=1 uv run uvicorn main:app --host 127.0.0.1 --port 47001 --workers 1 --log-level warning > /tmp/claude-proxy-canary.log 2>&1 & \
	CANARY_PID=$$!; \
	echo "Canary started (PID: $$CANARY_PID)"; \
	HEALTHY=0; \
	for i in 1 2 3 4 5 6 7 8 9 10; do \
		sleep 2; \
		if curl -sf http://localhost:47001/health > /dev/null 2>&1; then \
			echo "✅ Canary healthy ($$((i*2))s)"; \
			HEALTHY=1; \
			break; \
		fi; \
		echo "  Waiting for canary... ($$((i*2))s)"; \
	done; \
	if [ "$$HEALTHY" -eq 0 ]; then \
		echo "❌ Canary failed to start - aborting, old proxy unchanged"; \
		kill $$CANARY_PID 2>/dev/null; \
		exit 1; \
	fi; \
	if [ -n "$$OAUTH_TOKEN" ]; then \
		echo "Running smoke test against canary..."; \
		SMOKE_RESULT=$$(curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:47001/v1/messages/dry-run \
			-H "Authorization: Bearer $$OAUTH_TOKEN" \
			-H "Content-Type: application/json" \
			-d '{"model":"claude-haiku-4-5-20251001","messages":[{"role":"user","content":"hello"}],"max_tokens":10}'); \
		if [ "$$SMOKE_RESULT" = "200" ]; then \
			echo "✅ Smoke test passed (HTTP $$SMOKE_RESULT)"; \
		else \
			echo "❌ Smoke test failed (HTTP $$SMOKE_RESULT) - aborting, old proxy unchanged"; \
			kill $$CANARY_PID 2>/dev/null; \
			exit 1; \
		fi; \
	else \
		echo "⚠️  No OAuth token found, skipping smoke test"; \
	fi; \
	kill $$CANARY_PID 2>/dev/null; \
	echo "Canary validated and stopped, reloading main process..."; \
	rm -rf __pycache__ providers/__pycache__; \
	if [ -n "$$MASTER_PID" ]; then \
		kill -HUP $$MASTER_PID && echo "✅ HUP sent to main process (PID: $$MASTER_PID)"; \
		for i in 1 2 3 4 5; do \
			sleep 2; \
			if curl -sf http://localhost:47000/health > /dev/null 2>&1; then \
				echo "✅ Proxy healthy after reload ($$((i*2))s)"; \
				exit 0; \
			fi; \
		done; \
		echo "⚠️  Health check failed after HUP - check logs with: make app-logs"; \
	else \
		echo "⚠️  Main process not found, falling back to hard start..."; \
		$(MAKE) start; \
		for i in 1 2 3 4 5; do \
			sleep 2; \
			if curl -sf http://localhost:47000/health > /dev/null 2>&1; then \
				echo "✅ Proxy healthy after start ($$((i*2))s)"; \
				exit 0; \
			fi; \
		done; \
	fi

# Restart the proxy (validates via canary, zero-downtime via HUP, hard restart as fallback)
restart:
	@echo "Validating new code..."
	@uv run python -c "import main" || (echo "❌ Import failed, aborting restart"; exit 1)
	@uv run python -m pytest test_providers.py -q || (echo "❌ Tests failed, aborting restart"; exit 1)
	@echo "✅ Validation passed, restarting..."
	@MASTER_PID=$$(pgrep -f "uvicorn main:app" | head -1); \
	if [ -n "$$MASTER_PID" ]; then \
		echo "Live process found — using zero-downtime reload..."; \
		$(MAKE) reload; \
	else \
		echo "No live process — starting fresh..."; \
		rm -rf __pycache__ providers/__pycache__; \
		$(MAKE) start; \
		echo "Waiting for proxy to start..."; \
		for i in 1 2 3 4 5 6 7 8 9 10; do \
			sleep 2; \
			if curl -sf http://localhost:47000/health > /dev/null 2>&1; then \
				echo "✅ Proxy healthy after restart ($$((i*2))s)"; \
				exit 0; \
			fi; \
			echo "  Waiting... ($$((i*2))s)"; \
		done; \
		echo "⚠️  Health check failed after 20s - check logs with: make app-logs"; \
	fi

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

# Benchmarking targets (no API calls needed for dry-run/watch)
bench:
	@uv run python bench.py dry-run

bench-compare:
	@uv run python bench.py compare

bench-watch:
	@uv run python bench.py watch

# Start a separate test proxy instance on port 47001
test-instance:
	@echo "Starting test proxy on port 47001..."
	@echo "Point a test agent at it: alias test-claude='env -u CLAUDE_CODE_USE_BEDROCK ANTHROPIC_BASE_URL=http://localhost:47001 claude'"
	PROXY_PORT=47001 uv run python main.py

# Model config validation and generation
validate-models:
	@echo "Validating Bedrock model mappings..."
	@python3 scripts/validate_bedrock_models.py --validate

list-models:
	@echo "=== Bedrock Models ==="
	@python3 scripts/validate_bedrock_models.py --list
	@echo "\n=== Anthropic Models ==="
	@python3 scripts/fetch_anthropic_models.py --list

regenerate-configs:
	@echo "Regenerating model configs..."
	@python3 scripts/validate_bedrock_models.py --generate
	@python3 scripts/fetch_anthropic_models.py --generate
	@echo "✅ Configs regenerated - reload proxy to apply"

.DEFAULT_GOAL := help