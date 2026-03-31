"""Provider interface and exceptions."""
from abc import ABC, abstractmethod
from typing import Dict, Any, AsyncIterator, Optional


class RateLimitError(Exception):
    """Raised when a provider hits rate limits."""
    def __init__(self, message: str, retry_after: int = None):
        super().__init__(message)
        self.retry_after = retry_after  # seconds to wait before retrying


class ValidationError(Exception):
    """Raised when request parameters are invalid (4xx errors)."""
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


class TimeoutError(Exception):
    """Raised when a request times out (retryable)."""
    pass


class AuthenticationError(Exception):
    """Raised when authentication fails (not retryable)."""
    pass


class ModelUnsupportedError(Exception):
    """Raised when a provider doesn't support the requested model (try next provider)."""
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
        headers: Optional[Dict[str, str]] = None,
        request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send a message and return the response."""
        pass

    @abstractmethod
    async def stream_message(
        self,
        body: Dict[str, Any],
        token: str,
        auth_type: str,
        headers: Optional[Dict[str, str]] = None,
        request_id: Optional[str] = None
    ) -> AsyncIterator[str]:
        """Stream a message response."""
        pass

    def normalize_model_name(self, model: str) -> str:
        """Normalize model name for the provider."""
        # Remove Bedrock prefixes if present
        if model.startswith("us.anthropic."):
            model = model.replace("us.anthropic.", "")
            # Remove version suffix (e.g., -v1:0 or -v1)
            import re
            model = re.sub(r'-v\d+(?::\d+)?$', '', model)
        return model

    def _clean_message_content(self, body: Dict[str, Any]) -> Dict[str, Any]:
        """Clean message content to remove unsupported content types.

        Removes unsupported content types like 'tool_reference' from tool results.
        Both Anthropic API and AWS Bedrock only support: text, image, document, search_result

        Args:
            body: Request body containing messages

        Returns:
            Cleaned request body
        """
        import logging
        logger = logging.getLogger(__name__)

        body = body.copy()

        # Clean message content - remove unsupported content types
        if "messages" in body and isinstance(body["messages"], list):
            cleaned_messages = []
            for msg_idx, message in enumerate(body["messages"]):
                if isinstance(message, dict) and "content" in message:
                    message = message.copy()
                    if isinstance(message["content"], list):
                        cleaned_content = []
                        for content_item in message["content"]:
                            if isinstance(content_item, dict):
                                content_item = content_item.copy()
                                # Clean tool_result content
                                if content_item.get("type") == "tool_result" and "content" in content_item:
                                    if isinstance(content_item["content"], list):
                                        # Filter out unsupported content types like 'tool_reference'
                                        # Supported types: 'text', 'image', 'document', 'search_result'
                                        filtered_content = [
                                            c for c in content_item["content"]
                                            if isinstance(c, dict) and c.get("type") in ["text", "image", "document", "search_result"]
                                        ]
                                        if len(filtered_content) != len(content_item["content"]):
                                            removed_count = len(content_item["content"]) - len(filtered_content)
                                            logger.debug(f"Filtered {removed_count} unsupported content type(s) from message[{msg_idx}].content.tool_result")
                                        content_item["content"] = filtered_content
                            cleaned_content.append(content_item)
                        message["content"] = cleaned_content
                cleaned_messages.append(message)
            body["messages"] = cleaned_messages

        return body