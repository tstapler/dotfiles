"""Self-check for PluginSource's marketplace-plugin discovery. Run directly:
uv run --directory stapler-scripts/llm-sync python src/sources/test_plugins.py
"""
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sources.plugins import PluginSource  # noqa: E402


def _write_manifest(plugin_dir: Path, name: str) -> None:
    manifest_dir = plugin_dir / ".claude-plugin"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    (manifest_dir / "plugin.json").write_text(
        json.dumps({"name": name, "description": "", "version": "1.0.0"})
    )


def _source(tmp: Path, installed_plugins=None, settings=None, settings_local=None) -> PluginSource:
    installed_file = tmp / "installed_plugins.json"
    if installed_plugins is not None:
        installed_file.write_text(json.dumps({"version": 2, "plugins": installed_plugins}))

    settings_file = tmp / "settings.json"
    if settings is not None:
        settings_file.write_text(json.dumps(settings))

    settings_local_file = tmp / "settings.local.json"
    if settings_local is not None:
        settings_local_file.write_text(json.dumps(settings_local))

    return PluginSource(
        global_plugins_dir=tmp / "no-global-plugins",
        local_plugins_dir=tmp / "no-local-plugins",
        installed_plugins_file=installed_file,
        claude_settings_file=settings_file,
        claude_settings_local_file=settings_local_file,
    )


def test_enabled_marketplace_plugin_is_loaded():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        plugin_dir = tmp / "cache" / "foo" / "1.0.0"
        _write_manifest(plugin_dir, "foo-plugin")
        src = _source(
            tmp,
            installed_plugins={
                "foo-plugin@mp": [
                    {"scope": "user", "installPath": str(plugin_dir)}
                ]
            },
        )
        names = {p.name for p in src.load_plugins()}
        assert "foo-plugin" in names, names


def test_disabled_marketplace_plugin_is_excluded():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        plugin_dir = tmp / "cache" / "foo" / "1.0.0"
        _write_manifest(plugin_dir, "foo-plugin")
        src = _source(
            tmp,
            installed_plugins={
                "foo-plugin@mp": [
                    {"scope": "user", "installPath": str(plugin_dir)}
                ]
            },
            settings={"enabledPlugins": {"foo-plugin@mp": False}},
        )
        names = {p.name for p in src.load_plugins()}
        assert "foo-plugin" not in names, names


def test_disabled_in_local_settings_wins():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        plugin_dir = tmp / "cache" / "foo" / "1.0.0"
        _write_manifest(plugin_dir, "foo-plugin")
        src = _source(
            tmp,
            installed_plugins={
                "foo-plugin@mp": [{"scope": "user", "installPath": str(plugin_dir)}]
            },
            settings={"enabledPlugins": {"foo-plugin@mp": True}},
            settings_local={"enabledPlugins": {"foo-plugin@mp": False}},
        )
        names = {p.name for p in src.load_plugins()}
        assert "foo-plugin" not in names, names


def test_missing_installed_plugins_file_does_not_crash():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        src = _source(tmp)  # no installed_plugins.json written
        assert src.marketplace_plugin_dirs == []
        assert src.load_plugins() == []


def test_malformed_installed_plugins_file_does_not_crash():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        installed_file = tmp / "installed_plugins.json"
        installed_file.write_text("{not valid json")
        src = _source(tmp)  # installed_plugins.json already malformed on disk above
        assert src.marketplace_plugin_dirs == []


def test_bare_dict_record_is_normalized_to_list():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        plugin_dir = tmp / "cache" / "foo" / "1.0.0"
        _write_manifest(plugin_dir, "foo-plugin")
        installed_file = tmp / "installed_plugins.json"
        installed_file.write_text(json.dumps({
            "version": 2,
            # bare dict, not wrapped in a list -- installed_plugins.json's schema
            # allows a single scope record without list-wrapping.
            "plugins": {"foo-plugin@mp": {"scope": "user", "installPath": str(plugin_dir)}},
        }))
        src = PluginSource(
            global_plugins_dir=tmp / "no-global-plugins",
            local_plugins_dir=tmp / "no-local-plugins",
            installed_plugins_file=installed_file,
            claude_settings_file=tmp / "settings.json",
            claude_settings_local_file=tmp / "settings.local.json",
        )
        assert src.marketplace_plugin_dirs == [plugin_dir], src.marketplace_plugin_dirs


def test_user_scope_preferred_over_project_scope():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        project_dir = tmp / "cache" / "foo-project" / "1.0.0"
        user_dir = tmp / "cache" / "foo-user" / "1.0.0"
        _write_manifest(project_dir, "foo-plugin")
        _write_manifest(user_dir, "foo-plugin")
        src = _source(
            tmp,
            installed_plugins={
                "foo-plugin@mp": [
                    {"scope": "project", "installPath": str(project_dir)},
                    {"scope": "user", "installPath": str(user_dir)},
                ]
            },
        )
        assert src.marketplace_plugin_dirs == [user_dir], src.marketplace_plugin_dirs


def test_falls_back_to_project_scope_when_user_scope_path_is_stale():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        stale_user_dir = tmp / "cache" / "foo-user" / "1.0.0"  # never created
        project_dir = tmp / "cache" / "foo-project" / "1.0.0"
        _write_manifest(project_dir, "foo-plugin")
        src = _source(
            tmp,
            installed_plugins={
                "foo-plugin@mp": [
                    {"scope": "user", "installPath": str(stale_user_dir)},
                    {"scope": "project", "installPath": str(project_dir)},
                ]
            },
        )
        assert src.marketplace_plugin_dirs == [project_dir], src.marketplace_plugin_dirs


def test_multi_scope_entry_dedupes_to_one_plugin():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        plugin_dir = tmp / "cache" / "foo" / "1.0.0"
        _write_manifest(plugin_dir, "foo-plugin")
        src = _source(
            tmp,
            installed_plugins={
                "foo-plugin@mp": [
                    {"scope": "project", "installPath": str(plugin_dir)},
                    {"scope": "user", "installPath": str(plugin_dir)},
                ]
            },
        )
        loaded = [p for p in src.load_plugins() if p.name == "foo-plugin"]
        assert len(loaded) == 1, loaded


def test_stale_install_path_is_skipped_others_still_load():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        good_dir = tmp / "cache" / "good" / "1.0.0"
        _write_manifest(good_dir, "good-plugin")
        stale_dir = tmp / "cache" / "stale" / "1.0.0"  # never created on disk
        src = _source(
            tmp,
            installed_plugins={
                "good-plugin@mp": [{"scope": "user", "installPath": str(good_dir)}],
                "stale-plugin@mp": [{"scope": "user", "installPath": str(stale_dir)}],
            },
        )
        names = {p.name for p in src.load_plugins()}
        assert "good-plugin" in names, names
        assert "stale-plugin" not in names, names


def test_local_dotfiles_plugin_overrides_marketplace_by_name():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        marketplace_dir = tmp / "cache" / "shared" / "1.0.0"
        _write_manifest(marketplace_dir, "shared-plugin")

        local_root = tmp / "local-plugins"
        local_plugin_dir = local_root / "shared-plugin"
        _write_manifest(local_plugin_dir, "shared-plugin")

        installed_file = tmp / "installed_plugins.json"
        installed_file.write_text(json.dumps({
            "version": 2,
            "plugins": {
                "shared-plugin@mp": [{"scope": "user", "installPath": str(marketplace_dir)}]
            },
        }))

        src = PluginSource(
            global_plugins_dir=tmp / "no-global-plugins",
            local_plugins_dir=local_root,
            installed_plugins_file=installed_file,
            claude_settings_file=tmp / "settings.json",
            claude_settings_local_file=tmp / "settings.local.json",
        )
        loaded = {p.name: p for p in src.load_plugins()}
        assert loaded["shared-plugin"].source_dir == str(local_plugin_dir)


def test_unsafe_manifest_name_falls_back_to_directory_name():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        plugin_dir = tmp / "cache" / "foo" / "1.0.0"
        # A manifest name with a path separator/traversal segment must never be
        # trusted to build destination paths -- fall back to the safe dir name.
        _write_manifest(plugin_dir, "../../etc/pwned")
        src = _source(
            tmp,
            installed_plugins={
                "foo-plugin@mp": [{"scope": "user", "installPath": str(plugin_dir)}]
            },
        )
        loaded = src.load_plugins()
        names = {p.name for p in loaded}
        assert "../../etc/pwned" not in names, names
        assert "1.0.0" in names, names  # plugin_dir.name


def test_symlinked_command_is_skipped():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        plugin_dir = tmp / "cache" / "foo" / "1.0.0"
        _write_manifest(plugin_dir, "foo-plugin")
        secret = tmp / "secret.md"
        secret.write_text("top secret content")
        commands_dir = plugin_dir / "commands"
        commands_dir.mkdir(parents=True)
        (commands_dir / "linked.md").symlink_to(secret)
        src = _source(
            tmp,
            installed_plugins={
                "foo-plugin@mp": [{"scope": "user", "installPath": str(plugin_dir)}]
            },
        )
        loaded = {p.name: p for p in src.load_plugins()}
        assert loaded["foo-plugin"].commands == [], loaded["foo-plugin"].commands


def run_all():
    tests = [v for k, v in globals().items() if k.startswith("test_") and callable(v)]
    for t in tests:
        t()
        print(f"ok  {t.__name__}")
    print(f"\n{len(tests)} checks passed")


if __name__ == "__main__":
    run_all()
