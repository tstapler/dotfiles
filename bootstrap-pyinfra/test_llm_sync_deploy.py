"""Verifies the pass-through claim in deploys/llm_sync.py's docstring: that
main.py's `stale Pi package: ...` report line survives unmodified through
`common.shell_capture`, the mechanism `llm_sync()` uses to invoke main.py.

`llm_sync()` itself can't be called directly here: it's a pyinfra
`@deploy`-decorated function that calls `shell_capture`, which calls
`host.get_fact()`, and that only resolves inside a connected pyinfra run --
not a plain `uv run` test process (the same reason test_pi_install.py only
tests the pure functions in deploys/pi.py, never the `@deploy("Pi")`-decorated
`pi()` itself). So these tests reproduce llm_sync()'s actual invocation shape
via subprocess instead: driving main.py's real CLI entrypoint through `uv
run` (the same tool llm_sync()'s shell command uses), against a fixture
matching stapler-scripts/llm-sync/test_pi_package_ledger.py's
`_seed_environment`/`_base_args` pattern for a single stale ledger entry.

Run directly: uv run test_llm_sync_deploy.py
"""

import json
import subprocess
import tempfile
from pathlib import Path

LLM_SYNC_DIR = Path(__file__).parent.parent / "stapler-scripts" / "llm-sync"

_STALE_LINE = (
    "stale Pi package: old-extension (not pruned; run with --prune-stale-pi-packages)"
)

# Marker string common.shell_capture uses to split captured output from the
# trailing exit code it appends via `printf "%s{marker}%d" "$OUT" "$CODE"`.
_SHELL_CAPTURE_MARKER = "__PYINFRA_EXIT__"


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def _seed_environment(root: Path) -> Path:
    """Same fixture shape as test_pi_package_ledger.py's `_seed_environment`:
    no packages enabled in config, plus a pre-existing stale ledger entry
    named `old-extension` whose recorded artifact path is a real directory.
    """
    _write_json(root / "config.d" / "10-empty.json", {"packages": {}})
    _write_json(root / "extensions-manifest.json", {"extensions": {}})

    artifact_dir = root / "agent" / "npm" / "node_modules" / "old-extension"
    artifact_dir.mkdir(parents=True)
    (artifact_dir / "index.js").write_text("// stale", encoding="utf-8")

    _write_json(root / "package-state.json", {"old-extension": str(artifact_dir)})
    return artifact_dir


def _main_py_args(root: Path) -> list[str]:
    """The subset of main.py's fixture-pointing flags needed to reach the
    stale-report code path without touching this machine's real ~/.claude,
    ~/.pi, or ~/.config/pi state."""
    return [
        "main.py",
        "--target",
        "pi",
        "--source-dir",
        str(root / "claude_src"),  # empty/nonexistent: no real Claude assets synced
        "--state-file",
        str(root / "state.json"),
        "--pi-dir",
        str(root / "agent"),
        "--pi-config-file",
        str(root / "config.json"),
        "--pi-config-dir",
        str(root / "config.d"),
        "--pi-local-config",
        str(root / "config.local.json"),
        "--pi-local-config-dir",
        str(root / "config.local.d"),
        "--pi-extensions-manifest",
        str(root / "extensions-manifest.json"),
        "--pi-settings-file",
        str(root / "agent" / "settings.json"),
        "--pi-settings-state-file",
        str(root / "settings-state.json"),
        "--pi-package-ledger-state-file",
        str(root / "package-state.json"),
    ]


def test_llm_sync_deploy_prints_stale_pi_package_report_line() -> None:
    """main.py, invoked through its real CLI entrypoint via `uv run` (the
    same tool llm_sync()'s shell command uses) rather than calling
    sync_pi_settings() in-process, reaches the stale-report code path and
    prints the byte-exact line."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _seed_environment(root)

        result = subprocess.run(
            ["uv", "run", *_main_py_args(root)],
            cwd=LLM_SYNC_DIR,
            capture_output=True,
            text=True,
            timeout=60,
        )

        assert result.returncode == 0, result.stdout + result.stderr
        assert _STALE_LINE in result.stdout.splitlines()


def test_bootstrap_llm_sync_reproduces_exact_stale_report_line() -> None:
    """Reproduces `common.shell_capture`'s exact command shape --
    `OUT=$(command 2>&1); CODE=$?; printf "%s{marker}%d" "$OUT" "$CODE"`,
    then splitting on the marker the same way shell_capture does -- to prove
    the specific pass-through mechanism llm_sync() relies on (combining
    stdout+stderr through command substitution) doesn't truncate, reorder,
    or otherwise mangle the stale-report line."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _seed_environment(root)

        inner_command = "uv run " + " ".join(_main_py_args(root))
        wrapped = (
            f'OUT=$({inner_command} 2>&1); CODE=$?; '
            f'printf "%s{_SHELL_CAPTURE_MARKER}%d" "$OUT" "$CODE"'
        )

        result = subprocess.run(
            ["bash", "-c", wrapped],
            cwd=LLM_SYNC_DIR,
            capture_output=True,
            text=True,
            timeout=60,
        )

        assert result.returncode == 0, result.stdout + result.stderr
        captured_output, _, exit_code = result.stdout.rpartition(
            _SHELL_CAPTURE_MARKER
        )

        assert exit_code == "0", result.stdout
        assert _STALE_LINE in captured_output.splitlines()


if __name__ == "__main__":
    tests = [value for key, value in list(globals().items()) if key.startswith("test_")]
    for test in tests:
        test()
        print(f"ok  {test.__name__}")
    print(f"\n{len(tests)} checks passed")
