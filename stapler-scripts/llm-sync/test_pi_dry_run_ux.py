"""Surface 4 UX acceptance checks: `sync_pi_settings` dry-run output.

Covers project_plans/pi-dotfiles/design/ux.md's "bootstrap/pyinfra dry-run
output" surface, criteria 1, 3, and 5 (destination path, no credential leak,
closing line). Criterion 2 (enumerate each changed key individually) is a
known, tracked gap: `PiSettingsTarget.save()` only returns a bool today, not
the set of changed keys, so there's nothing for `sync_pi_settings` to print
per-key without changing that method's return contract (and the several
existing `assert target.save(...) is True/False` call sites in
test_pi_settings_target.py that depend on it) -- out of scope for this pass.

Run directly: uv run test_pi_dry_run_ux.py
"""

import argparse
import contextlib
import io
import json
import tempfile
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent / "src"))

from cli import sync_pi_settings
from sources.pi_config import PiConfigError


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def _base_args(root: Path, **overrides) -> argparse.Namespace:
    defaults = dict(
        pi_dir=root / "agent",
        pi_config_file=root / "config.json",
        pi_config_dir=root / "config.d",
        pi_local_config=root / "config.local.json",
        pi_local_config_dir=root / "config.local.d",
        pi_extensions_manifest=root / "extensions-manifest.json",
        pi_settings_file=root / "agent" / "settings.json",
        pi_settings_state_file=root / "settings-state.json",
        pi_package_ledger_state_file=root / "package-state.json",
        dry_run=True,
        prune_stale_pi_packages=False,
        reconcile_pi_package_ledger=False,
    )
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


def _run_sync(args: argparse.Namespace) -> str:
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        sync_pi_settings(args)
    return out.getvalue()


def test_dry_run_names_destination_path_pi_dir_or_real_path():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _write_json(root / "config.d" / "10-settings.json", {"settings": {"theme": "dark"}})
        _write_json(root / "extensions-manifest.json", {"extensions": {}})
        agent_dir = root / "agent"

        output = _run_sync(_base_args(root))

        assert str(agent_dir) in output


def test_dry_run_output_contains_no_credential_shaped_value():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        secret_value = "sk-super-secret-value-should-never-print"
        _write_json(
            root / "config.d" / "10-settings.json",
            {"settings": {"apiKey": secret_value}},
        )
        _write_json(root / "extensions-manifest.json", {"extensions": {}})

        out = io.StringIO()
        raised = None
        try:
            with contextlib.redirect_stdout(out):
                sync_pi_settings(_base_args(root))
        except PiConfigError as error:
            raised = error

        # The credential-material check runs before any dry-run print, so the
        # sync must abort rather than silently continue.
        assert raised is not None
        assert "apiKey" in str(raised)
        output = out.getvalue()
        assert secret_value not in output
        assert secret_value not in str(raised)
        for needle in ("apikey", "token", "auth"):
            assert needle not in output.lower()


def test_dry_run_closing_line_states_no_changes_made_and_destination():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _write_json(root / "config.d" / "10-settings.json", {"settings": {"theme": "dark"}})
        _write_json(root / "extensions-manifest.json", {"extensions": {}})
        agent_dir = root / "agent"

        output = _run_sync(_base_args(root))

        assert f"No changes made to {agent_dir} (dry run)." in output.splitlines()


def test_dry_run_closing_line_present_even_when_already_converged():
    """A dry run against an already-converged state still states no changes
    were made -- the closing line isn't conditional on there being a diff.
    """
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _write_json(root / "config.d" / "10-settings.json", {"settings": {}})
        _write_json(root / "extensions-manifest.json", {"extensions": {}})
        agent_dir = root / "agent"

        # First, a real (non-dry) run to converge state on disk...
        _run_sync(_base_args(root, dry_run=False))
        # ...then a dry run should report no changes without an "update" line.
        output = _run_sync(_base_args(root))

        assert f"No changes made to {agent_dir} (dry run)." in output.splitlines()
        assert "Would update managed Pi settings" not in output


if __name__ == "__main__":
    tests = [value for key, value in list(globals().items()) if key.startswith("test_")]
    for test in tests:
        test()
        print(f"ok  {test.__name__}")
    print(f"\n{len(tests)} checks passed")
