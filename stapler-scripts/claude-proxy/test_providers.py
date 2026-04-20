"""Unit tests for claude-proxy providers.

Tests the pure logic functions that don't require live AWS/Anthropic connections.
"""
import json
import pytest
import asyncio
from unittest.mock import MagicMock, patch, call, AsyncMock


@pytest.fixture(autouse=True)
def disable_compression(monkeypatch):
    """Ensure all existing provider tests bypass compression."""
    monkeypatch.setenv("STAPLER_COMPRESS", "0")


# ---------------------------------------------------------------------------
# Helpers to instantiate providers without real AWS/Anthropic connections
# ---------------------------------------------------------------------------

def make_bedrock_provider():
    """Create a BedrockProvider with all external dependencies mocked."""
    with patch("providers.bedrock.boto3.Session") as mock_session, \
         patch("providers.bedrock.ThreadPoolExecutor"), \
         patch("providers.bedrock.Cache"), \
         patch("providers.bedrock.config"):
        mock_session.return_value.client.return_value = MagicMock()
        from providers.bedrock import BedrockProvider
        provider = BedrockProvider()
        # Give the mock client some exception classes for _handle_bedrock_error
        provider.client.exceptions.ThrottlingException = type("ThrottlingException", (Exception,), {})
        provider.client.exceptions.ValidationException = type("ValidationException", (Exception,), {})
        return provider


def make_anthropic_provider():
    """Create an AnthropicProvider (no external deps in __init__)."""
    with patch("providers.anthropic.httpx.AsyncClient"):
        from providers.anthropic import AnthropicProvider
        return AnthropicProvider()


# ===========================================================================
# BedrockProvider._is_beta_compatible_with_model
# ===========================================================================

class TestIsBetaCompatibleWithModel:
    def setup_method(self):
        self.provider = make_bedrock_provider()

    def test_compatible_model_matches_prefix(self):
        assert self.provider._is_beta_compatible_with_model(
            "token-efficient-tools-2025-02-19", "claude-sonnet-4-20250514"
        )

    def test_compatible_exact_prefix_haiku(self):
        assert self.provider._is_beta_compatible_with_model(
            "token-efficient-tools-2025-02-19", "claude-haiku-4-5-20251001"
        )

    def test_incompatible_model_returns_false(self):
        # computer-use only for claude-3-7-sonnet
        assert not self.provider._is_beta_compatible_with_model(
            "computer-use-2025-01-24", "claude-sonnet-4-20250514"
        )

    def test_unsupported_beta_returns_false(self):
        assert not self.provider._is_beta_compatible_with_model(
            "nonexistent-beta-flag", "claude-sonnet-4-20250514"
        )

    def test_computer_use_matches_claude_3_7_sonnet(self):
        assert self.provider._is_beta_compatible_with_model(
            "computer-use-2025-01-24", "claude-3-7-sonnet-20250219"
        )


# ===========================================================================
# BedrockProvider._prepare_bedrock_body
# ===========================================================================

class TestPrepareBedrockBody:
    def setup_method(self):
        self.provider = make_bedrock_provider()

    def _prepare(self, body, model="claude-sonnet-4-20250514", headers=None):
        return self.provider._prepare_bedrock_body(body, model, headers)

    def test_adds_anthropic_version(self):
        result = self._prepare({"messages": []})
        assert result["anthropic_version"] == "bedrock-2023-05-31"

    def test_removes_unsupported_top_level_fields(self):
        body = {
            "model": "claude-sonnet-4-20250514",
            "stream": True,
            "output_config": {"effort": "high"},
            "context_management": {"enabled": True},
            "messages": [],
        }
        result = self._prepare(body)
        # All of these fields must be stripped (Anthropic-specific, not supported by Bedrock):
        # - model, stream: conveyed via modelId parameter and API method selection
        # - output_config: Anthropic-specific effort parameter
        # - context_management: Anthropic-specific prompt caching field (causes ValidationException on Bedrock)
        for field in ("model", "stream", "output_config", "context_management"):
            assert field not in result, f"Expected {field!r} to be stripped but it was present"

    def test_cleans_tools_removes_unsupported_fields(self):
        body = {
            "messages": [],
            "tools": [
                {
                    "name": "bash",
                    "description": "Run bash",
                    "input_schema": {},
                    "defer_loading": True,
                    "input_examples": ["ls -la"],
                    "custom": {"meta": "data"},
                    "cache_control": {"type": "ephemeral"},
                },
            ],
        }
        result = self._prepare(body)
        tool = result["tools"][0]
        assert "name" in tool
        assert "description" in tool
        assert "defer_loading" not in tool
        assert "input_examples" not in tool
        assert "custom" not in tool
        assert "cache_control" not in tool

    def test_clean_tools_preserves_clean_tools(self):
        body = {
            "messages": [],
            "tools": [{"name": "read_file", "description": "Read a file", "input_schema": {}}],
        }
        result = self._prepare(body)
        assert result["tools"][0]["name"] == "read_file"

    def test_thinking_budget_capped_to_max_tokens(self):
        body = {
            "messages": [],
            "max_tokens": 2000,
            "thinking": {"type": "enabled", "budget_tokens": 5000},
        }
        result = self._prepare(body)
        assert result["thinking"]["budget_tokens"] == 2000

    def test_thinking_removed_when_max_tokens_too_small(self):
        body = {
            "messages": [],
            "max_tokens": 500,
            "thinking": {"type": "enabled", "budget_tokens": 1000},
        }
        result = self._prepare(body)
        assert "thinking" not in result

    def test_thinking_budget_raised_to_minimum(self):
        body = {
            "messages": [],
            "max_tokens": 4096,
            "thinking": {"type": "enabled", "budget_tokens": 256},
        }
        result = self._prepare(body)
        assert result["thinking"]["budget_tokens"] == 1024

    def test_thinking_valid_budget_unchanged(self):
        body = {
            "messages": [],
            "max_tokens": 4096,
            "thinking": {"type": "enabled", "budget_tokens": 2048},
        }
        result = self._prepare(body)
        assert result["thinking"]["budget_tokens"] == 2048

    def test_beta_compatible_flags_added_to_body(self):
        body = {"messages": []}
        headers = {"anthropic-beta": "token-efficient-tools-2025-02-19"}
        result = self._prepare(body, model="claude-sonnet-4-20250514", headers=headers)
        assert "token-efficient-tools-2025-02-19" in result.get("anthropic_beta", [])

    def test_beta_incompatible_flags_filtered(self):
        body = {"messages": []}
        # computer-use only works with claude-3-7-sonnet, not claude-sonnet-4
        headers = {"anthropic-beta": "computer-use-2025-01-24"}
        result = self._prepare(body, model="claude-sonnet-4-20250514", headers=headers)
        assert "anthropic_beta" not in result

    def test_beta_unsupported_flags_filtered(self):
        body = {"messages": []}
        headers = {"anthropic-beta": "totally-fake-beta-flag"}
        result = self._prepare(body, model="claude-sonnet-4-20250514", headers=headers)
        assert "anthropic_beta" not in result

    def test_beta_mixed_flags_only_compatible_included(self):
        body = {"messages": []}
        headers = {
            "anthropic-beta": "token-efficient-tools-2025-02-19,computer-use-2025-01-24,fake-flag"
        }
        result = self._prepare(body, model="claude-sonnet-4-20250514", headers=headers)
        betas = result.get("anthropic_beta", [])
        assert "token-efficient-tools-2025-02-19" in betas
        assert "computer-use-2025-01-24" not in betas
        assert "fake-flag" not in betas

    def test_no_beta_header_no_anthropic_beta_field(self):
        body = {"messages": []}
        result = self._prepare(body)
        assert "anthropic_beta" not in result

    def test_does_not_mutate_original_body(self):
        body = {
            "model": "claude-sonnet-4-20250514",
            "messages": [],
            "tools": [{"name": "bash", "defer_loading": True}],
        }
        original = json.dumps(body, sort_keys=True)
        self._prepare(body)
        assert json.dumps(body, sort_keys=True) == original


# ===========================================================================
# BedrockProvider._stream_bedrock_sync — event routing
# ===========================================================================

class TestStreamBedrockSync:
    """Test the sync streaming helper that sends events to anyio stream."""

    def setup_method(self):
        self.provider = make_bedrock_provider()

    def _make_event(self, chunk_type: str, **extra):
        chunk = {"type": chunk_type, **extra}
        return {"chunk": {"bytes": json.dumps(chunk).encode()}}

    def test_content_block_delta_sent_to_stream(self):
        send_stream = MagicMock()
        delta = {"type": "text_delta", "text": "hello"}
        events = [self._make_event("content_block_delta", index=0, delta=delta)]
        self.provider.client.invoke_model_with_response_stream.return_value = {
            "body": events
        }

        with patch("providers.bedrock.anyio.from_thread.run") as mock_run:
            self.provider._stream_bedrock_sync(send_stream, "us.anthropic.claude-sonnet-4", {})

        # First call should be send with the SSE data, last call closes the stream
        run_calls = mock_run.call_args_list
        send_calls = [c for c in run_calls if c.args[0] == send_stream.send]
        assert len(send_calls) == 1
        sse_payload = send_calls[0].args[1]
        assert "content_block_delta" in sse_payload

    def test_message_stop_sends_anthropic_format(self):
        send_stream = MagicMock()
        events = [self._make_event("message_stop")]
        self.provider.client.invoke_model_with_response_stream.return_value = {
            "body": events
        }

        with patch("providers.bedrock.anyio.from_thread.run") as mock_run:
            self.provider._stream_bedrock_sync(send_stream, "us.anthropic.claude-sonnet-4", {})

        run_calls = mock_run.call_args_list
        send_calls = [c for c in run_calls if c.args[0] == send_stream.send]
        assert len(send_calls) == 1
        payload = send_calls[0].args[1]
        assert "message_stop" in payload
        assert payload.startswith("data: ")
        assert payload.endswith("\n\n")

    def test_all_event_types_forwarded(self):
        """All Bedrock event types should be forwarded directly, not filtered."""
        send_stream = MagicMock()
        events = [self._make_event("ping"), self._make_event("message_start")]
        self.provider.client.invoke_model_with_response_stream.return_value = {
            "body": events
        }

        with patch("providers.bedrock.anyio.from_thread.run") as mock_run:
            self.provider._stream_bedrock_sync(send_stream, "us.anthropic.claude-sonnet-4", {})

        run_calls = mock_run.call_args_list
        send_calls = [c for c in run_calls if c.args[0] == send_stream.send]
        assert len(send_calls) == 2  # Both ping and message_start forwarded

    def test_stream_always_closed_in_finally(self):
        send_stream = MagicMock()
        self.provider.client.invoke_model_with_response_stream.return_value = {
            "body": []
        }

        with patch("providers.bedrock.anyio.from_thread.run") as mock_run:
            self.provider._stream_bedrock_sync(send_stream, "us.anthropic.claude-sonnet-4", {})

        # Last call should be aclose
        last_call = mock_run.call_args_list[-1]
        assert last_call.args[0] == send_stream.aclose

    def test_stream_closed_even_on_exception(self):
        send_stream = MagicMock()
        self.provider.client.invoke_model_with_response_stream.side_effect = RuntimeError("network error")

        with patch("providers.bedrock.anyio.from_thread.run") as mock_run:
            try:
                self.provider._stream_bedrock_sync(send_stream, "us.anthropic.claude-sonnet-4", {})
            except Exception:
                pass

        close_calls = [c for c in mock_run.call_args_list if c.args[0] == send_stream.aclose]
        assert len(close_calls) == 1


# ===========================================================================
# Provider._clean_message_content  (base class, shared by both providers)
# ===========================================================================

class TestCleanMessageContent:
    def setup_method(self):
        # Use AnthropicProvider since Provider is abstract
        self.provider = make_anthropic_provider()

    def test_removes_tool_reference_from_tool_result(self):
        body = {
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": "x",
                            "content": [
                                {"type": "text", "text": "ok"},
                                {"type": "tool_reference", "ref": "something"},
                            ],
                        }
                    ],
                }
            ]
        }
        result = self.provider._clean_message_content(body)
        content = result["messages"][0]["content"][0]["content"]
        assert len(content) == 1
        assert content[0]["type"] == "text"

    def test_preserves_valid_content_types(self):
        body = {
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": "x",
                            "content": [
                                {"type": "text", "text": "a"},
                                {"type": "image", "source": {}},
                                {"type": "document", "source": {}},
                                {"type": "search_result", "source": {}},
                            ],
                        }
                    ],
                }
            ]
        }
        result = self.provider._clean_message_content(body)
        content = result["messages"][0]["content"][0]["content"]
        assert len(content) == 4

    def test_does_not_mutate_original(self):
        body = {
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": "x",
                            "content": [{"type": "tool_reference"}],
                        }
                    ],
                }
            ]
        }
        original_len = len(body["messages"][0]["content"][0]["content"])
        self.provider._clean_message_content(body)
        assert len(body["messages"][0]["content"][0]["content"]) == original_len


# ===========================================================================
# AnthropicProvider._clean_request_body — cache_control.ephemeral.scope
# ===========================================================================

class TestAnthropicCleanRequestBody:
    def setup_method(self):
        self.provider = make_anthropic_provider()

    def test_removes_scope_from_ephemeral_cache_control(self):
        body = {
            "system": [
                {
                    "type": "text",
                    "text": "You are an assistant.",
                    "cache_control": {"ephemeral": {"scope": "session"}},
                }
            ],
            "messages": [],
        }
        result = self.provider._clean_request_body(body)
        ephemeral = result["system"][0]["cache_control"]["ephemeral"]
        assert "scope" not in ephemeral

    def test_leaves_other_cache_control_fields_intact(self):
        body = {
            "system": [
                {
                    "type": "text",
                    "text": "system",
                    "cache_control": {"ephemeral": {"scope": "session", "ttl": 300}},
                }
            ],
            "messages": [],
        }
        result = self.provider._clean_request_body(body)
        ephemeral = result["system"][0]["cache_control"]["ephemeral"]
        assert "scope" not in ephemeral
        assert ephemeral.get("ttl") == 300

    def test_noop_when_no_system(self):
        body = {"messages": [{"role": "user", "content": "hi"}]}
        result = self.provider._clean_request_body(body)
        assert "system" not in result

    def test_noop_when_system_has_no_cache_control(self):
        body = {
            "system": [{"type": "text", "text": "plain"}],
            "messages": [],
        }
        result = self.provider._clean_request_body(body)
        assert "cache_control" not in result["system"][0]

    def test_noop_when_ephemeral_has_no_scope(self):
        body = {
            "system": [
                {
                    "type": "text",
                    "text": "text",
                    "cache_control": {"ephemeral": {"ttl": 60}},
                }
            ],
            "messages": [],
        }
        result = self.provider._clean_request_body(body)
        assert result["system"][0]["cache_control"]["ephemeral"] == {"ttl": 60}

    def test_does_not_mutate_original_body(self):
        body = {
            "system": [
                {
                    "type": "text",
                    "text": "x",
                    "cache_control": {"ephemeral": {"scope": "session"}},
                }
            ],
            "messages": [],
        }
        original = json.dumps(body, sort_keys=True)
        self.provider._clean_request_body(body)
        assert json.dumps(body, sort_keys=True) == original

    def test_handles_non_list_system_gracefully(self):
        body = {"system": "plain string system", "messages": []}
        # Should not raise
        result = self.provider._clean_request_body(body)
        assert result["system"] == "plain string system"


# ===========================================================================
# AnthropicProvider._get_supported_models — model lookup and caching
# ===========================================================================

class TestGetSupportedModels:
    def setup_method(self):
        from providers.anthropic import _model_cache
        _model_cache.clear()

    @pytest.mark.asyncio
    async def test_fetches_and_caches_model_list(self):
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {"id": "claude-sonnet-4-6"},
                {"id": "claude-opus-4-6"},
                {"id": "claude-haiku-4-5-20251001"},
            ]
        }
        mock_client.get.return_value = mock_response

        with patch("providers.anthropic.httpx.AsyncClient", return_value=mock_client):
            from providers.anthropic import AnthropicProvider
            provider = AnthropicProvider()
            result = await provider._get_supported_models("token", "oauth")

        assert "claude-sonnet-4-6" in result
        assert "claude-opus-4-6" in result
        assert "claude-haiku-4-5-20251001" in result
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_returns_cached_result_on_second_call(self):
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [{"id": "claude-sonnet-4-6"}]
        }
        mock_client.get.return_value = mock_response

        with patch("providers.anthropic.httpx.AsyncClient", return_value=mock_client):
            from providers.anthropic import AnthropicProvider
            provider = AnthropicProvider()

            # First call
            result1 = await provider._get_supported_models("token", "oauth")
            # Second call
            result2 = await provider._get_supported_models("token", "oauth")

        # Should only call API once (cached)
        assert mock_client.get.call_count == 1
        assert result1 == result2

    @pytest.mark.asyncio
    async def test_returns_empty_set_on_api_error(self):
        mock_client = AsyncMock()
        mock_client.get.side_effect = Exception("Network error")

        with patch("providers.anthropic.httpx.AsyncClient", return_value=mock_client):
            from providers.anthropic import AnthropicProvider
            provider = AnthropicProvider()
            result = await provider._get_supported_models("token", "oauth")

        assert result == set()

    @pytest.mark.asyncio
    async def test_returns_empty_set_on_non_200_status(self):
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_client.get.return_value = mock_response

        with patch("providers.anthropic.httpx.AsyncClient", return_value=mock_client):
            from providers.anthropic import AnthropicProvider
            provider = AnthropicProvider()
            result = await provider._get_supported_models("token", "oauth")

        assert result == set()


# ===========================================================================
# Model validation in send_message and stream_message
# ===========================================================================

class TestModelValidation:
    def setup_method(self):
        from providers.anthropic import _model_cache
        _model_cache.clear()

    @pytest.mark.asyncio
    async def test_send_message_raises_when_model_not_supported(self):
        from providers import ModelUnsupportedError

        mock_client = AsyncMock()

        with patch("providers.anthropic.httpx.AsyncClient", return_value=mock_client):
            from providers.anthropic import AnthropicProvider
            provider = AnthropicProvider()

            # Mock _get_supported_models to return limited set
            async def mock_get_models(token, auth_type):
                return {"claude-sonnet-4-6", "claude-opus-4-6"}

            provider._get_supported_models = mock_get_models

            body = {"model": "claude-unsupported-model", "messages": []}

            with pytest.raises(ModelUnsupportedError, match="not available on Anthropic API"):
                await provider.send_message(body, "token", "oauth", request_id="req123")

    @pytest.mark.asyncio
    async def test_send_message_allows_supported_model(self):
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "msg_123", "content": []}
        mock_client.post.return_value = mock_response

        with patch("providers.anthropic.httpx.AsyncClient", return_value=mock_client):
            from providers.anthropic import AnthropicProvider
            provider = AnthropicProvider()

            # Mock _get_supported_models to return model list
            async def mock_get_models(token, auth_type):
                return {"claude-sonnet-4-6"}

            provider._get_supported_models = mock_get_models

            body = {"model": "claude-sonnet-4-6", "messages": []}

            # Should not raise
            result = await provider.send_message(body, "token", "oauth", request_id="req123")
            assert result["id"] == "msg_123"

    @pytest.mark.asyncio
    async def test_send_message_skips_check_when_api_returns_empty(self):
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "msg_123"}
        mock_client.post.return_value = mock_response

        with patch("providers.anthropic.httpx.AsyncClient", return_value=mock_client):
            from providers.anthropic import AnthropicProvider
            provider = AnthropicProvider()

            # Mock _get_supported_models to return empty set (API error)
            async def mock_get_models(token, auth_type):
                return set()

            provider._get_supported_models = mock_get_models

            body = {"model": "claude-any-model", "messages": []}

            # Should not raise even though model might not be supported
            # (fallback to attempting the request)
            result = await provider.send_message(body, "token", "oauth", request_id="req123")
            assert result["id"] == "msg_123"


# ===========================================================================
# FallbackHandler — provider selection and error handling
# ===========================================================================

class TestFallbackHandler:
    def setup_method(self):
        # Mock providers
        self.anthropic = MagicMock()
        self.anthropic.name = "anthropic"
        self.anthropic.send_message = AsyncMock()
        self.anthropic.stream_message = AsyncMock()

        self.bedrock = MagicMock()
        self.bedrock.name = "bedrock"
        self.bedrock.send_message = AsyncMock()
        self.bedrock.stream_message = AsyncMock()

        # Mock diskcache and config
        with patch("fallback.diskcache.Cache") as mock_cache_cls, \
             patch("fallback.config"):
            mock_cache = MagicMock()
            mock_cache.get.return_value = None  # No cooldowns by default
            mock_cache.__iter__.return_value = iter([])  # Empty cooldowns
            mock_cache_cls.return_value = mock_cache

            from fallback import FallbackHandler
            self.handler = FallbackHandler([self.anthropic, self.bedrock])
            self.mock_cooldowns = mock_cache

    @pytest.mark.asyncio
    async def test_tries_anthropic_first_when_not_in_cooldown(self):
        self.anthropic.send_message.return_value = {"id": "msg_123"}

        result = await self.handler.send_message({}, "token", "oauth", "req123")

        assert result["id"] == "msg_123"
        self.anthropic.send_message.assert_called_once()
        self.bedrock.send_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_falls_back_to_bedrock_on_rate_limit(self):
        from providers import RateLimitError

        self.anthropic.send_message.side_effect = RateLimitError("Rate limited")
        self.bedrock.send_message.return_value = {"id": "msg_456"}

        result = await self.handler.send_message({}, "token", "oauth", "req123")

        assert result["id"] == "msg_456"
        self.anthropic.send_message.assert_called_once()
        self.bedrock.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_does_not_fall_back_on_validation_error(self):
        from providers import ValidationError

        self.anthropic.send_message.side_effect = ValidationError("Bad request")

        with pytest.raises(ValidationError):
            await self.handler.send_message({}, "token", "oauth", "req123")

        self.anthropic.send_message.assert_called_once()
        self.bedrock.send_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_falls_back_on_model_unsupported_error(self):
        from providers import ModelUnsupportedError

        self.anthropic.send_message.side_effect = ModelUnsupportedError("Model not supported")
        self.bedrock.send_message.return_value = {"id": "msg_789"}

        result = await self.handler.send_message({}, "token", "oauth", "req123")

        assert result["id"] == "msg_789"
        # Should try both providers
        self.anthropic.send_message.assert_called_once()
        self.bedrock.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_retries_bedrock_on_timeout(self):
        from providers import TimeoutError
        import time

        # Mock config to set max retries
        with patch("fallback.config") as mock_config:
            mock_config.BEDROCK_MAX_RETRIES = 3

            # Set anthropic in cooldown, bedrock not in cooldown
            def get_cooldown(provider_name):
                if provider_name == "anthropic":
                    return time.time() + 9999  # In cooldown
                return None  # Not in cooldown

            self.mock_cooldowns.get.side_effect = get_cooldown

            # First call times out, second succeeds
            self.bedrock.send_message.side_effect = [
                TimeoutError("Timeout"),
                {"id": "msg_retry"}
            ]

            result = await self.handler.send_message({}, "token", "oauth", "req123")

            assert result["id"] == "msg_retry"
            assert self.bedrock.send_message.call_count == 2


# ===========================================================================
# BedrockProvider._handle_bedrock_error — error classification
# ===========================================================================

class TestHandleBedrockError:
    def setup_method(self):
        self.provider = make_bedrock_provider()

    def test_throttling_exception_raises_rate_limit_error(self):
        from providers import RateLimitError

        error = self.provider.client.exceptions.ThrottlingException(
            {"Error": {"Message": "Rate exceeded"}},
            "invoke_model"
        )

        with pytest.raises(RateLimitError, match="Bedrock rate limit"):
            self.provider._handle_bedrock_error(error)

    def test_validation_exception_raises_validation_error(self):
        from providers import ValidationError

        error = self.provider.client.exceptions.ValidationException(
            {"Error": {"Message": "Invalid model"}},
            "invoke_model"
        )

        with pytest.raises(ValidationError, match="Bedrock validation"):
            self.provider._handle_bedrock_error(error)

    def test_timeout_in_message_raises_timeout_error(self):
        from providers import TimeoutError

        error = Exception("Timeout waiting for response")

        with pytest.raises(TimeoutError, match="timeout"):
            self.provider._handle_bedrock_error(error)

    def test_read_timeout_raises_timeout_error(self):
        from providers import TimeoutError
        from botocore.exceptions import ReadTimeoutError

        error = ReadTimeoutError(endpoint_url="https://example.com")

        with pytest.raises(TimeoutError):
            self.provider._handle_bedrock_error(error)

    def test_connect_timeout_raises_timeout_error(self):
        from providers import TimeoutError
        from botocore.exceptions import ConnectTimeoutError

        error = ConnectTimeoutError(endpoint_url="https://example.com")

        with pytest.raises(TimeoutError):
            self.provider._handle_bedrock_error(error)

    def test_expired_credentials_raises_auth_error(self):
        from providers import AuthenticationError

        error = Exception("The security token expired")

        with pytest.raises(AuthenticationError, match="credentials expired"):
            self.provider._handle_bedrock_error(error)

    def test_generic_exception_re_raises(self):
        # _handle_bedrock_error expects to be called in an exception context
        # (it uses bare 'raise' at the end)
        try:
            raise Exception("Unknown error")
        except Exception as e:
            with pytest.raises(Exception, match="Unknown error"):
                self.provider._handle_bedrock_error(e)
