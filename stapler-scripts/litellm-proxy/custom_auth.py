"""
Custom authentication for LiteLLM proxy.
Accepts Anthropic OAuth tokens (sk-ant-oat-*) as valid proxy keys.
This allows OAuth pass-through while keeping model routing and fallback.

Authentication Modes:
1. Request Token: OAuth token in Authorization header (sk-ant-oat-* or sk-ant-api-*)
2. Environment Token: Falls back to CLAUDE_CODE_OAUTH_TOKEN if no valid request token
3. Proxy Key: Accepts any non-empty key when environment token is configured

This enables:
- Direct OAuth passthrough when user provides token
- Automatic fallback to environment token for seamless operation
- Rate limit fallback to Bedrock works transparently
"""

import os
from typing import Union
from fastapi import Request
from litellm.proxy._types import UserAPIKeyAuth


def _get_env_oauth_token() -> str | None:
    """Get OAuth token from environment variable."""
    token = os.environ.get("CLAUDE_CODE_OAUTH_TOKEN", "").strip()
    if token and token.startswith("sk-ant-"):
        return token
    return None


async def user_api_key_auth(
    request: Request, api_key: str
) -> Union[UserAPIKeyAuth, str]:
    """
    Custom auth that accepts Anthropic OAuth tokens.

    Priority:
    1. Anthropic OAuth tokens (sk-ant-oat*) from request
    2. Anthropic API keys (sk-ant-api-*) from request
    3. Environment CLAUDE_CODE_OAUTH_TOKEN (when request has any non-empty key)

    This allows using Claude Code's native OAuth authentication while
    still getting LiteLLM's routing and fallback features.
    """
    # Accept Anthropic OAuth tokens (sk-ant-oat*) - various formats
    if api_key and api_key.startswith("sk-ant-oat"):
        # For OAuth, we need to tell LiteLLM to use Bearer auth
        # Store the token and headers in metadata for the callback to use
        return UserAPIKeyAuth(
            api_key=api_key,
            user_id="oauth-user",
            team_id="oauth-team",
            metadata={
                "raw_token": api_key,
                "auth_source": "request",
                "is_oauth": True,
                "headers": {
                    "Authorization": f"Bearer {api_key}",
                    "anthropic-beta": "oauth-2025-04-20"
                }
            },
        )

    # Accept Anthropic API keys (sk-ant-api-*)
    if api_key and api_key.startswith("sk-ant-api"):
        return UserAPIKeyAuth(
            api_key=api_key,
            user_id="apikey-user",
            team_id="apikey-team",
            metadata={"raw_token": api_key, "auth_source": "request"},
        )

    # If request has any key and we have environment token, use environment token
    # This enables: ANTHROPIC_API_KEY="proxy-key" with CLAUDE_CODE_OAUTH_TOKEN set
    env_token = _get_env_oauth_token()
    if api_key and env_token:
        return UserAPIKeyAuth(
            api_key=api_key,  # Use request key for logging/tracking
            user_id="env-oauth-user",
            team_id="env-oauth-team",
            metadata={"raw_token": env_token, "auth_source": "environment"},
        )

    # No valid authentication found
    env_hint = ""
    if not env_token:
        env_hint = " Set CLAUDE_CODE_OAUTH_TOKEN environment variable for automatic auth."

    raise Exception(
        f"Invalid API key. Expected Anthropic OAuth token (sk-ant-oat-*) "
        f"or API key (sk-ant-api-*). Received: {api_key[:20] if api_key else 'empty'}...{env_hint}"
    )
