"""Regression checks for the Pi extension review manifest loader.

Run directly: uv run test_extension_manifest.py
"""

import json
import sys
import tempfile
from pathlib import Path

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


if __name__ == "__main__":
    tests = [value for key, value in list(globals().items()) if key.startswith("test_")]
    for test in tests:
        test()
        print(f"ok  {test.__name__}")
    print(f"\n{len(tests)} checks passed")
