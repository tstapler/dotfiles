"""Ownership-safe ledger for on-disk Pi package artifacts.

Sibling to `PiSettingsTarget`'s `managedKeys` pattern (same atomic-write
shape), but for the files `pi install` writes under the Pi agent directory
rather than `settings.json` keys. Grounded in `.config/pi/README.md`'s
"Package lifecycle" spike: Pi does not garbage-collect installed packages
when `settings.json` is hand-edited (as `PiSettingsTarget.save()` does) --
only its own `pi remove`/`pi uninstall` CLI prunes artifacts. This ledger
lets `llm-sync` detect and, on request, clean up artifacts orphaned by a
config-only removal.
"""

import json
import os
import shutil
import tempfile
from pathlib import Path


class PiPackageLedgerError(ValueError):
    """Existing Pi package ledger state cannot be read safely."""


class PiPackageLedger:
    def __init__(self, state_path: Path, agent_dir: Path) -> None:
        self.state_path = state_path
        self.agent_dir = agent_dir

    def artifact_path_for_source(self, source: str) -> Path | None:
        """Return the on-disk artifact path for `source`, or `None` if unverified.

        Only the npm source shape is grounded in the Epic 2.1 spike: an
        `npm:`-prefixed `packages` entry lands under
        `<agent_dir>/npm/node_modules/<package-name>/`
        (`.config/pi/README.md`'s "Package lifecycle" section). Git-fork
        (`git:...@<commit>`) and local (`path:`/`./`/`~/`) source shapes have
        no confirmed artifact-path pattern -- rather than fabricate one,
        this returns `None`, which callers record as an explicit
        "unknown, not yet verified" sentinel instead of a guessed path.
        """
        if source.startswith("npm:"):
            return self.agent_dir / "npm" / "node_modules" / _npm_package_name(source)
        return None

    def save(self, enabled_packages: dict[str, str], dry_run: bool = False) -> bool:
        """Upsert artifact paths for every enabled `{entry_id: source}` pair.

        Entries already in the ledger for ids *not* in `enabled_packages`
        (i.e. removed from config) are left untouched here -- they remain
        visible to `find_stale()` until an explicit `prune()` removes them.
        """
        state = self._read_state()
        desired = dict(state)
        for entry_id, source in enabled_packages.items():
            path = self.artifact_path_for_source(source)
            desired[entry_id] = str(path) if path is not None else None

        if desired == state:
            return False
        if dry_run:
            return True

        self._write_state(desired)
        return True

    def find_stale(self, current_ids: set[str]) -> list[str]:
        """Ids present in the ledger but absent from `current_ids`. Read-only."""
        state = self._read_state()
        return sorted(set(state) - current_ids)

    def prune(self, stale_ids: list[str], dry_run: bool = False) -> list[str]:
        """Delete only the ledger-recorded artifact paths for `stale_ids`.

        Never touches a path that isn't recorded in the ledger for one of
        `stale_ids`. Returns the paths actually deleted (or, under
        `dry_run`, that would be deleted).
        """
        state = self._read_state()
        remaining = dict(state)
        deleted: list[str] = []

        for entry_id in stale_ids:
            if entry_id not in state:
                continue
            remaining.pop(entry_id, None)
            recorded = state[entry_id]
            if recorded is None:
                continue
            recorded_path = Path(recorded)
            if not recorded_path.exists():
                continue
            deleted.append(recorded)
            if not dry_run:
                if recorded_path.is_dir():
                    shutil.rmtree(recorded_path)
                else:
                    recorded_path.unlink()

        if not dry_run and remaining != state:
            self._write_state(remaining)
        return deleted

    def reconcile(
        self, enabled_packages: dict[str, str], dry_run: bool = False
    ) -> list[str]:
        """Backfill ledger entries missing after an interrupted sync.

        Recovery strategy: the caller re-derives the current
        `{entry_id: source}` mapping the same way `sync_pi_settings()` does
        (re-loading the tiered Pi config, since the rendered
        `settings.json` array has already dropped stable ids) and passes it
        here. Only ids absent from the ledger are added -- an id already
        recorded is left exactly as-is, even if its source has since
        changed (that's `save()`'s job on the next normal sync, not
        reconcile's). Returns the ids actually recovered.
        """
        state = self._read_state()
        merged = dict(state)
        recovered: list[str] = []

        for entry_id, source in enabled_packages.items():
            if entry_id in state:
                continue
            path = self.artifact_path_for_source(source)
            merged[entry_id] = str(path) if path is not None else None
            recovered.append(entry_id)

        if recovered and not dry_run:
            self._write_state(merged)
        return recovered

    def _read_state(self) -> dict[str, str | None]:
        if not self.state_path.exists():
            return {}
        try:
            value = json.loads(self.state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise PiPackageLedgerError(
                f"Cannot read {self.state_path}: {error}"
            ) from error
        if not isinstance(value, dict) or not all(
            isinstance(key, str) and (val is None or isinstance(val, str))
            for key, val in value.items()
        ):
            raise PiPackageLedgerError(
                f"{self.state_path} must be a JSON object mapping id -> path-or-null"
            )
        return value

    def _write_state(self, value: dict[str, str | None]) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        content = json.dumps(value, indent=2, sort_keys=True) + "\n"
        file_descriptor, temporary_name = tempfile.mkstemp(
            dir=self.state_path.parent, prefix=f".{self.state_path.name}.", text=True
        )
        temporary_path = Path(temporary_name)
        try:
            with os.fdopen(file_descriptor, "w", encoding="utf-8") as temporary_file:
                temporary_file.write(content)
                temporary_file.flush()
                os.fsync(temporary_file.fileno())
            os.chmod(temporary_path, 0o600)
            os.replace(temporary_path, self.state_path)
        finally:
            temporary_path.unlink(missing_ok=True)


def _npm_package_name(source: str) -> str:
    """Extract the npm package name from an `npm:`-prefixed source string.

    Handles both unversioned (`npm:@scope/name`, the exact shape observed
    in the Epic 2.1 spike) and versioned (`npm:@scope/name@1.2.3` or
    `npm:name@1.2.3`, the shape `pi_config.py`'s `_is_allowed_package_source`
    requires for `npm:@tstapler/` sources) forms.
    """
    spec = source.removeprefix("npm:")
    if spec.startswith("@"):
        scope, separator, rest = spec.partition("/")
        if not separator:
            return spec
        name, at, _version = rest.rpartition("@")
        return f"{scope}/{name if at else rest}"
    name, at, _version = spec.rpartition("@")
    return name if at else spec
