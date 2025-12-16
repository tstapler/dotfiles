# LiteLLM Proxy Configuration

## Overview

LiteLLM proxy for Claude Code with Anthropic API primary and AWS Bedrock fallback. Supports OAuth token passthrough for direct Anthropic API calls.

## Quick Start

```bash
make start          # Start proxy (refreshes SSO, starts PostgreSQL, launches LiteLLM)
make logs           # View proxy logs
make health         # Check proxy health
make status         # Check if proxy is running
make restart        # Restart proxy
make down           # Stop proxy
```

## Using with Claude Code

**Option 1: Environment variables (recommended for testing)**
```bash
./claude-proxy.sh   # Runs claude with proxy configured
```

**Option 2: Permanent configuration**
```bash
make configure-claude   # Add proxy to Claude Code settings
make remove-claude      # Remove proxy from Claude Code settings
```

## Architecture

```
Request → custom_auth.py (validates OAuth token) → oauth_passthrough.py (injects api_key) → Anthropic API
                                                                                      ↓ (on error)
                                                                                Bedrock Fallback
```

### Key Files

| File | Purpose |
|------|---------|
| `config.yaml` | Model routing, fallback configuration, callback registration |
| `custom_auth.py` | OAuth token validation (`sk-ant-oat-*`, `sk-ant-api-*`) |
| `oauth_passthrough.py` | Injects OAuth token for Anthropic API calls |
| `claude-proxy.sh` | Runs Claude Code with proxy via environment variables |

## Debugging LiteLLM

### Callback Not Being Invoked

**Symptom**: No callback logs appearing, custom handlers not executing.

**Causes and fixes**:

1. **Wrong callback format in config.yaml**
   ```yaml
   # WRONG - string format
   callbacks: oauth_passthrough.proxy_handler_instance

   # CORRECT - list format
   callbacks: [oauth_passthrough.proxy_handler_instance]
   ```

2. **PYTHONPATH not set** - Custom callback modules must be importable
   ```bash
   PYTHONPATH="/path/to/proxy/dir:$PYTHONPATH" litellm --config config.yaml
   ```
   The Makefile handles this automatically.

3. **Module instantiation** - Callback class must be instantiated at module level
   ```python
   # At end of oauth_passthrough.py
   proxy_handler_instance = OAuthPassthroughHandler()
   ```

### API Key Handling Issues

**Symptom**: OAuth token appears hashed or unavailable in callback.

**Cause**: LiteLLM hashes `UserAPIKeyAuth.api_key` for security.

**Fix**: Store raw token in metadata during custom auth:
```python
# In custom_auth.py
return UserAPIKeyAuth(
    api_key=api_key,
    user_id="oauth-user",
    team_id="oauth-team",
    metadata={"raw_token": api_key},  # Accessible in callbacks
)
```

Then retrieve in callback:
```python
# In oauth_passthrough.py
metadata = user_api_key_dict.metadata or {}
oauth_token = metadata.get("raw_token")
```

### Fallback Breaking After Token Injection

**Symptom**: Anthropic works but Bedrock fails with "Invalid API Key format".

**Cause**: Setting generic `data["api_key"]` passes to ALL providers including Bedrock.

**Workaround options**:

1. **Only inject for Anthropic models** (current approach):
   ```python
   if not is_bedrock:
       data["anthropic_api_key"] = oauth_token  # Provider-specific
   ```
   Note: LiteLLM may not honor provider-specific keys in all cases.

2. **Use passthrough endpoint** for direct Anthropic calls:
   ```yaml
   pass_through_endpoints:
     - path: "/anthropic/v1/messages"
       target: "https://api.anthropic.com/v1/messages"
       forward_headers: true
   ```

### AWS SSO Expired

**Symptom**: `The SSO session associated with this profile has expired`

**Fix**:
```bash
make sso-login   # Refresh AWS credentials
make restart     # Restart proxy with fresh credentials
```

### Claude Code Still Using Bedrock Directly

**Symptom**: Requests bypass proxy entirely, go straight to Bedrock.

**Cause**: `CLAUDE_CODE_USE_BEDROCK` environment variable forces direct Bedrock usage.

**Fix**: Unset the variable when using proxy:
```bash
env -u CLAUDE_CODE_USE_BEDROCK ANTHROPIC_BASE_URL=http://localhost:47000 claude
```

The `claude-proxy.sh` script handles this automatically.

### Debugging Callback Execution

Add debug output to callback methods:
```python
import sys
import litellm

def debug_print(msg):
    print(f"[OAuthPassthrough] {msg}", file=sys.stderr, flush=True)
    litellm.print_verbose(f"[OAuthPassthrough] {msg}")
```

View logs with `make logs` or `tail -f litellm.log`.

## Configuration Reference

### Model Naming Convention

| Pattern | Provider | Example |
|---------|----------|---------|
| `claude-*` | Anthropic (primary) | `claude-opus-4-5-20251101` |
| `*-bedrock` | Bedrock (explicit) | `claude-opus-4-5-20251101-bedrock` |

### Router Settings

```yaml
router_settings:
  num_retries: 3          # Retry count before fallback
  timeout: 120            # Request timeout (seconds)
  allowed_fails: 1        # Failures before cooldown
  cooldown_time: 60       # Cooldown period (seconds)
  retry_after: 5          # Wait between retries (seconds)
  fallbacks:
    - {"claude-opus-4-5-20251101": ["claude-opus-4-5-20251101-bedrock"]}
```

### Custom Auth Token Formats

| Prefix | Type | Description |
|--------|------|-------------|
| `sk-ant-oat-*` | OAuth token | Anthropic OAuth passthrough |
| `sk-ant-api-*` | API key | Direct Anthropic API key |

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `LITELLM_PORT` | Proxy listen port | `47000` |
| `AWS_PROFILE` | AWS SSO profile | `Sandbox.AdministratorAccess` |
| `AWS_REGION` | AWS region for Bedrock | `us-west-2` |
| `DATABASE_URL` | PostgreSQL connection | `postgresql://litellm:litellm@localhost:47432/litellm` |

## Testing

```bash
# Test with OAuth token
curl -X POST 'http://localhost:47000/chat/completions' \
  -H 'Authorization: Bearer sk-ant-oat-...' \
  -H 'Content-Type: application/json' \
  -d '{"model": "claude-haiku", "messages": [{"role": "user", "content": "ping"}]}'

# Force Bedrock (bypass Anthropic)
curl -X POST 'http://localhost:47000/chat/completions' \
  -H 'Authorization: Bearer sk-ant-oat-...' \
  -d '{"model": "claude-haiku-bedrock", ...}'

# Check which provider handled request
# Look for x-litellm-model-api-base in response headers
```

## Troubleshooting Checklist

1. **Proxy running?** `make status` or `make health`
2. **SSO valid?** `make sso-login` if expired
3. **Callbacks loading?** Check `make logs` for callback initialization
4. **PYTHONPATH set?** Automatic via Makefile, manual for direct `litellm` calls
5. **Bedrock env var?** Unset `CLAUDE_CODE_USE_BEDROCK` when using proxy
6. **Config format?** Callbacks must be list: `callbacks: [...]`
