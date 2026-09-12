#!/usr/bin/env python3
import json
import tempfile
import unittest
from pathlib import Path

from context_audit import analyze


class ContextAuditTest(unittest.TestCase):
    def test_analyzes_pi_session_messages_and_usage(self):
        entries = [
            {"type": "session", "id": "session-1", "timestamp": "2026-01-01T00:00:00Z"},
            {
                "type": "message",
                "timestamp": "2026-01-01T00:00:01Z",
                "message": {"role": "user", "content": [{"type": "text", "text": "hello"}]},
            },
            {
                "type": "message",
                "timestamp": "2026-01-01T00:00:02Z",
                "message": {
                    "role": "assistant",
                    "content": [
                        {"type": "thinking", "thinking": "consider"},
                        {"type": "toolCall", "name": "read", "arguments": {"path": "README.md"}},
                    ],
                    "usage": {"input": 100, "output": 20, "cacheRead": 30, "cacheWrite": 4},
                },
            },
            {
                "type": "message",
                "timestamp": "2026-01-01T00:00:03Z",
                "message": {
                    "role": "toolResult",
                    "toolName": "read",
                    "content": [{"type": "text", "text": "file contents"}],
                },
            },
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "session.jsonl"
            path.write_text("\n".join(json.dumps(entry) for entry in entries), encoding="utf-8")
            report = analyze(path)

        self.assertEqual(report["message_counts"], {"user": 1, "assistant": 1})
        self.assertEqual(report["by_tool_calls"], {"read": 1})
        self.assertGreater(report["breakdown"]["tool_results"], 0)
        self.assertEqual(report["usage_breakdown"], {
            "input": 100,
            "output": 20,
            "cache_creation": 4,
            "cache_read": 30,
        })
        self.assertEqual(report["actual_total_tokens"], 154)
        self.assertEqual(report["time_range"]["last"], "2026-01-01T00:00:03Z")


if __name__ == "__main__":
    unittest.main()
