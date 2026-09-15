#!/usr/bin/env python3
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from context_audit import analyze, store_sqlite


def _realistic_usage(input_tokens, output_tokens, cache_creation_input_tokens, cache_read_input_tokens):
    # Extra fields beyond the 4 read by analyze() — a real transcript's usage dict
    # carries these too, and a fixture missing them wouldn't catch a future edit
    # that reads the wrong (e.g. nested) shape.
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cache_creation_input_tokens": cache_creation_input_tokens,
        "cache_read_input_tokens": cache_read_input_tokens,
        "service_tier": "standard",
        "server_tool_use": {"web_search_requests": 0},
    }


def _write_jsonl(tmpdir, entries):
    path = Path(tmpdir) / "session.jsonl"
    path.write_text("\n".join(json.dumps(e) for e in entries), encoding="utf-8")
    return path


def _assistant_line(usage=None, model=None, ts="2026-01-01T00:00:00Z"):
    message = {"role": "assistant", "content": [{"type": "text", "text": "ok"}]}
    if model is not None:
        message["model"] = model
    if usage is not None:
        message["usage"] = usage
    return {"type": "assistant", "timestamp": ts, "message": message}


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


class ClaudeCodeUsageTrackingTest(unittest.TestCase):
    """Regression coverage for the c2ed9ce bug class: a synthetic assistant
    turn's usage silently overwriting the real 'last usage wins' total."""

    def test_actual_total_tokens_uses_last_turn_not_sum(self):
        entries = [
            _assistant_line(_realistic_usage(100, 20, 0, 0), ts="2026-01-01T00:00:01Z"),
            _assistant_line(_realistic_usage(300, 40, 500, 10), ts="2026-01-01T00:00:02Z"),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            report = analyze(_write_jsonl(tmp, entries))

        self.assertEqual(report["usage_breakdown"], {
            "input": 300, "output": 40, "cache_creation": 500, "cache_read": 10,
        })
        self.assertEqual(report["actual_total_tokens"], 850)

    def test_trailing_synthetic_turn_excluded_from_usage(self):
        entries = [
            _assistant_line(_realistic_usage(300, 40, 500, 10), ts="2026-01-01T00:00:01Z"),
            _assistant_line(_realistic_usage(9000, 900, 90, 9), model="<synthetic>", ts="2026-01-01T00:00:02Z"),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            report = analyze(_write_jsonl(tmp, entries))

        self.assertEqual(report["actual_total_tokens"], 850)

    def test_all_synthetic_transcript_yields_none(self):
        entries = [
            _assistant_line(_realistic_usage(9000, 900, 90, 9), model="<synthetic>"),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            report = analyze(_write_jsonl(tmp, entries))

        self.assertIsNone(report["actual_total_tokens"])
        self.assertIsNone(report["usage_breakdown"])

    def test_no_usage_data_yields_none(self):
        entries = [_assistant_line(usage=None)]
        with tempfile.TemporaryDirectory() as tmp:
            report = analyze(_write_jsonl(tmp, entries))

        self.assertIsNone(report["actual_total_tokens"])
        self.assertIsNone(report["usage_breakdown"])


def _create_legacy_compactions_table(db_path):
    # Pre-c2ed9ce schema: every store_sqlite() column except actual_total_tokens
    # (see context_audit.py's CREATE TABLE for the source of truth).
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE compactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                session_id TEXT NOT NULL,
                trigger TEXT NOT NULL,
                transcript_path TEXT NOT NULL,
                total_estimated_tokens INTEGER NOT NULL,
                thinking_tokens INTEGER NOT NULL,
                text_tokens INTEGER NOT NULL,
                tool_use_tokens INTEGER NOT NULL,
                tool_result_tokens INTEGER NOT NULL,
                attachment_tokens INTEGER NOT NULL,
                top_tools TEXT NOT NULL
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


class StoreSqliteMigrationTest(unittest.TestCase):
    def test_migrates_legacy_table_idempotently(self):
        report = {
            "total_estimated_tokens": 10,
            "breakdown": {
                "thinking": 1, "text": 2, "tool_use_inputs": 3,
                "tool_results": 4, "attachments": 0,
            },
            "by_tool": {},
            "actual_total_tokens": 850,
        }
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "trend.db"
            _create_legacy_compactions_table(db_path)

            store_sqlite(report, db_path, "sess-1", "manual", "/fake/path")
            store_sqlite(report, db_path, "sess-1", "manual", "/fake/path")

            conn = sqlite3.connect(db_path)
            rows = conn.execute(
                "SELECT actual_total_tokens FROM compactions ORDER BY id"
            ).fetchall()
            conn.close()

        self.assertEqual(rows, [(850,), (850,)])


if __name__ == "__main__":
    unittest.main()
