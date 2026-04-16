"""Comprehensive integration tests validating Bedrock API specification compliance.

These tests ensure we correctly implement AWS Bedrock's API requirements:
- Tool use/result pairing and validation
- Required and forbidden fields
- Message structure constraints
- Post-compaction message validity

Based on AWS Bedrock API specification for Claude models:
https://docs.aws.amazon.com/bedrock/latest/userguide/model-parameters-anthropic-claude-messages.html
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Mock aws_sso_lib before importing BedrockProvider
sys.modules['aws_sso_lib'] = Mock()
sys.modules['diskcache'] = Mock()

from providers.bedrock import BedrockProvider


class TestBedrockToolUseResultPairing:
    """Test Bedrock's strict tool_use/tool_result pairing requirements.

    Bedrock requires:
    1. Every tool_result must have a tool_use_id field
    2. Every tool_use_id must reference a tool_use block in the immediately preceding message
    3. tool_use blocks must have an 'id' field
    """

    def setup_method(self):
        """Create Bedrock provider instance for testing."""
        self.provider = BedrockProvider()

    def test_valid_tool_use_result_pair(self):
        """Test that valid tool_use/result pairs are preserved."""
        body = {
            "model": "claude-sonnet-4",
            "max_tokens": 1024,
            "messages": [
                {
                    "role": "user",
                    "content": "What's the weather?"
                },
                {
                    "role": "assistant",
                    "content": [
                        {
                            "type": "tool_use",
                            "id": "toolu_01ABC",
                            "name": "get_weather",
                            "input": {"city": "SF"}
                        }
                    ]
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": "toolu_01ABC",
                            "content": "Sunny, 72F"
                        }
                    ]
                }
            ]
        }

        result = self.provider._prepare_bedrock_body(body, model="claude-sonnet-4", headers={})

        # Verify tool_use and tool_result are both present
        assert len(result["messages"]) == 3
        assert result["messages"][1]["content"][0]["type"] == "tool_use"
        assert result["messages"][1]["content"][0]["id"] == "toolu_01ABC"
        assert result["messages"][2]["content"][0]["type"] == "tool_result"
        assert result["messages"][2]["content"][0]["tool_use_id"] == "toolu_01ABC"

    def test_orphaned_tool_result_removed(self):
        """Test that tool_result without corresponding tool_use is removed.

        This simulates post-compaction scenario where tool_use was removed.
        """
        body = {
            "model": "claude-sonnet-4",
            "max_tokens": 1024,
            "messages": [
                {
                    "role": "user",
                    "content": "What's the weather?"
                },
                # tool_use message was removed by compaction
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": "toolu_01MISSING",  # References removed tool_use
                            "content": "Sunny, 72F"
                        }
                    ]
                }
            ]
        }

        result = self.provider._prepare_bedrock_body(body, model="claude-sonnet-4", headers={})

        # Verify orphaned tool_result was removed
        assert len(result["messages"]) == 2
        # Second message should have empty content (tool_result was removed)
        assert result["messages"][1]["content"] == []

    def test_multiple_tool_results_partial_orphaned(self):
        """Test mixed scenario: some tool_results valid, some orphaned."""
        body = {
            "model": "claude-sonnet-4",
            "max_tokens": 1024,
            "messages": [
                {
                    "role": "user",
                    "content": "Check weather and time"
                },
                {
                    "role": "assistant",
                    "content": [
                        {
                            "type": "tool_use",
                            "id": "toolu_01VALID",
                            "name": "get_weather",
                            "input": {}
                        }
                        # Second tool_use was removed by compaction
                    ]
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": "toolu_01VALID",
                            "content": "Sunny"
                        },
                        {
                            "type": "tool_result",
                            "tool_use_id": "toolu_01MISSING",  # Orphaned
                            "content": "3:00 PM"
                        }
                    ]
                }
            ]
        }

        result = self.provider._prepare_bedrock_body(body, model="claude-sonnet-4", headers={})

        # Verify only valid tool_result remains
        tool_results = [
            c for c in result["messages"][2]["content"]
            if c.get("type") == "tool_result"
        ]
        assert len(tool_results) == 1
        assert tool_results[0]["tool_use_id"] == "toolu_01VALID"

    def test_tool_result_missing_tool_use_id_removed(self):
        """Test that tool_result without tool_use_id field is removed.

        Bedrock requires the tool_use_id field, so we must remove invalid tool_results.
        """
        body = {
            "model": "claude-sonnet-4",
            "max_tokens": 1024,
            "messages": [
                {
                    "role": "user",
                    "content": "Test"
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            # Missing tool_use_id field
                            "content": "Result"
                        }
                    ]
                }
            ]
        }

        result = self.provider._prepare_bedrock_body(body, model="claude-sonnet-4", headers={})

        # tool_result without tool_use_id should be removed (Bedrock requires it)
        assert result["messages"][1]["content"] == []


class TestBedrockFieldValidation:
    """Test Bedrock's field requirements and restrictions."""

    def setup_method(self):
        """Create Bedrock provider instance for testing."""
        self.provider = BedrockProvider()

    def test_top_level_fields_stripped(self):
        """Test that Anthropic-specific top-level fields are removed."""
        body = {
            "model": "claude-sonnet-4",
            "stream": True,
            "max_tokens": 1024,
            "output_config": {"effort": "high"},
            "context_management": {"enabled": True},
            "messages": []
        }

        result = self.provider._prepare_bedrock_body(body, model="claude-sonnet-4", headers={})

        # These fields must be stripped
        assert "model" not in result
        assert "stream" not in result
        assert "output_config" not in result
        assert "context_management" not in result

        # These fields must be kept
        assert "max_tokens" in result
        assert result["max_tokens"] == 1024

    def test_anthropic_version_added(self):
        """Test that anthropic_version is added for Bedrock."""
        body = {
            "model": "claude-sonnet-4",
            "max_tokens": 1024,
            "messages": []
        }

        result = self.provider._prepare_bedrock_body(body, model="claude-sonnet-4", headers={})

        assert "anthropic_version" in result
        assert result["anthropic_version"] == "bedrock-2023-05-31"


class TestBedrockMessageStructure:
    """Test Bedrock's message structure requirements."""

    def setup_method(self):
        """Create Bedrock provider instance for testing."""
        self.provider = BedrockProvider()

    def test_empty_content_list_preserved(self):
        """Test that messages with empty content lists are preserved.

        This can happen after removing orphaned tool_results.
        """
        body = {
            "model": "claude-sonnet-4",
            "max_tokens": 1024,
            "messages": [
                {
                    "role": "user",
                    "content": []  # Empty content list
                }
            ]
        }

        result = self.provider._prepare_bedrock_body(body, model="claude-sonnet-4", headers={})

        # Message is preserved with empty content
        assert len(result["messages"]) == 1
        assert result["messages"][0]["content"] == []

    def test_text_content_preserved(self):
        """Test that text content in messages is preserved."""
        body = {
            "model": "claude-sonnet-4",
            "max_tokens": 1024,
            "messages": [
                {
                    "role": "user",
                    "content": "Hello"
                },
                {
                    "role": "assistant",
                    "content": [
                        {
                            "type": "text",
                            "text": "Hi there!"
                        }
                    ]
                }
            ]
        }

        result = self.provider._prepare_bedrock_body(body, model="claude-sonnet-4", headers={})

        assert len(result["messages"]) == 2
        assert result["messages"][0]["content"] == "Hello"
        assert result["messages"][1]["content"][0]["type"] == "text"


class TestBedrockPostCompactionValidation:
    """Test that messages remain valid after compaction scenarios."""

    def setup_method(self):
        """Create Bedrock provider instance for testing."""
        self.provider = BedrockProvider()

    def test_compacted_messages_with_orphaned_tool_results(self):
        """Simulate compaction removing tool_use but leaving tool_result."""
        # This is the exact scenario causing the user's error
        body = {
            "model": "claude-haiku-4-5",
            "max_tokens": 1024,
            "messages": [
                # Imagine 20 messages were here before compaction
                {
                    "role": "user",
                    "content": "Summary after compaction"
                },
                # tool_use message was removed by compaction
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": "toolu_bdrk_01PZJnKouPec5GZL6hgMytV7",
                            "content": "Tool output"
                        }
                    ]
                }
            ]
        }

        result = self.provider._prepare_bedrock_body(body, model="claude-haiku-4-5", headers={})

        # Verify orphaned tool_result was removed
        tool_results = [
            c for msg in result["messages"]
            if isinstance(msg.get("content"), list)
            for c in msg["content"]
            if isinstance(c, dict) and c.get("type") == "tool_result"
        ]
        assert len(tool_results) == 0, "Orphaned tool_result should be removed"

    def test_compacted_messages_with_valid_tool_pairs(self):
        """Test that compaction preserving tool_use also preserves tool_result."""
        body = {
            "model": "claude-sonnet-4",
            "max_tokens": 1024,
            "messages": [
                {
                    "role": "user",
                    "content": "Summary"
                },
                {
                    "role": "assistant",
                    "content": [
                        {
                            "type": "tool_use",
                            "id": "toolu_01KEPT",
                            "name": "search",
                            "input": {}
                        }
                    ]
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": "toolu_01KEPT",
                            "content": "Result"
                        }
                    ]
                }
            ]
        }

        result = self.provider._prepare_bedrock_body(body, model="claude-sonnet-4", headers={})

        # Verify both tool_use and tool_result are preserved
        tool_uses = [
            c for msg in result["messages"]
            if isinstance(msg.get("content"), list)
            for c in msg["content"]
            if isinstance(c, dict) and c.get("type") == "tool_use"
        ]
        tool_results = [
            c for msg in result["messages"]
            if isinstance(msg.get("content"), list)
            for c in msg["content"]
            if isinstance(c, dict) and c.get("type") == "tool_result"
        ]

        assert len(tool_uses) == 1
        assert len(tool_results) == 1
        assert tool_results[0]["tool_use_id"] == tool_uses[0]["id"]


class TestBedrockBetaFeatures:
    """Test Bedrock's beta feature handling."""

    def setup_method(self):
        """Create Bedrock provider instance for testing."""
        self.provider = BedrockProvider()

    def test_supported_beta_feature_added(self):
        """Test that supported beta features are converted to anthropic_beta array."""
        body = {
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 1024,
            "messages": []
        }
        headers = {
            "anthropic-beta": "context-1m-2025-08-07"
        }

        result = self.provider._prepare_bedrock_body(body, model="claude-sonnet-4-20250514", headers=headers)

        assert "anthropic_beta" in result
        assert "context-1m-2025-08-07" in result["anthropic_beta"]

    def test_unsupported_beta_feature_filtered(self):
        """Test that unsupported beta features are filtered out."""
        body = {
            "model": "claude-sonnet-4",
            "max_tokens": 1024,
            "messages": []
        }
        headers = {
            "anthropic-beta": "unsupported-feature-2025"
        }

        result = self.provider._prepare_bedrock_body(body, model="claude-sonnet-4", headers=headers)

        # Unsupported beta should be filtered out
        assert "anthropic_beta" not in result or "unsupported-feature-2025" not in result.get("anthropic_beta", [])


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
