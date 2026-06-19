BINARY        = target/release/claude-proxy-rs
PLIST         = com.claude-proxy-rs.plist
PLIST_CANARY  = com.claude-proxy-rs-canary.plist
PLIST_DEST    = $(HOME)/Library/LaunchAgents/$(PLIST)
PLIST_CANARY_DEST = $(HOME)/Library/LaunchAgents/$(PLIST_CANARY)
PYTHON_PLIST  = $(HOME)/Library/LaunchAgents/com.claude-proxy.plist
PROD_PORT     = 47000
CANARY_PORT   = 47001

.PHONY: help build dev install start stop restart status logs app-logs http-logs test \
        canary canary-stop migrate rollback smoke-test decommission

# ─────────────────────────────────────────────────────────────────────────────
help:
	@echo "claude-proxy-rs management"
	@echo ""
	@echo "  build          Build release binary"
	@echo "  dev            Run on port 47001 (foreground, hot-reload friendly)"
	@echo "  install        Build + install plist (does NOT start — see migrate/start)"
	@echo "  start          Start prod proxy on :$(PROD_PORT)"
	@echo "  stop           Stop prod proxy"
	@echo "  restart        Stop + start prod proxy"
	@echo "  status         Show which proxy is active on each port"
	@echo "  logs           Tail prod proxy logs"
	@echo "  app-logs       Tail app log (provider switches, fallback)"
	@echo "  http-logs      Tail HTTP log"
	@echo "  test           Run unit tests"
	@echo ""
	@echo "Migration workflow (run these in order):"
	@echo ""
	@echo "  canary         Build + start Rust on :$(CANARY_PORT), Python stays on :$(PROD_PORT)"
	@echo "  canary-stop    Stop canary without touching Python"
	@echo "  smoke-test     Hit /health + /dry-run on a port (PORT=47001 make smoke-test)"
	@echo "  migrate        Full cutover: canary validates, then swap to Rust on :$(PROD_PORT)"
	@echo "  rollback       Immediately restore Python to :$(PROD_PORT), stop Rust"
	@echo "  decommission   Remove Python plist after 1-week soak (irreversible)"

# ─────────────────────────────────────────────────────────────────────────────
build:
	cargo build --release

dev:
	PROXY_PORT=$(CANARY_PORT) cargo run

# Install plist to ~/Library/LaunchAgents with token substitution.
# Does NOT start the proxy — use "make migrate" or "make start" explicitly.
install: build
	@if [ -z "$$CLAUDE_CODE_OAUTH_TOKEN" ]; then \
		echo "Error: CLAUDE_CODE_OAUTH_TOKEN environment variable not set"; \
		echo "Set it with: export CLAUDE_CODE_OAUTH_TOKEN=sk-ant-oat-..."; \
		exit 1; \
	fi
	@cp $(BINARY) /usr/local/bin/claude-proxy-rs
	@sed "s|INSERT_OAUTH_TOKEN_HERE|$$CLAUDE_CODE_OAUTH_TOKEN|g" \
		$(PLIST) > $(PLIST_DEST)
	@sed "s|INSERT_OAUTH_TOKEN_HERE|$$CLAUDE_CODE_OAUTH_TOKEN|g" \
		$(PLIST_CANARY) > $(PLIST_CANARY_DEST)
	@launchctl load $(PLIST_DEST) 2>/dev/null || true
	@echo "Installed claude-proxy-rs binary and plists (proxy NOT started)"
	@echo "Next steps:"
	@echo "  make canary    — test Rust on :$(CANARY_PORT) while Python stays on :$(PROD_PORT)"
	@echo "  make migrate   — full cutover when ready"

start:
	@launchctl start com.claude-proxy-rs 2>/dev/null || \
		launchctl bootstrap gui/$$(id -u) $(PLIST_DEST)

stop:
	@launchctl stop com.claude-proxy-rs 2>/dev/null || \
		launchctl bootout gui/$$(id -u) $(PLIST_DEST) 2>/dev/null || true

restart: stop start

# ─────────────────────────────────────────────────────────────────────────────
# Status: show which proxy is on each port
status:
	@echo "=== Proxy status ==="
	@echo ""
	@printf "  :$(PROD_PORT)  "
	@if curl -sf http://localhost:$(PROD_PORT)/health > /dev/null 2>&1; then \
		IMPL=$$(curl -s http://localhost:$(PROD_PORT)/health | grep -o '"service":"[^"]*"' | cut -d'"' -f4 || echo "unknown"); \
		echo "LIVE  ($$IMPL)"; \
	else \
		echo "DOWN"; \
	fi
	@printf "  :$(CANARY_PORT)  "
	@if curl -sf http://localhost:$(CANARY_PORT)/health > /dev/null 2>&1; then \
		IMPL=$$(curl -s http://localhost:$(CANARY_PORT)/health | grep -o '"service":"[^"]*"' | cut -d'"' -f4 || echo "unknown"); \
		echo "LIVE  ($$IMPL)"; \
	else \
		echo "DOWN"; \
	fi
	@echo ""
	@echo "LaunchAgents:"
	@launchctl list | grep "claude-proxy" || echo "  (none loaded)"

logs:
	@tail -f /tmp/claude-proxy-rs.log

app-logs:
	@tail -f /tmp/claude-proxy-rs.app.log

http-logs:
	@tail -f /tmp/claude-proxy-rs.http.log

test:
	@cargo test

# ─────────────────────────────────────────────────────────────────────────────
# MIGRATION WORKFLOW
# ─────────────────────────────────────────────────────────────────────────────

# Phase 1: Start Rust canary on :47001, Python unchanged on :47000.
# To test manually: ANTHROPIC_BASE_URL=http://localhost:47001 claude
canary: build
	@if [ -z "$$CLAUDE_CODE_OAUTH_TOKEN" ]; then \
		echo "Error: CLAUDE_CODE_OAUTH_TOKEN not set"; exit 1; \
	fi
	@cp $(BINARY) /usr/local/bin/claude-proxy-rs
	@sed "s|INSERT_OAUTH_TOKEN_HERE|$$CLAUDE_CODE_OAUTH_TOKEN|g" \
		$(PLIST_CANARY) > $(PLIST_CANARY_DEST)
	@launchctl load $(PLIST_CANARY_DEST) 2>/dev/null || true
	@echo "Waiting for canary to start..."
	@for i in 1 2 3 4 5 6 7 8 9 10; do \
		sleep 2; \
		if curl -sf http://localhost:$(CANARY_PORT)/health > /dev/null 2>&1; then \
			echo "Canary healthy on :$(CANARY_PORT)"; \
			echo "Python still active on :$(PROD_PORT)"; \
			echo ""; \
			echo "Test the canary:"; \
			echo "  PORT=$(CANARY_PORT) make smoke-test"; \
			echo "  alias test-claude='ANTHROPIC_BASE_URL=http://localhost:$(CANARY_PORT) claude'"; \
			echo ""; \
			echo "When ready to cut over:  make migrate"; \
			echo "To abort canary:         make canary-stop"; \
			exit 0; \
		fi; \
		echo "  Waiting... ($$(( i*2 ))s)"; \
	done; \
	echo "Canary failed to start — check logs:"; \
	echo "  tail /tmp/claude-proxy-rs-canary.error.log"; \
	exit 1

canary-stop:
	@launchctl unload $(PLIST_CANARY_DEST) 2>/dev/null || \
		launchctl bootout gui/$$(id -u) $(PLIST_CANARY_DEST) 2>/dev/null || true
	@echo "Canary stopped. Python still running on :$(PROD_PORT)."

# Smoke test against PORT (default: CANARY_PORT). Requires CLAUDE_CODE_OAUTH_TOKEN.
# Tests: /health, /v1/messages/dry-run
PORT ?= $(CANARY_PORT)
smoke-test:
	@TARGET_PORT=$(PORT); \
	echo "=== Smoke test against :$$TARGET_PORT ==="; \
	echo ""; \
	echo "1. Health check..."; \
	if curl -sf http://localhost:$$TARGET_PORT/health > /dev/null 2>&1; then \
		echo "   PASS"; \
	else \
		echo "   FAIL — proxy not responding"; \
		exit 1; \
	fi; \
	echo ""; \
	echo "2. Dry-run (body cleaning + compression, no upstream)..."; \
	if [ -z "$$CLAUDE_CODE_OAUTH_TOKEN" ]; then \
		echo "   SKIP (CLAUDE_CODE_OAUTH_TOKEN not set)"; \
	else \
		HTTP_CODE=$$(curl -s -o /tmp/smoke-dry-run.json -w "%{http_code}" \
			-X POST http://localhost:$$TARGET_PORT/v1/messages/dry-run \
			-H "Authorization: Bearer $$CLAUDE_CODE_OAUTH_TOKEN" \
			-H "Content-Type: application/json" \
			-H "anthropic-version: 2023-06-01" \
			-d '{"model":"claude-haiku-4-5-20251001","messages":[{"role":"user","content":"Say hello"}],"max_tokens":10}' \
			2>/dev/null); \
		if [ "$$HTTP_CODE" = "200" ]; then \
			echo "   PASS (HTTP 200)"; \
			cat /tmp/smoke-dry-run.json | python3 -m json.tool 2>/dev/null || cat /tmp/smoke-dry-run.json; \
		else \
			echo "   FAIL (HTTP $$HTTP_CODE)"; \
			cat /tmp/smoke-dry-run.json; \
			exit 1; \
		fi; \
	fi; \
	echo ""; \
	echo "3. Metrics endpoint..."; \
	if curl -sf http://localhost:$$TARGET_PORT/metrics > /dev/null 2>&1; then \
		echo "   PASS"; \
	else \
		echo "   FAIL"; \
		exit 1; \
	fi; \
	echo ""; \
	echo "All smoke tests passed on :$$TARGET_PORT"

# Phase 2: Full cutover. Validates Rust on :47001, then atomically swaps to :47000.
# Python is moved to standby (plist remains installed) — rollback is always available.
#
# Cutover sequence:
#   1. Build + start canary on :47001
#   2. Run smoke tests against canary
#   3. Stop Python on :47000
#   4. Start Rust on :47000
#   5. Health check Rust on :47000
#   6. If health check fails → auto-rollback (restart Python on :47000)
migrate: build
	@if [ -z "$$CLAUDE_CODE_OAUTH_TOKEN" ]; then \
		echo "Error: CLAUDE_CODE_OAUTH_TOKEN not set"; exit 1; \
	fi
	@echo "=== claude-proxy-rs migration ==="
	@echo ""
	@echo "Step 1: Install binary and plists..."
	@cp $(BINARY) /usr/local/bin/claude-proxy-rs
	@sed "s|INSERT_OAUTH_TOKEN_HERE|$$CLAUDE_CODE_OAUTH_TOKEN|g" \
		$(PLIST) > $(PLIST_DEST)
	@sed "s|INSERT_OAUTH_TOKEN_HERE|$$CLAUDE_CODE_OAUTH_TOKEN|g" \
		$(PLIST_CANARY) > $(PLIST_CANARY_DEST)
	@launchctl load $(PLIST_DEST) 2>/dev/null || true
	@launchctl load $(PLIST_CANARY_DEST) 2>/dev/null || true
	@echo ""
	@echo "Step 2: Start canary on :$(CANARY_PORT)..."
	@launchctl start com.claude-proxy-rs-canary 2>/dev/null || true
	@CANARY_UP=0; \
	for i in 1 2 3 4 5 6 7 8 9 10; do \
		sleep 2; \
		if curl -sf http://localhost:$(CANARY_PORT)/health > /dev/null 2>&1; then \
			echo "   Canary healthy ($$(( i*2 ))s)"; \
			CANARY_UP=1; \
			break; \
		fi; \
		echo "   Waiting... ($$(( i*2 ))s)"; \
	done; \
	if [ "$$CANARY_UP" -eq 0 ]; then \
		echo "Canary failed to start — aborting. Python proxy unchanged."; \
		echo "Check: tail /tmp/claude-proxy-rs-canary.error.log"; \
		launchctl unload $(PLIST_CANARY_DEST) 2>/dev/null || true; \
		exit 1; \
	fi
	@echo ""
	@echo "Step 3: Smoke test canary on :$(CANARY_PORT)..."
	@$(MAKE) --no-print-directory smoke-test PORT=$(CANARY_PORT) || { \
		echo "Smoke test failed — aborting. Python proxy unchanged."; \
		launchctl unload $(PLIST_CANARY_DEST) 2>/dev/null || true; \
		exit 1; \
	}
	@echo ""
	@echo "Step 4: Stop canary..."
	@launchctl stop com.claude-proxy-rs-canary 2>/dev/null || true
	@launchctl unload $(PLIST_CANARY_DEST) 2>/dev/null || true
	@echo ""
	@echo "Step 5: Stop Python proxy on :$(PROD_PORT)..."
	@if [ -f "$(PYTHON_PLIST)" ]; then \
		launchctl unload $(PYTHON_PLIST) 2>/dev/null || \
		launchctl bootout gui/$$(id -u) $(PYTHON_PLIST) 2>/dev/null || true; \
		echo "   Python proxy stopped"; \
	else \
		echo "   Python plist not found at $(PYTHON_PLIST) — skipping"; \
	fi
	@sleep 1
	@echo ""
	@echo "Step 6: Start Rust proxy on :$(PROD_PORT)..."
	@launchctl start com.claude-proxy-rs 2>/dev/null || \
		launchctl bootstrap gui/$$(id -u) $(PLIST_DEST) 2>/dev/null || true
	@RUST_UP=0; \
	for i in 1 2 3 4 5 6 7 8 9 10; do \
		sleep 2; \
		if curl -sf http://localhost:$(PROD_PORT)/health > /dev/null 2>&1; then \
			echo "   Rust proxy healthy ($$(( i*2 ))s)"; \
			RUST_UP=1; \
			break; \
		fi; \
		echo "   Waiting... ($$(( i*2 ))s)"; \
	done; \
	if [ "$$RUST_UP" -eq 0 ]; then \
		echo ""; \
		echo "Rust proxy failed to start — AUTO-ROLLBACK"; \
		$(MAKE) --no-print-directory rollback; \
		exit 1; \
	fi
	@echo ""
	@echo "Migration complete."
	@echo ""
	@echo "Python proxy is installed but stopped. Rollback available for 1 week:"
	@echo "  make rollback"
	@echo ""
	@echo "After 1-week soak, permanently decommission Python:"
	@echo "  make decommission"

# Rollback: stop Rust, restart Python on :47000. Fast path — < 5 seconds.
rollback:
	@echo "=== ROLLBACK: restoring Python proxy ==="
	@echo ""
	@echo "Stopping Rust proxy..."
	@launchctl stop com.claude-proxy-rs 2>/dev/null || true
	@launchctl unload $(PLIST_CANARY_DEST) 2>/dev/null || true
	@echo ""
	@if [ -f "$(PYTHON_PLIST)" ]; then \
		echo "Starting Python proxy on :$(PROD_PORT)..."; \
		launchctl load $(PYTHON_PLIST) 2>/dev/null || true; \
		launchctl start com.claude-proxy 2>/dev/null || true; \
		for i in 1 2 3 4 5; do \
			sleep 2; \
			if curl -sf http://localhost:$(PROD_PORT)/health > /dev/null 2>&1; then \
				echo "Python proxy healthy — rollback complete ($$(( i*2 ))s)"; \
				exit 0; \
			fi; \
			echo "  Waiting... ($$(( i*2 ))s)"; \
		done; \
		echo "Python proxy did not become healthy in 10s."; \
		echo "Check: cd ../claude-proxy && make app-logs"; \
		exit 1; \
	else \
		echo "Python plist not found at $(PYTHON_PLIST)"; \
		echo "Manual recovery: cd stapler-scripts/claude-proxy && make install"; \
		exit 1; \
	fi

# Decommission Python proxy after 1-week soak. Irreversible.
# Only run when confident Rust proxy is stable.
decommission:
	@echo "=== DECOMMISSION Python proxy ==="
	@echo ""
	@echo "This removes the Python plist from LaunchAgents."
	@echo "Rollback will no longer be available via 'make rollback'."
	@echo ""
	@printf "Are you sure? [y/N] "; \
	read CONFIRM; \
	if [ "$$CONFIRM" != "y" ] && [ "$$CONFIRM" != "Y" ]; then \
		echo "Aborted."; \
		exit 0; \
	fi
	@if [ -f "$(PYTHON_PLIST)" ]; then \
		launchctl unload $(PYTHON_PLIST) 2>/dev/null || true; \
		launchctl bootout gui/$$(id -u) $(PYTHON_PLIST) 2>/dev/null || true; \
		rm -f $(PYTHON_PLIST); \
		echo "Python proxy decommissioned."; \
	else \
		echo "Python plist already removed."; \
	fi

.DEFAULT_GOAL := help
