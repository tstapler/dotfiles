.PHONY: up down restart logs status health test monitoring clean generate-key sso-login start update-models install-service configure-claude update-claude remove-claude show-claude test-claude install-litellm install-sso-refresh uninstall-sso-refresh sso-refresh-status install-all uninstall-all

SCRIPT_DIR := $(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))
LITELLM_PORT := 47000
POSTGRES_PORT := 47432
DATABASE_URL := postgresql://litellm:litellm@localhost:$(POSTGRES_PORT)/litellm
LITELLM_PID_FILE := $(SCRIPT_DIR)/.litellm.pid

# Load .env if it exists
ifneq (,$(wildcard $(SCRIPT_DIR)/.env))
    include $(SCRIPT_DIR)/.env
    export
endif

# Default target - start with SSO refresh
start: sso-login up
	@echo "Proxy started with fresh SSO credentials"

# Install everything: litellm, services, claude config
install-all: setup install-service install-sso-refresh configure-claude
	@echo ""
	@echo "============================================"
	@echo "Installation complete!"
	@echo "============================================"
	@echo ""
	@echo "Reload your shell to apply changes:"
	@echo "  source ~/.zshrc  # or your shell profile"
	@echo ""
	@echo "Then start the proxy:"
	@echo "  make start"
	@echo ""

# Uninstall everything
uninstall-all: uninstall-service uninstall-sso-refresh remove-claude
	@echo "All services and configurations removed."

# Refresh AWS SSO credentials
sso-login:
	aws-sso-util login

# Install LiteLLM via uv
install-litellm:
	@command -v uv >/dev/null 2>&1 || { echo "Installing uv..."; curl -LsSf https://astral.sh/uv/install.sh | sh; }
	uv tool install litellm[proxy]

# Start PostgreSQL container (required for health check disable feature)
postgres-up:
	@docker compose up -d postgres
	@echo "Waiting for PostgreSQL..."
	@for i in $$(seq 1 30); do \
		if docker compose exec -T postgres pg_isready -U litellm >/dev/null 2>&1; then \
			echo "PostgreSQL is ready."; \
			break; \
		fi; \
		sleep 1; \
	done

# Start LiteLLM proxy (native, not Docker)
# Priority: Claude API (OAuth) first, Bedrock fallback on rate limits
#
# IMPORTANT: CLAUDE_CODE_OAUTH_TOKEN is passed as ANTHROPIC_API_KEY to LiteLLM.
# This enables the built-in Anthropic authentication for primary path.
# Bedrock fallback uses AWS credentials (AWS_PROFILE/AWS_REGION).
up: postgres-up
	@if [ -f "$(LITELLM_PID_FILE)" ] && kill -0 $$(cat "$(LITELLM_PID_FILE)") 2>/dev/null; then \
		echo "LiteLLM already running (PID $$(cat $(LITELLM_PID_FILE)))"; \
	else \
		echo "Starting LiteLLM proxy on port $(LITELLM_PORT)..."; \
		AWS_PROFILE_CLEAN=$$(echo "$${AWS_PROFILE:-Sandbox.AdministratorAccess}" | tr -d '"'); \
		AWS_REGION_CLEAN=$$(echo "$${AWS_REGION:-us-west-2}" | tr -d '"'); \
		OAUTH_TOKEN="$${CLAUDE_CODE_OAUTH_TOKEN:-}"; \
		if [ -n "$$OAUTH_TOKEN" ]; then \
			echo "Using OAuth token from CLAUDE_CODE_OAUTH_TOKEN as ANTHROPIC_API_KEY"; \
		else \
			echo "No CLAUDE_CODE_OAUTH_TOKEN set - will rely on request tokens"; \
		fi; \
		DATABASE_URL=$(DATABASE_URL) \
		HOME=$$HOME \
		AWS_CONFIG_FILE=$$HOME/.aws/config \
		AWS_SHARED_CREDENTIALS_FILE=$$HOME/.aws/credentials \
		AWS_PROFILE=$$AWS_PROFILE_CLEAN \
		AWS_REGION=$$AWS_REGION_CLEAN \
		ANTHROPIC_API_KEY="$$OAUTH_TOKEN" \
		CLAUDE_CODE_OAUTH_TOKEN="$$OAUTH_TOKEN" \
		PYTHONPATH="$(SCRIPT_DIR):$$PYTHONPATH" \
		nohup uv tool run litellm --config "$(SCRIPT_DIR)/config.yaml" --host 127.0.0.1 --port $(LITELLM_PORT) --num_workers 1 --debug > "$(SCRIPT_DIR)/litellm.log" 2>&1 & \
		echo $$! > "$(LITELLM_PID_FILE)"; \
		sleep 2; \
		if kill -0 $$(cat "$(LITELLM_PID_FILE)") 2>/dev/null; then \
			echo "LiteLLM started (PID $$(cat $(LITELLM_PID_FILE)))"; \
			echo ""; \
			echo "Routing: Claude API (primary) -> Bedrock (fallback on 429)"; \
		else \
			echo "Failed to start LiteLLM. Check $(SCRIPT_DIR)/litellm.log"; \
			rm -f "$(LITELLM_PID_FILE)"; \
			exit 1; \
		fi \
	fi

# Stop the proxy
down:
	@if [ -f "$(LITELLM_PID_FILE)" ]; then \
		PID=$$(cat "$(LITELLM_PID_FILE)"); \
		if kill -0 $$PID 2>/dev/null; then \
			echo "Stopping LiteLLM (PID $$PID)..."; \
			kill $$PID; \
			rm -f "$(LITELLM_PID_FILE)"; \
			echo "LiteLLM stopped"; \
		else \
			echo "LiteLLM not running (stale PID file)"; \
			rm -f "$(LITELLM_PID_FILE)"; \
		fi \
	else \
		echo "LiteLLM not running (no PID file)"; \
	fi

# Restart the proxy
restart: down up

# View logs
logs:
	@tail -f "$(SCRIPT_DIR)/litellm.log"

# Check status
status:
	@if [ -f "$(LITELLM_PID_FILE)" ] && kill -0 $$(cat "$(LITELLM_PID_FILE)") 2>/dev/null; then \
		echo "LiteLLM running (PID $$(cat $(LITELLM_PID_FILE)))"; \
	else \
		echo "LiteLLM not running"; \
	fi

# Health check
health:
	@curl -s http://localhost:$(LITELLM_PORT)/health | jq . || echo "Proxy not responding"

# Test request
test:
	@echo "Testing proxy with a simple request..."
	@curl -s -X POST http://localhost:$(LITELLM_PORT)/v1/chat/completions \
		-H "Content-Type: application/json" \
		-H "Authorization: Bearer $${LITELLM_MASTER_KEY}" \
		-d '{"model": "claude-haiku", "messages": [{"role": "user", "content": "Say hello in one word"}], "max_tokens": 10}' | jq .

# List available models
models:
	@curl -s http://localhost:$(LITELLM_PORT)/v1/models \
		-H "Authorization: Bearer $${LITELLM_MASTER_KEY}" | jq '.data[].id'

# Start with monitoring (Prometheus + Grafana)
monitoring: up
	docker compose up -d
	@echo "LiteLLM Proxy: http://localhost:$(LITELLM_PORT)"
	@echo "Prometheus: http://localhost:47090"
	@echo "Grafana: http://localhost:47300 (admin/admin)"

# Stop monitoring stack
monitoring-down:
	docker compose down

# Stop everything including monitoring
clean: down
	docker compose down -v

# Generate a new master key
generate-key:
	@echo "New master key:"
	@openssl rand -hex 32

# Setup: Create .env from template
setup: install-litellm
	@if [ ! -f .env ]; then \
		cp .env.template .env; \
		echo "Created .env file. Please edit it with your API keys."; \
		echo "Generate a master key with: make generate-key"; \
	else \
		echo ".env already exists"; \
	fi

# Show proxy info
info:
	@echo "LiteLLM Proxy (Native)"
	@echo "====================="
	@echo "Endpoint: http://localhost:$(LITELLM_PORT)"
	@echo "Health: http://localhost:$(LITELLM_PORT)/health"
	@echo "Models: http://localhost:$(LITELLM_PORT)/v1/models"
	@echo ""
	@echo "To use with Claude Code, run:"
	@echo "  ANTHROPIC_BASE_URL=http://localhost:$(LITELLM_PORT) ANTHROPIC_API_KEY=\$${LITELLM_MASTER_KEY} claude"
	@echo ""
	@echo "Or run: make configure-claude"

# Wrapper to run claude code with proxy
claude:
	@if [ -z "$${LITELLM_MASTER_KEY}" ]; then \
		echo "Error: LITELLM_MASTER_KEY not set. Source .env first: source .env"; \
		exit 1; \
	fi
	ANTHROPIC_BASE_URL=http://localhost:$(LITELLM_PORT) ANTHROPIC_API_KEY=$${LITELLM_MASTER_KEY} claude

# Update models config from Anthropic/Bedrock
update-models:
	./update-models.sh update

# Show available models
show-models:
	./update-models.sh show

# Install auto-start service (macOS launchd / Linux systemd)
install-service:
	./install-service.sh install

# Uninstall auto-start service
uninstall-service:
	./install-service.sh uninstall

# Check service status
service-status:
	./install-service.sh status

# Configure Claude Code to use proxy
configure-claude:
	./configure-claude-code.sh install

# Update Claude Code configuration (after changing API key)
update-claude:
	./configure-claude-code.sh update

# Remove Claude Code proxy configuration
remove-claude:
	./configure-claude-code.sh remove

# Show Claude Code configuration
show-claude:
	./configure-claude-code.sh show

# Test Claude Code proxy connection
test-claude:
	./configure-claude-code.sh test

# Install AWS SSO auto-refresh service (every 4 hours)
install-sso-refresh:
	./install-sso-refresh.sh install

# Uninstall AWS SSO auto-refresh service
uninstall-sso-refresh:
	./install-sso-refresh.sh uninstall

# Check SSO refresh service status
sso-refresh-status:
	./install-sso-refresh.sh status
