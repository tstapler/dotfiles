"""Fallback handler for provider orchestration."""
import time
from typing import Dict, Any, List, AsyncIterator, Optional
from providers import Provider, RateLimitError, ValidationError
import config


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
        print(f"Provider {provider_name} in cooldown for {seconds} seconds")

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
                print(f"Skipping {provider.name} (in cooldown)")
                continue

            try:
                print(f"Trying provider: {provider.name}")
                result = await provider.send_message(body, token, auth_type, headers)
                print(f"Success with provider: {provider.name}")
                return result

            except RateLimitError as e:
                print(f"Rate limit on {provider.name}: {e}")
                self._set_cooldown(provider.name)
                last_error = e
                continue

            except ValidationError as e:
                # Validation errors are client errors - don't retry with other providers
                print(f"Validation error from {provider.name}: {e}")
                raise

            except Exception as e:
                print(f"Error with {provider.name}: {e}")
                last_error = e
                continue

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
                print(f"Skipping {provider.name} (in cooldown)")
                continue

            try:
                print(f"Trying streaming with provider: {provider.name}")
                async for chunk in provider.stream_message(body, token, auth_type, headers):
                    yield chunk
                print(f"Stream completed with provider: {provider.name}")
                return

            except RateLimitError as e:
                print(f"Rate limit on {provider.name}: {e}")
                self._set_cooldown(provider.name)
                last_error = e
                continue

            except ValidationError as e:
                # Validation errors are client errors - don't retry with other providers
                print(f"Validation error from {provider.name}: {e}")
                raise

            except Exception as e:
                print(f"Error with {provider.name}: {e}")
                last_error = e
                continue

        # All providers failed
        if last_error:
            raise last_error
        raise Exception("All providers are in cooldown or failed")