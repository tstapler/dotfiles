import json
from pathlib import Path
from typing import Dict, List, Optional

try:
    from core import MCPServer
except ImportError:
    from ..core import MCPServer

from rich.console import Console

console = Console()

_KNOWN_KEYS = {"command", "args", "env", "type", "url", "disabled"}


class McpConfigSource:
    """Loads MCP server definitions from a config.d-style layered set of sources.

    Merge order (later wins on name collision): global file, global config.d/*.json
    (sorted by filename), local file, local config.d/*.json (sorted by filename).
    This lets multiple repos/fragments contribute servers without editing a shared
    file — e.g. a personal dotfiles repo's mcp-servers.json plus a separate overlay
    repo's mcp-servers.d/50-something.json.
    """

    def __init__(
        self,
        global_config_file: Optional[Path] = None,
        local_config_file: Optional[Path] = None,
        global_config_dir: Optional[Path] = None,
        local_config_dir: Optional[Path] = None,
    ):
        # Global: checked into dotfiles repo (./.config/mcp/mcp-servers.json)
        self.global_config_file = global_config_file or self._find_global(
            "mcp-servers.json"
        )
        # Global config.d: additional tracked fragments, merged on top of the
        # global file (e.g. .config/mcp/mcp-servers.d/50-work.json)
        self.global_config_dir = global_config_dir or self._find_global(
            "mcp-servers.d"
        )
        # Local: machine-specific overrides, gitignored (~/.config/mcp/mcp-servers.local.json)
        self.local_config_file = local_config_file or (
            Path.home() / ".config" / "mcp" / "mcp-servers.local.json"
        )
        # Local config.d: additional machine-local fragments, gitignored
        self.local_config_dir = local_config_dir or (
            Path.home() / ".config" / "mcp" / "mcp-servers.local.d"
        )

    def _find_global(self, name: str) -> Path:
        local_path = Path.cwd() / ".config" / "mcp" / name
        if local_path.exists():
            return local_path
        return Path.home() / ".config" / "mcp" / name

    def load_servers(self) -> List[MCPServer]:
        servers: Dict[str, MCPServer] = {}

        def apply(path: Path):
            loaded = self._load_file(path)
            if loaded:
                servers.update(loaded)
                console.print(
                    f"[dim]Loaded {len(loaded)} MCP servers from {path}[/dim]"
                )

        for path in [self.global_config_file]:
            if path and path.exists() and path.is_file():
                apply(path)

        for path in self._sorted_fragments(self.global_config_dir):
            apply(path)

        for path in [self.local_config_file]:
            if path and path.exists() and path.is_file():
                apply(path)

        for path in self._sorted_fragments(self.local_config_dir):
            apply(path)

        return list(servers.values())

    def _sorted_fragments(self, directory: Optional[Path]) -> List[Path]:
        if not directory or not directory.is_dir():
            return []
        return sorted(directory.glob("*.json"))

    def _load_file(self, path: Path) -> Dict[str, MCPServer]:
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            result = {}
            for name, config in data.get("mcpServers", {}).items():
                extra = {
                    k: v
                    for k, v in config.items()
                    if k not in _KNOWN_KEYS and not k.startswith("_")
                }
                result[name] = MCPServer(
                    name=name,
                    command=config.get("command", ""),
                    args=config.get("args", []),
                    env=config.get("env", {}),
                    type=config.get("type"),
                    url=config.get("url"),
                    disabled=config.get("disabled", False),
                    extra=extra,
                )
            return result
        except Exception as e:
            console.print(f"[red]Error reading MCP config {path}: {e}[/red]")
            return {}
