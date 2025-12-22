"""Anthropic API provider implementation."""
import httpx
import json
from typing import Dict, Any, AsyncIterator, Optional
from . import Provider, RateLimitError


class AnthropicProvider(Provider):
    """Provider for Anthropic API with OAuth support."""

    def __init__(self):
        self.base_url = "https://api.anthropic.com"
        self.client = httpx.AsyncClient(timeout=60.0)

    @property
    def name(self) -> str:
        return "anthropic"

    def _build_headers(
        self,
        token: str,
        auth_type: str,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, str]:
        """Build headers with proper authentication."""
        result = headers.copy() if headers else {}

        # Add required Anthropic headers
        result["anthropic-version"] = result.get("anthropic-version", "2023-06-01")
        result["content-type"] = "application/json"

        # Set authentication based on type
        if auth_type == "oauth":
            result["Authorization"] = f"Bearer {token}"
            result["anthropic-beta"] = "oauth-2025-04-20"
        else:
            result["x-api-key"] = token

        return result

    async def send_message(
        self,
        body: Dict[str, Any],
        token: str,
        auth_type: str,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Send message to Anthropic API."""
        # Normalize model name
        if "model" in body:
            body["model"] = self.normalize_model_name(body["model"])

        headers = self._build_headers(token, auth_type, headers)

        response = await self.client.post(
            f"{self.base_url}/v1/messages",
            json=body,
            headers=headers
        )

        if response.status_code == 429:
            raise RateLimitError("Rate limit exceeded")

        if response.status_code != 200:
            error_text = response.text
            raise Exception(f"Anthropic API error ({response.status_code}): {error_text}")

        return response.json()

    async def stream_message(
        self,
        body: Dict[str, Any],
        token: str,
        auth_type: str,
        headers: Optional[Dict[str, str]] = None
    ) -> AsyncIterator[str]:
        """Stream message from Anthropic API."""
        # Enable streaming
        body = body.copy()
        body["stream"] = True

        # Normalize model name
        if "model" in body:
            body["model"] = self.normalize_model_name(body["model"])

        headers = self._build_headers(token, auth_type, headers)

        async with self.client.stream(
            "POST",
            f"{self.base_url}/v1/messages",
            json=body,
            headers=headers
        ) as response:
            if response.status_code == 429:
                raise RateLimitError("Rate limit exceeded")

            if response.status_code != 200:
                error_text = await response.aread()
                raise Exception(f"Anthropic API error ({response.status_code}): {error_text}")

            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    yield line + "\n"