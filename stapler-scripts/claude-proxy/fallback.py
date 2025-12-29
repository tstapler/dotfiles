"""Fallback handler for provider orchestration."""
import time
import logging
from typing import Dict, Any, List, AsyncIterator, Optional
from providers import Provider, RateLimitError, ValidationError, TimeoutError
import config

logger = logging.getLogger(__name__)


class FallbackHandler:
    """Orchestrates providers with automatic fallback on rate limits."""

    def __init__(self, providers: List[Provider]):
        self.providers = providers
        self.cooldowns: Dict[str, float] = {}

    def _is_in_cooldown(self, provider_name: str) -> bool:
        """Check if provider is in cooldown period."""
        if provider_name not in self.cooldowns:
            return False
        return time.time() < self.cooldowns[provider_name]

    def _set_cooldown(self, provider_name: str, seconds: int = None):
        """Set cooldown for a provider."""
        if seconds is None:
            seconds = config.COOLDOWN_SECONDS
        self.cooldowns[provider_name] = time.time() + seconds
        logger.warning(f"Provider {provider_name} in cooldown for {seconds}s")

    async def send_message(
        self,
        body: Dict[str, Any],
        token: str,
        auth_type: str,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Send message with automatic fallback."""
        last_error = None

        for provider in self.providers:
            # Skip providers in cooldown
            if self._is_in_cooldown(provider.name):
                logger.debug(f"Skipping {provider.name} (cooldown)")
                continue

            # Retry logic for the current provider
            max_retries = config.BEDROCK_MAX_RETRIES if provider.name == "bedrock" else 1
            for attempt in range(max_retries):
                try:
                    if attempt > 0:
                        logger.info(f"↻ {provider.name} (retry {attempt}/{max_retries})")
                    else:
                        logger.info(f"→ {provider.name}")

                    result = await provider.send_message(body, token, auth_type, headers)
                    logger.info(f"✓ {provider.name}")
                    return result

                except TimeoutError as e:
                    logger.warning(f"⏱ {provider.name}: timeout (attempt {attempt + 1}/{max_retries})")
                    last_error = e
                    if attempt + 1 >= max_retries:
                        # Exhausted retries, move to next provider
                        break
                    # Retry the same provider
                    continue

                except RateLimitError as e:
                    logger.warning(f"✗ {provider.name}: rate limit")
                    # Only put Anthropic in cooldown, never Bedrock
                    if provider.name != "bedrock":
                        self._set_cooldown(provider.name)
                    last_error = e
                    break

                except ValidationError as e:
                    # Validation errors are client errors - don't retry with other providers
                    logger.error(f"✗ {provider.name}: validation error - {e}")
                    raise

                except Exception as e:
                    logger.error(f"✗ {provider.name}: {e}")
                    last_error = e
                    break

        # All providers failed
        if last_error:
            raise last_error
        raise Exception("All providers are in cooldown or failed")

    async def stream_message(
        self,
        body: Dict[str, Any],
        token: str,
        auth_type: str,
        headers: Optional[Dict[str, str]] = None
    ) -> AsyncIterator[str]:
        """Stream message with automatic fallback."""
        last_error = None

        for provider in self.providers:
            # Skip providers in cooldown
            if self._is_in_cooldown(provider.name):
                logger.debug(f"Skipping {provider.name} (cooldown)")
                continue

            # Retry logic for the current provider
            max_retries = config.BEDROCK_MAX_RETRIES if provider.name == "bedrock" else 1
            for attempt in range(max_retries):
                try:
                    if attempt > 0:
                        logger.info(f"↻ {provider.name} stream (retry {attempt}/{max_retries})")
                    else:
                        logger.info(f"⟳ {provider.name}")

                    async for chunk in provider.stream_message(body, token, auth_type, headers):
                        yield chunk
                    logger.info(f"✓ {provider.name} stream")
                    return

                except TimeoutError as e:
                    logger.warning(f"⏱ {provider.name}: stream timeout (attempt {attempt + 1}/{max_retries})")
                    last_error = e
                    if attempt + 1 >= max_retries:
                        # Exhausted retries, move to next provider
                        break
                    # Retry the same provider
                    continue

                except RateLimitError as e:
                    logger.warning(f"✗ {provider.name}: rate limit")
                    # Only put Anthropic in cooldown, never Bedrock
                    if provider.name != "bedrock":
                        self._set_cooldown(provider.name)
                    last_error = e
                    break

                except ValidationError as e:
                    # Validation errors are client errors - don't retry with other providers
                    logger.error(f"✗ {provider.name}: validation error - {e}")
                    raise

                except Exception as e:
                    logger.error(f"✗ {provider.name}: {e}")
                    last_error = e
                    break

        # All providers failed
        if last_error:
            raise last_error
        raise Exception("All providers are in cooldown or failed")