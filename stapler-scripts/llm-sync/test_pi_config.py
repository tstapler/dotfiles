"""Regression checks for rendering tiered Pi configuration.

Run directly: uv run test_pi_config.py
"""

import json
import sys
import tempfile
from pathlib import Path

sys.path.append(str(Path(__file__).parent / "src"))

from sources.pi_config import PiConfigError, PiConfigSource
from sources.tiered_config import TieredJsonConfig


def _write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def _source(root: Path) -> PiConfigSource:
    return PiConfigSource(
        TieredJsonConfig(
            universal_file=root / "config.json",
            tracked_fragments_dir=root / "config.d",
            local_file=root / "config.local.json",
            local_fragments_dir=root / "config.local.d",
        )
    )


def test_renders_enabled_registries_to_native_pi_settings():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _write(
            root / "config.json",
            {
                "settings": {"theme": "dark", "defaultProjectTrust": "ask"},
                "trustedPackageScopes": ["npm:@work-org"],
                "packages": {
                    "tools": {
                        "source": "git:github.com/tstapler/pi-tools@0123456789abcdef",
                        "extensions": ["extensions/*.ts"],
                    },
                    "work": {
                        "source": "npm:@work-org/pi-agent",
                    },
                    "off": {
                        "enabled": False,
                        "source": "git:github.com/tstapler/disabled@abcdef0",
                    },
                },
                "extensions": {
                    "ponytail": {"path": "~/dotfiles/plugins/ponytail/pi/index.ts"},
                    "experiment": {"enabled": False, "path": "/tmp/experiment.ts"},
                },
                "skills": {"claude": {"path": "~/.claude/skills"}},
            },
        )

        loaded = _source(root).load()

        assert loaded.settings == {
            "theme": "dark",
            "defaultProjectTrust": "ask",
            "packages": [
                {
                    "source": "git:github.com/tstapler/pi-tools@0123456789abcdef",
                    "extensions": ["extensions/*.ts"],
                },
                "npm:@work-org/pi-agent",
            ],
            "extensions": ["~/dotfiles/plugins/ponytail/pi/index.ts"],
            "skills": ["~/.claude/skills"],
        }
        assert loaded.managed_keys == {
            "defaultProjectTrust",
            "extensions",
            "packages",
            "skills",
            "theme",
        }


def test_later_layer_can_disable_a_base_registry_entry():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _write(
            root / "config.json",
            {
                "packages": {
                    "base": {
                        "source": "git:github.com/tstapler/base@0123456789abcdef"
                    }
                }
            },
        )
        _write(root / "config.d" / "90-off.json", {"packages": {"base": {"enabled": False}}})

        assert _source(root).load().settings == {"packages": []}


def test_rejects_unpinned_untrusted_remote_package():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _write(
            root / "config.json",
            {"packages": {"unsafe": {"source": "npm:someone-elses-package"}}},
        )

        try:
            _source(root).load()
        except PiConfigError as error:
            assert "unsafe" in str(error)
            assert "pinned" in str(error)
        else:
            raise AssertionError("an unpinned third-party package should be rejected")


def test_rejects_package_from_scope_not_listed_in_trusted_package_scopes():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _write(
            root / "config.json",
            {
                "trustedPackageScopes": ["npm:@work-org"],
                "packages": {"unsafe": {"source": "npm:@other-org/pi-agent"}},
            },
        )

        try:
            _source(root).load()
        except PiConfigError as error:
            assert "unsafe" in str(error)
        else:
            raise AssertionError("a package outside the trusted scopes should be rejected")


def test_allows_pinned_tyler_npm_and_local_packages():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _write(
            root / "config.json",
            {
                "packages": {
                    "npm": {"source": "npm:@tstapler/pi-tool@1.2.3"},
                    "local": {"source": "~/dotfiles/plugins/ponytail"},
                }
            },
        )

        assert _source(root).load().settings["packages"] == [
            "npm:@tstapler/pi-tool@1.2.3",
            "~/dotfiles/plugins/ponytail",
        ]


def test_rejects_pinned_upstream_and_mutable_fork_ref():
    rejected = (
        "npm:pi-tool@1.2.3",
        "git:github.com/someone/pi-tool@0123456789abcdef",
        "git:github.com/tstapler/pi-tool@main",
    )
    for source in rejected:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / "config.json", {"packages": {"unsafe": {"source": source}}})
            try:
                _source(root).load()
            except PiConfigError as error:
                assert "Tyler-owned/fork" in str(error)
            else:
                raise AssertionError(f"unsafe package source should be rejected: {source}")


def test_rejects_credential_material_in_nested_settings():
    forbidden = ("apiKey", "access_token", "refresh-token", "password", "clientSecret")
    for key in forbidden:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(
                root / "config.json",
                {"settings": {"providerConfig": {key: "do-not-store-this"}}},
            )
            try:
                _source(root).load()
            except PiConfigError as error:
                assert "credential material" in str(error)
                assert key in str(error)
            else:
                raise AssertionError(f"credential-bearing key should be rejected: {key}")


def test_rejects_url_shaped_path_for_extension_registry_entry():
    """A URL-shaped `path` value isn't recognized by the fork-pin-review
    gate's scan (only `packages`/`extensions` sources routed through
    `parse_fork_source()` are), so it must be rejected at render time
    instead of silently passing through unchecked."""
    rejected = (
        "https://github.com/someone-else/pi-extension",
        "git:github.com/someone-else/pi-extension@0123456789abcdef",
        "npm:@someone-else/pi-extension",
    )
    for path in rejected:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(
                root / "config.json",
                {"extensions": {"remote": {"path": path}}},
            )

            try:
                _source(root).load()
            except PiConfigError as error:
                assert "remote" in str(error)
                assert "local path" in str(error)
            else:
                raise AssertionError(
                    f"URL-shaped extension path should be rejected: {path}"
                )


def test_rejects_reserved_resource_keys_inside_settings():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _write(
            root / "config.json",
            {"settings": {"packages": ["npm:bypass@1.0.0"]}},
        )

        try:
            _source(root).load()
        except PiConfigError as error:
            assert "packages" in str(error)
        else:
            raise AssertionError("resource registries must not be bypassed")


if __name__ == "__main__":
    tests = [value for key, value in list(globals().items()) if key.startswith("test_")]
    for test in tests:
        test()
        print(f"ok  {test.__name__}")
    print(f"\n{len(tests)} checks passed")
