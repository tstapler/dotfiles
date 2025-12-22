# LiteLLM Proxy

OpenAI-compatible proxy with **automatic Claude API → Bedrock fallback** on rate limits.

**Key Feature**: Uses Claude's direct API first (faster, uses your Claude subscription), automatically falls back to AWS Bedrock when rate limited. No user interaction required.

**Runs natively** (not in Docker) to support AWS SSO browser authentication prompts.

## Ports

All services use the 47xxx range to avoid conflicts:

| Service | Port |
|---------|------|
| LiteLLM Proxy | 47000 |
| Prometheus | 47090 |
| Grafana | 47300 |

## Quick Start

```bash
# 1. Create .env from template
cp .env.template .env
# Edit .env with your API keys and AWS profile

# 2. Install everything (litellm, auto-start, SSO refresh, Claude config)
make install-all

# 3. Reload shell and start
source ~/.zshrc
make start

# 4. Verify it's working
make health
```

This single `make install-all` command:
- Installs LiteLLM via uv
- Sets up auto-start service (launchd/systemd)
- Installs SSO credential refresh (every 4 hours)
- Configures Claude Code to use the proxy

## Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Yes | Your Anthropic API key |
| `LITELLM_MASTER_KEY` | Yes | Proxy authentication key (generate with `make generate-key`) |
| `AWS_PROFILE` | Yes | AWS SSO profile name with Bedrock access |
| `AWS_REGION` | Yes | AWS region for Bedrock |

### AWS Bedrock Authentication

The proxy uses AWS SSO credentials from `~/.aws`. Ensure you have:
- AWS SSO configured (`aws configure sso`)
- `aws-sso-util` installed for credential refresh
- Bedrock model access enabled in your AWS account

## Usage

### Endpoint

```
http://localhost:47000
```

### Available Models

| Model Name | Description |
|------------|-------------|
| `claude-opus` | Latest Claude Opus (4.5) |
| `claude-sonnet` | Latest Claude Sonnet (4.5) |
| `claude-haiku` | Latest Claude Haiku (3.5) |
| `claude-opus-4-5-20251101` | Specific version |
| `claude-sonnet-4-5-20250929` | Specific version |
| `claude-3-7-sonnet-20250219` | Extended thinking |
| ... | All Claude models supported |

### Example Request

```bash
curl -X POST http://localhost:47000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
  -d '{
    "model": "claude-sonnet",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

## Claude Code Integration

### Automatic Configuration

```bash
# Add proxy config to your shell profile
make configure-claude

# Reload your shell
source ~/.zshrc  # or ~/.bashrc, ~/.config/fish/config.fish

# Use Claude Code normally - it will use the proxy
claude
```

This adds environment variables and a `claude-proxy` alias that auto-starts the proxy if needed.

### Manual Configuration

Add to your shell profile (`.zshrc` / `.bashrc`):

```bash
export ANTHROPIC_BASE_URL="http://localhost:47000"
export ANTHROPIC_API_KEY="<your-litellm-master-key>"
```

### Claude Code Commands

| Command | Description |
|---------|-------------|
| `make configure-claude` | Add proxy config to shell profile |
| `make update-claude` | Update config (after changing API key) |
| `make remove-claude` | Remove proxy config from shell |
| `make show-claude` | Show current configuration |
| `make test-claude` | Test proxy connection |

## Fallback Behavior

### Routing Priority

1. **Primary**: Claude API (Anthropic Direct) - uses your OAuth token
2. **Fallback**: AWS Bedrock - triggered automatically on rate limits (429)

### How It Works

```
Request → Claude API (OAuth token)
              ↓
         Rate limited? (429)
              ↓
         Yes → Bedrock (AWS credentials)
              ↓
         Response
```

### Configuration

The proxy automatically handles rate limits without user intervention:

| Setting | Value | Description |
|---------|-------|-------------|
| `allowed_fails` | 1 | Fallback after first rate limit |
| `cooldown_time` | 300s | Primary model cooldown (5 min) |
| `retry_policy.RateLimitError` | 0 retries | Immediate fallback on 429 |

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `CLAUDE_CODE_OAUTH_TOKEN` | No* | OAuth token for Claude API (primary) |
| `AWS_PROFILE` | Yes | AWS SSO profile for Bedrock (fallback) |
| `AWS_REGION` | Yes | AWS region (e.g., us-west-2) |

*Claude Code passes its OAuth token in requests automatically. Set `CLAUDE_CODE_OAUTH_TOKEN` only if you want to use a specific token for all requests.

### Testing Fallback

```bash
# Test the complete fallback flow
./test-proxy.sh fallback

# Test with specific OAuth token
CLAUDE_CODE_OAUTH_TOKEN="sk-ant-oat-..." ./test-proxy.sh fallback
```

## Model Management

```bash
# Show current models in config
make show-models

# Discover and update available models
make update-models
```

## Monitoring (Optional)

The monitoring stack (Prometheus + Grafana) runs in Docker while LiteLLM runs natively:

```bash
make monitoring
```

- Prometheus: http://localhost:47090 (scrapes LiteLLM on host)
- Grafana: http://localhost:47300 (admin/admin)

Stop monitoring:
```bash
make monitoring-down
```

## Auto-Start Service

### macOS (launchd)

```bash
# Install LiteLLM auto-start
make install-service

# Install AWS SSO auto-refresh (every 4 hours)
make install-sso-refresh

# Check status
make service-status
make sso-refresh-status

# Uninstall
make uninstall-service
make uninstall-sso-refresh
```

### Linux (systemd)

```bash
# Install LiteLLM auto-start
make install-service

# Install AWS SSO auto-refresh (every 4 hours)
make install-sso-refresh

# Check status
make service-status
make sso-refresh-status

# Uninstall
make uninstall-service
make uninstall-sso-refresh

# Optional: Start at boot (before login)
sudo loginctl enable-linger $USER
```

### AWS SSO Auto-Refresh

The SSO refresh service runs `aws-sso-util login --all` every 4 hours:
- If SSO session is still valid → refreshes silently in background
- If SSO session expired → opens browser for re-authentication

This keeps your Bedrock credentials fresh without manual intervention (as long as your SSO session hasn't fully expired).

## All Commands

| Command | Description |
|---------|-------------|
| `make install-all` | **Install everything** (recommended) |
| `make uninstall-all` | Remove all services and config |
| `make start` | SSO login + start proxy |
| `make up` | Start proxy (without SSO refresh) |
| `make down` | Stop proxy |
| `make restart` | Restart proxy |
| `make logs` | View logs |
| `make health` | Health check |
| `make test` | Test request |
| `make models` | List available models |
| `make monitoring` | Start with observability stack |
| `make clean` | Stop and remove volumes |
| `make info` | Show configuration info |
| `make generate-key` | Generate new master key |
| `make update-models` | Discover and update model config |
| `make show-models` | Show models in config |
| `make install-service` | Install auto-start service |
| `make uninstall-service` | Remove auto-start service |
| `make service-status` | Check service status |
| `make install-sso-refresh` | Install SSO auto-refresh (every 4h) |
| `make uninstall-sso-refresh` | Remove SSO auto-refresh |
| `make sso-refresh-status` | Check SSO refresh status |
| `make configure-claude` | Configure Claude Code |
| `make update-claude` | Update Claude Code config |
| `make remove-claude` | Remove Claude Code config |
| `make show-claude` | Show Claude Code config |
| `make test-claude` | Test Claude Code connection |
