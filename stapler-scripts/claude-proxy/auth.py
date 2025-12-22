"""Authentication module for validating tokens."""
from typing import Tuple, Optional
from fastapi import HTTPException, Request
import config


def extract_token(request: Request) -> str:
    """Extract token from Authorization header."""
    auth_header = request.headers.get("Authorization", "")

    if auth_header.startswith("Bearer "):
        return auth_header[7:]  # Remove "Bearer " prefix

    # Check for x-api-key header as fallback
    if api_key := request.headers.get("x-api-key"):
        return api_key

    # Try environment variable as last resort
    if config.CLAUDE_CODE_OAUTH_TOKEN:
        return config.CLAUDE_CODE_OAUTH_TOKEN

    raise HTTPException(status_code=401, detail="No authentication token provided")


def validate_token(token: str) -> Tuple[str, str]:
    """
    Validate token and return (token, auth_type).

    Returns:
        Tuple of (token, auth_type) where auth_type is 'oauth' or 'api_key'
    """
    if not token:
        raise HTTPException(status_code=401, detail="Empty token")

    # OAuth tokens
    if token.startswith("sk-ant-oat"):
        return token, "oauth"

    # API keys
    if token.startswith("sk-ant-api"):
        return token, "api_key"

    # Unknown token format - assume it might be valid
    # (could be a test token or future format)
    return token, "unknown"


def get_auth_from_request(request: Request) -> Tuple[str, str]:
    """Extract and validate authentication from request."""
    token = extract_token(request)
    return validate_token(token)