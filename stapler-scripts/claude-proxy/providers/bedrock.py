"""AWS Bedrock provider implementation."""
import json
import anyio
import boto3
import asyncio
import logging
import os
import time
import configparser
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from botocore.config import Config
from botocore.exceptions import ReadTimeoutError, ConnectTimeoutError
from typing import Dict, Any, AsyncIterator, Optional, Tuple
from diskcache import Cache
from . import Provider, RateLimitError, ValidationError, TimeoutError, AuthenticationError
import config
from aws_sso_lib import login as sso_login

# Shared lock file for coordinating SSO login across multiple workers
SSO_LOCK_FILE = "/tmp/claude-proxy-sso-login.lock"
SSO_LOCK_TIMEOUT = 120  # 2 minutes

logger = logging.getLogger(__name__)


def _load_bedrock_model_mapping() -> Dict[str, str]:
    """Load Bedrock model mapping from config file.

    Returns mapping with us. inference profile prefix added.
    Fallback to hardcoded mapping if config file not found.
    """
    config_file = Path(__file__).parent.parent / "config" / "bedrock_models.json"

    if config_file.exists():
        try:
            with open(config_file) as f:
                data = json.load(f)
                # Add us. prefix to all model IDs for cross-region inference profiles
                return {
                    normalized: f"us.{bedrock_id}"
                    for normalized, bedrock_id in data.get("models", {}).items()
                }
        except Exception as e:
            logger.warning(f"Failed to load {config_file}: {e}, using hardcoded mapping")

    # Hardcoded fallback (subset of common models)
    return {
        "claude-sonnet-4-6": "us.anthropic.claude-sonnet-4-6",
        "claude-opus-4-6": "us.anthropic.claude-opus-4-6-v1",
        "claude-sonnet-4-5-20250929": "us.anthropic.claude-sonnet-4-5-20250929-v1:0",
        "claude-opus-4-5-20251101": "us.anthropic.claude-opus-4-5-20251101-v1:0",
        "claude-haiku-4-5-20251001": "us.anthropic.claude-haiku-4-5-20251001-v1:0",
        "claude-3-7-sonnet-20250219": "us.anthropic.claude-3-7-sonnet-20250219-v1:0",
        "claude-3-5-haiku-20241022": "us.anthropic.claude-3-5-haiku-20241022-v1:0",
        "claude-3-haiku-20240307": "us.anthropic.claude-3-haiku-20240307-v1:0",
    }

# Beta flags supported by Bedrock with model compatibility
# Reference: https://docs.aws.amazon.com/bedrock/latest/userguide/model-parameters-anthropic-claude-messages-request-response.html
# Tool-specific reference: https://docs.aws.amazon.com/bedrock/latest/userguide/model-parameters-anthropic-claude-messages-tool-use.html#model-parameters-anthropic-claude-tool-search-tool
BEDROCK_BETA_COMPATIBILITY = {
    "computer-use-2025-01-24": [
        "claude-3-7-sonnet",  # Claude 3.7 Sonnet
    ],
    "token-efficient-tools-2025-02-19": [
        "claude-3-7-sonnet",  # Claude 3.7 Sonnet
        "claude-sonnet-4",    # Claude Sonnet 4+
        "claude-opus-4",      # Claude Opus 4+
        "claude-haiku-4",     # Claude Haiku 4+
    ],
    "Interleaved-thinking-2025-05-14": [
        "claude-sonnet-4",    # Claude Sonnet 4+
        "claude-opus-4",      # Claude Opus 4+
        "claude-haiku-4",     # Claude Haiku 4+
    ],
    "output-128k-2025-02-19": [
        "claude-3-7-sonnet",  # Claude 3.7 Sonnet
    ],
    "dev-full-thinking-2025-05-14": [
        "claude-sonnet-4",    # Claude Sonnet 4+
        "claude-opus-4",      # Claude Opus 4+
        "claude-haiku-4",     # Claude Haiku 4+
    ],
    "context-1m-2025-08-07": [
        "claude-sonnet-4",    # Claude Sonnet 4
    ],
    "context-management-2025-06-27": [
        "claude-sonnet-4-5",  # Claude Sonnet 4.5
        "claude-haiku-4-5",   # Claude Haiku 4.5
    ],
    "effort-2025-11-24": [
        "claude-opus-4-5",    # Claude Opus 4.5
    ],
    "tool-search-tool-2025-10-19": [
        "claude-opus-4-5",    # Claude Opus 4.5
    ],
    "tool-examples-2025-10-29": [
        "claude-opus-4-5",    # Claude Opus 4.5
    ],
}


class BedrockProvider(Provider):
    """Provider for AWS Bedrock."""

    def __init__(self):
        # Configure boto3 with 5-minute timeout
        boto_config = Config(
            read_timeout=config.REQUEST_TIMEOUT,
            connect_timeout=30,
            retries={'max_attempts': 0}  # Handle retries in fallback handler
        )
        # Use Session to enable credential refresh checking
        self.session = boto3.Session()
        self.client = self.session.client(
            "bedrock-runtime",
            region_name=config.AWS_REGION,
            config=boto_config
        )
        # Thread pool for running blocking boto3 calls without blocking event loop
        # Sized via BEDROCK_THREAD_POOL_SIZE (default 40) — all boto3 calls use this pool
        self.executor = ThreadPoolExecutor(max_workers=config.BEDROCK_THREAD_POOL_SIZE, thread_name_prefix="bedrock-io")
        # Disk cache for SSO config and credential validity checks
        # Shared across all workers via /tmp directory
        self.cache = Cache("/tmp/claude-proxy-bedrock-cache")

    @property
    def name(self) -> str:
        return "bedrock"

    def _is_beta_compatible_with_model(self, beta_feature: str, model: str) -> bool:
        """Check if a beta feature is compatible with the given model.

        Args:
            beta_feature: Beta feature flag (e.g., "computer-use-2025-01-24")
            model: Normalized model name (e.g., "claude-haiku-4-5-20251001")

        Returns:
            True if compatible, False otherwise
        """
        if beta_feature not in BEDROCK_BETA_COMPATIBILITY:
            return False

        compatible_patterns = BEDROCK_BETA_COMPATIBILITY[beta_feature]

        # Check if model matches any of the compatible patterns (prefix match)
        # e.g., "claude-haiku-4-5-20251001" matches "claude-haiku-4-5"
        for pattern in compatible_patterns:
            if model.startswith(pattern):
                return True

        return False

    def _check_and_refresh_credentials(self):
        """Check if credentials are expiring soon and refresh proactively."""
        # Check cache first - avoid expensive boto3 calls on every request
        cache_key = f"creds_valid:{config.AWS_PROFILE}"
        cached_result = self.cache.get(cache_key)
        if cached_result:
            is_valid, minutes_remaining = cached_result
            if is_valid and minutes_remaining > 5:
                # Credentials recently validated and still have >5 min
                logger.debug(f"Using cached credential validity (valid for {minutes_remaining}m)")
                return
            else:
                logger.debug(f"Cached credentials expiring soon ({minutes_remaining}m), re-checking")

        # Check shared lock file to see if SSO login is in progress (across all workers)
        in_progress, elapsed = self._is_sso_login_in_progress()
        if in_progress:
            # Try to get credentials - user may have completed SSO login
            # Create new session and force credential cache invalidation
            logger.debug(f"SSO login in progress for {elapsed}s, checking if credentials now available")
            self._recreate_client()

            # Make a test API call to verify credentials actually work
            # This forces boto3 to re-invoke credential_process (aws-vault)
            try:
                # Use STS GetCallerIdentity as a cheap test call
                test_client = self.session.client('sts', region_name=config.AWS_REGION)
                identity = test_client.get_caller_identity()
                # Success! Credentials work
                logger.info(f"✓ SSO login completed successfully after {elapsed}s - verified with STS call (Account: {identity['Account']})")
                self._clear_sso_lock()
                # Cache successful validation (assume new SSO tokens are valid for 1 hour)
                cache_key = f"creds_valid:{config.AWS_PROFILE}"
                self.cache.set(cache_key, (True, 60), expire=30)  # Cache for 30s
                return  # Credentials valid, continue with request
            except Exception as e:
                # Credentials still not available or invalid
                error_type = type(e).__name__
                error_msg = str(e).lower()
                logger.debug(f"SSO login still in progress: {error_type}: {e}")

                # If we get UnauthorizedSSOTokenError, SSO login incomplete
                if 'unauthorized' in error_msg or 'expired' in error_msg or 'invalid' in error_msg:
                    raise AuthenticationError(f"AWS SSO login in progress (started {elapsed}s ago). Please complete authentication in browser and retry.")
                else:
                    # Some other error - let it propagate
                    raise

        try:
            # Get current credentials from session
            credentials = self.session.get_credentials()
            if not credentials:
                logger.error("❌ No credentials found - SSO login required")
                # Trigger SSO login automatically (respects in-progress flag)
                browser_opened = self._trigger_sso_login()
                if browser_opened:
                    raise AuthenticationError("No AWS credentials found. Browser opened for SSO login - please complete authentication and retry.")
                else:
                    raise AuthenticationError("AWS SSO login already in progress. Please complete authentication in browser and retry.")

            # Check if credentials have an expiry time
            # Works with SSO, assume role, credential_process (aws-vault), etc.
            if hasattr(credentials, '_expiry_time') and credentials._expiry_time:
                expiry_time = credentials._expiry_time

                # Calculate time until expiry
                now = datetime.now(expiry_time.tzinfo) if expiry_time.tzinfo else datetime.now()
                time_until_expiry = expiry_time - now

                # Check if already expired
                if time_until_expiry < timedelta(0):
                    logger.error(f"❌ Credentials expired {int(abs(time_until_expiry.total_seconds() / 60))}m ago - SSO login required")
                    # Trigger SSO login automatically (respects in-progress flag)
                    browser_opened = self._trigger_sso_login()
                    if browser_opened:
                        raise AuthenticationError("AWS SSO session expired. Browser opened for login - please complete authentication and retry.")
                    else:
                        raise AuthenticationError("AWS SSO login already in progress. Please complete authentication in browser and retry.")
                # Refresh if expiring within 5 minutes
                elif time_until_expiry < timedelta(minutes=5):
                    logger.warning(f"🔄 Credentials expiring in {int(time_until_expiry.total_seconds() / 60)}m, refreshing proactively")
                    self._recreate_client()
                    # Verify refresh worked by checking expiry again
                    refreshed_creds = self.session.get_credentials()
                    if refreshed_creds and hasattr(refreshed_creds, '_expiry_time') and refreshed_creds._expiry_time:
                        new_expiry = refreshed_creds._expiry_time
                        new_time_until_expiry = new_expiry - datetime.now(new_expiry.tzinfo if new_expiry.tzinfo else None)
                        if new_time_until_expiry > timedelta(minutes=15):
                            logger.info(f"✓ Credentials refreshed successfully (valid for {int(new_time_until_expiry.total_seconds() / 60)}m)")
                            self._clear_sso_lock()
                            # Cache successful refresh
                            cache_key = f"creds_valid:{config.AWS_PROFILE}"
                            minutes = int(new_time_until_expiry.total_seconds() / 60)
                            self.cache.set(cache_key, (True, minutes), expire=30)
                        else:
                            logger.warning(f"⚠️  Credentials still expiring soon ({int(new_time_until_expiry.total_seconds() / 60)}m) after refresh")
                elif time_until_expiry < timedelta(minutes=15):
                    logger.debug(f"Credentials valid for {int(time_until_expiry.total_seconds() / 60)} minutes")
                    # Cache that credentials are valid
                    cache_key = f"creds_valid:{config.AWS_PROFILE}"
                    minutes = int(time_until_expiry.total_seconds() / 60)
                    self.cache.set(cache_key, (True, minutes), expire=30)
                else:
                    # Credentials valid for >15 minutes
                    logger.debug(f"Credentials valid for {int(time_until_expiry.total_seconds() / 60)} minutes")
                    # Cache that credentials are valid
                    cache_key = f"creds_valid:{config.AWS_PROFILE}"
                    minutes = int(time_until_expiry.total_seconds() / 60)
                    self.cache.set(cache_key, (True, minutes), expire=30)
        except Exception as e:
            # Make credential errors visible - these indicate SSO issues
            logger.warning(f"⚠️  Credential check error: {e}")
            logger.warning(f"   This may indicate expired SSO session. Run: aws-vault exec {config.AWS_PROFILE} -- aws sts get-caller-identity")

    def _recreate_client(self):
        """Recreate boto3 client and force credential cache invalidation.

        This is necessary because boto3 caches credentials and won't re-invoke
        credential_process (aws-vault) until the cached credentials expire.
        """
        boto_config = Config(
            read_timeout=config.REQUEST_TIMEOUT,
            connect_timeout=30,
            retries={'max_attempts': 0}
        )
        # Create completely new session to force credential refresh
        self.session = boto3.Session()

        # Force credential cache invalidation by getting credentials and invalidating them
        # This makes boto3 re-invoke credential_process (aws-vault) on next use
        try:
            creds = self.session.get_credentials()
            if creds and hasattr(creds, '_refresh'):
                # Force refresh on next access
                logger.debug("Invalidating boto3 credential cache")
                # Set credentials as needing refresh
                if hasattr(creds, '_frozen_credentials'):
                    creds._frozen_credentials = None
        except Exception as e:
            logger.debug(f"Error invalidating credentials: {e}")

        self.client = self.session.client(
            "bedrock-runtime",
            region_name=config.AWS_REGION,
            config=boto_config
        )

    def _is_sso_login_in_progress(self) -> tuple[bool, int]:
        """Check if SSO login is in progress by checking shared lock file.

        Returns:
            (in_progress, elapsed_seconds): Whether SSO login is in progress and how long ago it started
        """
        try:
            if os.path.exists(SSO_LOCK_FILE):
                lock_time = os.path.getmtime(SSO_LOCK_FILE)
                elapsed = time.time() - lock_time
                if elapsed < SSO_LOCK_TIMEOUT:
                    return True, int(elapsed)
                else:
                    # Lock file expired, remove it
                    logger.warning(f"⚠️  SSO lock file expired after {int(elapsed)}s, removing")
                    os.remove(SSO_LOCK_FILE)
                    return False, 0
            return False, 0
        except Exception as e:
            logger.debug(f"Error checking SSO lock file: {e}")
            return False, 0

    def _create_sso_lock(self) -> bool:
        """Create SSO login lock file atomically to prevent concurrent browser opens.

        Returns:
            True if lock was created (this worker won the race), False if lock already exists
        """
        try:
            # Use O_CREAT | O_EXCL for atomic creation - fails if file exists
            # This prevents race conditions between multiple workers
            fd = os.open(SSO_LOCK_FILE, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
            try:
                os.write(fd, str(time.time()).encode())
            finally:
                os.close(fd)
            logger.debug(f"Created SSO lock file atomically: {SSO_LOCK_FILE}")
            return True
        except FileExistsError:
            logger.debug(f"SSO lock file already exists (another worker won the race)")
            return False
        except Exception as e:
            logger.warning(f"Failed to create SSO lock file: {e}")
            return False

    def _clear_sso_lock(self) -> None:
        """Clear SSO login lock file."""
        try:
            if os.path.exists(SSO_LOCK_FILE):
                os.remove(SSO_LOCK_FILE)
                logger.debug(f"Cleared SSO lock file: {SSO_LOCK_FILE}")
        except Exception as e:
            logger.debug(f"Error clearing SSO lock file: {e}")

    def _get_sso_config(self) -> Tuple[str, str]:
        """Get SSO configuration from AWS profile with caching.

        Returns:
            (start_url, sso_region): SSO configuration values

        Raises:
            ValueError: If profile not found or missing SSO config
        """
        # Cache key based on profile name
        cache_key = f"sso_config:{config.AWS_PROFILE}"

        # Try to get from cache first (TTL: 1 hour)
        cached = self.cache.get(cache_key)
        if cached:
            logger.debug(f"Using cached SSO config for profile '{config.AWS_PROFILE}'")
            return cached

        # Cache miss - read from ~/.aws/config
        logger.debug(f"Reading SSO config for profile '{config.AWS_PROFILE}' from ~/.aws/config")
        config_path = os.path.expanduser("~/.aws/config")
        aws_config = configparser.ConfigParser()
        aws_config.read(config_path)

        # Profile name in config file has "profile " prefix (unless it's "default")
        profile_section = f"profile {config.AWS_PROFILE}" if config.AWS_PROFILE != "default" else "default"

        if profile_section not in aws_config:
            raise ValueError(f"Profile '{config.AWS_PROFILE}' not found in {config_path}")

        profile = aws_config[profile_section]
        start_url = profile.get('sso_start_url')
        sso_region = profile.get('sso_region')

        if not start_url or not sso_region:
            raise ValueError(f"Profile '{config.AWS_PROFILE}' missing sso_start_url or sso_region")

        # Cache for 1 hour (config rarely changes)
        result = (start_url, sso_region)
        self.cache.set(cache_key, result, expire=3600)
        logger.debug(f"Cached SSO config for profile '{config.AWS_PROFILE}' (TTL: 1h)")

        return result

    def _trigger_sso_login(self) -> bool:
        """Programmatically trigger AWS SSO login using aws-sso-lib.

        Opens browser for authentication and refreshes SSO token cache in
        ~/.aws/sso/cache/ that aws-vault credential_process reads.

        Returns True if login triggered successfully, False if already in progress.
        """
        # Check if SSO login already in progress (file lock)
        lock_acquired = self._create_sso_lock()
        if not lock_acquired:
            in_progress, elapsed = self._is_sso_login_in_progress()
            logger.warning(f"⚠️  SSO login already in progress (started {elapsed}s ago). Waiting for completion...")
            return False

        try:
            # Get SSO configuration from AWS profile (cached)
            start_url, sso_region = self._get_sso_config()

            logger.warning(f"🔐 AWS SSO session expired. Opening browser for login...")
            logger.info(f"   Start URL: {start_url}")
            logger.info(f"   SSO Region: {sso_region}")

            # Use aws-sso-lib to trigger interactive SSO login
            # This opens browser and updates ~/.aws/sso/cache/
            token = sso_login(
                start_url=start_url,
                sso_region=sso_region,
                force_refresh=True  # Force new token even if one exists
            )

            if token:
                logger.info("✓ SSO login completed successfully")
                self._clear_sso_lock()
                return True
            else:
                logger.error("❌ SSO login returned no token")
                self._clear_sso_lock()
                return False

        except Exception as e:
            logger.error(f"❌ SSO login failed: {e}", exc_info=True)
            self._clear_sso_lock()
            return False

    def _convert_to_bedrock_model(self, model: str) -> str:
        """Convert model name to Bedrock format.

        Uses config/bedrock_models.json (generated via scripts/validate_bedrock_models.py)
        with fallback to common models if config unavailable.

        Raises:
            ValidationError: If model is not available on Bedrock
        """
        # Remove any existing prefixes
        model = self.normalize_model_name(model)

        # Remove -bedrock suffix if present
        if model.endswith("-bedrock"):
            model = model[:-8]

        # Load mapping from config (cached at module level)
        if not hasattr(self.__class__, '_model_mapping_cache'):
            self.__class__._model_mapping_cache = _load_bedrock_model_mapping()

        model_mapping = self.__class__._model_mapping_cache

        # Try exact match first
        if model in model_mapping:
            return model_mapping[model]

        # Fallback: construct model ID (may fail if model doesn't exist)
        logger.warning(f"Model {model} not in Bedrock mapping, constructing ID (may fail)")
        return f"us.anthropic.{model}-v1:0"

    def _convert_response(self, bedrock_response: Dict[str, Any], model: str) -> Dict[str, Any]:
        """Convert Bedrock response to Anthropic format."""
        # Extract content from Bedrock response
        content = bedrock_response.get("content", [])
        if isinstance(content, str):
            content = [{"type": "text", "text": content}]

        return {
            "id": bedrock_response.get("id", "msg_bedrock"),
            "type": "message",
            "role": "assistant",
            "model": model,
            "content": content,
            "stop_reason": bedrock_response.get("stop_reason", "end_turn"),
            "stop_sequence": bedrock_response.get("stop_sequence"),
            "usage": bedrock_response.get("usage", {
                "input_tokens": 0,
                "output_tokens": 0
            })
        }

    def _prepare_bedrock_body(
        self,
        body: Dict[str, Any],
        model: str,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Prepare request body for Bedrock API.

        Args:
            body: Request body
            model: Normalized model name (for beta feature compatibility checking)
            headers: Optional headers (for anthropic-beta)

        Handles:
        - Adding anthropic_version
        - Validating thinking.budget_tokens (Bedrock-specific workaround)
        - Converting anthropic-beta header to body format with model-specific filtering
        - Removing unsupported parameters
        - Cleaning tool definitions
        - Cleaning message content (removes tool_reference, etc.)
        """
        bedrock_body = body.copy()
        bedrock_body["anthropic_version"] = "bedrock-2023-05-31"

        # Clean tool definitions - remove fields that aren't supported
        # See: https://github.com/anthropics/claude-code/issues/11678
        if "tools" in bedrock_body and isinstance(bedrock_body["tools"], list):
            cleaned_tools = []
            cleaned_count = 0
            for idx, tool in enumerate(bedrock_body["tools"]):
                if isinstance(tool, dict):
                    tool = tool.copy()
                    # Remove Claude Code specific fields that Bedrock doesn't support
                    # - custom: Claude Code-specific metadata
                    # - defer_loading: Claude Code-specific loading control
                    # - input_examples: Claude Code-specific examples
                    # - cache_control: Prompt caching only supported in messages/system, not tools
                    removed_fields = []
                    for field in ["defer_loading", "input_examples", "custom", "cache_control"]:
                        if field in tool:
                            del tool[field]
                            removed_fields.append(field)

                    if removed_fields:
                        logger.debug(f"Cleaned tool[{idx}]: removed {removed_fields}")
                        cleaned_count += 1
                cleaned_tools.append(tool)
            bedrock_body["tools"] = cleaned_tools
            if cleaned_count > 0:
                logger.info(f"Bedrock: Cleaned {cleaned_count} tools by removing unsupported fields")

        # Use shared method to clean message content (removes tool_reference, etc.)
        bedrock_body = self._clean_message_content(bedrock_body)

        # Bedrock-specific workaround: ensure thinking.budget_tokens is valid
        # See: https://github.com/anthropics/claude-code/issues/8756
        # Bedrock has stricter limits (4096 output) and burndown throttling
        # Constraints: 1024 <= thinking.budget_tokens <= max_tokens
        if "thinking" in bedrock_body and isinstance(bedrock_body["thinking"], dict):
            budget_tokens = bedrock_body["thinking"].get("budget_tokens")
            max_tokens = bedrock_body.get("max_tokens")
            if budget_tokens and max_tokens:
                if budget_tokens > max_tokens:
                    # If max_tokens is too small for thinking (< 1024), disable thinking
                    if max_tokens < 1024:
                        logger.warning(f"Bedrock: max_tokens={max_tokens} too small for thinking mode (min 1024), disabling thinking")
                        del bedrock_body["thinking"]
                    else:
                        logger.warning(f"Bedrock: Capping thinking.budget_tokens from {budget_tokens} to max_tokens {max_tokens}")
                        bedrock_body["thinking"]["budget_tokens"] = max_tokens
                elif budget_tokens < 1024:
                    # Ensure minimum thinking budget
                    logger.warning(f"Bedrock: Increasing thinking.budget_tokens from {budget_tokens} to minimum 1024")
                    bedrock_body["thinking"]["budget_tokens"] = 1024

        # Convert anthropic-beta header to body format for Bedrock
        if headers and "anthropic-beta" in headers:
            beta_value = headers["anthropic-beta"]
            # Parse comma-separated list of beta features
            requested_betas = [f.strip() for f in beta_value.split(",")]

            # Filter to only supported beta flags that are compatible with this model
            compatible_betas = []
            incompatible_betas = []
            unsupported_betas = []

            for beta in requested_betas:
                if beta not in BEDROCK_BETA_COMPATIBILITY:
                    unsupported_betas.append(beta)
                elif self._is_beta_compatible_with_model(beta, model):
                    compatible_betas.append(beta)
                else:
                    incompatible_betas.append(beta)

            # Log filtered features
            if unsupported_betas:
                logger.debug(f"Filtering unsupported beta flags for Bedrock: {unsupported_betas}")
            if incompatible_betas:
                logger.debug(f"Filtering model-incompatible beta flags for {model}: {incompatible_betas}")

            # Only add anthropic_beta if we have compatible flags
            if compatible_betas:
                bedrock_body["anthropic_beta"] = compatible_betas
                logger.debug(f"Using beta features for {model}: {compatible_betas}")

        # Remove fields that Bedrock does not accept at the top level:
        # - stream: conveyed via invoke_model_with_response_stream vs invoke_model
        # - model: specified as modelId parameter, not in the body
        # - output_config: Anthropic-specific effort parameter (not supported by Bedrock)
        # - context_management: Anthropic-specific field for prompt caching (not supported by Bedrock)
        #
        # Note: While Bedrock has its own context management features, the context_management
        # field format from Claude Code is Anthropic-specific and causes ValidationException on Bedrock
        bedrock_body.pop("stream", None)
        bedrock_body.pop("model", None)
        bedrock_body.pop("output_config", None)
        bedrock_body.pop("context_management", None)

        # Bedrock-specific: Validate and clean orphaned tool_result blocks after compaction
        # Problem: Compaction may remove tool_use blocks while keeping tool_result blocks
        # Bedrock requires: Every tool_use_id in tool_result must have corresponding tool_use in previous message
        # Solution: Collect all valid tool_use_ids, remove tool_results with orphaned references
        if "messages" in bedrock_body and isinstance(bedrock_body["messages"], list):
            for i, message in enumerate(bedrock_body["messages"]):
                if not isinstance(message, dict) or "content" not in message:
                    continue
                if not isinstance(message["content"], list):
                    continue

                # Collect tool_use_ids from previous message (if exists)
                valid_tool_use_ids = set()
                if i > 0:
                    prev_message = bedrock_body["messages"][i - 1]
                    if isinstance(prev_message, dict) and "content" in prev_message:
                        if isinstance(prev_message["content"], list):
                            for content_item in prev_message["content"]:
                                if isinstance(content_item, dict) and content_item.get("type") == "tool_use":
                                    tool_id = content_item.get("id")
                                    if tool_id:
                                        valid_tool_use_ids.add(tool_id)

                # Filter out invalid tool_results (missing or orphaned tool_use_id)
                cleaned_content = []
                for content_item in message["content"]:
                    if isinstance(content_item, dict) and content_item.get("type") == "tool_result":
                        tool_use_id = content_item.get("tool_use_id")
                        # Bedrock requires tool_use_id field and it must reference a valid tool_use
                        if not tool_use_id:
                            logger.debug(f"Removing tool_result with missing tool_use_id field (required by Bedrock)")
                            continue
                        if tool_use_id not in valid_tool_use_ids:
                            logger.debug(f"Removing orphaned tool_result with tool_use_id={tool_use_id} (no matching tool_use found)")
                            continue
                    cleaned_content.append(content_item)

                message["content"] = cleaned_content

        return bedrock_body

    def _handle_bedrock_error(self, e: Exception) -> None:
        """Handle Bedrock exceptions and convert to appropriate error types."""
        if isinstance(e, self.client.exceptions.ThrottlingException):
            raise RateLimitError("Bedrock rate limit exceeded")
        elif isinstance(e, self.client.exceptions.ValidationException):
            raise ValidationError(f"Bedrock validation error: {str(e)}", status_code=400)
        elif isinstance(e, (ReadTimeoutError, ConnectTimeoutError)):
            raise TimeoutError(f"Bedrock timeout: {str(e)}")
        else:
            error_msg = str(e).lower()
            # Check for expired security token (aws-vault/SSO issue)
            if "security token" in error_msg and "expired" in error_msg:
                logger.error(f"❌ AWS credentials expired. Run: aws-vault exec {config.AWS_PROFILE} -- aws sts get-caller-identity")
                raise AuthenticationError(f"AWS credentials expired. Run 'aws-vault exec {config.AWS_PROFILE}' to refresh SSO session")
            # Check for invalid credentials
            if "credentials" in error_msg and ("invalid" in error_msg or "not found" in error_msg or "unable to locate" in error_msg):
                logger.error(f"❌ AWS credentials not found or invalid. Run: aws-vault exec {config.AWS_PROFILE} -- aws sts get-caller-identity")
                raise AuthenticationError(f"AWS credentials not found. Run 'aws-vault exec {config.AWS_PROFILE}' to initialize SSO session")
            # Check for SSO authentication errors (not retryable)
            if "sso" in error_msg and ("expired" in error_msg or "invalid" in error_msg):
                # Automatically trigger SSO login to open browser
                browser_opened = self._trigger_sso_login()
                if browser_opened:
                    raise AuthenticationError(f"AWS SSO session expired. Browser opened for login - please complete authentication and retry.")
                else:
                    raise AuthenticationError(f"AWS SSO session expired. Please complete authentication in browser and retry.")
            # Check if it's a timeout in the exception message
            if "timeout" in error_msg or "timed out" in error_msg:
                raise TimeoutError(f"Bedrock timeout: {str(e)}")
            raise

    async def send_message(
        self,
        body: Dict[str, Any],
        token: str,
        auth_type: str,
        headers: Optional[Dict[str, str]] = None,
        request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send message to Bedrock."""
        # Proactively refresh credentials if expiring soon
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(self.executor, self._check_and_refresh_credentials)

        # Convert model name
        original_model = body.get("model", "claude-3-haiku-20240307")
        normalized_model = self.normalize_model_name(original_model)
        bedrock_model = self._convert_to_bedrock_model(original_model)

        # Prepare Bedrock request body (pass normalized model for beta compatibility checking)
        bedrock_body = self._prepare_bedrock_body(body, normalized_model, headers)

        try:
            # Run invoke_model in dedicated thread pool (not anyio's default pool)
            # This ensures all Bedrock I/O shares the same bounded, configurable executor
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                self.executor,
                lambda: self.client.invoke_model(
                    modelId=bedrock_model,
                    contentType="application/json",
                    accept="application/json",
                    body=json.dumps(bedrock_body)
                )
            )

            # Reading response body is also blocking I/O — run in same pool
            body_content = await loop.run_in_executor(self.executor, response["body"].read)
            result = json.loads(body_content)
            return self._convert_response(result, original_model)

        except Exception as e:
            self._handle_bedrock_error(e)

    async def stream_message(
        self,
        body: Dict[str, Any],
        token: str,
        auth_type: str,
        headers: Optional[Dict[str, str]] = None,
        request_id: Optional[str] = None
    ) -> AsyncIterator[str]:
        """Stream message from Bedrock."""
        # Proactively refresh credentials if expiring soon
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(self.executor, self._check_and_refresh_credentials)

        # Convert model name
        original_model = body.get("model", "claude-3-haiku-20240307")
        normalized_model = self.normalize_model_name(original_model)
        bedrock_model = self._convert_to_bedrock_model(original_model)

        # Prepare Bedrock request body (pass normalized model for beta compatibility checking)
        bedrock_body = self._prepare_bedrock_body(body, normalized_model, headers)

        send_stream, receive_stream = anyio.create_memory_object_stream(max_buffer_size=10)

        async with anyio.create_task_group() as tg:
            tg.start_soon(
                anyio.to_thread.run_sync,
                self._stream_bedrock_sync,
                send_stream,
                bedrock_model,
                bedrock_body
            )

            async with receive_stream:
                async for item in receive_stream:
                    yield item

    def _stream_bedrock_sync(self, send_stream, bedrock_model: str, bedrock_body: Dict[str, Any]):
        """Synchronous worker to stream from Bedrock in a thread."""
        try:
            response = self.client.invoke_model_with_response_stream(
                modelId=bedrock_model,
                contentType="application/json",
                accept="application/json",
                body=json.dumps(bedrock_body)
            )

            for event in response["body"]:
                chunk = json.loads(event["chunk"]["bytes"])
                anyio.from_thread.run(send_stream.send, f"data: {json.dumps(chunk)}\n\n")

        except Exception as e:
            self._handle_bedrock_error(e)
        finally:
            anyio.from_thread.run(send_stream.aclose)
