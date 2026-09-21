"""Load and validate the tracked Pi extension review manifest."""

import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_REQUIRED_FIELDS = (
    "id",
    "capability",
    "upstream_repo",
    "upstream_commit",
    "license",
    "fork_repo",
    "fork_commit",
    "disposition",
)

# The gate checklist this evidence check is a mechanical proxy for; used only
# to phrase "which sub-area(s) look uncovered" when too few paths are cited.
_GATE_SUBAREAS = ("network", "subprocess", "filesystem", "secrets", "telemetry")
_MIN_EVIDENCE_PATHS = len(_GATE_SUBAREAS)

# Extraction rule: a run of `/`-joined path segments (word chars, '.', '-')
# ending in a dot-extension, e.g. `src/foo/bar.py` or bare src/foo/bar.py.
# Optional surrounding backticks are matched and discarded. This is a
# syntactic heuristic over free text, not a filesystem check.
_CANDIDATE_PATH_RE = re.compile(r"`?((?:[\w.\-]+/)+[\w.\-]+\.[A-Za-z0-9]+)`?")


class ManifestError(ValueError):
    """The extension manifest is invalid or contains an illegal review state."""


@dataclass(frozen=True)
class ManifestEntry:
    """One review record for a forked/reviewed Pi extension.

    Enforces the Approval Gate invariant at construction time (not only at
    load time) so no caller — including a future fork-helper script — can
    build an `approved` entry without an approver on record.
    """

    id: str
    capability: str
    upstream_repo: str
    upstream_commit: str
    license: str
    fork_repo: str
    fork_commit: str
    package_paths: tuple[str, ...] | None
    disposition: str
    reviewer: str | None
    review_date: str | None
    notes: str | None
    approved_by: str | None
    approved_date: str | None

    def __post_init__(self) -> None:
        if self.disposition == "approved" and not (self.approved_by and self.approved_date):
            raise ManifestError(
                f"Manifest entry '{self.id}' has disposition 'approved' but is "
                "missing required field(s) 'approved_by' and 'approved_date' "
                "(both are required for an approved entry)"
            )


@dataclass(frozen=True)
class ExtensionManifest:
    """The full set of manifest entries, keyed by stable extension id."""

    entries: dict[str, ManifestEntry]


class ExtensionManifestSource:
    """Parse `.config/pi/extensions-manifest.json` into validated `ManifestEntry` objects."""

    @staticmethod
    def load(path: Path) -> ExtensionManifest:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict) or not isinstance(raw.get("extensions"), dict):
            raise ManifestError(
                f"Manifest file '{path}' must be a JSON object with an 'extensions' map"
            )

        entries: dict[str, ManifestEntry] = {}
        for entry_id, data in raw["extensions"].items():
            entries[entry_id] = ExtensionManifestSource._parse_entry(entry_id, data)
        return ExtensionManifest(entries=entries)

    @staticmethod
    def _parse_entry(entry_id: str, data: Any) -> ManifestEntry:
        if not isinstance(data, dict):
            raise ManifestError(f"Manifest entry '{entry_id}' must be a JSON object")

        missing = [field for field in _REQUIRED_FIELDS if not data.get(field)]
        if missing:
            raise ManifestError(
                f"Manifest entry '{entry_id}' is missing required field(s): "
                + ", ".join(missing)
            )

        package_paths = data.get("package_paths")
        entry = ManifestEntry(
            id=data["id"],
            capability=data["capability"],
            upstream_repo=data["upstream_repo"],
            upstream_commit=data["upstream_commit"],
            license=data["license"],
            fork_repo=data["fork_repo"],
            fork_commit=data["fork_commit"],
            package_paths=tuple(package_paths) if package_paths else None,
            disposition=data["disposition"],
            reviewer=data.get("reviewer"),
            review_date=data.get("review_date"),
            notes=data.get("notes"),
            approved_by=data.get("approved_by"),
            approved_date=data.get("approved_date"),
        )

        # Requires a `gh api` call (external I/O keyed on fork_repo/fork_commit),
        # so it runs here at load time rather than in ManifestEntry.__post_init__.
        if entry.disposition == "approved":
            ExtensionManifestSource._verify_notes_evidence(entry)

        return entry

    @staticmethod
    def _verify_notes_evidence(entry: "ManifestEntry") -> None:
        """Mechanically confirm an approved entry's `notes` cite real evidence.

        Requires at least `_MIN_EVIDENCE_PATHS` distinct file paths in `notes`
        (see `_CANDIDATE_PATH_RE` for the extraction rule), each confirmed to
        exist in the fork tree at `fork_commit` via `gh api
        repos/tstapler/<fork_repo>/git/trees/<fork_commit>?recursive=1`.

        This only proves the cited paths exist in the fork at that commit —
        it cannot and does not judge whether they were meaningfully reviewed.
        """
        candidates = ExtensionManifestSource._extract_candidate_paths(entry.notes or "")
        if len(candidates) < _MIN_EVIDENCE_PATHS:
            missing_areas = _GATE_SUBAREAS[len(candidates) :]
            raise ManifestError(
                f"Manifest entry '{entry.id}' has disposition 'approved' but "
                f"'notes' cites only {len(candidates)} distinct file path(s); "
                f"at least {_MIN_EVIDENCE_PATHS} are required (one per review "
                f"sub-area). Evidence looks missing for: "
                f"{', '.join(missing_areas)}. This check only confirms cited "
                "paths exist — it does not judge whether they were "
                "meaningfully reviewed."
            )

        tree_paths = ExtensionManifestSource._fetch_fork_tree_paths(
            entry.fork_repo, entry.fork_commit
        )
        missing_paths = [path for path in candidates if path not in tree_paths]
        if missing_paths:
            raise ManifestError(
                f"Manifest entry '{entry.id}' notes cite path(s) not found in "
                f"fork '{entry.fork_repo}' at commit '{entry.fork_commit}': "
                + ", ".join(missing_paths)
            )

    @staticmethod
    def _extract_candidate_paths(notes: str) -> list[str]:
        """Pull distinct candidate file paths out of free-text `notes`.

        See `_CANDIDATE_PATH_RE` for the extraction rule. Returns paths in
        first-seen order with duplicates removed.
        """
        seen: dict[str, None] = {}
        for match in _CANDIDATE_PATH_RE.finditer(notes):
            seen.setdefault(match.group(1), None)
        return list(seen.keys())

    @staticmethod
    def _fetch_fork_tree_paths(fork_repo: str, fork_commit: str) -> set[str]:
        repo_slug = fork_repo.rstrip("/").rsplit("/", 1)[-1]
        if repo_slug.endswith(".git"):
            repo_slug = repo_slug[: -len(".git")]
        endpoint = f"repos/tstapler/{repo_slug}/git/trees/{fork_commit}?recursive=1"

        result = subprocess.run(
            ["gh", "api", endpoint],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise ManifestError(
                f"failed to fetch fork tree via 'gh api {endpoint}': "
                f"{result.stderr.strip() or 'unknown gh error'}"
            )

        payload = json.loads(result.stdout)
        return {item["path"] for item in payload.get("tree", []) if "path" in item}
