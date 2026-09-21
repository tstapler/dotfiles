"""Cross-reference rendered Pi config sources against the extension review manifest.

Kept separate from `extension_manifest.py` (manifest-schema parsing) and
`pi_config.py` (config rendering): this module's only job is cross-referencing
one already-loaded aggregate (`LoadedPiConfig`) against another
(`ExtensionManifest`).
"""

from .extension_manifest import ExtensionManifest, ManifestEntry
from .pi_config import LoadedPiConfig, PiConfigError, SourceRef, normalize_fork_repo, parse_fork_source

_SCANNED_RESOURCE_KEYS = ("packages", "extensions")


def verify_pinned_sources_reviewed(
    loaded: LoadedPiConfig,
    manifest: ExtensionManifest,
    trusted_scopes: tuple[str, ...] = (),
) -> None:
    """Raise `PiConfigError` if any rendered fork source lacks an approved
    manifest entry at the exact pinned commit.

    Only sources `parse_fork_source()` recognizes as `github.com/tstapler/`
    fork-shaped are checked. Everything else — trusted-scope sources,
    `@tstapler` npm sources, local paths — is exempt by construction, since
    `parse_fork_source()` returns `None` for all of them. `trusted_scopes` is
    accepted for interface symmetry with the config source but is not used
    to special-case anything here (see Task 1.2.2a).
    """
    del trusted_scopes  # exemption is structural (parse_fork_source), not scope-based

    for resource_key in _SCANNED_RESOURCE_KEYS:
        for entry in loaded.settings.get(resource_key, []):
            source = entry["source"] if isinstance(entry, dict) else entry
            if not isinstance(source, str):
                continue
            ref = parse_fork_source(source)
            if ref is None:
                continue
            _check_reviewed(source, ref, manifest)


def _check_reviewed(source: str, ref: SourceRef, manifest: ExtensionManifest) -> None:
    matching = [
        candidate
        for candidate in manifest.entries.values()
        if _same_repo(candidate, ref.repo)
    ]
    if not matching:
        raise PiConfigError(
            f"Pi source '{source}' is pinned to an unreviewed fork "
            f"({ref.repo}@{ref.commit}); add an approved manifest entry "
            "before syncing"
        )

    at_commit = [m for m in matching if m.fork_commit.lower() == ref.commit.lower()]
    if not at_commit:
        approved_commits = ", ".join(sorted({m.fork_commit for m in matching}))
        raise PiConfigError(
            f"Pi source '{source}' is pinned at commit '{ref.commit}', but "
            f"the manifest's approved commit(s) for {ref.repo} are: "
            f"{approved_commits}"
        )

    not_approved = [m for m in at_commit if m.disposition != "approved"]
    if not_approved:
        dispositions = ", ".join(sorted({m.disposition for m in not_approved}))
        raise PiConfigError(
            f"Pi source '{source}' has a manifest entry at the exact commit "
            f"but its disposition is '{dispositions}', not 'approved'"
        )


def _same_repo(entry: ManifestEntry, repo: str) -> bool:
    return normalize_fork_repo(entry.fork_repo) == repo
