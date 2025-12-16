"""
OAuth passthrough callback for LiteLLM proxy.
Injects the OAuth token from custom_auth as the api_key for Anthropic direct calls.

This enables the following flow:
1. Client sends request with OAuth token in Authorization header
2. custom_auth.py validates the token and stores it in UserAPIKeyAuth.api_key
3. This callback intercepts the request before the LLM call
4. For Anthropic direct models, it injects the OAuth token as the api_key
5. LiteLLM uses this api_key to authenticate with Anthropic's API
"""
import sys
import litellm
from litellm.integrations.custom_logger import CustomLogger
from litellm.proxy.proxy_server import UserAPIKeyAuth, DualCache
from typing import Literal, Optional

# Force output to stdout for debugging
def debug_print(msg):
    print(f"[OAuthPassthrough] {msg}", file=sys.stderr, flush=True)
    litellm.print_verbose(f"[OAuthPassthrough] {msg}")


class OAuthPassthroughHandler(CustomLogger):
    """Injects OAuth token as api_key for Anthropic models."""

    def __init__(self):
        super().__init__()
        debug_print("Handler __init__ called")

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
        Before LLM call, inject OAuth token for Anthropic models.

        The token was captured by custom_auth.py and stored in user_api_key_dict.api_key.
        We only inject for Anthropic direct models (not Bedrock fallbacks).
        """
        debug_print(f"===== async_pre_call_hook CALLED =====")
        debug_print(f"call_type: {call_type}")

        model = data.get("model", "")
        debug_print(f"model in data: {model}")

        # Check if this is a Bedrock model (explicit bypass)
        # If NOT Bedrock, inject the OAuth token so Anthropic direct API can be tried first
        is_bedrock = "bedrock" in model.lower() or model.endswith("-bedrock")

        debug_print(f"is_bedrock={is_bedrock}")

        # Inject token for all non-Bedrock models (Anthropic direct API will use it)
        if not is_bedrock:
            # Get the raw OAuth token from custom auth metadata
            # (api_key field gets hashed, so we store the raw token in metadata)
            metadata = user_api_key_dict.metadata or {}
            oauth_token = metadata.get("raw_token")
            token_preview = f"{oauth_token[:20]}..." if oauth_token else "None"
            debug_print(f"OAuth token from metadata: {token_preview}")
            if oauth_token and oauth_token.startswith("sk-ant-"):
                # ONLY use anthropic_api_key for provider-specific auth
                # Do NOT set generic api_key - it breaks Bedrock fallback
                data["anthropic_api_key"] = oauth_token
                debug_print("anthropic_api_key INJECTED into data dict (NOT generic api_key)")
            else:
                debug_print(f"Token NOT injected - not found or doesn't start with sk-ant-")
        else:
            debug_print("Skipping injection - Bedrock model detected")

        debug_print("===== async_pre_call_hook END =====")
        return data


proxy_handler_instance = OAuthPassthroughHandler()
debug_print("Callback handler instantiated at module load")
