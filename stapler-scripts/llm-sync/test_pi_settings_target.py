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


def test_rollback_restores_only_managed_keys_and_preserves_auth_and_sessions():
    """Rollback procedure verification for rollout-runbook.md's Task 5.2.1b.

    The runbook's documented rollback is a literal `cp` of settings.json and
    the state file, not a call through PiSettingsTarget. This proves two
    things empirically: PiSettingsTarget never touches auth.json/session
    files (so a rollback that never names them is safe by construction), and
    the restore is a whole-file copy rather than a managedKeys-scoped patch
    -- a work-only key changed by something other than PiSettingsTarget
    between backup and rollback is reverted too, not preserved. This
    contradicts a literal reading of the runbook's "no more, no less" claim;
    see the corrected wording in rollout-runbook.md's Rollback section.
    """
    with tempfile.TemporaryDirectory() as tmp:
        agent_dir = Path(tmp) / "agent"
        agent_dir.mkdir()
        settings_path = agent_dir / "settings.json"
        state_path = agent_dir / "pi-settings-state.json"
        auth_path = agent_dir / "auth.json"
        session_path = agent_dir / "session-abc123.json"

        # Pre-adoption: theme/packages are managedKeys-tracked; workOnlyKey
        # simulates a pre-existing work-specific key dotfiles never manages.
        settings_path.write_text(
            json.dumps(
                {
                    "theme": "old-theme",
                    "packages": ["npm:@tstapler/pi-permission-system"],
                    "workOnlyKey": "pre-existing-work-value",
                }
            ),
            encoding="utf-8",
        )
        state_path.write_text(
            json.dumps({"managedKeys": ["theme", "packages"]}), encoding="utf-8"
        )
        auth_content = b'{"token": "do-not-touch-me"}'
        session_content = b'{"sessionId": "abc123", "history": ["hi"]}'
        auth_path.write_bytes(auth_content)
        session_path.write_bytes(session_content)

        # Task 5.2.1a: backup is a literal file copy, taken before adoption.
        settings_backup = settings_path.with_name(settings_path.name + ".pre-dotfiles-backup")
        state_backup = state_path.with_name(state_path.name + ".pre-dotfiles-backup")
        settings_backup.write_bytes(settings_path.read_bytes())
        state_backup.write_bytes(state_path.read_bytes())

        # Adoption: a managed sync mutates only the managed keys...
        changed = PiSettingsTarget(settings_path, state_path).save(
            _loaded(
                {
                    "theme": "new-theme",
                    "packages": [
                        "npm:@tstapler/pi-permission-system",
                        "npm:@work-org/pi-agent",
                    ],
                },
                {"theme", "packages"},
            )
        )
        assert changed is True

        # ...proven empirically: workOnlyKey and the auth/session files are
        # untouched by PiSettingsTarget itself.
        after_save = json.loads(settings_path.read_text(encoding="utf-8"))
        assert after_save["workOnlyKey"] == "pre-existing-work-value"
        assert auth_path.read_bytes() == auth_content
        assert session_path.read_bytes() == session_content

        # ...and, separately, something other than PiSettingsTarget (Pi
        # itself, a manual edit) changes the non-managed key in the same
        # adopted window, to test whether rollback really scopes itself to
        # managedKeys or reverts the whole file.
        after_save["workOnlyKey"] = "changed-after-adoption-by-something-else"
        settings_path.write_text(json.dumps(after_save), encoding="utf-8")

        # Task 5.2.1b: rollback is a literal file copy, not a
        # PiSettingsTarget call.
        settings_path.write_bytes(settings_backup.read_bytes())
        state_path.write_bytes(state_backup.read_bytes())

        restored_settings = json.loads(settings_path.read_text(encoding="utf-8"))
        restored_state = json.loads(state_path.read_text(encoding="utf-8"))

        assert restored_settings["theme"] == "old-theme"
        assert restored_settings["packages"] == ["npm:@tstapler/pi-permission-system"]
        assert restored_state == {"managedKeys": ["theme", "packages"]}

        # Discrepancy: the runbook claims this restore touches "exactly the
        # keys that were present in managedKeys ... no more, no less." The
        # actual mechanism is a whole-file copy, so workOnlyKey's
        # out-of-band post-adoption change is reverted too, not preserved.
        assert restored_settings["workOnlyKey"] == "pre-existing-work-value"

        # The one guarantee that holds unconditionally, because the copy
        # commands never name these paths at all.
        assert auth_path.read_bytes() == auth_content
        assert session_path.read_bytes() == session_content


if __name__ == "__main__":
    tests = [value for key, value in list(globals().items()) if key.startswith("test_")]
    for test in tests:
        test()
        print(f"ok  {test.__name__}")
    print(f"\n{len(tests)} checks passed")
