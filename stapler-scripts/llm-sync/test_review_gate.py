"""Regression checks for the manifest enforcement gate in the Pi settings sync.

Run directly: uv run test_review_gate.py
"""

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.append(str(Path(__file__).parent / "src"))

from cli import sync_pi_settings
from sources.extension_manifest import ExtensionManifest, ManifestEntry
from sources.pi_config import LoadedPiConfig, PiConfigError, parse_fork_source
from sources.review_gate import verify_pinned_sources_reviewed

_BASE_ENTRY_FIELDS = {
    "capability": "permission-system",
    "upstream_repo": "https://github.com/gotgenes/pi-permission-system",
    "upstream_commit": "0123456789abcdef0123456789abcdef01234567",
    "license": "MIT",
    "package_paths": None,
    "reviewer": None,
    "review_date": None,
    "notes": None,
    "approved_by": None,
    "approved_date": None,
}

_FORK_SOURCE = "git:github.com/tstapler/pi-permission-system@abc1234"


def _entry(**overrides) -> ManifestEntry:
    fields = {
        **_BASE_ENTRY_FIELDS,
        "id": "gotgenes-pi-permission-system",
        "fork_repo": "https://github.com/tstapler/pi-permission-system",
        "fork_commit": "abc1234",
        "disposition": "candidate",
        **overrides,
    }
    return ManifestEntry(**fields)


def _approved_entry(**overrides) -> ManifestEntry:
    return _entry(disposition="approved", approved_by="tstapler", approved_date="2026-09-01", **overrides)


def _manifest(*entries: ManifestEntry) -> ExtensionManifest:
    return ExtensionManifest(entries={entry.id: entry for entry in entries})


def _loaded(packages: list = None, extensions: list = None, trusted_scopes: tuple = ()) -> LoadedPiConfig:
    settings = {}
    if packages is not None:
        settings["packages"] = packages
    if extensions is not None:
        settings["extensions"] = extensions
    return LoadedPiConfig(
        settings=settings,
        managed_keys=set(settings),
        layers=(),
        trusted_scopes=trusted_scopes,
    )


def test_verify_pinned_sources_reviewed_raises_when_source_has_no_manifest_entry():
    loaded = _loaded(packages=[_FORK_SOURCE])
    try:
        verify_pinned_sources_reviewed(loaded, _manifest())
    except PiConfigError as error:
        assert _FORK_SOURCE in str(error)
    else:
        raise AssertionError("a source with no manifest entry must raise PiConfigError")


def test_verify_pinned_sources_reviewed_passes_when_approved_entry_matches_exact_commit():
    loaded = _loaded(packages=[_FORK_SOURCE])
    manifest = _manifest(_approved_entry(fork_commit="abc1234"))
    verify_pinned_sources_reviewed(loaded, manifest)


def test_verify_pinned_sources_reviewed_raises_when_commit_mismatched():
    loaded = _loaded(packages=["git:github.com/tstapler/pi-permission-system@def5678"])
    manifest = _manifest(_approved_entry(fork_commit="abc1234"))
    try:
        verify_pinned_sources_reviewed(loaded, manifest)
    except PiConfigError as error:
        message = str(error)
        assert "def5678" in message
        assert "abc1234" in message
    else:
        raise AssertionError("a stale-commit approval must still raise PiConfigError")


def test_verify_pinned_sources_reviewed_raises_when_disposition_is_hold():
    loaded = _loaded(packages=[_FORK_SOURCE])
    manifest = _manifest(_entry(fork_commit="abc1234", disposition="hold"))
    try:
        verify_pinned_sources_reviewed(loaded, manifest)
    except PiConfigError as error:
        message = str(error)
        assert _FORK_SOURCE in message
        assert "hold" in message
    else:
        raise AssertionError("a 'hold' disposition must still raise PiConfigError")


def test_verify_pinned_sources_reviewed_raises_when_disposition_is_rejected():
    loaded = _loaded(packages=[_FORK_SOURCE])
    manifest = _manifest(_entry(fork_commit="abc1234", disposition="rejected"))
    try:
        verify_pinned_sources_reviewed(loaded, manifest)
    except PiConfigError as error:
        message = str(error)
        assert _FORK_SOURCE in message
        assert "rejected" in message
    else:
        raise AssertionError("a 'rejected' disposition must still raise PiConfigError")


def test_verify_pinned_sources_reviewed_matches_commit_case_insensitively():
    upper_manifest = _manifest(_approved_entry(fork_commit="ABC1234"))
    verify_pinned_sources_reviewed(_loaded(packages=[_FORK_SOURCE]), upper_manifest)

    lower_manifest = _manifest(_approved_entry(fork_commit="abc1234"))
    upper_source = "git:github.com/tstapler/pi-permission-system@ABC1234"
    verify_pinned_sources_reviewed(_loaded(packages=[upper_source]), lower_manifest)


def test_verify_pinned_sources_reviewed_treats_prefix_length_mismatch_as_mismatch():
    full_sha = "abc1234def5678901234567890123456789012ab"
    manifest = _manifest(_approved_entry(fork_commit=full_sha))
    loaded = _loaded(packages=[_FORK_SOURCE])  # pinned at the 7-char prefix "abc1234"
    try:
        verify_pinned_sources_reviewed(loaded, manifest)
    except PiConfigError as error:
        message = str(error)
        assert "abc1234" in message
        assert full_sha in message
    else:
        raise AssertionError("a short-vs-long commit pair must be treated as a mismatch")


def test_verify_pinned_sources_reviewed_exempts_trusted_scope_source_with_empty_manifest():
    loaded = _loaded(
        packages=["npm:@work-org/pi-tool@2.3.0"], trusted_scopes=("npm:@work-org",)
    )
    verify_pinned_sources_reviewed(loaded, _manifest())


def test_verify_pinned_sources_reviewed_exempts_tstapler_scoped_source():
    loaded = _loaded(packages=["npm:@tstapler/pi-claude-compat@1.0.0"])
    verify_pinned_sources_reviewed(loaded, _manifest())


def test_verify_pinned_sources_reviewed_only_scans_github_com_tstapler_fork_shaped_sources():
    loaded = _loaded(
        packages=["npm:@other-org/pi-tool@1.0.0", "~/dotfiles/plugins/local"],
        extensions=["~/dotfiles/plugins/ponytail/pi/index.ts"],
    )
    # Empty manifest: if the scan touched any of these, it would raise.
    verify_pinned_sources_reviewed(loaded, _manifest())


_METAMORPHIC_SOURCE_CORPUS = (
    "git:github.com/tstapler/pi-tools@0123456789abcdef",
    "https://github.com/tstapler/pi-tools@abc1234",
    "git@github.com:tstapler/pi-tools@abc1234",
    "git:github.com/someone-else/pi-tools@abc1234",  # wrong owner
    "git:github.com/tstapler/pi-tools@main",  # mutable ref
    "npm:@tstapler/pi-tool@1.2.3",  # not fork-shaped at all
    "npm:someone-elses-package@1.0.0",
    "~/dotfiles/plugins/local",
)


def _source_checker():
    from sources.pi_config import PiConfigSource
    from sources.tiered_config import TieredJsonConfig

    return PiConfigSource(
        TieredJsonConfig(
            universal_file=Path("/nonexistent/config.json"),
            tracked_fragments_dir=Path("/nonexistent/config.d"),
            local_file=Path("/nonexistent/config.local.json"),
            local_fragments_dir=Path("/nonexistent/config.local.d"),
        )
    )


def _assert_agree(source: str, checker) -> None:
    ref = parse_fork_source(source)
    if ref is None:
        # Not fork-shaped: _is_allowed_package_source may still accept it via
        # the local/trusted-scope/npm-tstapler branches, but never via the
        # fork branch.
        return
    assert ref.repo == "github.com/tstapler/pi-tools", source
    if checker._is_allowed_package_source(source):
        assert ref.commit.lower() in source.lower(), source


def test_parse_fork_source_and_is_allowed_package_source_agree():
    """Task 1.2.1h metamorphic test.

    `parse_fork_source()` is the single shape-parser both `pi_config.py`'s
    `_is_allowed_package_source` and `review_gate.py`'s scan rely on: for
    every fixture source, if `_is_allowed_package_source` accepts it via the
    fork branch, `parse_fork_source` must have recognized the same repo and
    commit (immutable-commit format is `_is_allowed_package_source`'s own
    extra layer on top, not `parse_fork_source`'s job).
    """
    checker = _source_checker()
    for source in _METAMORPHIC_SOURCE_CORPUS:
        _assert_agree(source, checker)


def test_sync_pi_settings_aborts_and_writes_nothing_when_source_unreviewed():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        config_dir = root / "config.d"
        config_dir.mkdir(parents=True)
        (config_dir / "10-fork.json").write_text(
            json.dumps({"packages": {"unreviewed": {"source": _FORK_SOURCE}}}),
            encoding="utf-8",
        )

        manifest_path = root / "extensions-manifest.json"
        manifest_path.write_text(json.dumps({"extensions": {}}), encoding="utf-8")

        settings_path = root / "agent" / "settings.json"
        settings_path.parent.mkdir(parents=True)
        original_settings = json.dumps({"theme": "dark", "lastChangelogVersion": "0.84.4"})
        settings_path.write_text(original_settings, encoding="utf-8")

        args = argparse.Namespace(
            pi_dir=None,
            pi_config_file=root / "config.json",
            pi_config_dir=config_dir,
            pi_local_config=root / "config.local.json",
            pi_local_config_dir=root / "config.local.d",
            pi_extensions_manifest=manifest_path,
            pi_settings_file=settings_path,
            pi_settings_state_file=root / "state.json",
            dry_run=False,
        )

        try:
            sync_pi_settings(args)
        except PiConfigError as error:
            assert _FORK_SOURCE in str(error)
        else:
            raise AssertionError("an unreviewed fork source must abort sync_pi_settings")

        assert settings_path.read_text(encoding="utf-8") == original_settings
        assert not (root / "state.json").exists()


def test_blocked_sync_error_names_exact_unreviewed_source_string():
    loaded = _loaded(packages=[_FORK_SOURCE])
    try:
        verify_pinned_sources_reviewed(loaded, _manifest())
    except PiConfigError as error:
        assert str(error).count(_FORK_SOURCE) >= 1
    else:
        raise AssertionError("expected PiConfigError")


def test_blocked_sync_stale_approval_names_both_configured_and_approved_commits():
    loaded = _loaded(packages=["git:github.com/tstapler/pi-permission-system@1111111"])
    manifest = _manifest(_approved_entry(fork_commit="2222222"))
    try:
        verify_pinned_sources_reviewed(loaded, manifest)
    except PiConfigError as error:
        message = str(error)
        assert "1111111" in message
        assert "2222222" in message
    else:
        raise AssertionError("expected PiConfigError naming both commits")


def test_blocked_sync_error_states_settings_json_unchanged():
    # Covered end-to-end by test_sync_pi_settings_aborts_and_writes_nothing_when_source_unreviewed;
    # here we assert the gate itself never touches any settings state as a
    # side effect (it is a pure check).
    loaded = _loaded(packages=[_FORK_SOURCE])
    before = dict(loaded.settings)
    try:
        verify_pinned_sources_reviewed(loaded, _manifest())
    except PiConfigError:
        pass
    assert loaded.settings == before


def test_blocked_sync_never_fires_for_trusted_or_tstapler_scoped_sources():
    loaded = _loaded(
        packages=[
            "npm:@work-org/pi-tool@2.3.0",
            "npm:@tstapler/pi-claude-compat@1.0.0",
        ],
        trusted_scopes=("npm:@work-org",),
    )
    verify_pinned_sources_reviewed(loaded, _manifest())


if __name__ == "__main__":
    tests = [value for key, value in list(globals().items()) if key.startswith("test_")]
    for test in tests:
        test()
        print(f"ok  {test.__name__}")
    print(f"\n{len(tests)} checks passed")
