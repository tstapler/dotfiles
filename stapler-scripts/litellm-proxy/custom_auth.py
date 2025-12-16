"""
Custom authentication for LiteLLM proxy.
Accepts Anthropic OAuth tokens (sk-ant-oat-*) as valid proxy keys.
This allows OAuth pass-through while keeping model routing and fallback.
"""

from typing import Union
from fastapi import Request
from litellm.proxy._types import UserAPIKeyAuth


async def user_api_key_auth(
    request: Request, api_key: str
) -> Union[UserAPIKeyAuth, str]:
    """
    Custom auth that accepts Anthropic OAuth tokens.

    OAuth tokens start with 'sk-ant-oat-' and are passed through to Anthropic.
    This allows using Claude Code's native OAuth authentication while
    still getting LiteLLM's routing and fallback features.
    """
    # Accept Anthropic OAuth tokens (sk-ant-oat*) - various formats like sk-ant-oat-, sk-ant-oat01-, etc.
    if api_key and api_key.startswith("sk-ant-oat"):
        # Return a UserAPIKeyAuth object that allows the request
        # Store raw token in metadata since api_key gets hashed
        return UserAPIKeyAuth(
            api_key=api_key,
            user_id="oauth-user",
            team_id="oauth-team",
            metadata={"raw_token": api_key},  # Store for callback access
        )

    # Accept Anthropic API keys (sk-ant-api-*)
    if api_key and api_key.startswith("sk-ant-api"):
        return UserAPIKeyAuth(
            api_key=api_key,
            user_id="apikey-user",
            team_id="apikey-team",
            metadata={"raw_token": api_key},  # Store for callback access
        )

    # Reject other keys
    raise Exception(
        f"Invalid API key. Expected Anthropic OAuth token (sk-ant-oat-*) "
        f"or API key (sk-ant-api-*). Received: {api_key[:20]}..."
    )
