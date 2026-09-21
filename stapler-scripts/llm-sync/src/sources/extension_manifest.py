"""Load and validate the tracked Pi extension review manifest."""

import json
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
        return ManifestEntry(
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
