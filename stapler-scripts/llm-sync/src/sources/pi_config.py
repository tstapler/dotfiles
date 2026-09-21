"""Render tiered declarative Pi configuration into Pi's native settings shape."""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .tiered_config import TieredJsonConfig

_RESOURCE_KEYS = ("packages", "extensions", "skills", "prompts", "themes")
_TRUSTED_SCOPES_KEY = "trustedPackageScopes"
_FORBIDDEN_CREDENTIAL_KEYS = {
    "apikey",
    "accesstoken",
    "refreshtoken",
    "password",
    "secret",
    "clientsecret",
    "credentials",
}
_PACKAGE_FIELDS = {
    "source",
    "autoload",
    "extensions",
    "skills",
    "prompts",
    "themes",
}


class PiConfigError(ValueError):
    """The effective Pi configuration is invalid or unsafe."""


@dataclass(frozen=True)
class LoadedPiConfig:
    settings: dict[str, Any]
    managed_keys: set[str]
    layers: tuple[Path, ...]
    trusted_scopes: tuple[str, ...] = ()


@dataclass(frozen=True)
class SourceRef:
    """A parsed `tstapler`-owned fork source: its repo and pinned commit."""

    repo: str
    commit: str


_FORK_SCHEME_PREFIXES = ("git:", "git@", "https://", "http://", "ssh://", "git://")


def normalize_fork_repo(repo: str) -> str:
    """Canonicalize a fork repo URL/slug to `github.com/tstapler/<repo>` form.

    Lowercases, strips a leading scheme, converts the `git@host:owner/repo`
    colon separator to a slash, and drops a trailing `.git`/`/`.
    """
    normalized = repo.lower().removeprefix("git:")
    for prefix in ("git://", "https://", "http://", "ssh://", "git@"):
        normalized = normalized.removeprefix(prefix)
    normalized = normalized.replace("github.com:tstapler/", "github.com/tstapler/")
    normalized = normalized.rstrip("/")
    if normalized.endswith(".git"):
        normalized = normalized[: -len(".git")]
    return normalized


def parse_fork_source(source: str) -> SourceRef | None:
    """Parse a package source string as a `tstapler`-owned fork reference.

    Returns `None` when `source` isn't shaped like one at all: wrong scheme,
    no trailing `@<ref>`, or not a `github.com/tstapler/` (or SSH
    `github.com:tstapler/`) URL once normalized. Otherwise returns the
    `(repo, commit)` pair with `repo` normalized via `normalize_fork_repo`
    and `commit` exactly as given — commit case-folding, if needed, is the
    caller's job (see `review_gate.py`), not this parser's.

    Does not validate that `commit` looks like an immutable SHA; that check
    stays in `_is_allowed_package_source`, which layers it on top of this.
    """
    if not source.startswith(_FORK_SCHEME_PREFIXES):
        return None
    before_ref, separator, ref = source.rpartition("@")
    if not separator:
        return None
    normalized = normalize_fork_repo(before_ref)
    if "github.com/tstapler/" not in normalized:
        return None
    return SourceRef(repo=normalized, commit=ref)


class PiConfigSource:
    """Convert stable-ID resource registries to native Pi resource arrays."""

    def __init__(self, config: TieredJsonConfig) -> None:
        self.config = config
        self._trusted_scopes: tuple[str, ...] = ()

    def load(self) -> LoadedPiConfig:
        loaded = self.config.load()
        raw_settings = loaded.value.get("settings", {})
        if not isinstance(raw_settings, dict):
            raise PiConfigError("Pi config 'settings' must be a JSON object")

        self._reject_credential_material(raw_settings)

        bypassed = sorted(set(raw_settings).intersection(_RESOURCE_KEYS))
        if bypassed:
            raise PiConfigError(
                "Pi resource keys must use stable-ID registries, not settings: "
                + ", ".join(bypassed)
            )

        self._trusted_scopes = self._load_trusted_scopes(loaded.value)

        settings = dict(raw_settings)
        for resource_key in _RESOURCE_KEYS:
            if resource_key not in loaded.value:
                continue
            registry = loaded.value[resource_key]
            if not isinstance(registry, dict):
                raise PiConfigError(
                    f"Pi config '{resource_key}' must be an object keyed by stable ID"
                )
            settings[resource_key] = self._render_registry(resource_key, registry)

        unknown = sorted(
            set(loaded.value) - {"settings", _TRUSTED_SCOPES_KEY, *_RESOURCE_KEYS}
        )
        if unknown:
            raise PiConfigError("Unknown Pi config keys: " + ", ".join(unknown))

        return LoadedPiConfig(
            settings=settings,
            managed_keys=set(settings),
            layers=loaded.layers,
            trusted_scopes=self._trusted_scopes,
        )

    @staticmethod
    def _load_trusted_scopes(value: dict[str, Any]) -> tuple[str, ...]:
        raw = value.get(_TRUSTED_SCOPES_KEY, [])
        if not isinstance(raw, list) or not all(isinstance(s, str) and s for s in raw):
            raise PiConfigError(f"Pi config '{_TRUSTED_SCOPES_KEY}' must be a list of non-empty strings")
        return tuple(raw)

    @classmethod
    def _reject_credential_material(cls, value: Any, path: str = "settings") -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                normalized = re.sub(r"[^a-z]", "", str(key).lower())
                if normalized in _FORBIDDEN_CREDENTIAL_KEYS:
                    raise PiConfigError(
                        f"Pi config '{path}.{key}' may contain credential material; "
                        "use an approved runtime credential-provider extension"
                    )
                cls._reject_credential_material(child, f"{path}.{key}")
        elif isinstance(value, list):
            for index, child in enumerate(value):
                cls._reject_credential_material(child, f"{path}[{index}]")

    def _render_registry(
        self, resource_key: str, registry: dict[str, Any]
    ) -> list[Any]:
        rendered: list[Any] = []
        for entry_id, entry in registry.items():
            if not isinstance(entry, dict):
                raise PiConfigError(
                    f"Pi {resource_key} entry '{entry_id}' must be a JSON object"
                )
            enabled = entry.get("enabled", True)
            if not isinstance(enabled, bool):
                raise PiConfigError(
                    f"Pi {resource_key} entry '{entry_id}' has non-boolean enabled"
                )
            if not enabled:
                continue

            if resource_key == "packages":
                rendered.append(self._render_package(entry_id, entry))
            else:
                rendered.append(self._render_path(resource_key, entry_id, entry))
        return rendered

    @staticmethod
    def _render_path(resource_key: str, entry_id: str, entry: dict[str, Any]) -> str:
        unexpected = set(entry) - {"enabled", "path"}
        if unexpected:
            raise PiConfigError(
                f"Pi {resource_key} entry '{entry_id}' has unknown fields: "
                + ", ".join(sorted(unexpected))
            )
        path = entry.get("path")
        if not isinstance(path, str) or not path.strip():
            raise PiConfigError(
                f"Pi {resource_key} entry '{entry_id}' requires a non-empty path"
            )
        return path

    def _render_package(self, entry_id: str, entry: dict[str, Any]) -> Any:
        unexpected = set(entry) - {"enabled", *_PACKAGE_FIELDS}
        if unexpected:
            raise PiConfigError(
                f"Pi packages entry '{entry_id}' has unknown fields: "
                + ", ".join(sorted(unexpected))
            )

        source = entry.get("source")
        if not isinstance(source, str) or not source.strip():
            raise PiConfigError(
                f"Pi packages entry '{entry_id}' requires a non-empty source"
            )
        if not self._is_allowed_package_source(source):
            raise PiConfigError(
                f"Pi packages entry '{entry_id}' must be local, from a "
                "trustedPackageScopes-listed scope, or an exactly pinned "
                "Tyler-owned/fork source"
            )

        package = {
            key: value
            for key, value in entry.items()
            if key in _PACKAGE_FIELDS
        }
        if set(package) == {"source"}:
            return source
        return package

    def _is_allowed_package_source(self, source: str) -> bool:
        if source.startswith(("/", "./", "../", "~/")):
            return True
        if any(source.startswith(f"{scope}/") for scope in self._trusted_scopes):
            return True
        if source.startswith("npm:@tstapler/"):
            package_spec = source.removeprefix("npm:")
            package_name, separator, version = package_spec.rpartition("@")
            return bool(separator and package_name and version and version != "latest")
        if source.startswith(_FORK_SCHEME_PREFIXES):
            ref = parse_fork_source(source)
            if ref is None:
                return False
            return bool(re.fullmatch(r"[0-9a-fA-F]{7,64}", ref.commit))
        return False
