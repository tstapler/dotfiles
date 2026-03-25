"""Fallback handler for provider orchestration."""
import time
import asyncio
import logging
from typing import Dict, Any, List, AsyncIterator, Optional
from providers import Provider, RateLimitError, ValidationError, TimeoutError, AuthenticationError
import config
import diskcache
import os

logger = logging.getLogger(__name__)


class FallbackHandler:
    """Orchestrates providers with automatic fallback on rate limits."""

    def __init__(self, providers: List[Provider], metrics=None):
        self.providers = providers
        self.metrics = metrics
        # Use diskcache for persistent cooldown tracking across restarts
        cache_dir = os.path.expanduser("~/.cache/claude-proxy/cooldowns")
        self.cooldowns = diskcache.Cache(cache_dir)

        # Log any existing cooldowns on startup
        for provider_name in list(self.cooldowns):
            cooldown_until = self.cooldowns.get(provider_name)
            if cooldown_until:
                remaining = int(cooldown_until - time.time())
                if remaining > 0:
                    logger.info(f"🔄 Restored cooldown: {provider_name} has {remaining}s remaining")
                else:
                    # Expired, clean it up
                    self.cooldowns.delete(provider_name)

    def _is_in_cooldown(self, provider_name: str) -> bool:
        """Check if provider is in cooldown period."""
        cooldown_until = self.cooldowns.get(provider_name)
        if cooldown_until is None:
            return False
        if time.time() >= cooldown_until:
            # Cooldown expired, remove it
            self.cooldowns.delete(provider_name)
            return False
        return True

    def _set_cooldown(self, provider_name: str, seconds: int = None):
        """Set cooldown for a provider."""
        if seconds is None:
            seconds = config.COOLDOWN_SECONDS
        cooldown_until = time.time() + seconds
        self.cooldowns.set(provider_name, cooldown_until)
        logger.warning(f"Provider {provider_name} in cooldown for {seconds}s (persisted to disk)")

    async def send_message(
        self,
        body: Dict[str, Any],
        token: str,
        auth_type: str,
        headers: Optional[Dict[str, str]] = None,
        request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send message with automatic fallback."""
        start_time = time.time()
        last_error = None
        req_prefix = f"[{request_id}] " if request_id else ""
        model = body.get("model", "unknown")

        for provider in self.providers:
            # Skip providers in cooldown
            if self._is_in_cooldown(provider.name):
                logger.debug(f"{req_prefix}Skipping {provider.name} (cooldown)")
                continue

            # Retry logic for the current provider
            max_retries = config.BEDROCK_MAX_RETRIES if provider.name == "bedrock" else 1
            for attempt in range(max_retries):
                try:
                    if attempt > 0:
                        logger.info(f"{req_prefix}↻ {provider.name} (retry {attempt}/{max_retries}, model={model})")
                    else:
                        logger.info(f"{req_prefix}→ {provider.name} (model={model})")

                    result = await provider.send_message(body, token, auth_type, headers, request_id)
                    logger.info(f"{req_prefix}✓ {provider.name} (model={model})")
                    if self.metrics:
                        self.metrics.record_request_complete(provider.name, model, start_time, True, stream=False)
                    return result

                except TimeoutError as e:
                    logger.warning(f"{req_prefix}⏱ {provider.name}: stream timeout (attempt {attempt + 1}/{max_retries}, model={model})")
                    last_error = e
                    if attempt + 1 >= max_retries:
                        # Exhausted retries, move to next provider
                        break
                    # Retry the same provider
                    continue

                except RateLimitError as e:
                    retry_after = getattr(e, 'retry_after', None)
                    if retry_after:
                        logger.warning(f"{req_prefix}✗ {provider.name}: rate limit (attempt {attempt + 1}/{max_retries}, model={model}) - retry after {retry_after}s")
                    else:
                        logger.warning(f"{req_prefix}✗ {provider.name}: rate limit (attempt {attempt + 1}/{max_retries}, model={model})")
                    last_error = e
                    # Anthropic: put in cooldown, move to next provider
                    if provider.name != "bedrock":
                        self._set_cooldown(provider.name, retry_after)
                        if self.metrics:
                            self.metrics.record_fallback(provider.name, "bedrock", "rate_limit")
                        break
                    # Bedrock: retry with exponential backoff (never goes in cooldown)
                    if attempt + 1 >= max_retries:
                        logger.error(f"{req_prefix}✗ {provider.name}: exhausted retries on rate limit (model={model})")
                        break
                    # Exponential backoff: 2s, 4s, 8s, etc.
                    backoff = 2 ** attempt
                    logger.info(f"{req_prefix}⏸ Waiting {backoff}s before retry...")
                    await asyncio.sleep(backoff)
                    continue

                except ValidationError as e:
                    # Validation errors are client errors - don't retry with other providers
                    logger.error(f"{req_prefix}✗ {provider.name}: validation error (model={model}) - {e}")
                    if self.metrics:
                        self.metrics.record_request_complete(provider.name, model, start_time, False, "validation", stream=False)
                    raise

                except AuthenticationError as e:
                    # Authentication errors are not retryable - fail immediately
                    logger.error(f"{req_prefix}✗ {provider.name}: authentication error (model={model}) - {e}")
                    if self.metrics:
                        self.metrics.record_request_complete(provider.name, model, start_time, False, "auth", stream=False)
                    raise

                except Exception as e:
                    logger.error(f"{req_prefix}✗ {provider.name} (model={model}): {e}")
                    last_error = e
                    break

        # All providers failed
        if self.metrics:
            error_type = "rate_limit" if isinstance(last_error, RateLimitError) else "timeout" if isinstance(last_error, TimeoutError) else "unknown"
            self.metrics.record_request_complete("none", model, start_time, False, error_type, stream=False)
        if last_error:
            raise last_error
        raise Exception("All providers are in cooldown or failed")

    async def stream_message(
        self,
        body: Dict[str, Any],
        token: str,
        auth_type: str,
        headers: Optional[Dict[str, str]] = None,
        request_id: Optional[str] = None
    ) -> AsyncIterator[str]:
        """Stream message with automatic fallback."""
        start_time = time.time()
        last_error = None
        req_prefix = f"[{request_id}] " if request_id else ""
        model = body.get("model", "unknown")

        for provider in self.providers:
            # Skip providers in cooldown
            if self._is_in_cooldown(provider.name):
                logger.debug(f"{req_prefix}Skipping {provider.name} (cooldown)")
                continue

            # Retry logic for the current provider
            max_retries = config.BEDROCK_MAX_RETRIES if provider.name == "bedrock" else 1
            for attempt in range(max_retries):
                try:
                    if attempt > 0:
                        logger.info(f"{req_prefix}↻ {provider.name} stream (retry {attempt}/{max_retries}, model={model})")
                    else:
                        logger.info(f"{req_prefix}⟳ {provider.name} (model={model})")

                    chunk_count = 0
                    all_chunks = []
                    async for chunk in provider.stream_message(body, token, auth_type, headers, request_id):
                        chunk_count += 1
                        # Capture chunks for short stream analysis
                        if chunk_count <= 20:
                            all_chunks.append(chunk)
                        # Log first chunk for debugging
                        if chunk_count == 1:
                            logger.debug(f"{req_prefix}{provider.name} first chunk: {chunk[:100]}...")
                        yield chunk

                    # Log suspiciously short streams with complete response
                    if chunk_count < 20:
                        full_response = "".join(all_chunks)
                        logger.warning(f"{req_prefix}⚠️  Short stream detected: {chunk_count} chunks (model={model}, max_tokens={body.get('max_tokens')}, thinking={body.get('thinking') is not None})")
                        logger.warning(f"{req_prefix}Full response:\n{full_response}")

                    logger.info(f"{req_prefix}✓ {provider.name} stream ({chunk_count} chunks, model={model})")
                    if self.metrics:
                        self.metrics.record_request_complete(provider.name, model, start_time, True, stream=True)
                    return

                except TimeoutError as e:
                    logger.warning(f"{req_prefix}⏱ {provider.name}: stream timeout (attempt {attempt + 1}/{max_retries})")
                    last_error = e
                    if attempt + 1 >= max_retries:
                        # Exhausted retries, move to next provider
                        break
                    # Retry the same provider
                    continue

                except RateLimitError as e:
                    retry_after = getattr(e, 'retry_after', None)
                    if retry_after:
                        logger.warning(f"{req_prefix}✗ {provider.name}: rate limit (attempt {attempt + 1}/{max_retries}) - retry after {retry_after}s")
                    else:
                        logger.warning(f"{req_prefix}✗ {provider.name}: rate limit (attempt {attempt + 1}/{max_retries})")
                    last_error = e
                    # Anthropic: put in cooldown, move to next provider
                    if provider.name != "bedrock":
                        self._set_cooldown(provider.name, retry_after)
                        if self.metrics:
                            self.metrics.record_fallback(provider.name, "bedrock", "rate_limit")
                        break
                    # Bedrock: retry with exponential backoff (never goes in cooldown)
                    if attempt + 1 >= max_retries:
                        logger.error(f"{req_prefix}✗ {provider.name}: exhausted retries on rate limit")
                        break
                    # Exponential backoff: 2s, 4s, 8s, etc.
                    backoff = 2 ** attempt
                    logger.info(f"{req_prefix}⏸ Waiting {backoff}s before retry...")
                    await asyncio.sleep(backoff)
                    continue

                except ValidationError as e:
                    # Validation errors are client errors - don't retry with other providers
                    logger.error(f"{req_prefix}✗ {provider.name}: validation error - {e}")
                    if self.metrics:
                        self.metrics.record_request_complete(provider.name, model, start_time, False, "validation", stream=True)
                    raise

                except AuthenticationError as e:
                    # Authentication errors are not retryable - fail immediately
                    logger.error(f"{req_prefix}✗ {provider.name}: authentication error - {e}")
                    if self.metrics:
                        self.metrics.record_request_complete(provider.name, model, start_time, False, "auth", stream=True)
                    raise

                except Exception as e:
                    logger.error(f"{req_prefix}✗ {provider.name}: {e}")
                    last_error = e
                    break

        # All providers failed
        if self.metrics:
            error_type = "rate_limit" if isinstance(last_error, RateLimitError) else "timeout" if isinstance(last_error, TimeoutError) else "unknown"
            self.metrics.record_request_complete("none", model, start_time, False, error_type, stream=True)
        if last_error:
            raise last_error
        raise Exception("All providers are in cooldown or failed")