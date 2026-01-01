"""Configuration settings for Claude Proxy."""
import os
from typing import Optional

# OAuth token for Anthropic API
CLAUDE_CODE_OAUTH_TOKEN: Optional[str] = os.environ.get("CLAUDE_CODE_OAUTH_TOKEN")

# AWS settings for Bedrock
AWS_PROFILE: str = os.environ.get("AWS_PROFILE", "Sandbox.AdministratorAccess")
AWS_REGION: str = os.environ.get("AWS_REGION", "us-west-2")

# Proxy settings
PROXY_PORT: int = int(os.environ.get("PROXY_PORT", "47000"))
COOLDOWN_SECONDS: int = int(os.environ.get("COOLDOWN_SECONDS", "300"))  # 5 minutes
REQUEST_TIMEOUT: int = int(os.environ.get("REQUEST_TIMEOUT", "60"))