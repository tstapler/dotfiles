"""Strict config.d-style JSON loading with deterministic precedence."""

import copy
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class TieredConfigError(ValueError):
    """A configuration layer could not be loaded safely."""


@dataclass(frozen=True)
class LoadedTieredConfig:
    value: dict[str, Any]
    layers: tuple[Path, ...]


class TieredJsonConfig:
    """Merge universal, tracked-fragment, local, and local-fragment layers.

    Objects merge recursively, arrays and scalar values replace earlier values,
    and JSON null deletes an inherited object key. Fragment directories are read
    in lexical filename order.
    """

    def __init__(
        self,
        *,
        universal_file: Path,
        tracked_fragments_dir: Path,
        local_file: Path,
        local_fragments_dir: Path,
    ) -> None:
        self.universal_file = universal_file
        self.tracked_fragments_dir = tracked_fragments_dir
        self.local_file = local_file
        self.local_fragments_dir = local_fragments_dir

    def load(self) -> LoadedTieredConfig:
        value: dict[str, Any] = {}
        loaded_paths: list[Path] = []

        for path in self._layer_paths():
            layer = self._read_object(path)
            value = self._merge(value, layer)
            loaded_paths.append(path)

        return LoadedTieredConfig(value=value, layers=tuple(loaded_paths))

    def _layer_paths(self) -> list[Path]:
        paths: list[Path] = []
        if self.universal_file.is_file():
            paths.append(self.universal_file)
        if self.tracked_fragments_dir.is_dir():
            paths.extend(sorted(self.tracked_fragments_dir.glob("*.json")))
        if self.local_file.is_file():
            paths.append(self.local_file)
        if self.local_fragments_dir.is_dir():
            paths.extend(sorted(self.local_fragments_dir.glob("*.json")))
        return paths

    @staticmethod
    def _read_object(path: Path) -> dict[str, Any]:
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise TieredConfigError(f"Cannot load configuration layer {path}: {error}") from error

        if not isinstance(loaded, dict):
            raise TieredConfigError(
                f"Configuration layer {path} must contain a JSON object"
            )
        return loaded

    @classmethod
    def _merge(
        cls, inherited: dict[str, Any], override: dict[str, Any]
    ) -> dict[str, Any]:
        result = copy.deepcopy(inherited)
        for key, value in override.items():
            if value is None:
                result.pop(key, None)
            elif isinstance(value, dict) and isinstance(result.get(key), dict):
                result[key] = cls._merge(result[key], value)
            else:
                result[key] = copy.deepcopy(value)
        return result
