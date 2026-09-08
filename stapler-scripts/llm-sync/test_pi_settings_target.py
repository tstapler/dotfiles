"""Regression checks for ownership-safe Pi settings writes.

Run directly: uv run test_pi_settings_target.py
"""

import json
import sys
import tempfile
from pathlib import Path

sys.path.append(str(Path(__file__).parent / "src"))

from sources.pi_config import LoadedPiConfig
from targets.pi_settings import PiSettingsTarget, PiSettingsTargetError


def _loaded(settings: dict, managed_keys: set[str]) -> LoadedPiConfig:
    return LoadedPiConfig(settings=settings, managed_keys=managed_keys, layers=())


def test_replaces_previously_managed_keys_and_preserves_unmanaged_state():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        settings_path = root / "agent" / "settings.json"
        state_path = root / "state.json"
        settings_path.parent.mkdir(parents=True)
        settings_path.write_text(
            json.dumps(
                {
                    "theme": "old",
                    "obsoleteManaged": True,
                    "lastChangelogVersion": "0.84.4",
                    "manualPreference": "keep",
                }
            ),
            encoding="utf-8",
        )
        state_path.write_text(
            json.dumps({"managedKeys": ["theme", "obsoleteManaged"]}),
            encoding="utf-8",
        )

        changed = PiSettingsTarget(settings_path, state_path).save(
            _loaded(
                {"theme": "dark", "packages": ["npm:@work-org/pi-agent"]},
                {"theme", "packages"},
            )
        )

        assert changed is True
        assert json.loads(settings_path.read_text(encoding="utf-8")) == {
            "lastChangelogVersion": "0.84.4",
            "manualPreference": "keep",
            "packages": ["npm:@work-org/pi-agent"],
            "theme": "dark",
        }
        assert json.loads(state_path.read_text(encoding="utf-8")) == {
            "managedKeys": ["packages", "theme"]
        }


def test_second_identical_save_is_idempotent():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        target = PiSettingsTarget(root / "settings.json", root / "state.json")
        config = _loaded({"theme": "dark"}, {"theme"})

        assert target.save(config) is True
        assert target.save(config) is False


def test_dry_run_does_not_write_files():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        settings_path = root / "settings.json"
        state_path = root / "state.json"

        changed = PiSettingsTarget(settings_path, state_path).save(
            _loaded({"theme": "dark"}, {"theme"}), dry_run=True
        )

        assert changed is True
        assert not settings_path.exists()
        assert not state_path.exists()


def test_rejects_malformed_ownership_state():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        state_path = root / "state.json"
        state_path.write_text("not-json", encoding="utf-8")

        try:
            PiSettingsTarget(root / "settings.json", state_path).save(
                _loaded({"theme": "dark"}, {"theme"})
            )
        except PiSettingsTargetError as error:
            assert str(state_path) in str(error)
        else:
            raise AssertionError("malformed ownership state should fail safely")


if __name__ == "__main__":
    tests = [value for key, value in list(globals().items()) if key.startswith("test_")]
    for test in tests:
        test()
        print(f"ok  {test.__name__}")
    print(f"\n{len(tests)} checks passed")
