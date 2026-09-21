"""Regression checks for the Pi package ownership ledger.

Run directly: uv run test_pi_package_ledger.py
"""

import argparse
import contextlib
import io
import json
import sys
import tempfile
from pathlib import Path

sys.path.append(str(Path(__file__).parent / "src"))

from cli import sync_pi_settings
from targets.pi_package_ledger import PiPackageLedger, PiPackageLedgerError

_NPM_SOURCE = "npm:@gotgenes/pi-permission-system"
_NPM_ARTIFACT_SUFFIX = Path("npm") / "node_modules" / "@gotgenes" / "pi-permission-system"


# --- direct PiPackageLedger unit tests -------------------------------------


def test_pi_package_ledger_save_records_artifact_paths_for_enabled_entries():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        ledger = PiPackageLedger(state_path=root / "state.json", agent_dir=root / "agent")

        changed = ledger.save({"gotgenes-pi-packages": _NPM_SOURCE})

        assert changed is True
        recorded = json.loads((root / "state.json").read_text(encoding="utf-8"))
        assert recorded == {
            "gotgenes-pi-packages": str(root / "agent" / _NPM_ARTIFACT_SUFFIX)
        }


def test_pi_package_ledger_find_stale_reports_without_deleting():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        artifact_dir = root / "agent" / _NPM_ARTIFACT_SUFFIX
        artifact_dir.mkdir(parents=True)
        (artifact_dir / "index.js").write_text("// installed", encoding="utf-8")

        state_path = root / "state.json"
        state_path.write_text(
            json.dumps({"gotgenes-pi-packages": str(artifact_dir)}), encoding="utf-8"
        )
        ledger = PiPackageLedger(state_path=state_path, agent_dir=root / "agent")

        stale = ledger.find_stale(current_ids=set())

        assert stale == ["gotgenes-pi-packages"]
        assert artifact_dir.exists()
        assert json.loads(state_path.read_text(encoding="utf-8")) == {
            "gotgenes-pi-packages": str(artifact_dir)
        }


def test_pi_package_ledger_prune_deletes_only_ledger_recorded_paths():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        managed_dir = root / "agent" / _NPM_ARTIFACT_SUFFIX
        managed_dir.mkdir(parents=True)
        (managed_dir / "index.js").write_text("// installed", encoding="utf-8")

        unmanaged_dir = root / "agent" / "npm" / "node_modules" / "unmanaged-package"
        unmanaged_dir.mkdir(parents=True)
        (unmanaged_dir / "index.js").write_text("// not tracked", encoding="utf-8")

        state_path = root / "state.json"
        state_path.write_text(
            json.dumps({"gotgenes-pi-packages": str(managed_dir)}), encoding="utf-8"
        )
        ledger = PiPackageLedger(state_path=state_path, agent_dir=root / "agent")

        stale = ledger.find_stale(current_ids=set())
        deleted = ledger.prune(stale, dry_run=False)

        assert deleted == [str(managed_dir)]
        assert not managed_dir.exists()
        assert unmanaged_dir.exists()
        assert json.loads(state_path.read_text(encoding="utf-8")) == {}


def test_pi_package_ledger_prune_dry_run_deletes_nothing():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        managed_dir = root / "agent" / _NPM_ARTIFACT_SUFFIX
        managed_dir.mkdir(parents=True)

        state_path = root / "state.json"
        state_path.write_text(
            json.dumps({"gotgenes-pi-packages": str(managed_dir)}), encoding="utf-8"
        )
        ledger = PiPackageLedger(state_path=state_path, agent_dir=root / "agent")

        deleted = ledger.prune(["gotgenes-pi-packages"], dry_run=True)

        assert deleted == [str(managed_dir)]
        assert managed_dir.exists()
        assert json.loads(state_path.read_text(encoding="utf-8")) == {
            "gotgenes-pi-packages": str(managed_dir)
        }


def test_pi_package_ledger_reconcile_recovers_entry_after_interrupted_write():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        ledger = PiPackageLedger(state_path=root / "state.json", agent_dir=root / "agent")
        # No ledger file at all: simulates PiSettingsTarget.save() having
        # succeeded (settings.json already reflects the entry as active)
        # but the process crashing before PiPackageLedger.save() ran.
        enabled_packages = {"gotgenes-pi-packages": _NPM_SOURCE}

        recovered = ledger.reconcile(enabled_packages)

        assert recovered == ["gotgenes-pi-packages"]
        assert json.loads((root / "state.json").read_text(encoding="utf-8")) == {
            "gotgenes-pi-packages": str(root / "agent" / _NPM_ARTIFACT_SUFFIX)
        }
        assert ledger.find_stale(current_ids={"gotgenes-pi-packages"}) == []


def test_pi_package_ledger_reconcile_never_overwrites_existing_entries():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        state_path = root / "state.json"
        state_path.write_text(
            json.dumps({"gotgenes-pi-packages": "/pinned/by/hand"}), encoding="utf-8"
        )
        ledger = PiPackageLedger(state_path=state_path, agent_dir=root / "agent")

        recovered = ledger.reconcile({"gotgenes-pi-packages": _NPM_SOURCE})

        assert recovered == []
        assert json.loads(state_path.read_text(encoding="utf-8")) == {
            "gotgenes-pi-packages": "/pinned/by/hand"
        }


def test_pi_package_ledger_save_records_null_for_unverified_source_shape():
    """Non-npm sources (git-fork, local path) have no confirmed artifact-path
    pattern per the Epic 2.1 spike, so they're recorded as an explicit
    unknown sentinel rather than a fabricated path."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        ledger = PiPackageLedger(state_path=root / "state.json", agent_dir=root / "agent")

        ledger.save(
            {"fork-package": "git:github.com/tstapler/pi-tools@abc1234"}
        )

        assert json.loads((root / "state.json").read_text(encoding="utf-8")) == {
            "fork-package": None
        }


def test_pi_package_ledger_save_rejects_malformed_ledger_state():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        state_path = root / "state.json"
        state_path.write_text("not-json", encoding="utf-8")
        ledger = PiPackageLedger(state_path=state_path, agent_dir=root / "agent")

        try:
            ledger.save({"gotgenes-pi-packages": _NPM_SOURCE})
        except PiPackageLedgerError as error:
            assert str(state_path) in str(error)
        else:
            raise AssertionError("malformed ledger state should fail safely")


# --- CLI-level (Surface 3) tests --------------------------------------------


def _write_json(path: Path, value: object) -> None:
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
        dry_run=False,
        prune_stale_pi_packages=False,
        reconcile_pi_package_ledger=False,
    )
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


def _seed_environment(root: Path) -> Path:
    """Config with no packages enabled, plus a pre-existing stale ledger entry
    named `old-extension` whose recorded artifact path is a real directory.

    Returns that artifact directory so tests can assert on its survival or
    deletion.
    """
    _write_json(root / "config.d" / "10-empty.json", {"packages": {}})
    _write_json(root / "extensions-manifest.json", {"extensions": {}})

    artifact_dir = root / "agent" / "npm" / "node_modules" / "old-extension"
    artifact_dir.mkdir(parents=True)
    (artifact_dir / "index.js").write_text("// stale", encoding="utf-8")

    _write_json(root / "package-state.json", {"old-extension": str(artifact_dir)})
    return artifact_dir


def _run_sync(args: argparse.Namespace) -> str:
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        sync_pi_settings(args)
    return out.getvalue()


def test_stale_report_line_matches_exact_format_without_prune_flag():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        artifact_dir = _seed_environment(root)

        output = _run_sync(_base_args(root))

        assert (
            "stale Pi package: old-extension "
            "(not pruned; run with --prune-stale-pi-packages)"
        ) in output.splitlines()
        assert artifact_dir.exists()


def test_stale_report_always_runs_deletion_only_with_flag():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        artifact_dir = _seed_environment(root)

        without_flag = _run_sync(_base_args(root))
        assert "stale Pi package: old-extension" in without_flag
        assert artifact_dir.exists()

        with_flag = _run_sync(_base_args(root, prune_stale_pi_packages=True))
        assert "stale Pi package: old-extension" in with_flag
        assert not artifact_dir.exists()


def test_prune_flag_prints_pruned_path_after_deletion():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        artifact_dir = _seed_environment(root)

        output = _run_sync(_base_args(root, prune_stale_pi_packages=True))

        stale_index = output.index("stale Pi package: old-extension")
        pruned_index = output.index(f"Pruned: {artifact_dir}")
        assert pruned_index > stale_index
        assert not artifact_dir.exists()


def test_prune_output_silent_for_paths_outside_ledger():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        artifact_dir = _seed_environment(root)
        unmanaged_dir = root / "agent" / "npm" / "node_modules" / "unmanaged-package"
        unmanaged_dir.mkdir(parents=True)
        (unmanaged_dir / "index.js").write_text("// keep me", encoding="utf-8")

        output = _run_sync(_base_args(root, prune_stale_pi_packages=True))

        assert "unmanaged-package" not in output
        assert unmanaged_dir.exists()
        assert not artifact_dir.exists()


if __name__ == "__main__":
    tests = [value for key, value in list(globals().items()) if key.startswith("test_")]
    for test in tests:
        test()
        print(f"ok  {test.__name__}")
    print(f"\n{len(tests)} checks passed")
