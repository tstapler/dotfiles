# ADR-001: Explicit lazy plugin registry with a `typing.Protocol` contract

**Status**: Accepted (2026-10-16) · **Plan**: Stories 2.1, 2.3

## Context
Analysis stages (faces, age, era, OCR, cloud) must be addable without editing `cli.py`'s core flow. `cli.py` is a PEP 723 uv script with sibling flat imports (`research/architecture.md` s3). Requirements warn against plugin-framework over-engineering; 3-5 plugins exist.

## Decision
A registry maps `name -> "module:Class"` strings; only enabled plugins are imported. The contract is a `typing.Protocol` (`name`, `version`, `requires_cloud`, `scope`, `runtime`, `after`, `analyze`). Ordering is an explicit DAG via `after=`. Adding a plugin = one new file + one registry entry. Amended 2026-10-16: the registry is the union of one-line entry files `G/plugins/registry.d/<name>.toml` (name, `module:Class`, runtime, default-enabled); reading them imports nothing, so loading stays explicit and lazy, and plugin stories in one agent wave never edit a shared `registry.py` dict.

## Consequences
- Heavy dependencies never load unless the plugin is enabled and its `runtime` is reachable (see ADR-004).
- Cloud plugins are not imported without `CloudPolicy(allow_cloud=True)` (ADR-005).
- The registry line edit is outside `cli.py`'s flow, satisfying the success metric; verified by a toy-plugin test (Story 10.5).

## Alternatives rejected
- **Entry points / stevedore**: need an installed distribution; a PEP 723 script has none (INFERRED).
- **pluggy**: hook-spec ceremony designed for third-party ecosystems; exceeds the need.
- **Directory auto-discovery**: acceptable but implicit load order and import-time side effects; may be added later as an escape hatch.
