"""
OAuth passthrough callback for LiteLLM proxy.
Handles OAuth token passthrough for Anthropic direct API calls.
Also converts between Claude Code's Bedrock model IDs and proxy model names.

Key features:
1. OAuth token injection for Enterprise Anthropic API
2. Model name conversion (Bedrock format <-> proxy format)
3. Header cleanup for Bedrock fallback

Model conversion examples:
- us.anthropic.claude-opus-4-5-20251101-v1:0 -> claude-opus-4-5-20251101
- us.anthropic.claude-3-haiku-20240307-v1:0 -> claude-3-haiku-20240307
"""
import os
import sys
import re
import litellm
from litellm.integrations.custom_logger import CustomLogger
from litellm.proxy.proxy_server import UserAPIKeyAuth, DualCache
from typing import Literal, Optional


def debug_print(msg):
    """Force output to stderr for debugging."""
    print(f"[OAuthPassthrough] {msg}", file=sys.stderr, flush=True)
    litellm.print_verbose(f"[OAuthPassthrough] {msg}")


class OAuthPassthroughHandler(CustomLogger):
    """
    Placeholder callback handler.

    The actual authentication is handled by:
    1. custom_auth.py - validates OAuth tokens in requests
    2. config.yaml - configurable_clientside_auth_params: ["api_key"]
    3. ANTHROPIC_API_KEY env var - set from CLAUDE_CODE_OAUTH_TOKEN at startup

    This handler is kept for logging/debugging purposes but doesn't
    modify the request data to avoid conflicts with fallback.
    """

    def __init__(self):
        super().__init__()
        debug_print("Handler __init__ called")
        debug_print(f"Handler class: {self.__class__.__name__}")
        debug_print(f"Has async_pre_call_hook: {hasattr(self, 'async_pre_call_hook')}")
        oauth_token = os.environ.get("CLAUDE_CODE_OAUTH_TOKEN", "")
        anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if oauth_token:
            debug_print(f"CLAUDE_CODE_OAUTH_TOKEN available: {oauth_token[:20]}...")
        if anthropic_key:
            debug_print(f"ANTHROPIC_API_KEY available: {anthropic_key[:20]}...")

    def convert_model_format(self, model: str, target_provider: str = None) -> str:
        """
        Convert between Bedrock and proxy model formats based on context.

        Examples:
        - Bedrock to proxy: us.anthropic.claude-opus-4-5-20251101-v1:0 -> claude-opus-4-5-20251101
        - Proxy to Bedrock: claude-opus-4-5-20251101-bedrock -> keep as-is (already explicit)
        - For fallback: claude-opus-4-5-20251101 might need Bedrock suffix
        """
        original_model = model

        # Handle Bedrock format -> Proxy format
        if model.startswith("us.anthropic."):
            # Remove the us.anthropic. prefix
            model = model.replace("us.anthropic.", "")
            # Remove the version suffix (e.g., -v1:0, -v2:0)
            model = re.sub(r'-v\d+:\d+$', '', model)
            debug_print(f"Converted Bedrock format to proxy: {original_model} -> {model}")

        # If model ends with -bedrock, it's already explicit - no conversion needed
        elif model.endswith("-bedrock"):
            debug_print(f"Model already explicit Bedrock: {model}")

        # For regular proxy models, check if we're targeting Bedrock
        elif target_provider == "bedrock" and not model.endswith("-bedrock"):
            # Add -bedrock suffix for explicit Bedrock routing
            model = f"{model}-bedrock"
            debug_print(f"Added Bedrock suffix for fallback: {original_model} -> {model}")

        return model

    async def async_pre_call_hook(
        self,
        user_api_key_dict: UserAPIKeyAuth,
        cache: DualCache,
        data: dict,
        call_type: Literal[
            "completion",
            "text_completion",
            "embeddings",
            "image_generation",
            "moderation",
            "audio_transcription",
        ],
    ) -> Optional[dict]:
        """
        Pre-call hook - converts model names and injects OAuth tokens.

        1. Converts Bedrock model IDs to proxy model names
        2. Injects OAuth tokens for Anthropic (non-Bedrock) models
        3. Cleans up for Bedrock fallback
        """
        debug_print("========== async_pre_call_hook CALLED ==========")
        debug_print(f"call_type: {call_type}")
        debug_print(f"data keys: {list(data.keys())}")

        original_model = data.get("model", "")

        # Determine target provider based on model name and context
        target_provider = None
        if "bedrock" in original_model.lower() or original_model.endswith("-bedrock"):
            target_provider = "bedrock"

        # Convert model format as needed
        model = self.convert_model_format(original_model, target_provider)
        if model != original_model:
            data["model"] = model
            debug_print(f"Model converted: {original_model} -> {model}")

        debug_print(f"pre_call_hook: model={model}, call_type={call_type}")

        # Log auth source for debugging
        metadata = user_api_key_dict.metadata or {}
        auth_source = metadata.get("auth_source", "unknown")
        debug_print(f"auth_source={auth_source}")

        # Check if this is an Anthropic model (not Bedrock)
        is_anthropic = "anthropic" in model.lower() or model.startswith("claude-")
        is_bedrock = "bedrock" in model.lower()

        if is_bedrock:
            # For Bedrock, make sure we don't pass any OAuth tokens or extra params
            debug_print(f"Bedrock model detected: {model}, removing any OAuth tokens")
            # Remove any api_key that might have been set
            if "api_key" in data:
                del data["api_key"]
            if "litellm_params" in data and "api_key" in data["litellm_params"]:
                del data["litellm_params"]["api_key"]
            # Remove optional_params to avoid Bedrock errors
            if "optional_params" in data:
                del data["optional_params"]
            debug_print(f"Cleaned auth for Bedrock model {model}")
        elif is_anthropic:
            # Get OAuth token from metadata for Anthropic models
            oauth_token = metadata.get("raw_token")

            if oauth_token and oauth_token.startswith("sk-ant-oat"):
                debug_print(f"Injecting OAuth token for Anthropic model: {model}")
                debug_print(f"Token prefix: {oauth_token[:20]}...")

                # Enterprise OAuth tokens require:
                # 1. Authorization: Bearer header
                # 2. anthropic-beta: oauth-2025-04-20 header
                # 3. NO x-api-key header

                # We need to pass headers but NOT set api_key
                # Setting api_key would make LiteLLM use x-api-key which fails

                # First, ensure we have the headers structure
                if "headers" not in data:
                    data["headers"] = {}

                # Add OAuth-specific headers directly to data["headers"]
                data["headers"]["Authorization"] = f"Bearer {oauth_token}"
                data["headers"]["anthropic-beta"] = "oauth-2025-04-20"

                # Make sure we don't set api_key which would override Authorization
                if "api_key" in data:
                    del data["api_key"]

                debug_print(f"OAuth Bearer token and beta header set for {model}")
            elif oauth_token and oauth_token.startswith("sk-ant-api"):
                # Regular API keys use x-api-key header
                debug_print(f"Injecting API key for Anthropic model: {model}")
                data["api_key"] = oauth_token
                debug_print(f"API key injected for {model}")
            else:
                debug_print(f"No valid token found in metadata for {model}")
        else:
            debug_print(f"Unknown model type: {model}")

        return data


proxy_handler_instance = OAuthPassthroughHandler()
debug_print("Callback handler instantiated at module load")
