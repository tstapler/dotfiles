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

# The only namespace this script forks into. Epic 1.3's plan.md left
# org-vs-personal as an open decision (see plan.md's "Unresolved Questions"),
# but the plan's own acceptance criteria fix the fork target at
# "github.com/tstapler/<repo>", so that's what's implemented here.
FORK_OWNER = "tstapler"

DEFAULT_MANIFEST_FILE = _REPO_ROOT / ".config" / "pi" / "extensions-manifest.json"

# Dry-run never calls `gh`, so it cannot know the real commit yet. This
# sentinel stands in for it in the printed preview.
PENDING_COMMIT = "<pending: captured from `gh repo fork` / `gh api` after fork creation>"

# License isn't fetched by this script (not in scope per Task 1.3.1a/b); the
# human reviewer fills this in for real during review, before hand-editing
# disposition.
PLACEHOLDER_LICENSE = "UNKNOWN (confirm license during human review)"


class GhCommandError(ValueError):
    """A `gh` subprocess invocation failed."""


def run_gh_fork(upstream: str) -> None:
    """Fork `upstream` (owner/repo) into `github.com/tstapler/<repo>` via `gh repo fork`.

    A thin, mockable wrapper — tests monkeypatch this instead of shelling
    out to a real `gh repo fork`.
    """
    result = subprocess.run(
        ["gh", "repo", "fork", upstream, "--default-branch-only"],
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    if result.returncode != 0:
        raise GhCommandError(
            f"'gh repo fork {upstream}' failed: {result.stderr.strip() or 'unknown gh error'}"
        )


def run_gh_head_commit(fork_repo_slug: str) -> str:
    """Return the current HEAD commit SHA of `github.com/tstapler/<fork_repo_slug>`.

    A thin, mockable wrapper around `gh api` — see `run_gh_fork`.
    """
    endpoint = f"repos/{FORK_OWNER}/{fork_repo_slug}/commits/HEAD"
    result = subprocess.run(
        ["gh", "api", endpoint, "--jq", ".sha"],
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    if result.returncode != 0:
        raise GhCommandError(
            f"'gh api {endpoint}' failed: {result.stderr.strip() or 'unknown gh error'}"
        )
    sha = result.stdout.strip()
    if not sha:
        raise GhCommandError(f"'gh api {endpoint}' returned an empty commit SHA")
    return sha


def _repo_slug(upstream: str) -> str:
    return upstream.rstrip("/").rsplit("/", 1)[-1]


def build_entry_dict(*, entry_id: str, capability: str, upstream: str, commit: str) -> dict:
    """Build the manifest-entry dict. The one function both code paths call.

    `commit` is the only value that comes from `gh`; everything else is
    derived from CLI arguments. The real run passes the SHA `gh` returned;
    the dry-run preview passes `PENDING_COMMIT`. Routing both paths through
    this single function is what makes
    `test_fork_pin_extension_dry_run_matches_real_run_manifest_diff` a real
    regression guard rather than two independently-hand-written dicts that
    could silently drift apart.
    """
    repo_slug = _repo_slug(upstream)
    return {
        "id": entry_id,
        "capability": capability,
        "upstream_repo": f"https://github.com/{upstream}",
        "upstream_commit": commit,
        "license": PLACEHOLDER_LICENSE,
        "fork_repo": f"https://github.com/{FORK_OWNER}/{repo_slug}",
        "fork_commit": commit,
        "package_paths": None,
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
    """Print the fork + manifest plan. Makes zero `gh`/subprocess calls."""
    planned = build_entry_dict(
        entry_id=entry_id, capability=capability, upstream=upstream, commit=PENDING_COMMIT
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
    fork_target: str,
    fork_repo_slug: str,
    manifest_file: Path,
    raw_manifest: dict,
) -> None:
    """Create the fork via `gh`, then write and validate the manifest entry."""
    try:
        run_gh_fork(upstream)
        commit = run_gh_head_commit(fork_repo_slug)
    except GhCommandError as error:
        typer.echo(f"Error: {error}", err=True)
        raise typer.Exit(1)

    entry_dict = build_entry_dict(
        entry_id=entry_id, capability=capability, upstream=upstream, commit=commit
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

    typer.echo(f"Forked {upstream} -> {fork_target}")
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
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Print the plan only: no gh calls, no manifest write"
    ),
    manifest_file: Path = typer.Option(
        DEFAULT_MANIFEST_FILE,
        "--manifest-file",
        help="Path to the extension review manifest JSON",
    ),
) -> None:
    """Fork UPSTREAM and scaffold a candidate manifest entry for it.

    Always writes disposition "candidate" with approved_by/approved_date set
    to null; nothing here ever sets the terminal review state, which is a
    human hand-edit of the manifest file, not a scriptable action.
    """
    raw_manifest = _load_raw_manifest(manifest_file)
    _reject_if_id_exists(raw_manifest, entry_id)

    fork_repo_slug = _repo_slug(upstream)
    fork_target = f"github.com/{FORK_OWNER}/{fork_repo_slug}"

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
        fork_target=fork_target,
        fork_repo_slug=fork_repo_slug,
        manifest_file=manifest_file,
        raw_manifest=raw_manifest,
    )


if __name__ == "__main__":
    app()
