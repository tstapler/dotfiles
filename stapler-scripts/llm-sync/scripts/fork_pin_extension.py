#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "typer>=0.12",
# ]
# ///
"""Fork an upstream Pi extension repo and scaffold a review-manifest entry.

Only ever writes `disposition: "candidate"` with `approved_by`/`approved_date`
left null. The terminal review state is reserved for a human hand-edit of
`.config/pi/extensions-manifest.json` — see
`project_plans/pi-dotfiles/extension-audit.md`'s review gate. This script has
no argument, flag, or code path that reaches that value; see
`test_fork_pin_extension_argparser_has_no_flag_that_writes_approved_disposition`
in test_fork_pin_extension.py, which scans this file's own source for the
literal string this docstring is carefully avoiding.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import typer

_SCRIPT_DIR = Path(__file__).resolve().parent
_LLM_SYNC_DIR = _SCRIPT_DIR.parent
_REPO_ROOT = _LLM_SYNC_DIR.parent.parent
sys.path.append(str(_LLM_SYNC_DIR / "src"))

from sources.extension_manifest import (  # noqa: E402 (path setup must precede this)
    ExtensionManifestSource,
    ManifestEntry,
)

app = typer.Typer(add_completion=False, no_args_is_help=True)


@app.callback()
def _callback() -> None:
    """Fork-and-pin scaffolding for Pi extension review manifests.

    An empty callback, kept only so Typer always requires an explicit
    subcommand name (`fork ...`) instead of collapsing a single-command app
    into a bare `fork_pin_extension.py <args>` invocation -- matches
    plan.md's specified `fork_pin_extension.py fork <upstream> ...` usage
    and leaves room for future subcommands without changing this one's shape.
    """

# ADR-003: all forks land as a git-subtree import into this one consolidated
# repo (`third-party/<entry-id>` prefix) instead of a native `gh repo fork`
# per upstream. Epic 1.3's plan.md left org-vs-personal as an open decision
# (see plan.md's "Unresolved Questions"); this keeps Tyler's own namespace.
FORK_OWNER = "tstapler"
CONSOLIDATED_FORK_REPO_SLUG = "pi-extensions"
CONSOLIDATED_FORK_URL = f"https://github.com/{FORK_OWNER}/{CONSOLIDATED_FORK_REPO_SLUG}.git"

DEFAULT_MANIFEST_FILE = _REPO_ROOT / ".config" / "pi" / "extensions-manifest.json"

# Dry-run never calls `git`/network, so it cannot know either real commit yet
# (upstream_commit needs a live `git ls-remote`/fetch to confirm it resolves;
# fork_commit only exists after the subtree import + push). This sentinel
# stands in for both in the printed preview.
PENDING_COMMIT = "<pending: captured from git ls-remote/subtree/push after import>"

# License isn't fetched by this script (not in scope per Task 1.3.1a/b); the
# human reviewer fills this in for real during review, before hand-editing
# disposition.
PLACEHOLDER_LICENSE = "UNKNOWN (confirm license during human review)"


class CommandError(ValueError):
    """A `git` subprocess invocation failed."""


def run_git(args: list[str], *, cwd: Path | None = None) -> str:
    """Run a git subcommand, returning stripped stdout. Raises `CommandError` on failure.

    A thin, mockable wrapper — tests monkeypatch this (or the higher-level
    functions below) instead of shelling out to real git/network operations.
    """
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    if result.returncode != 0:
        raise CommandError(
            f"'git {' '.join(args)}' failed: {result.stderr.strip() or 'unknown git error'}"
        )
    return result.stdout.strip()


def resolve_upstream_head(upstream: str) -> str:
    """Return `upstream`'s current default-branch HEAD commit SHA via `git ls-remote`.

    Used only when `--upstream-commit` isn't given explicitly. A thin,
    mockable wrapper — see `run_git`.
    """
    output = run_git(["ls-remote", f"https://github.com/{upstream}.git", "HEAD"])
    sha, _, _ref = output.partition("\t")
    if not sha:
        raise CommandError(f"'git ls-remote' returned no HEAD SHA for {upstream!r}")
    return sha


def run_subtree_import(*, upstream: str, upstream_commit: str, entry_id: str, workdir: Path) -> str:
    """Subtree-import `upstream` at `upstream_commit` into `pi-extensions`.

    Clones `CONSOLIDATED_FORK_URL` into `workdir`, fetches the exact upstream
    commit (GitHub permits fetching by full SHA even when it isn't an
    advertised branch/tag tip — verified live against a real upstream before
    this design was adopted; see ADR-003), squash-imports it under
    `third-party/<entry_id>`, pushes to feature branch `extension/<entry_id>`
    (never `main` — a human still reviews/merges the diff), and returns the
    resulting commit SHA on `pi-extensions`. A thin, mockable wrapper — see
    `run_git`.
    """
    clone_dir = workdir / CONSOLIDATED_FORK_REPO_SLUG
    run_git(["clone", CONSOLIDATED_FORK_URL, str(clone_dir)])
    run_git(["fetch", f"https://github.com/{upstream}.git", upstream_commit], cwd=clone_dir)
    prefix = f"third-party/{entry_id}"
    run_git(
        [
            "subtree", "add", f"--prefix={prefix}", "FETCH_HEAD", "--squash",
            "-m", f"Import {upstream}@{upstream_commit[:12]} at {prefix} (ADR-003)",
        ],
        cwd=clone_dir,
    )
    branch = f"extension/{entry_id}"
    run_git(["checkout", "-b", branch], cwd=clone_dir)
    run_git(["push", "origin", branch], cwd=clone_dir)
    return run_git(["rev-parse", "HEAD"], cwd=clone_dir)


def build_entry_dict(
    *, entry_id: str, capability: str, upstream: str, upstream_commit: str, fork_commit: str
) -> dict:
    """Build the manifest-entry dict. The one function both code paths call.

    `upstream_commit`/`fork_commit` are the only values that come from
    `git`; everything else is derived from CLI arguments. The real run
    passes the SHAs the subtree import produced; the dry-run preview passes
    `PENDING_COMMIT` for both. Routing both paths through this single
    function is what makes
    `test_fork_pin_extension_dry_run_matches_real_run_manifest_diff` a real
    regression guard rather than two independently-hand-written dicts that
    could silently drift apart.
    """
    return {
        "id": entry_id,
        "capability": capability,
        "upstream_repo": f"https://github.com/{upstream}",
        "upstream_commit": upstream_commit,
        "license": PLACEHOLDER_LICENSE,
        "fork_repo": CONSOLIDATED_FORK_URL.removesuffix(".git"),
        "fork_commit": fork_commit,
        "package_paths": [f"third-party/{entry_id}"],
        "disposition": "candidate",
        "reviewer": None,
        "review_date": None,
        "notes": None,
        "approved_by": None,
        "approved_date": None,
    }


def _load_raw_manifest(path: Path) -> dict:
    if not path.exists():
        return {"extensions": {}}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("extensions"), dict):
        typer.echo(
            f"Error: manifest file '{path}' must be a JSON object with an 'extensions' map",
            err=True,
        )
        raise typer.Exit(1)
    return data


def _print_entry(entry: dict, *, heading: str) -> None:
    typer.echo(heading)
    typer.echo(json.dumps(entry, indent=2, sort_keys=True))


def _reject_if_id_exists(raw_manifest: dict, entry_id: str) -> None:
    existing = raw_manifest["extensions"].get(entry_id)
    if existing is None:
        return
    current_disposition = existing.get("disposition", "<unknown>")
    typer.echo(
        f"Error: manifest entry '{entry_id}' already exists with disposition "
        f"'{current_disposition}'. Pick a different --id, or if you mean to "
        f"re-review it, edit the existing entry by hand instead of "
        f"re-running fork.",
        err=True,
    )
    raise typer.Exit(1)


def _show_dry_run_plan(
    *, entry_id: str, capability: str, upstream: str, fork_target: str, manifest_file: Path
) -> None:
    """Print the fork + manifest plan. Makes zero `git`/subprocess/network calls."""
    planned = build_entry_dict(
        entry_id=entry_id,
        capability=capability,
        upstream=upstream,
        upstream_commit=PENDING_COMMIT,
        fork_commit=PENDING_COMMIT,
    )
    typer.echo(f"Would fork: {upstream} -> {fork_target}")
    typer.echo(f"Would write to: {manifest_file}")
    _print_entry(planned, heading="Planned manifest entry:")
    typer.echo("Re-run without --dry-run to create the fork and write the manifest entry.")


def _validate_entry(entry_dict: dict) -> None:
    """Reuse `ManifestEntry`'s own constructor for its invariant checks.

    Defense in depth alongside the round-trip load in `_execute_fork`, even
    though disposition is always "candidate" here. `entry_dict`'s keys match
    `ManifestEntry`'s fields one-for-one (both originate from
    `build_entry_dict`), so `**entry_dict` is a safe drop-in for the
    field-by-field constructor call this replaced.
    """
    ManifestEntry(**entry_dict)


def _execute_fork(
    *,
    entry_id: str,
    capability: str,
    upstream: str,
    upstream_commit: str | None,
    fork_target: str,
    manifest_file: Path,
    raw_manifest: dict,
) -> None:
    """Subtree-import the fork via `git` (see ADR-003), then write and validate the manifest entry."""
    try:
        resolved_upstream_commit = upstream_commit or resolve_upstream_head(upstream)
        with tempfile.TemporaryDirectory() as tmp:
            fork_commit = run_subtree_import(
                upstream=upstream,
                upstream_commit=resolved_upstream_commit,
                entry_id=entry_id,
                workdir=Path(tmp),
            )
    except CommandError as error:
        typer.echo(f"Error: {error}", err=True)
        raise typer.Exit(1)

    entry_dict = build_entry_dict(
        entry_id=entry_id,
        capability=capability,
        upstream=upstream,
        upstream_commit=resolved_upstream_commit,
        fork_commit=fork_commit,
    )
    _validate_entry(entry_dict)

    raw_manifest["extensions"][entry_id] = entry_dict
    manifest_file.parent.mkdir(parents=True, exist_ok=True)
    manifest_file.write_text(
        json.dumps(raw_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    # Round-trip through the real loader to prove the file just written
    # parses as a valid manifest (Task 1.3.1b: "reuses ExtensionManifestSource
    # for validation").
    ExtensionManifestSource.load(manifest_file)

    typer.echo(f"Imported {upstream}@{resolved_upstream_commit} -> {fork_target}")
    typer.echo(f"Wrote manifest entry to: {manifest_file}")
    _print_entry(entry_dict, heading="Manifest entry:")


@app.command()
def fork(
    upstream: str = typer.Argument(
        ..., help="Upstream repo as owner/repo, e.g. gotgenes/pi-packages"
    ),
    entry_id: str = typer.Option(
        ..., "--id", help="Stable manifest entry id, e.g. gotgenes-pi-packages"
    ),
    capability: str = typer.Option(
        ..., "--capability", help="Comma-separated capability tag(s) for the entry"
    ),
    upstream_commit: str = typer.Option(
        None,
        "--upstream-commit",
        help="Exact upstream commit/review-anchor to import (defaults to upstream's current HEAD)",
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Print the plan only: no git/network calls, no manifest write"
    ),
    manifest_file: Path = typer.Option(
        DEFAULT_MANIFEST_FILE,
        "--manifest-file",
        help="Path to the extension review manifest JSON",
    ),
) -> None:
    """Subtree-import UPSTREAM into pi-extensions and scaffold a candidate manifest entry (ADR-003).

    Always writes disposition "candidate" with approved_by/approved_date set
    to null; nothing here ever sets the terminal review state, which is a
    human hand-edit of the manifest file, not a scriptable action.
    """
    raw_manifest = _load_raw_manifest(manifest_file)
    _reject_if_id_exists(raw_manifest, entry_id)

    fork_target = f"github.com/{FORK_OWNER}/{CONSOLIDATED_FORK_REPO_SLUG} (third-party/{entry_id})"

    if dry_run:
        _show_dry_run_plan(
            entry_id=entry_id,
            capability=capability,
            upstream=upstream,
            fork_target=fork_target,
            manifest_file=manifest_file,
        )
        return

    _execute_fork(
        entry_id=entry_id,
        capability=capability,
        upstream=upstream,
        upstream_commit=upstream_commit,
        fork_target=fork_target,
        manifest_file=manifest_file,
        raw_manifest=raw_manifest,
    )


if __name__ == "__main__":
    app()
