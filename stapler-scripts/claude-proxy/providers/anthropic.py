"""Anthropic API provider implementation."""
import httpx
import json
import os
import diskcache
from typing import Dict, Any, AsyncIterator, Optional
from . import Provider, RateLimitError, ValidationError, ModelUnsupportedError

_model_cache = diskcache.Cache(
    os.path.expanduser("~/.cache/claude-proxy/model-cache"),
    size_limit=1 * 1024 * 1024
)
_MODEL_CACHE_TTL = 3600  # 1 hour


class AnthropicProvider(Provider):
    """Provider for Anthropic API with OAuth support."""

    def __init__(self):
        self.base_url = "https://api.anthropic.com"
        # Timeout settings for long-running requests
        # connect: 10s to establish connection
        # read: 600s (10min) to read response chunks (for long streaming responses)
        # write: 30s to write request
        # pool: 30s to acquire connection from pool
        timeout = httpx.Timeout(10.0, read=600.0, write=30.0, pool=30.0)
        self.client = httpx.AsyncClient(timeout=timeout)

    @property
    def name(self) -> str:
        return "anthropic"

    async def _get_supported_models(self, token: str, auth_type: str) -> set:
        """Fetch and cache the list of model IDs supported by the Anthropic API.

        Returns empty set on error so callers fall back to attempting the request.
        """
        import logging
        logger = logging.getLogger(__name__)
        cache_key = f"anthropic_models:{auth_type}"
        cached = _model_cache.get(cache_key)
        if cached is not None:
            return cached
        try:
            headers = self._build_headers(token, auth_type)
            response = await self.client.get(f"{self.base_url}/v1/models", headers=headers)
            if response.status_code == 200:
                model_ids = {m["id"] for m in response.json().get("data", [])}
                _model_cache.set(cache_key, model_ids, expire=_MODEL_CACHE_TTL)
                logger.debug(f"Cached {len(model_ids)} Anthropic models")
                return model_ids
            logger.warning(f"GET /v1/models returned {response.status_code} — skipping model check")
        except Exception as e:
            logger.warning(f"Could not fetch Anthropic model list: {e} — skipping model check")
        return set()

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

    def _clean_request_body(self, body: Dict[str, Any]) -> Dict[str, Any]:
        """Clean request body to remove Bedrock-specific or unsupported fields.

        Claude Code may send Bedrock-specific fields that Anthropic API doesn't support.
        This function removes those fields to prevent validation errors.

        See: https://github.com/anthropics/claude-code/issues/11678
        """
        import logging
        import json
        logger = logging.getLogger(__name__)

        body = body.copy()

        # Clean tool definitions
        if "tools" in body and isinstance(body["tools"], list):
            cleaned_tools = []
            cleaned_count = 0
            for idx, tool in enumerate(body["tools"]):
                if isinstance(tool, dict):
                    tool = tool.copy()
                    # Remove Bedrock/Claude Code specific fields that Anthropic API doesn't support
                    # See: https://github.com/anthropics/claude-code/issues/11678
                    # - custom: Claude Code-specific metadata
                    # - defer_loading: Claude Code-specific loading control
                    # - input_examples: Claude Code-specific examples
                    # - cache_control: Prompt caching only supported in messages/system, not tools
                    removed_fields = []
                    for field in ["defer_loading", "input_examples", "custom", "cache_control"]:
                        if field in tool:
                            # Log what we're removing for debugging
                            if field in ["custom", "cache_control"]:
                                logger.info(f"Removing '{field}' from tool[{idx}]: {json.dumps(tool[field], indent=2)}")
                            del tool[field]
                            removed_fields.append(field)

                    if removed_fields:
                        logger.debug(f"Cleaned tool[{idx}]: removed {removed_fields}")
                        cleaned_count += 1
                cleaned_tools.append(tool)
            body["tools"] = cleaned_tools
            if cleaned_count > 0:
                logger.info(f"Cleaned {cleaned_count} tools by removing unsupported fields")

        # Use shared method to clean message content (removes tool_reference, etc.)
        body = self._clean_message_content(body)

        # Clean system messages - remove scope from cache_control.ephemeral
        # Claude Code sends cache_control.ephemeral.scope which Anthropic API doesn't support
        # Error: "system.X.cache_control.ephemeral.scope: Extra inputs are not permitted"
        if "system" in body and isinstance(body["system"], list):
            cleaned_system = []
            for idx, item in enumerate(body["system"]):
                if isinstance(item, dict):
                    item = item.copy()
                    if "cache_control" in item and isinstance(item["cache_control"], dict):
                        cache_control = item["cache_control"].copy()
                        if "ephemeral" in cache_control and isinstance(cache_control["ephemeral"], dict):
                            ephemeral = cache_control["ephemeral"].copy()
                            if "scope" in ephemeral:
                                del ephemeral["scope"]
                                logger.debug(f"Removed 'scope' from system[{idx}].cache_control.ephemeral")
                            cache_control["ephemeral"] = ephemeral
                        item["cache_control"] = cache_control
                cleaned_system.append(item)
            body["system"] = cleaned_system

        # Clean top-level Bedrock-specific request fields
        # Claude Code sends requests formatted for AWS Bedrock which includes fields
        # that Anthropic API doesn't support, causing validation errors.
        #
        # Bedrock-specific fields that need removal:
        #
        # - output_config: Bedrock-only field for effort parameter (Claude Opus 4.5)
        #   Used with effort-2025-11-24 beta feature to control token spending
        #   Reference: https://docs.aws.amazon.com/bedrock/latest/userguide/model-parameters-anthropic-claude-messages.html
        #   Error: "output_config: Extra inputs are not permitted"
        #
        # - context_management: Bedrock-specific field for context caching configuration
        #   Reference: https://github.com/anthropics/claude-code/issues/21612
        #   Error: "context_management: Extra inputs are not permitted"
        removed_top_level = []
        for field in ["output_config", "context_management"]:
            if field in body:
                del body[field]
                removed_top_level.append(field)
        if removed_top_level:
            logger.debug(f"Removed Bedrock-specific top-level fields: {removed_top_level}")

        return body

    async def send_message(
        self,
        body: Dict[str, Any],
        token: str,
        auth_type: str,
        headers: Optional[Dict[str, str]] = None,
        request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send message to Anthropic API."""
        import logging
        logger = logging.getLogger(__name__)

        # Normalize model name
        if "model" in body:
            body["model"] = self.normalize_model_name(body["model"])

        # Check model is supported before sending (avoids a wasted round-trip)
        model = body.get("model", "")
        supported = await self._get_supported_models(token, auth_type)
        if supported and model not in supported:
            raise ModelUnsupportedError(f"Model '{model}' not available on Anthropic API")

        # Log tool count before cleaning
        if "tools" in body:
            logger.info(f"[{request_id}] Found {len(body['tools'])} tools before cleaning")
            # Log if any tools have custom field
            custom_count = sum(1 for t in body['tools'] if isinstance(t, dict) and 'custom' in t)
            if custom_count > 0:
                logger.info(f"[{request_id}] {custom_count} tools have 'custom' field before cleaning")
            else:
                logger.info(f"[{request_id}] No tools have 'custom' field before cleaning")
            # Log tool 19 specifically (the one in the error)
            if len(body['tools']) > 19:
                tool19 = body['tools'][19]
                logger.info(f"[{request_id}] Tool[19] keys before cleaning: {list(tool19.keys()) if isinstance(tool19, dict) else 'not a dict'}")

        # Clean request body to remove unsupported fields
        body = self._clean_request_body(body)

        # Log tool count after cleaning
        if "tools" in body:
            logger.info(f"[{request_id}] Have {len(body['tools'])} tools after cleaning")
            # Verify custom fields are gone
            custom_count = sum(1 for t in body['tools'] if isinstance(t, dict) and 'custom' in t)
            if custom_count > 0:
                logger.warning(f"[{request_id}] WARNING! {custom_count} tools STILL have 'custom' field after cleaning!")
                # Log details of first tool with custom field
                for idx, t in enumerate(body['tools']):
                    if isinstance(t, dict) and 'custom' in t:
                        logger.warning(f"[{request_id}] Tool {idx} still has custom: {t.get('custom')}")
                        break
            else:
                logger.info(f"[{request_id}] All tools cleaned - no 'custom' fields remaining")
            # Log tool 19 specifically after cleaning
            if len(body['tools']) > 19:
                tool19 = body['tools'][19]
                logger.info(f"[{request_id}] Tool[19] keys after cleaning: {list(tool19.keys()) if isinstance(tool19, dict) else 'not a dict'}")

        headers = self._build_headers(token, auth_type, headers)

        response = await self.client.post(
            f"{self.base_url}/v1/messages",
            json=body,
            headers=headers
        )

        # Check for rate limit and overloaded errors
        if response.status_code == 429:
            retry_after = int(response.headers.get("retry-after", 60))
            raise RateLimitError("Rate limit exceeded", retry_after=retry_after)

        if response.status_code == 529:
            retry_after = int(response.headers.get("retry-after", 60))
            raise RateLimitError("API overloaded", retry_after=retry_after)

        if 400 <= response.status_code < 500:
            error_text = response.text
            raise ValidationError(f"Anthropic API error ({response.status_code}): {error_text}", status_code=response.status_code)

        if response.status_code != 200:
            error_text = response.text
            raise Exception(f"Anthropic API error ({response.status_code}): {error_text}")

        # Parse response and check for rate limit errors in body
        response_data = response.json()
        if response_data.get("type") == "error":
            error_type = response_data.get("error", {}).get("type", "")
            if error_type in ["rate_limit_error", "overloaded_error"]:
                raise RateLimitError(f"Rate limit: {response_data.get('error', {}).get('message', '')}")

        return response_data

    async def stream_message(
        self,
        body: Dict[str, Any],
        token: str,
        auth_type: str,
        headers: Optional[Dict[str, str]] = None,
        request_id: Optional[str] = None
    ) -> AsyncIterator[str]:
        """Stream message from Anthropic API."""
        import logging
        logger = logging.getLogger(__name__)

        # Enable streaming
        body = body.copy()
        body["stream"] = True

        # Normalize model name
        if "model" in body:
            body["model"] = self.normalize_model_name(body["model"])

        # Check model is supported before sending (avoids a wasted round-trip)
        model = body.get("model", "")
        supported = await self._get_supported_models(token, auth_type)
        if supported and model not in supported:
            raise ModelUnsupportedError(f"Model '{model}' not available on Anthropic API")

        # Log tool count before cleaning
        if "tools" in body:
            logger.info(f"[{request_id}] STREAM: Found {len(body['tools'])} tools before cleaning")
            # Log if any tools have custom field
            custom_count = sum(1 for t in body['tools'] if isinstance(t, dict) and 'custom' in t)
            if custom_count > 0:
                logger.info(f"[{request_id}] STREAM: {custom_count} tools have 'custom' field before cleaning")

        # Clean request body to remove unsupported fields
        body = self._clean_request_body(body)

        # Log tool count after cleaning
        if "tools" in body:
            logger.info(f"[{request_id}] STREAM: Have {len(body['tools'])} tools after cleaning")
            # Verify custom fields are gone
            custom_count = sum(1 for t in body['tools'] if isinstance(t, dict) and 'custom' in t)
            if custom_count > 0:
                logger.warning(f"[{request_id}] STREAM: WARNING! {custom_count} tools STILL have 'custom' field after cleaning!")
                # Log details of first tool with custom field
                for idx, t in enumerate(body['tools']):
                    if isinstance(t, dict) and 'custom' in t:
                        logger.warning(f"[{request_id}] STREAM: Tool {idx} still has custom: {t.get('custom')}")
                        break

        headers = self._build_headers(token, auth_type, headers)

        async with self.client.stream(
            "POST",
            f"{self.base_url}/v1/messages",
            json=body,
            headers=headers
        ) as response:
            # Check for rate limit and overloaded errors
            if response.status_code == 429:
                retry_after = int(response.headers.get("retry-after", 60))
                raise RateLimitError("Rate limit exceeded", retry_after=retry_after)

            if response.status_code == 529:
                retry_after = int(response.headers.get("retry-after", 60))
                raise RateLimitError("API overloaded", retry_after=retry_after)

            if 400 <= response.status_code < 500:
                error_text = await response.aread()
                raise ValidationError(f"Anthropic API error ({response.status_code}): {error_text}", status_code=response.status_code)

            if response.status_code != 200:
                error_text = await response.aread()
                raise Exception(f"Anthropic API error ({response.status_code}): {error_text}")

            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    yield line + "\n\n"