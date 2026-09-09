"""Ownership-safe writer for generated portions of Pi settings.json."""

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from sources.pi_config import LoadedPiConfig


class PiSettingsTargetError(ValueError):
    """Existing Pi settings or ownership state cannot be read safely."""


class PiSettingsTarget:
    def __init__(self, settings_path: Path, state_path: Path) -> None:
        self.settings_path = settings_path
        self.state_path = state_path

    def save(self, config: LoadedPiConfig, dry_run: bool = False) -> bool:
        existing = self._read_object(self.settings_path)
        state = self._read_object(self.state_path)
        previous_managed = state.get("managedKeys", [])
        if not isinstance(previous_managed, list) or not all(
            isinstance(key, str) for key in previous_managed
        ):
            raise PiSettingsTargetError(
                f"Pi ownership state {self.state_path} has invalid managedKeys"
            )

        desired = {
            key: value
            for key, value in existing.items()
            if key not in set(previous_managed)
        }
        desired.update(config.settings)
        desired_state = {"managedKeys": sorted(config.managed_keys)}

        settings_changed = desired != existing
        state_changed = desired_state != state
        changed = settings_changed or state_changed
        if dry_run or not changed:
            return changed

        if settings_changed:
            self._write_object(self.settings_path, desired)
        if state_changed:
            self._write_object(self.state_path, desired_state)
        return True

    @staticmethod
    def _read_object(path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise PiSettingsTargetError(f"Cannot read {path}: {error}") from error
        if not isinstance(value, dict):
            raise PiSettingsTargetError(f"{path} must contain a JSON object")
        return value

    @staticmethod
    def _write_object(path: Path, value: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        content = json.dumps(value, indent=2, sort_keys=True) + "\n"
        file_descriptor, temporary_name = tempfile.mkstemp(
            dir=path.parent, prefix=f".{path.name}.", text=True
        )
        temporary_path = Path(temporary_name)
        try:
            with os.fdopen(file_descriptor, "w", encoding="utf-8") as temporary_file:
                temporary_file.write(content)
                temporary_file.flush()
                os.fsync(temporary_file.fileno())
            os.chmod(temporary_path, 0o600)
            os.replace(temporary_path, path)
        finally:
            temporary_path.unlink(missing_ok=True)
