"""Unit tests for compactor.py.

Tests the compression guards, content routing, Rewind injection, and flag
handling in isolation — without live FusionEngine calls.
"""
from __future__ import annotations

import pytest
import asyncio
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _text_message(role: str, text: str) -> dict:
    return {"role": role, "content": text}


def _multipart_message(role: str, parts: list) -> dict:
    return {"role": role, "content": parts}


def _tool_use_block(tool_id: str, name: str, input_: dict) -> dict:
    return {"type": "tool_use", "id": tool_id, "name": name, "input": input_}


def _tool_result_block(tool_use_id: str, content: str) -> dict:
    return {"type": "tool_result", "tool_use_id": tool_use_id, "content": content}


def _text_block(text: str) -> dict:
    return {"type": "text", "text": text}


REWIND_MARKER = "[3 items compressed to 1. Retrieve: hash=abc123def456abc123def456]"


# ---------------------------------------------------------------------------
# TestSentinelGuard — double-compression detection
# ---------------------------------------------------------------------------

class TestSentinelGuard:
    def test_detects_marker_in_string_content(self):
        from compactor import _has_rewind_markers
        messages = [_text_message("assistant", f"Some text\n{REWIND_MARKER}")]
        assert _has_rewind_markers(messages) is True

    def test_detects_marker_in_text_block(self):
        from compactor import _has_rewind_markers
        messages = [_multipart_message("assistant", [_text_block(f"Compressed\n{REWIND_MARKER}")])]
        assert _has_rewind_markers(messages) is True

    def test_detects_marker_in_tool_result_content(self):
        from compactor import _has_rewind_markers
        block = _tool_result_block("tid_1", f"output\n{REWIND_MARKER}")
        messages = [_multipart_message("user", [block])]
        assert _has_rewind_markers(messages) is True

    def test_no_marker_returns_false(self):
        from compactor import _has_rewind_markers
        messages = [
            _text_message("user", "clean message"),
            _text_message("assistant", "clean response"),
        ]
        assert _has_rewind_markers(messages) is False

    def test_empty_messages_returns_false(self):
        from compactor import _has_rewind_markers
        assert _has_rewind_markers([]) is False

    def test_empty_content_returns_false(self):
        from compactor import _has_rewind_markers
        messages = [{"role": "user", "content": ""}]
        assert _has_rewind_markers(messages) is False


# ---------------------------------------------------------------------------
# TestToolProtection — tool_use and tool_result block handling
# ---------------------------------------------------------------------------

class TestToolProtection:
    """FusionEngine already skips non-text blocks, but we verify the integration
    ensures tool_use messages pass through unchanged."""

    def test_tool_use_in_assistant_message_is_preserved(self):
        """Multipart assistant messages with tool_use blocks pass through."""
        from compactor import _run_compression_sync

        tool_use_block = _tool_use_block("tu_1", "bash", {"command": "ls"})
        messages = [_multipart_message("assistant", [tool_use_block])]

        with patch("compactor._engine") as mock_engine:
            mock_engine.compress_messages.return_value = {
                "messages": messages,  # engine returns same (tool_use passes through)
                "stats": {"original_tokens": 10, "compressed_tokens": 10,
                          "reduction_pct": 0.0, "total_timing_ms": 1.0,
                          "message_count": 1},
            }
            result_messages, stats = _run_compression_sync(messages, {"floor": 0})

        # Tool use block should be identical
        assert result_messages[0]["content"][0]["type"] == "tool_use"
        assert result_messages[0]["content"][0]["id"] == "tu_1"

    def test_tool_result_block_passes_through(self):
        """Tool result blocks in user messages pass through FusionEngine unchanged."""
        from compactor import _run_compression_sync

        tool_result = _tool_result_block("tu_1", '{"result": "ok"}')
        messages = [_multipart_message("user", [tool_result])]

        with patch("compactor._engine") as mock_engine:
            mock_engine.compress_messages.return_value = {
                "messages": messages,
                "stats": {"original_tokens": 5, "compressed_tokens": 5,
                          "reduction_pct": 0.0, "total_timing_ms": 0.5,
                          "message_count": 1},
            }
            result_messages, _ = _run_compression_sync(messages, {"floor": 0})

        assert result_messages[0]["content"][0]["type"] == "tool_result"
        assert result_messages[0]["content"][0]["tool_use_id"] == "tu_1"


# ---------------------------------------------------------------------------
# TestRewindInjection
# ---------------------------------------------------------------------------

class TestRewindInjection:
    def test_injects_rewind_tool_when_markers_present(self):
        from compactor import _ensure_rewind_tool

        messages_with_marker = [_text_message("assistant", f"Compressed\n{REWIND_MARKER}")]
        tools = [{"name": "bash", "description": "run bash"}]

        updated = _ensure_rewind_tool(tools, messages_with_marker)

        assert len(updated) == 2
        assert any(t.get("name") == "rewind_retrieve" for t in updated)

    def test_does_not_duplicate_rewind_tool(self):
        from compactor import _ensure_rewind_tool

        existing_rewind = {"name": "rewind_retrieve", "description": "existing"}
        messages_with_marker = [_text_message("assistant", f"x\n{REWIND_MARKER}")]
        tools = [existing_rewind]

        updated = _ensure_rewind_tool(tools, messages_with_marker)

        assert len(updated) == 1  # no duplication
        assert updated[0] is existing_rewind

    def test_no_injection_when_no_markers(self):
        from compactor import _ensure_rewind_tool

        messages = [_text_message("assistant", "clean, no markers")]
        tools = [{"name": "bash"}]

        updated = _ensure_rewind_tool(tools, messages)
        assert updated is tools  # exact same object, no copy


# ---------------------------------------------------------------------------
# TestFloorBytes
# ---------------------------------------------------------------------------

class TestFloorBytes:
    def test_skips_compression_below_floor(self):
        from compactor import _run_compression_sync

        messages = [_text_message("user", "hi")]  # tiny, well below 4096 bytes
        flags = {"floor": 4096}

        with patch("compactor._engine") as mock_engine:
            result_messages, stats = _run_compression_sync(messages, flags)

        # Engine should not have been called
        mock_engine.compress_messages.assert_not_called()
        assert stats.get("skipped") == "below_floor"
        assert result_messages is messages

    def test_compresses_above_floor(self):
        from compactor import _run_compression_sync

        long_text = "x" * 5000
        messages = [_text_message("user", long_text)]
        flags = {"floor": 100}

        compressed_msg = _text_message("user", "compressed")
        with patch("compactor._engine") as mock_engine:
            mock_engine.compress_messages.return_value = {
                "messages": [compressed_msg],
                "stats": {"original_tokens": 100, "compressed_tokens": 50,
                          "reduction_pct": 50.0, "total_timing_ms": 5.0,
                          "message_count": 1},
            }
            result_messages, stats = _run_compression_sync(messages, flags)

        mock_engine.compress_messages.assert_called_once_with(messages)
        assert stats["original_tokens"] == 100


# ---------------------------------------------------------------------------
# TestFlagsDisable
# ---------------------------------------------------------------------------

class TestFlagsDisable:
    def test_returns_unchanged_when_enabled_false(self):
        """compress_messages() returns original when flags["enabled"] is False."""
        from compactor import compress_messages as async_compress

        messages = [_text_message("user", "test")]
        tools = []
        flags = {"enabled": False}

        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(async_compress(messages, tools, flags))
        finally:
            loop.close()
        out_messages, out_tools, out_stats = result
        assert out_messages is messages
        assert out_tools is tools
        assert out_stats == {}

    def test_returns_unchanged_when_engine_none(self):
        """compress_messages() is a no-op when _engine is None."""
        from compactor import compress_messages as async_compress

        messages = [_text_message("user", "test " * 1000)]  # above floor
        tools = []
        flags = {"enabled": True, "floor": 0, "rewind": False}

        with patch("compactor._engine", None):
            loop = asyncio.new_event_loop()
            try:
                result = loop.run_until_complete(async_compress(messages, tools, flags))
            finally:
                loop.close()

        out_messages, out_tools, out_stats = result
        assert out_messages is messages

    def test_skips_already_compressed(self):
        """compress_messages() skips when Rewind markers are already present."""
        from compactor import compress_messages as async_compress

        messages = [_text_message("assistant", f"stuff\n{REWIND_MARKER}")]
        tools = []
        flags = {"enabled": True, "floor": 0, "rewind": False}

        with patch("compactor._engine") as mock_engine:
            loop = asyncio.new_event_loop()
            try:
                result = loop.run_until_complete(async_compress(messages, tools, flags))
            finally:
                loop.close()

        mock_engine.compress_messages.assert_not_called()
        out_messages, _, out_stats = result
        assert out_messages is messages
        assert out_stats.get("skipped") == "already_compressed"


# ---------------------------------------------------------------------------
# TestGetFlags
# ---------------------------------------------------------------------------

class TestGetFlags:
    def test_returns_disabled_defaults_when_ff_none(self):
        from compactor import get_flags
        with patch("compactor._ff", None):
            flags = get_flags()
        assert flags["enabled"] is False

    def test_returns_flag_values_when_initialized(self):
        from compactor import get_flags

        mock_ff = MagicMock()
        mock_ff.get_boolean_value.side_effect = lambda key, default: {
            "compression-enabled": True,
            "rewind-tool-injection": True,
        }.get(key, default)
        mock_ff.get_integer_value.return_value = 2048

        with patch("compactor._ff", mock_ff):
            flags = get_flags()

        assert flags["enabled"] is True
        assert flags["rewind"] is True
        assert flags["floor"] == 2048
