#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "typer>=0.12",
# ]
# ///
"""Regression checks for the fork-and-pin helper script.

Run directly: uv run test_fork_pin_extension.py

Every `git`/network call is mocked -- no real network/GitHub access happens
here.
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


_FIXED_UPSTREAM_SHA = "e64946b5ce96ca004b753d98932c8b13106dd132"
_FIXED_FORK_SHA = "cafef00d0123456789abcdef0123456789abcdef"


def test_fork_pin_extension_fork_creates_candidate_manifest_entry_with_fork_commit():
    with tempfile.TemporaryDirectory() as tmp:
        manifest_file = Path(tmp) / "extensions-manifest.json"

        with (
            patch.object(
                fork_pin_extension, "resolve_upstream_head", return_value=_FIXED_UPSTREAM_SHA
            ) as mock_head,
            patch.object(
                fork_pin_extension, "run_subtree_import", return_value=_FIXED_FORK_SHA
            ) as mock_subtree,
        ):
            stdout, stderr, exit_code = _run_fork(
                upstream="gotgenes/pi-packages",
                entry_id="gotgenes-pi-packages",
                capability="permission-system,subagents",
                upstream_commit=None,
                dry_run=False,
                manifest_file=manifest_file,
            )

        assert exit_code is None, f"unexpected failure: {stderr}"
        mock_head.assert_called_once_with("gotgenes/pi-packages")
        mock_subtree.assert_called_once()
        assert mock_subtree.call_args.kwargs["upstream"] == "gotgenes/pi-packages"
        assert mock_subtree.call_args.kwargs["upstream_commit"] == _FIXED_UPSTREAM_SHA
        assert mock_subtree.call_args.kwargs["entry_id"] == "gotgenes-pi-packages"

        written = json.loads(manifest_file.read_text(encoding="utf-8"))
        entry = written["extensions"]["gotgenes-pi-packages"]
        assert entry["disposition"] == "candidate"
        assert entry["fork_repo"] == "https://github.com/tstapler/pi-extensions"
        assert entry["package_paths"] == ["third-party/gotgenes-pi-packages"]
        assert entry["upstream_commit"] == _FIXED_UPSTREAM_SHA
        assert entry["fork_commit"] == _FIXED_FORK_SHA
        assert entry["approved_by"] is None
        assert entry["approved_date"] is None


def test_fork_pin_extension_fork_uses_explicit_upstream_commit_without_resolving_head():
    with tempfile.TemporaryDirectory() as tmp:
        manifest_file = Path(tmp) / "extensions-manifest.json"

        with (
            patch.object(fork_pin_extension, "resolve_upstream_head") as mock_head,
            patch.object(
                fork_pin_extension, "run_subtree_import", return_value=_FIXED_FORK_SHA
            ) as mock_subtree,
        ):
            stdout, stderr, exit_code = _run_fork(
                upstream="gotgenes/pi-packages",
                entry_id="gotgenes-pi-packages",
                capability="permission-system,subagents",
                upstream_commit=_FIXED_UPSTREAM_SHA,
                dry_run=False,
                manifest_file=manifest_file,
            )

        assert exit_code is None, f"unexpected failure: {stderr}"
        mock_head.assert_not_called()
        assert mock_subtree.call_args.kwargs["upstream_commit"] == _FIXED_UPSTREAM_SHA

        written = json.loads(manifest_file.read_text(encoding="utf-8"))
        entry = written["extensions"]["gotgenes-pi-packages"]
        assert entry["upstream_commit"] == _FIXED_UPSTREAM_SHA


def test_fork_pin_extension_fork_fails_when_id_already_has_manifest_entry():
    with tempfile.TemporaryDirectory() as tmp:
        manifest_file = Path(tmp) / "extensions-manifest.json"
        _write(
            manifest_file,
            {"extensions": {"existing-id": {"disposition": "candidate"}}},
        )

        with (
            patch.object(fork_pin_extension, "resolve_upstream_head") as mock_head,
            patch.object(fork_pin_extension, "run_subtree_import") as mock_subtree,
        ):
            stdout, stderr, exit_code = _run_fork(
                upstream="gotgenes/pi-packages",
                entry_id="existing-id",
                capability="permission-system",
                upstream_commit=None,
                dry_run=False,
                manifest_file=manifest_file,
            )

        assert exit_code == 1
        assert "existing-id" in stderr
        mock_head.assert_not_called()
        mock_subtree.assert_not_called()


def test_fork_pin_extension_dry_run_prints_plan_without_calling_gh():
    with tempfile.TemporaryDirectory() as tmp:
        manifest_file = Path(tmp) / "extensions-manifest.json"

        with patch.object(fork_pin_extension, "subprocess") as mock_subprocess:
            stdout, stderr, exit_code = _run_fork(
                upstream="gotgenes/pi-packages",
                entry_id="gotgenes-pi-packages",
                capability="permission-system",
                upstream_commit=None,
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
            raise AssertionError("git must not be called during --dry-run")

        with (
            patch.object(fork_pin_extension, "resolve_upstream_head", side_effect=_fail_loudly),
            patch.object(fork_pin_extension, "run_subtree_import", side_effect=_fail_loudly),
        ):
            stdout, stderr, exit_code = _run_fork(
                upstream="gotgenes/pi-packages",
                entry_id="gotgenes-pi-packages",
                capability="permission-system",
                upstream_commit=None,
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
            upstream_commit=None,
            dry_run=True,
            manifest_file=dry_manifest,
        )
        assert dry_exit is None

        with (
            patch.object(
                fork_pin_extension, "resolve_upstream_head", return_value=_FIXED_UPSTREAM_SHA
            ),
            patch.object(fork_pin_extension, "run_subtree_import", return_value=_FIXED_FORK_SHA),
        ):
            real_stdout, real_stderr, real_exit = _run_fork(
                upstream="gotgenes/pi-packages",
                entry_id="gotgenes-pi-packages",
                capability="permission-system",
                upstream_commit=None,
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
            patch.object(
                fork_pin_extension, "resolve_upstream_head", return_value=_FIXED_UPSTREAM_SHA
            ),
            patch.object(fork_pin_extension, "run_subtree_import", return_value=_FIXED_FORK_SHA),
        ):
            stdout, stderr, exit_code = _run_fork(
                upstream="gotgenes/pi-packages",
                entry_id="gotgenes-pi-packages",
                capability="permission-system",
                upstream_commit=None,
                dry_run=False,
                manifest_file=manifest_file,
            )
        assert exit_code is None, f"unexpected failure: {stderr}"

        printed = _extract_json_block(stdout, "Manifest entry:")
        written = json.loads(manifest_file.read_text(encoding="utf-8"))
        written_entry = written["extensions"]["gotgenes-pi-packages"]

        assert printed["fork_commit"] == written_entry["fork_commit"]
        assert printed["fork_commit"] == _FIXED_FORK_SHA


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
            upstream_commit=None,
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
            upstream_commit=None,
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
            patch.object(
                fork_pin_extension, "resolve_upstream_head", return_value=_FIXED_UPSTREAM_SHA
            ),
            patch.object(fork_pin_extension, "run_subtree_import", return_value=_FIXED_FORK_SHA),
        ):
            _, real_stderr, real_exit = _run_fork(
                upstream_commit=None, dry_run=False, manifest_file=real_manifest, **fixture
            )
        assert real_exit is None, f"unexpected failure: {real_stderr}"
        persisted = json.loads(real_manifest.read_text(encoding="utf-8"))["extensions"][
            fixture["entry_id"]
        ]

        def _fail_loudly(*_args, **_kwargs):
            raise AssertionError("git must not be called during --dry-run")

        with (
            patch.object(fork_pin_extension, "resolve_upstream_head", side_effect=_fail_loudly),
            patch.object(fork_pin_extension, "run_subtree_import", side_effect=_fail_loudly),
        ):
            dry_stdout, dry_stderr, dry_exit = _run_fork(
                upstream_commit=None, dry_run=True, manifest_file=dry_manifest, **fixture
            )
        assert dry_exit is None, f"unexpected failure: {dry_stderr}"
        planned = _extract_json_block(dry_stdout, "Planned manifest entry:")

        # Every field that doesn't depend on `git` output must be byte-for-byte
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
        assert persisted["fork_commit"] == _FIXED_FORK_SHA
        assert persisted["upstream_commit"] == _FIXED_UPSTREAM_SHA

        # Tightest possible version of the same guarantee: feed the shared
        # entry-builder the exact commits the real run used, and require an
        # exact match against what was persisted -- proving both paths route
        # through the very same function, not just similarly-shaped ones.
        replayed = fork_pin_extension.build_entry_dict(
            entry_id=fixture["entry_id"],
            capability=fixture["capability"],
            upstream=fixture["upstream"],
            upstream_commit=_FIXED_UPSTREAM_SHA,
            fork_commit=_FIXED_FORK_SHA,
        )
        assert replayed == persisted


def test_run_subtree_import_without_subdir_fetches_upstream_directly():
    """No monorepo scoping requested: fetch the upstream URL/commit as before."""
    calls: list[list[str]] = []

    def _fake_run_git(args, *, cwd=None, timeout=None):
        calls.append(args)
        if args[0] == "rev-parse":
            return _FIXED_FORK_SHA
        return ""

    with patch.object(fork_pin_extension, "run_git", side_effect=_fake_run_git):
        with tempfile.TemporaryDirectory() as tmp:
            fork_pin_extension.run_subtree_import(
                upstream="gotgenes/pi-packages",
                upstream_commit=_FIXED_UPSTREAM_SHA,
                entry_id="gotgenes-pi-packages",
                workdir=Path(tmp),
            )

    fetch_calls = [c for c in calls if c[0] == "fetch"]
    assert len(fetch_calls) == 1, calls
    assert fetch_calls[0] == ["fetch", "https://github.com/gotgenes/pi-packages.git", _FIXED_UPSTREAM_SHA]
    assert not any(c[0] == "subtree" and c[1] == "split" for c in calls), calls


def test_run_subtree_import_with_subdir_splits_upstream_before_fetching():
    """Monorepo scoping requested: split the subdir out of a full upstream

    clone first, and fetch *that* filtered commit -- never the raw upstream
    URL/commit directly -- so unrelated sibling packages under the same
    upstream repo never enter pi-extensions. Regression test for the
    `narumiruna/pi-extensions` fork attempt that pulled in an unrelated
    package's test fixture and tripped a pre-push content-scanning hook.
    """
    calls: list[list[str]] = []
    split_commit_sha = "deadbeefdeadbeefdeadbeefdeadbeefdeadbeef"

    def _fake_run_git(args, *, cwd=None, timeout=None):
        calls.append(args)
        if args[0] == "subtree" and args[1] == "split":
            return split_commit_sha
        if args[0] == "rev-parse":
            return _FIXED_FORK_SHA
        return ""

    with patch.object(fork_pin_extension, "run_git", side_effect=_fake_run_git):
        with tempfile.TemporaryDirectory() as tmp:
            fork_pin_extension.run_subtree_import(
                upstream="narumiruna/pi-extensions",
                upstream_commit=_FIXED_UPSTREAM_SHA,
                entry_id="narumiruna-pi-plan-mode",
                workdir=Path(tmp),
                upstream_subdir="packages/pi-plan-mode",
            )

    # The raw upstream repo must never be fetched directly by URL -- only
    # ever cloned in full (required for `subtree split` to see the whole
    # history), then split, then fetched from the *local* split clone.
    assert not any(
        c[0] == "fetch" and c[1] == "https://github.com/narumiruna/pi-extensions.git"
        for c in calls
    ), calls

    clone_calls = [c for c in calls if c[0] == "clone"]
    assert any(c[1] == "https://github.com/narumiruna/pi-extensions.git" for c in clone_calls), calls

    split_calls = [c for c in calls if c[0] == "subtree" and c[1] == "split"]
    assert len(split_calls) == 1, calls
    assert split_calls[0] == ["subtree", "split", "--prefix=packages/pi-plan-mode", _FIXED_UPSTREAM_SHA]

    fetch_calls = [c for c in calls if c[0] == "fetch"]
    assert len(fetch_calls) == 1, calls
    assert fetch_calls[0][2] == "subtree-split"


if __name__ == "__main__":
    from _test_runner import run_tests

    run_tests(globals())
