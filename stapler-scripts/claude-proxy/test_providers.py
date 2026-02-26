"""Unit tests for claude-proxy providers.

Tests the pure logic functions that don't require live AWS/Anthropic connections.
"""
import json
import pytest
from unittest.mock import MagicMock, patch, call


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
        for field in ("model", "stream", "output_config", "context_management"):
            assert field not in result

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

    def test_message_stop_sends_done(self):
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
        assert "[DONE]" in send_calls[0].args[1]

    def test_unknown_event_type_ignored(self):
        send_stream = MagicMock()
        events = [self._make_event("ping"), self._make_event("message_start")]
        self.provider.client.invoke_model_with_response_stream.return_value = {
            "body": events
        }

        with patch("providers.bedrock.anyio.from_thread.run") as mock_run:
            self.provider._stream_bedrock_sync(send_stream, "us.anthropic.claude-sonnet-4", {})

        run_calls = mock_run.call_args_list
        send_calls = [c for c in run_calls if c.args[0] == send_stream.send]
        assert len(send_calls) == 0  # No data events sent for ping/message_start

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
