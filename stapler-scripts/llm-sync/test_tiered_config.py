"""Regression checks for config.d-style layered configuration.

Run directly: uv run test_tiered_config.py
"""

import json
import sys
import tempfile
from pathlib import Path

sys.path.append(str(Path(__file__).parent / "src"))

from sources.tiered_config import TieredConfigError, TieredJsonConfig


def _write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def test_loads_four_layers_in_precedence_order():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        universal = root / "config.json"
        tracked_fragments = root / "config.d"
        local = root / "config.local.json"
        local_fragments = root / "config.local.d"

        _write(
            universal,
            {
                "settings": {"theme": "dark", "compaction": {"enabled": True}},
                "packages": {
                    "base": {"source": "git:github.com/tstapler/base@abc"}
                },
            },
        )
        _write(
            tracked_fragments / "50-work.json",
            {
                "settings": {"defaultProvider": "work"},
                "packages": {
                    "work": {"source": "npm:@work-org/pi-agent@1.2.3"}
                },
            },
        )
        _write(local, {"settings": {"theme": "light"}})
        _write(
            local_fragments / "90-machine.json",
            {"settings": {"compaction": {"enabled": False}}},
        )

        loaded = TieredJsonConfig(
            universal_file=universal,
            tracked_fragments_dir=tracked_fragments,
            local_file=local,
            local_fragments_dir=local_fragments,
        ).load()

        assert loaded.value == {
            "settings": {
                "theme": "light",
                "compaction": {"enabled": False},
                "defaultProvider": "work",
            },
            "packages": {
                "base": {"source": "git:github.com/tstapler/base@abc"},
                "work": {"source": "npm:@work-org/pi-agent@1.2.3"},
            },
        }
        assert loaded.layers == (
            universal,
            tracked_fragments / "50-work.json",
            local,
            local_fragments / "90-machine.json",
        )


def test_null_deletes_a_value_and_arrays_replace():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        universal = root / "config.json"
        fragments = root / "config.d"
        _write(
            universal,
            {
                "settings": {
                    "enabledModels": ["anthropic/*", "openai/*"],
                    "theme": "dark",
                }
            },
        )
        _write(
            fragments / "50-override.json",
            {"settings": {"enabledModels": ["anthropic/*"], "theme": None}},
        )

        loaded = TieredJsonConfig(
            universal_file=universal,
            tracked_fragments_dir=fragments,
            local_file=root / "missing.local.json",
            local_fragments_dir=root / "missing.local.d",
        ).load()

        assert loaded.value == {"settings": {"enabledModels": ["anthropic/*"]}}


def test_missing_optional_layers_produce_empty_configuration():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        loaded = TieredJsonConfig(
            universal_file=root / "missing.json",
            tracked_fragments_dir=root / "missing.d",
            local_file=root / "missing.local.json",
            local_fragments_dir=root / "missing.local.d",
        ).load()

        assert loaded.value == {}
        assert loaded.layers == ()


def test_rejects_invalid_json_with_the_layer_path():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        broken = root / "config.json"
        broken.write_text("{not json", encoding="utf-8")

        try:
            TieredJsonConfig(
                universal_file=broken,
                tracked_fragments_dir=root / "config.d",
                local_file=root / "config.local.json",
                local_fragments_dir=root / "config.local.d",
            ).load()
        except TieredConfigError as error:
            assert str(broken) in str(error)
        else:
            raise AssertionError("invalid JSON should raise TieredConfigError")


def test_rejects_non_object_layer():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        universal = root / "config.json"
        _write(universal, ["not", "an", "object"])

        try:
            TieredJsonConfig(
                universal_file=universal,
                tracked_fragments_dir=root / "config.d",
                local_file=root / "config.local.json",
                local_fragments_dir=root / "config.local.d",
            ).load()
        except TieredConfigError as error:
            assert "JSON object" in str(error)
        else:
            raise AssertionError("non-object JSON should raise TieredConfigError")


if __name__ == "__main__":
    tests = [value for key, value in list(globals().items()) if key.startswith("test_")]
    for test in tests:
        test()
        print(f"ok  {test.__name__}")
    print(f"\n{len(tests)} checks passed")
