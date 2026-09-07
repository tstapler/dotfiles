#!/usr/bin/env python3
"""Unit tests for agent-tool-usage-report. Run: python3 stapler-scripts/test_agent_tool_usage_report.py

Builds a synthetic ~/.claude/projects-shaped fixture tree per test — never
reads real project history, so these stay green regardless of what this
machine has actually run.
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parent / "agent-tool-usage-report"
_loader = SourceFileLoader("agent_tool_usage_report", str(_SCRIPT))
report = type(sys)("agent_tool_usage_report")
sys.modules["agent_tool_usage_report"] = report
_loader.exec_module(report)


def write_invocation(projects_dir: Path, project: str, session: str, agent_id: str,
                      agent_type: str, tool_use_lines: list[dict]) -> None:
    subagents = projects_dir / project / session / "subagents"
    subagents.mkdir(parents=True, exist_ok=True)
    meta = {"agentType": agent_type, "description": "test", "toolUseId": "toolu_1", "spawnDepth": 1}
    (subagents / f"agent-{agent_id}.meta.json").write_text(json.dumps(meta), encoding="utf-8")
    lines = [json.dumps({"message": {"content": [tu]}}) for tu in tool_use_lines]
    (subagents / f"agent-{agent_id}.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")


class IterAgentInvocationsTests(unittest.TestCase):
    def test_finds_invocation_with_matching_meta_and_jsonl(self):
        with tempfile.TemporaryDirectory() as d:
            projects_dir = Path(d)
            write_invocation(projects_dir, "proj", "sess", "abc", "my-agent",
                              [{"type": "tool_use", "name": "Bash", "id": "1"}])
            results = list(report.iter_agent_invocations(projects_dir))
            self.assertEqual(len(results), 1)
            agent_type, desc, jsonl_path = results[0]
            self.assertEqual(agent_type, "my-agent")
            self.assertTrue(jsonl_path.exists())

    def test_meta_without_agent_type_is_skipped(self):
        with tempfile.TemporaryDirectory() as d:
            projects_dir = Path(d)
            subagents = projects_dir / "proj" / "sess" / "subagents"
            subagents.mkdir(parents=True)
            (subagents / "agent-xyz.meta.json").write_text(
                json.dumps({"description": "a fork, no agentType"}), encoding="utf-8")
            (subagents / "agent-xyz.jsonl").write_text("", encoding="utf-8")
            self.assertEqual(list(report.iter_agent_invocations(projects_dir)), [])

    def test_missing_jsonl_is_skipped(self):
        with tempfile.TemporaryDirectory() as d:
            projects_dir = Path(d)
            subagents = projects_dir / "proj" / "sess" / "subagents"
            subagents.mkdir(parents=True)
            (subagents / "agent-abc.meta.json").write_text(
                json.dumps({"agentType": "my-agent"}), encoding="utf-8")
            # no matching .jsonl written
            self.assertEqual(list(report.iter_agent_invocations(projects_dir)), [])


class ToolUsesInTranscriptTests(unittest.TestCase):
    def test_extracts_tool_names(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "t.jsonl"
            p.write_text(
                json.dumps({"message": {"content": [{"type": "tool_use", "name": "Read"}]}}) + "\n"
                + json.dumps({"message": {"content": [{"type": "tool_use", "name": "Bash"}]}}) + "\n",
                encoding="utf-8")
            results = list(report.tool_uses_in_transcript(p))
            self.assertEqual(results, [("Read", None), ("Bash", None)])

    def test_skill_tool_use_extracts_skill_name(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "t.jsonl"
            p.write_text(json.dumps({
                "message": {"content": [
                    {"type": "tool_use", "name": "Skill", "input": {"skill": "golang-testing"}}
                ]}
            }) + "\n", encoding="utf-8")
            results = list(report.tool_uses_in_transcript(p))
            self.assertEqual(results, [("Skill", "golang-testing")])

    def test_non_tool_use_lines_are_ignored(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "t.jsonl"
            p.write_text(json.dumps({"message": {"content": "just text, no list"}}) + "\n",
                         encoding="utf-8")
            self.assertEqual(list(report.tool_uses_in_transcript(p)), [])

    def test_malformed_json_line_is_skipped_not_fatal(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "t.jsonl"
            p.write_text('not valid json {"tool_use"\n' +
                         json.dumps({"message": {"content": [{"type": "tool_use", "name": "Read"}]}}) + "\n",
                         encoding="utf-8")
            results = list(report.tool_uses_in_transcript(p))
            self.assertEqual(results, [("Read", None)])


class BuildReportTests(unittest.TestCase):
    def test_aggregates_across_multiple_invocations_of_same_agent(self):
        with tempfile.TemporaryDirectory() as d:
            projects_dir = Path(d)
            write_invocation(projects_dir, "proj-a", "sess-1", "aaa", "code-reviewer",
                              [{"type": "tool_use", "name": "Read"},
                               {"type": "tool_use", "name": "Bash"}])
            write_invocation(projects_dir, "proj-b", "sess-2", "bbb", "code-reviewer",
                              [{"type": "tool_use", "name": "Read"}])
            invocations, tools, skills = report.build_report(projects_dir)
            self.assertEqual(invocations["code-reviewer"], 2)
            self.assertEqual(tools["code-reviewer"]["Read"], 2)
            self.assertEqual(tools["code-reviewer"]["Bash"], 1)

    def test_distinct_agent_types_kept_separate(self):
        with tempfile.TemporaryDirectory() as d:
            projects_dir = Path(d)
            write_invocation(projects_dir, "proj", "sess", "aaa", "agent-one",
                              [{"type": "tool_use", "name": "Write"}])
            write_invocation(projects_dir, "proj", "sess", "bbb", "agent-two",
                              [{"type": "tool_use", "name": "Read"}])
            invocations, tools, _ = report.build_report(projects_dir)
            self.assertEqual(set(invocations), {"agent-one", "agent-two"})
            self.assertNotIn("Write", tools["agent-two"])


if __name__ == "__main__":
    unittest.main()
