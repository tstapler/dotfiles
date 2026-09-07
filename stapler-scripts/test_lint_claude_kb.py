#!/usr/bin/env python3
"""Unit tests for lint-claude-kb. Run: python3 stapler-scripts/test_lint_claude_kb.py

Every check runs against synthetic tmp-dir fixtures, never the real .claude/
tree — so these stay green regardless of how the live repo's content drifts.
`lint-claude-kb` has no .py extension (matches this repo's executable-script
convention), so it's loaded via importlib.util instead of a normal import.
"""
from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parent / "lint-claude-kb"
# No .py suffix (matches this repo's executable-script convention), so
# importlib can't infer a loader from the extension — pass one explicitly.
# dataclasses needs the module registered in sys.modules before exec_module
# (it looks itself up there while processing @dataclass), which the normal
# import machinery does for us but a manual load doesn't.
_loader = SourceFileLoader("lint_claude_kb", str(_SCRIPT))
_spec = importlib.util.spec_from_loader("lint_claude_kb", _loader)
lint = importlib.util.module_from_spec(_spec)
sys.modules["lint_claude_kb"] = lint
_loader.exec_module(lint)


def write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


class ParseFrontmatterTests(unittest.TestCase):
    def test_no_frontmatter_returns_none(self):
        self.assertIsNone(lint.parse_frontmatter("# just a heading\nbody text\n"))

    def test_simple_fields(self):
        fm = lint.parse_frontmatter("---\nname: foo\ndescription: does a thing\n---\nbody\n")
        self.assertEqual(fm, {"name": "foo", "description": "does a thing"})

    def test_folded_multiline_value_is_concatenated(self):
        text = "---\ndescription: >-\n  first line\n  second line\n---\nbody\n"
        fm = lint.parse_frontmatter(text)
        self.assertEqual(fm["description"], "first line second line")


class NameLimitTests(unittest.TestCase):
    def test_valid_name_has_no_findings(self):
        self.assertEqual(lint.check_name_limits(Path("x"), {"name": "my-skill-123"}), [])

    def test_too_long_name_is_error(self):
        long_name = "a" * 65
        findings = lint.check_name_limits(Path("x"), {"name": long_name})
        self.assertEqual([f.check for f in findings], ["name-too-long"])
        self.assertEqual(findings[0].level, "error")

    def test_uppercase_or_space_is_invalid_chars(self):
        findings = lint.check_name_limits(Path("x"), {"name": "My Skill"})
        self.assertIn("name-invalid-chars", [f.check for f in findings])

    def test_paired_xml_tag_in_name_is_flagged(self):
        findings = lint.check_name_limits(Path("x"), {"name": "<example>x</example>"})
        self.assertIn("name-xml-tag", [f.check for f in findings])

    def test_no_name_field_has_no_findings(self):
        self.assertEqual(lint.check_name_limits(Path("x"), {}), [])


class DescriptionLimitTests(unittest.TestCase):
    def test_valid_description_has_no_findings(self):
        self.assertEqual(
            lint.check_description_limits(Path("x"), {"description": "Use when doing Y."}), [])

    def test_too_long_description_is_error(self):
        findings = lint.check_description_limits(Path("x"), {"description": "a" * 1025})
        self.assertEqual([f.check for f in findings], ["description-too-long"])

    def test_bare_placeholder_angle_brackets_not_flagged(self):
        # Regression test: this repo uses `<project>`-style human placeholders
        # constantly — a bare, unpaired tag must NOT be treated as markup.
        findings = lint.check_description_limits(
            Path("x"), {"description": "Outputs: project_plans/<project>/requirements.md"})
        self.assertEqual(findings, [])

    def test_paired_xml_tag_is_flagged(self):
        findings = lint.check_description_limits(
            Path("x"), {"description": "See <example>context</example> for details."})
        self.assertIn("description-xml-tag", [f.check for f in findings])


class NameAndDescriptionTests(unittest.TestCase):
    def test_mismatch_is_error(self):
        with tempfile.TemporaryDirectory() as d:
            p = write(Path(d) / "SKILL.md", "---\nname: wrong-name\ndescription: x\n---\n")
            findings = lint.check_name_and_description(p, "right-name")
            self.assertIn("name-mismatch", [f.check for f in findings])

    def test_matching_name_is_clean(self):
        with tempfile.TemporaryDirectory() as d:
            p = write(Path(d) / "SKILL.md", "---\nname: my-skill\ndescription: x\n---\n")
            findings = lint.check_name_and_description(p, "my-skill")
            self.assertEqual(findings, [])

    def test_no_frontmatter_is_clean(self):
        with tempfile.TemporaryDirectory() as d:
            p = write(Path(d) / "SKILL.md", "Just prose, no frontmatter at all.\n")
            self.assertEqual(lint.check_name_and_description(p, "anything"), [])

    def test_missing_description_is_warn(self):
        with tempfile.TemporaryDirectory() as d:
            p = write(Path(d) / "SKILL.md", "---\nname: my-skill\n---\n")
            findings = lint.check_name_and_description(p, "my-skill")
            self.assertEqual([(f.check, f.level) for f in findings],
                              [("missing-description", "warn")])

    def test_agent_long_description_with_examples_is_not_flagged(self):
        # Agent files legitimately embed <example>...</example> blocks and run
        # well past 1024 chars — that spec is Skill-only, per is_agent=True.
        long_desc = "Use this agent when X. " + ("filler " * 200)
        text = f"---\nname: my-agent\ndescription: '{long_desc}'\n---\n<example>\n...\n</example>\n"
        with tempfile.TemporaryDirectory() as d:
            p = write(Path(d) / "my-agent.md", text)
            findings = lint.check_name_and_description(p, "my-agent", is_agent=True)
            self.assertEqual(findings, [])


class OversizedTests(unittest.TestCase):
    def test_namespaced_skill_is_skipped_regardless_of_size(self):
        with tempfile.TemporaryDirectory() as d:
            p = write(Path(d) / "SKILL.md", "\n" * 900)
            self.assertEqual(lint.check_oversized(p, None), [])

    def test_split_dir_present_suppresses_finding(self):
        with tempfile.TemporaryDirectory() as d:
            p = write(Path(d) / "SKILL.md", "\n" * 900)
            (Path(d) / "references").mkdir()
            self.assertEqual(lint.check_oversized(p, "my-skill"), [])

    def test_over_error_threshold_no_split(self):
        with tempfile.TemporaryDirectory() as d:
            p = write(Path(d) / "SKILL.md", "\n" * 600)
            findings = lint.check_oversized(p, "my-skill")
            self.assertEqual([(f.check, f.level) for f in findings],
                              [("oversized-no-split", "error")])

    def test_warn_band_no_split(self):
        with tempfile.TemporaryDirectory() as d:
            p = write(Path(d) / "SKILL.md", "\n" * 350)
            findings = lint.check_oversized(p, "my-skill")
            self.assertEqual([(f.check, f.level) for f in findings],
                              [("oversized-no-split", "warn")])

    def test_under_threshold_is_clean(self):
        with tempfile.TemporaryDirectory() as d:
            p = write(Path(d) / "SKILL.md", "\n" * 50)
            self.assertEqual(lint.check_oversized(p, "my-skill"), [])


class NestedReferencesTests(unittest.TestCase):
    def test_no_references_dir_is_clean(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(lint.check_nested_references(Path(d)), [])

    def test_flat_references_is_clean(self):
        with tempfile.TemporaryDirectory() as d:
            write(Path(d) / "references" / "a.md", "content")
            self.assertEqual(lint.check_nested_references(Path(d)), [])

    def test_nested_subdirectory_is_flagged(self):
        with tempfile.TemporaryDirectory() as d:
            write(Path(d) / "references" / "sub" / "deep.md", "content")
            findings = lint.check_nested_references(Path(d))
            self.assertEqual([f.check for f in findings], ["nested-references"])


class WindowsPathTests(unittest.TestCase):
    def test_backslash_path_is_flagged_with_line_number(self):
        text = "line one\nsee scripts\\helper.py for details\n"
        findings = lint.check_windows_paths(Path("x"), text)
        self.assertEqual(len(findings), 1)
        self.assertIn("line 2", findings[0].detail)

    def test_forward_slash_path_is_clean(self):
        text = "see scripts/helper.py for details\n"
        self.assertEqual(lint.check_windows_paths(Path("x"), text), [])


class DanglingSymlinkTests(unittest.TestCase):
    def test_broken_symlink_is_flagged(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            (base / "broken.md").symlink_to(base / "does-not-exist.md")
            findings = lint.check_dangling_symlinks(base)
            self.assertEqual([f.check for f in findings], ["dangling-symlink"])

    def test_working_symlink_is_clean(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            target = write(base / "real.md", "content")
            (base / "link.md").symlink_to(target)
            self.assertEqual(lint.check_dangling_symlinks(base), [])

    def test_broken_symlink_inside_node_modules_is_skipped(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            (base / "node_modules").mkdir()
            (base / "node_modules" / "broken.js").symlink_to(base / "nope.js")
            self.assertEqual(lint.check_dangling_symlinks(base), [])


class BrokenRefTests(unittest.TestCase):
    def test_no_ref_in_text_is_clean(self):
        findings = _check_text("nothing to see here\n", {"foo-bar"})
        self.assertEqual(findings, [])

    def test_unresolved_ref_detected_in_text(self):
        text = "line one\nthe `no-such-skill` skill does X\n"
        p_text = text
        findings = _check_text(p_text, set())
        self.assertEqual([f.check for f in findings], ["broken-skill-ref"])
        self.assertIn("line 2", findings[0].detail)

    def test_external_allowlisted_skill_is_not_flagged(self):
        text = "the `security-review` skill runs a scan\n"
        findings = _check_text(text, set())
        self.assertEqual(findings, [])

    def test_owner_repo_at_name_form_resolves_against_bare_name(self):
        text = "See the `samber/cc-skills-golang@golang-lint` skill for rules.\n"
        findings = _check_text(text, {"golang-lint"})
        self.assertEqual(findings, [])

    def test_valid_ref_is_not_flagged(self):
        text = "Use the `foo-bar` skill for this.\n"
        findings = _check_text(text, {"foo-bar"})
        self.assertEqual(findings, [])


def _check_text(text: str, valid_ids: set[str]) -> list:
    """check_broken_refs reads the file itself, so route through a real tmp file."""
    with tempfile.TemporaryDirectory() as d:
        p = write(Path(d) / "SKILL.md", text)
        return lint.check_broken_refs(p, valid_ids)


class SkillDiscoveryTests(unittest.TestCase):
    def _build_fixture(self, root: Path) -> None:
        write(root / "top-level-skill" / "SKILL.md", "---\nname: top-level-skill\n---\n")
        write(root / "single-file-skill.md", "---\nname: single-file-skill\n---\n")
        write(root / "myns" / "skills" / "sub-a" / "SKILL.md", "---\ndescription: x\n---\n")

    def test_iter_skill_files_yields_expected_ids(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self._build_fixture(root)
            results = {(p.relative_to(root).as_posix(), expected)
                       for p, expected in lint.iter_skill_files(root)}
            self.assertEqual(results, {
                ("single-file-skill.md", "single-file-skill"),
                ("top-level-skill/SKILL.md", "top-level-skill"),
                ("myns/skills/sub-a/SKILL.md", None),
            })

    def test_registry_includes_namespaced_and_bare_ids(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self._build_fixture(root)
            ids = lint.build_skill_id_registry(root)
            self.assertEqual(ids, {
                "top-level-skill", "single-file-skill", "myns:sub-a", "sub-a",
            })


if __name__ == "__main__":
    unittest.main()
