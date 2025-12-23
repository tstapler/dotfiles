"""Provider interface and exceptions."""
from abc import ABC, abstractmethod
from typing import Dict, Any, AsyncIterator, Optional


class RateLimitError(Exception):
    """Raised when a provider hits rate limits."""
    pass


class ValidationError(Exception):
    """Raised when request parameters are invalid (4xx errors)."""
    pass


class Provider(ABC):
    """Abstract base class for API providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Return provider name."""
        pass

    @abstractmethod
    async def send_message(
        self,
        body: Dict[str, Any],
        token: str,
        auth_type: str,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Send a message and return the response."""
        pass

    @abstractmethod
    async def stream_message(
        self,
        body: Dict[str, Any],
        token: str,
        auth_type: str,
        headers: Optional[Dict[str, str]] = None
    ) -> AsyncIterator[str]:
        """Stream a message response."""
        pass

    def normalize_model_name(self, model: str) -> str:
        """Normalize model name for the provider."""
        # Remove Bedrock prefixes if present
        if model.startswith("us.anthropic."):
            model = model.replace("us.anthropic.", "")
            # Remove version suffix (e.g., -v1:0)
            import re
            model = re.sub(r'-v\d+:\d+$', '', model)
        return model