#!/usr/bin/env python3
"""Headless smoke test: does every currently-enabled Pi extension load without error?

Implements the "Pre-`pi_install_version`-bump smoke-test gate (Task 5.1.1c)"
described in project_plans/pi-dotfiles/implementation/rollout-runbook.md,
which that document flagged as not yet built. Runs the real Pi extension
loader (`discoverAndLoadExtensions`, exported from `@earendil-works/pi-coding-agent`'s
public entrypoint -- the exact function Pi's own startup path uses) against
every extension path the tracked+local Pi config currently renders as
enabled, plus the global `~/.pi/agent/extensions/` directory. No TUI, no
real Pi session required.

For a `packages` entry whose `source` is a pinned `tstapler` fork
(`git:github.com/tstapler/<repo>@<commit>`), clones (or reuses a cached
clone of) that exact commit and resolves each of the entry's declared
`extensions` paths relative to the clone root.

Usage:
    uv run scripts/pi_extension_smoke_test.py [--pi-package-entry PATH]

Exits 1 if any extension fails to load or if any expected fork commit
cannot be resolved locally.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_LLM_SYNC_SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(_LLM_SYNC_SRC))

from sources.pi_config import PiConfigSource, normalize_fork_repo, parse_fork_source  # noqa: E402
from sources.tiered_config import TieredJsonConfig  # noqa: E402

_HARNESS_SCRIPT = Path(__file__).resolve().parent / "pi_extension_smoke_test.mjs"
_DEFAULT_PI_PACKAGE_ENTRY = (
    Path.home()
    / ".local"
    / "share"
    / "pi"
    / "lib"
    / "node_modules"
    / "@earendil-works"
    / "pi-coding-agent"
    / "dist"
    / "index.js"
)
_FORK_CLONE_CACHE = Path.home() / ".cache" / "llm-sync" / "pi-extension-smoke-test-forks"


def _resolve_local_extension_paths(settings: dict) -> list[str]:
    """The `extensions` registry's rendered array: already-real local paths."""
    return [
        str(Path(entry).expanduser())
        for entry in settings.get("extensions", [])
        if isinstance(entry, str)
    ]


def _resolve_package_extension_paths(settings: dict) -> list[str]:
    """For each pinned-fork `packages` entry, clone (or reuse) the pinned
    commit and resolve its declared `extensions` paths against it."""
    resolved: list[str] = []
    for entry in settings.get("packages", []):
        if not isinstance(entry, dict):
            continue
        source = entry.get("source")
        extensions = entry.get("extensions") or []
        if not isinstance(source, str) or not extensions:
            continue
        ref = parse_fork_source(source)
        if ref is None:
            continue
        clone_dir = _clone_at_commit(ref.repo, ref.commit)
        resolved.extend(str(clone_dir / ext_path) for ext_path in extensions)
    return resolved


def _clone_at_commit(repo: str, commit: str) -> Path:
    slug = normalize_fork_repo(repo).rsplit("/", 1)[-1]
    clone_dir = _FORK_CLONE_CACHE / f"{slug}-{commit}"
    if (clone_dir / ".git").exists():
        return clone_dir
    clone_dir.parent.mkdir(parents=True, exist_ok=True)
    url = f"https://{normalize_fork_repo(repo)}.git"
    subprocess.run(["git", "clone", "--quiet", url, str(clone_dir)], check=True)
    subprocess.run(["git", "checkout", "--quiet", commit], check=True, cwd=clone_dir)
    return clone_dir


def _discover_global_extensions(agent_dir: Path) -> list[str]:
    ext_dir = agent_dir / "extensions"
    if not ext_dir.is_dir():
        return []
    return [
        str(path)
        for path in sorted(ext_dir.iterdir())
        if path.is_file() and path.suffix in (".ts", ".js", ".mjs")
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pi-package-entry",
        type=Path,
        default=_DEFAULT_PI_PACKAGE_ENTRY,
        help="Path to @earendil-works/pi-coding-agent's dist/index.js",
    )
    parser.add_argument(
        "--pi-dir",
        type=Path,
        default=Path.home() / ".pi" / "agent",
        help="Pi agent directory (for global ~/.pi/agent/extensions discovery)",
    )
    args = parser.parse_args()

    if not args.pi_package_entry.exists():
        print(
            f"error: pi-coding-agent entry not found at {args.pi_package_entry} "
            "(pass --pi-package-entry)",
            file=sys.stderr,
        )
        return 1

    config_root = Path.home() / ".config" / "pi"
    source = PiConfigSource(
        TieredJsonConfig(
            universal_file=config_root / "config.json",
            tracked_fragments_dir=config_root / "config.d",
            local_file=config_root / "config.local.json",
            local_fragments_dir=config_root / "config.local.d",
        )
    )
    loaded = source.load()

    extension_paths = sorted(
        set(_resolve_local_extension_paths(loaded.settings))
        | set(_resolve_package_extension_paths(loaded.settings))
        | set(_discover_global_extensions(args.pi_dir))
    )

    if not extension_paths:
        print("No enabled extension paths found; nothing to smoke test.")
        return 0

    print(f"Smoke-testing {len(extension_paths)} extension path(s):")
    for path in extension_paths:
        print(f"  - {path}")

    result = subprocess.run(
        ["node", str(_HARNESS_SCRIPT), str(args.pi_package_entry), *extension_paths],
        capture_output=True,
        text=True,
    )
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        report = json.loads(result.stdout) if result.stdout.strip() else {}
        for error in report.get("errors", []):
            print(f"FAILED: {error['path']}: {error['error']}", file=sys.stderr)
        return 1

    print("All extensions loaded without error.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
