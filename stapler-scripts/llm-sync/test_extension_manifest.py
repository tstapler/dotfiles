"""Regression checks for the Pi extension review manifest loader.

Run directly: uv run test_extension_manifest.py
"""

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.append(str(Path(__file__).parent / "src"))

from sources.extension_manifest import (
    ExtensionManifestSource,
    ManifestEntry,
    ManifestError,
)

_REPO_ROOT = Path(__file__).parent.parent.parent
_TRACKED_MANIFEST = _REPO_ROOT / ".config" / "pi" / "extensions-manifest.json"

_BASE_FIELDS = {
    "id": "gotgenes-pi-permission-system",
    "capability": "permission-system",
    "upstream_repo": "https://github.com/gotgenes/pi-permission-system",
    "upstream_commit": "0123456789abcdef0123456789abcdef01234567",
    "license": "MIT",
    "fork_repo": "https://github.com/tstapler/pi-permission-system",
    "fork_commit": "abcdef0123456789abcdef0123456789abcdef01",
}


def _write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def _write_approved_entry(path: Path, notes: str) -> None:
    entry = {
        **_BASE_FIELDS,
        "id": "narumiruna-pi-plan-mode",
        "disposition": "approved",
        "approved_by": "tstapler",
        "approved_date": "2026-09-01",
        "notes": notes,
    }
    _write(path, {"extensions": {"narumiruna-pi-plan-mode": entry}})


def test_tracked_manifest_file_parses_to_empty_extensions_registry():
    manifest = ExtensionManifestSource.load(_TRACKED_MANIFEST)
    assert manifest.entries == {}


def test_load_raises_on_entry_missing_required_field():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "extensions-manifest.json"
        entry = {**_BASE_FIELDS, "disposition": "candidate"}
        del entry["upstream_commit"]
        _write(path, {"extensions": {"gotgenes-pi-permission-system": entry}})

        try:
            ExtensionManifestSource.load(path)
        except ManifestError as error:
            assert "gotgenes-pi-permission-system" in str(error)
            assert "upstream_commit" in str(error)
        else:
            raise AssertionError("missing required field must raise ManifestError")


def test_manifest_load_rejects_approved_entry_missing_approved_by_or_date_naming_entry_and_fields():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "extensions-manifest.json"
        entry = {
            **_BASE_FIELDS,
            "id": "narumiruna-pi-plan-mode",
            "disposition": "approved",
            "approved_by": None,
            "approved_date": None,
        }
        _write(path, {"extensions": {"narumiruna-pi-plan-mode": entry}})

        try:
            ExtensionManifestSource.load(path)
        except ManifestError as error:
            message = str(error)
            assert "narumiruna-pi-plan-mode" in message
            assert "approved_by" in message
            assert "approved_date" in message
        else:
            raise AssertionError(
                "approved entry missing approved_by/approved_date must raise ManifestError"
            )


def test_candidate_entry_with_null_approved_by_loads_successfully():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "extensions-manifest.json"
        entry = {
            **_BASE_FIELDS,
            "id": "narumiruna-pi-plan-mode",
            "disposition": "candidate",
            "approved_by": None,
            "approved_date": None,
        }
        _write(path, {"extensions": {"narumiruna-pi-plan-mode": entry}})

        manifest = ExtensionManifestSource.load(path)

        assert manifest.entries["narumiruna-pi-plan-mode"].disposition == "candidate"


def test_manifest_entry_construction_rejects_approved_without_approver():
    try:
        ManifestEntry(
            **_BASE_FIELDS,
            package_paths=None,
            disposition="approved",
            reviewer=None,
            review_date=None,
            notes=None,
            approved_by=None,
            approved_date=None,
        )
    except ManifestError as error:
        message = str(error)
        assert _BASE_FIELDS["id"] in message
        assert "approved_by" in message
        assert "approved_date" in message
    else:
        raise AssertionError(
            "direct ManifestEntry construction must enforce the approval invariant"
        )


def test_approved_entry_with_fewer_than_five_notes_paths_is_rejected():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "extensions-manifest.json"
        _write_approved_entry(
            path, "Reviewed `src/network.py` and `src/subprocess_runner.py` only."
        )

        with patch("sources.extension_manifest.subprocess.run") as mock_run:
            try:
                ExtensionManifestSource.load(path)
            except ManifestError as error:
                assert "narumiruna-pi-plan-mode" in str(error)
            else:
                raise AssertionError(
                    "approved entry with <5 notes paths must raise ManifestError"
                )

        # Too few candidate paths is decidable from `notes` text alone; no
        # need to spend a `gh api` call confirming existence.
        mock_run.assert_not_called()


def test_approved_entry_with_five_verified_notes_paths_passes():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "extensions-manifest.json"
        paths = [
            "src/network.py",
            "src/subprocess_runner.py",
            "src/filesystem.py",
            "src/secrets.py",
            "src/telemetry.py",
        ]
        _write_approved_entry(path, "Reviewed " + ", ".join(f"`{p}`" for p in paths) + ".")

        tree_response = json.dumps({"tree": [{"path": p, "type": "blob"} for p in paths]})
        fake_result = MagicMock(returncode=0, stdout=tree_response, stderr="")

        with patch(
            "sources.extension_manifest.subprocess.run", return_value=fake_result
        ) as mock_run:
            manifest = ExtensionManifestSource.load(path)

        assert manifest.entries["narumiruna-pi-plan-mode"].disposition == "approved"
        mock_run.assert_called_once()
        gh_args = mock_run.call_args.args[0]
        assert gh_args[:2] == ["gh", "api"]
        assert _BASE_FIELDS["fork_commit"] in gh_args[2]


def test_approved_entry_with_unverifiable_notes_path_is_rejected_by_name():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "extensions-manifest.json"
        paths = [
            "src/network.py",
            "src/subprocess_runner.py",
            "src/filesystem.py",
            "src/secrets.py",
            "src/telemetry_missing.py",
        ]
        _write_approved_entry(path, "Reviewed " + ", ".join(f"`{p}`" for p in paths) + ".")

        # Every cited path except the last is really in the fork tree.
        tree_response = json.dumps({"tree": [{"path": p, "type": "blob"} for p in paths[:-1]]})
        fake_result = MagicMock(returncode=0, stdout=tree_response, stderr="")

        with patch("sources.extension_manifest.subprocess.run", return_value=fake_result):
            try:
                ExtensionManifestSource.load(path)
            except ManifestError as error:
                assert "src/telemetry_missing.py" in str(error)
            else:
                raise AssertionError(
                    "notes path missing from fork tree must raise ManifestError"
                )


def test_extension_manifest_load_raises_on_duplicate_entry_id():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "extensions-manifest.json"
        first = {**_BASE_FIELDS, "id": "gotgenes-pi-packages", "disposition": "candidate"}
        second = {**_BASE_FIELDS, "id": "gotgenes-pi-packages", "disposition": "candidate"}
        _write(
            path,
            {
                "extensions": {
                    "gotgenes-pi-packages-v1": first,
                    "gotgenes-pi-packages-v2": second,
                }
            },
        )

        try:
            ExtensionManifestSource.load(path)
        except ManifestError as error:
            assert "gotgenes-pi-packages" in str(error)
        else:
            raise AssertionError("duplicate manifest entry id must raise ManifestError")


if __name__ == "__main__":
    tests = [value for key, value in list(globals().items()) if key.startswith("test_")]
    for test in tests:
        test()
        print(f"ok  {test.__name__}")
    print(f"\n{len(tests)} checks passed")
