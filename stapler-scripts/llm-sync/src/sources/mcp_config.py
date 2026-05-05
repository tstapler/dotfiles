import json
from pathlib import Path
from typing import Dict, List, Optional

try:
    from core import MCPServer
except ImportError:
    from ..core import MCPServer

from rich.console import Console

console = Console()


class McpConfigSource:
    def __init__(
        self,
        global_config_file: Optional[Path] = None,
        local_config_file: Optional[Path] = None,
    ):
        # Global: checked into dotfiles repo (./.config/mcp/mcp-servers.json)
        self.global_config_file = global_config_file or self._find_global()
        # Local: machine-specific overrides, gitignored (~/.config/mcp/mcp-servers.local.json)
        self.local_config_file = local_config_file or (
            Path.home() / ".config" / "mcp" / "mcp-servers.local.json"
        )

    def _find_global(self) -> Path:
        local_path = Path.cwd() / ".config" / "mcp" / "mcp-servers.json"
        if local_path.exists():
            return local_path
        return Path.home() / ".config" / "mcp" / "mcp-servers.json"

    def load_servers(self) -> List[MCPServer]:
        servers: Dict[str, MCPServer] = {}
        for path in [self.global_config_file, self.local_config_file]:
            if path and path.exists():
                loaded = self._load_file(path)
                if loaded:
                    servers.update(loaded)
                    console.print(
                        f"[dim]Loaded {len(loaded)} MCP servers from {path}[/dim]"
                    )
        return list(servers.values())

    def _load_file(self, path: Path) -> Dict[str, MCPServer]:
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            result = {}
            for name, config in data.get("mcpServers", {}).items():
                result[name] = MCPServer(
                    name=name,
                    command=config.get("command", ""),
                    args=config.get("args", []),
                    env=config.get("env", {}),
                    type=config.get("type"),
                    url=config.get("url"),
                    disabled=config.get("disabled", False),
                )
            return result
        except Exception as e:
            console.print(f"[red]Error reading MCP config {path}: {e}[/red]")
            return {}
