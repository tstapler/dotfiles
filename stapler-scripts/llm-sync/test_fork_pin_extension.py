#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "typer>=0.12",
# ]
# ///
"""Regression checks for the fork-and-pin helper script.

Run directly: uv run test_fork_pin_extension.py

Every `gh` call is mocked -- no real network/GitHub access happens here.
"""

import contextlib
import inspect
import io
import json
import re
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.append(str(Path(__file__).parent / "src"))
sys.path.append(str(Path(__file__).parent / "scripts"))

import typer  # noqa: E402 (path setup above must run first)
import typer.main  # noqa: E402

import fork_pin_extension  # noqa: E402

_SCRIPT_PATH = Path(__file__).parent / "scripts" / "fork_pin_extension.py"

# Matches an exact quoted string literal `"approved"` / `'approved'` -- but
# not `"approved_by"` or `"approved_date"`, which are real, required field
# names this script legitimately references (always to set them to null).
_APPROVED_LITERAL_RE = re.compile(r"""(['"])approved\1""")

_FIXED_SHA = "cafef00d0123456789abcdef0123456789abcdef"


def _write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def _run_fork(**kwargs) -> tuple[str, str, int | None]:
    """Call the `fork` command function directly, capturing stdout/stderr.

    Returns (stdout, stderr, exit_code). exit_code is None when the command
    returned normally instead of raising typer.Exit.
    """
    out, err = io.StringIO(), io.StringIO()
    exit_code = None
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            fork_pin_extension.fork(**kwargs)
    except typer.Exit as exit_error:
        exit_code = exit_error.exit_code
    return out.getvalue(), err.getvalue(), exit_code


def _extract_json_block(stdout: str, heading: str) -> dict:
    """Pull the JSON entry printed under `heading` (see `_print_entry`).

    Uses `raw_decode` rather than `json.loads` because real (non-dry-run)
    output has more lines after the JSON block; `raw_decode` stops at the
    end of the first JSON value instead of erroring on the trailing text.
    """
    _, _, remainder = stdout.partition(heading + "\n")
    assert remainder, f"expected stdout to contain heading {heading!r}:\n{stdout}"
    entry, _ = json.JSONDecoder().raw_decode(remainder)
    return entry


def test_fork_pin_extension_argparser_has_no_flag_that_writes_approved_disposition():
    source = _SCRIPT_PATH.read_text(encoding="utf-8")
    matches = _APPROVED_LITERAL_RE.findall(source)
    assert not matches, (
        "fork_pin_extension.py must never contain the quoted string literal "
        "'approved' -- that's the one value disposition/approved_by/"
        "approved_date must never be assigned by this script. (Field "
        "*names* like approved_by/approved_date are fine and expected; "
        "only the literal value \"approved\" is banned.) A source-text scan "
        "was chosen over pure signature introspection because the value "
        "could otherwise be smuggled in via a default, a constant, or a "
        "dict literal that never shows up as a CLI-visible flag."
    )

    # Belt-and-suspenders: introspect the actual click command typer builds,
    # confirming no declared CLI parameter is itself approval-named or
    # defaults to the literal value "approved".
    click_command = typer.main.get_command(fork_pin_extension.app)
    for param in click_command.params:
        assert "approv" not in (param.name or "").lower(), (
            f"unexpected approval-related CLI parameter: {param.name}"
        )
        assert "approved" != str(param.default).lower()


def test_fork_pin_extension_fork_creates_candidate_manifest_entry_with_fork_commit():
    with tempfile.TemporaryDirectory() as tmp:
        manifest_file = Path(tmp) / "extensions-manifest.json"

        with (
            patch.object(fork_pin_extension, "run_gh_fork") as mock_fork,
            patch.object(fork_pin_extension, "run_gh_head_commit", return_value=_FIXED_SHA),
        ):
            stdout, stderr, exit_code = _run_fork(
                upstream="gotgenes/pi-packages",
                entry_id="gotgenes-pi-packages",
                capability="permission-system,subagents",
                dry_run=False,
                manifest_file=manifest_file,
            )

        assert exit_code is None, f"unexpected failure: {stderr}"
        mock_fork.assert_called_once_with("gotgenes/pi-packages")

        written = json.loads(manifest_file.read_text(encoding="utf-8"))
        entry = written["extensions"]["gotgenes-pi-packages"]
        assert entry["disposition"] == "candidate"
        assert entry["fork_repo"] == "https://github.com/tstapler/pi-packages"
        assert entry["fork_commit"] == _FIXED_SHA
        assert entry["approved_by"] is None
        assert entry["approved_date"] is None


def test_fork_pin_extension_fork_fails_when_id_already_has_manifest_entry():
    with tempfile.TemporaryDirectory() as tmp:
        manifest_file = Path(tmp) / "extensions-manifest.json"
        _write(
            manifest_file,
            {"extensions": {"existing-id": {"disposition": "candidate"}}},
        )

        with (
            patch.object(fork_pin_extension, "run_gh_fork") as mock_fork,
            patch.object(fork_pin_extension, "run_gh_head_commit") as mock_commit,
        ):
            stdout, stderr, exit_code = _run_fork(
                upstream="gotgenes/pi-packages",
                entry_id="existing-id",
                capability="permission-system",
                dry_run=False,
                manifest_file=manifest_file,
            )

        assert exit_code == 1
        assert "existing-id" in stderr
        mock_fork.assert_not_called()
        mock_commit.assert_not_called()


def test_fork_pin_extension_dry_run_prints_plan_without_calling_gh():
    with tempfile.TemporaryDirectory() as tmp:
        manifest_file = Path(tmp) / "extensions-manifest.json"

        with patch.object(fork_pin_extension, "subprocess") as mock_subprocess:
            stdout, stderr, exit_code = _run_fork(
                upstream="gotgenes/pi-packages",
                entry_id="gotgenes-pi-packages",
                capability="permission-system",
                dry_run=True,
                manifest_file=manifest_file,
            )

        assert exit_code is None, f"unexpected failure: {stderr}"
        mock_subprocess.run.assert_not_called()
        assert not manifest_file.exists()


def test_fork_dry_run_shows_planned_target_and_manifest_diff_without_writing():
    with tempfile.TemporaryDirectory() as tmp:
        manifest_file = Path(tmp) / "extensions-manifest.json"
        _write(manifest_file, {"extensions": {}})
        original_bytes = manifest_file.read_bytes()

        def _fail_loudly(*_args, **_kwargs):
            raise AssertionError("gh must not be called during --dry-run")

        with (
            patch.object(fork_pin_extension, "run_gh_fork", side_effect=_fail_loudly),
            patch.object(fork_pin_extension, "run_gh_head_commit", side_effect=_fail_loudly),
        ):
            stdout, stderr, exit_code = _run_fork(
                upstream="gotgenes/pi-packages",
                entry_id="gotgenes-pi-packages",
                capability="permission-system",
                dry_run=True,
                manifest_file=manifest_file,
            )

        assert exit_code is None, f"unexpected failure: {stderr}"
        assert "Would fork:" in stdout
        assert "Would write to:" in stdout
        assert manifest_file.read_bytes() == original_bytes


def test_fork_output_shows_candidate_disposition_and_null_approval_fields_always():
    with tempfile.TemporaryDirectory() as tmp:
        dry_manifest = Path(tmp) / "dry-manifest.json"
        real_manifest = Path(tmp) / "real-manifest.json"

        dry_stdout, _, dry_exit = _run_fork(
            upstream="gotgenes/pi-packages",
            entry_id="gotgenes-pi-packages",
            capability="permission-system",
            dry_run=True,
            manifest_file=dry_manifest,
        )
        assert dry_exit is None

        with (
            patch.object(fork_pin_extension, "run_gh_fork"),
            patch.object(fork_pin_extension, "run_gh_head_commit", return_value=_FIXED_SHA),
        ):
            real_stdout, real_stderr, real_exit = _run_fork(
                upstream="gotgenes/pi-packages",
                entry_id="gotgenes-pi-packages",
                capability="permission-system",
                dry_run=False,
                manifest_file=real_manifest,
            )
        assert real_exit is None, f"unexpected failure: {real_stderr}"

        for stdout in (dry_stdout, real_stdout):
            assert '"disposition": "candidate"' in stdout
            assert '"approved_by": null' in stdout
            assert '"approved_date": null' in stdout


def test_fork_real_run_printed_commit_matches_manifest_written_commit():
    with tempfile.TemporaryDirectory() as tmp:
        manifest_file = Path(tmp) / "extensions-manifest.json"

        with (
            patch.object(fork_pin_extension, "run_gh_fork"),
            patch.object(fork_pin_extension, "run_gh_head_commit", return_value=_FIXED_SHA),
        ):
            stdout, stderr, exit_code = _run_fork(
                upstream="gotgenes/pi-packages",
                entry_id="gotgenes-pi-packages",
                capability="permission-system",
                dry_run=False,
                manifest_file=manifest_file,
            )
        assert exit_code is None, f"unexpected failure: {stderr}"

        printed = _extract_json_block(stdout, "Manifest entry:")
        written = json.loads(manifest_file.read_text(encoding="utf-8"))
        written_entry = written["extensions"]["gotgenes-pi-packages"]

        assert printed["fork_commit"] == written_entry["fork_commit"]
        assert printed["fork_commit"] == _FIXED_SHA


def test_fork_rerun_existing_id_fails_naming_id_and_current_disposition():
    with tempfile.TemporaryDirectory() as tmp:
        manifest_file = Path(tmp) / "extensions-manifest.json"
        _write(
            manifest_file,
            {
                "extensions": {
                    "gotgenes-pi-packages": {
                        "id": "gotgenes-pi-packages",
                        "disposition": "approved",
                        "approved_by": "tstapler",
                        "approved_date": "2026-09-01",
                    }
                }
            },
        )

        stdout, stderr, exit_code = _run_fork(
            upstream="gotgenes/pi-packages",
            entry_id="gotgenes-pi-packages",
            capability="permission-system",
            dry_run=False,
            manifest_file=manifest_file,
        )

        assert exit_code == 1
        assert "gotgenes-pi-packages" in stderr
        assert "approved" in stderr


def test_fork_dry_run_closing_line_states_next_concrete_action():
    with tempfile.TemporaryDirectory() as tmp:
        manifest_file = Path(tmp) / "extensions-manifest.json"

        stdout, stderr, exit_code = _run_fork(
            upstream="gotgenes/pi-packages",
            entry_id="gotgenes-pi-packages",
            capability="permission-system",
            dry_run=True,
            manifest_file=manifest_file,
        )
        assert exit_code is None, f"unexpected failure: {stderr}"

        non_empty_lines = [line for line in stdout.splitlines() if line.strip()]
        assert non_empty_lines, "dry-run produced no output"
        assert non_empty_lines[-1].startswith("Re-run without --dry-run")


def test_fork_pin_extension_dry_run_matches_real_run_manifest_diff():
    with tempfile.TemporaryDirectory() as tmp:
        real_manifest = Path(tmp) / "real-manifest.json"
        dry_manifest = Path(tmp) / "dry-manifest.json"

        fixture = {
            "upstream": "gotgenes/pi-packages",
            "entry_id": "gotgenes-pi-packages",
            "capability": "permission-system,subagents",
        }

        with (
            patch.object(fork_pin_extension, "run_gh_fork"),
            patch.object(fork_pin_extension, "run_gh_head_commit", return_value=_FIXED_SHA),
        ):
            _, real_stderr, real_exit = _run_fork(
                dry_run=False, manifest_file=real_manifest, **fixture
            )
        assert real_exit is None, f"unexpected failure: {real_stderr}"
        persisted = json.loads(real_manifest.read_text(encoding="utf-8"))["extensions"][
            fixture["entry_id"]
        ]

        def _fail_loudly(*_args, **_kwargs):
            raise AssertionError("gh must not be called during --dry-run")

        with (
            patch.object(fork_pin_extension, "run_gh_fork", side_effect=_fail_loudly),
            patch.object(fork_pin_extension, "run_gh_head_commit", side_effect=_fail_loudly),
        ):
            dry_stdout, dry_stderr, dry_exit = _run_fork(
                dry_run=True, manifest_file=dry_manifest, **fixture
            )
        assert dry_exit is None, f"unexpected failure: {dry_stderr}"
        planned = _extract_json_block(dry_stdout, "Planned manifest entry:")

        # Every field that doesn't depend on `gh` output must be byte-for-byte
        # identical between the dry-run preview and what the real run wrote --
        # proving the two code paths cannot silently diverge in how they build
        # the entry (architecture-review.md's fork_pin_extension.py concern).
        commit_dependent_fields = {"fork_commit", "upstream_commit"}
        for key in persisted:
            if key in commit_dependent_fields:
                continue
            assert planned[key] == persisted[key], f"field {key!r} diverged between dry-run and real run"

        assert planned["fork_commit"] == fork_pin_extension.PENDING_COMMIT
        assert planned["upstream_commit"] == fork_pin_extension.PENDING_COMMIT
        assert persisted["fork_commit"] == _FIXED_SHA
        assert persisted["upstream_commit"] == _FIXED_SHA

        # Tightest possible version of the same guarantee: feed the shared
        # entry-builder the exact commit the real run used, and require an
        # exact match against what was persisted -- proving both paths route
        # through the very same function, not just similarly-shaped ones.
        replayed = fork_pin_extension.build_entry_dict(
            entry_id=fixture["entry_id"],
            capability=fixture["capability"],
            upstream=fixture["upstream"],
            commit=_FIXED_SHA,
        )
        assert replayed == persisted


if __name__ == "__main__":
    tests = [value for key, value in list(globals().items()) if key.startswith("test_")]
    for test in tests:
        test()
        print(f"ok  {test.__name__}")
    print(f"\n{len(tests)} checks passed")
