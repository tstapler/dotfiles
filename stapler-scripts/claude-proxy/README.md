# Claude Proxy

A simple, lightweight proxy for Claude Code that supports OAuth authentication with automatic Bedrock fallback on rate limits.

## Features

- ✅ OAuth token support (`sk-ant-oat-*`) with proper Bearer authentication
- ✅ Automatic fallback to AWS Bedrock on rate limits (429)
- ✅ Claude Code compatible (`/v1/messages` endpoint)
- ✅ Streaming support for both providers
- ✅ Model name normalization (handles Bedrock format from Claude Code)
- ✅ Simple and maintainable (~460 lines total)

## Architecture

```
Claude Code → FastAPI Proxy → Anthropic API (OAuth)
                           ↓ (on 429)
                        AWS Bedrock (Fallback)
```

## Installation

### Quick Start (Development)

1. Install dependencies with uv:
```bash
uv venv
uv pip install -r requirements.txt
```

2. Set environment variables:
```bash
export CLAUDE_CODE_OAUTH_TOKEN=sk-ant-oat-...  # Your OAuth token
export AWS_PROFILE=Sandbox.AdministratorAccess  # AWS profile for Bedrock
export AWS_REGION=us-west-2                     # AWS region
```

3. Run the proxy:
```bash
uv run python main.py
# Or use the Makefile:
make dev
```

### Production Deployment (LaunchAgent)

Deploy as a macOS LaunchAgent for automatic startup:

```bash
# Set your OAuth token
export CLAUDE_CODE_OAUTH_TOKEN=sk-ant-oat-...

# Install and start the proxy
make install

# Check status
make status

# View logs
make logs
```

### Management Commands

```bash
make start          # Start the proxy
make stop           # Stop the proxy
make restart        # Restart the proxy
make status         # Check proxy status
make logs           # View proxy logs
make error-logs     # View error logs
make uninstall      # Remove LaunchAgent
make update-token   # Update OAuth token
make test           # Run basic tests
```

## Usage with Claude Code

### Option 1: Shell Wrapper Script

Use the included wrapper script:
```bash
./claude-proxy.sh -p "Hello!"
# Or make it globally available:
ln -s $(pwd)/claude-proxy.sh /usr/local/bin/proxy-claude
proxy-claude -p "Hello!"
```

### Option 2: Shell Alias

Add this alias to your shell configuration (~/.zshrc or ~/.bashrc):
```bash
alias proxy-claude='env -u CLAUDE_CODE_USE_BEDROCK ANTHROPIC_BASE_URL=http://localhost:47000 claude'
```

Then use:
```bash
proxy-claude -p "Hello!"        # Non-interactive mode
proxy-claude                     # Interactive mode
```

## How It Works

1. **Primary Path**: OAuth token is sent to Anthropic API with proper headers
2. **Rate Limit Detection**: 429 responses trigger automatic fallback
3. **Bedrock Fallback**: Switches to AWS Bedrock using proxy's AWS credentials
4. **Cooldown Period**: 5-minute cooldown before retrying Anthropic
5. **Model Conversion**: Automatically handles Claude Code's Bedrock model format

## Endpoints

- `GET /` - Basic info about the proxy
- `GET /health` - Health check endpoint
- `POST /v1/messages` - Claude Code compatible endpoint
- `POST /chat/completions` - OpenAI compatible endpoint (for testing)

## Configuration

Environment variables:
- `CLAUDE_CODE_OAUTH_TOKEN` - OAuth token for Anthropic API
- `AWS_PROFILE` - AWS profile name (default: Sandbox.AdministratorAccess)
- `AWS_REGION` - AWS region (default: us-west-2)
- `PROXY_PORT` - Port to run on (default: 47000)
- `COOLDOWN_SECONDS` - Cooldown period for rate-limited providers (default: 300)
- `REQUEST_TIMEOUT` - Request timeout in seconds (default: 60)

## Testing

```bash
# Test OAuth with Anthropic
curl -X POST 'http://localhost:47000/v1/messages' \
  -H "Authorization: Bearer $CLAUDE_CODE_OAUTH_TOKEN" \
  -H "anthropic-version: 2023-06-01" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-3-haiku-20240307",
    "messages": [{"role": "user", "content": "Hello"}],
    "max_tokens": 10
  }'

# Test with OpenAI format
curl -X POST 'http://localhost:47000/chat/completions' \
  -H "Authorization: Bearer $CLAUDE_CODE_OAUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-3-haiku-20240307",
    "messages": [{"role": "user", "content": "Hello"}],
    "max_tokens": 10
  }'
```

## Comparison with LiteLLM

| Feature | Claude Proxy | LiteLLM |
|---------|-------------|---------|
| Lines of Code | ~460 | 5000+ |
| OAuth Support | First-class | Workaround needed |
| Fallback Logic | Simple, transparent | Complex routing system |
| Dependencies | 5 | 50+ |
| Setup Time | 2 minutes | 30+ minutes |
| Maintainability | High | Moderate |

## Adding New Providers

To add a new provider:

1. Create a new provider class in `providers/`:
```python
class NewProvider(Provider):
    async def send_message(self, body, token, auth_type, headers):
        # Implementation
```

2. Add to the fallback chain in `main.py`:
```python
fallback = FallbackHandler([anthropic, new_provider, bedrock])
```

That's it! No complex configuration or registration needed.