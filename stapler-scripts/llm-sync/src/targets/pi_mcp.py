import json
from pathlib import Path
from typing import List, Optional

try:
    from core import MCPServer
except ImportError:
    from ..core import MCPServer

from rich.console import Console

console = Console()


class PiMcpTarget:
    """Merges opted-in MCP servers into ~/.pi/agent/mcp.json.

    Unlike the Claude/Antigravity targets this never replaces the file: it is
    shared with a work-managed wrapper that owns the gateway entries, so only
    servers whose `_targets` list names "pi" are added or updated and every
    other entry is preserved. Removing a server from the source does not remove
    it here.
    """

    def __init__(self, agent_dir: Optional[Path] = None, mcp_config_file: Optional[Path] = None):
        base = Path(agent_dir) if agent_dir else Path.home() / ".pi" / "agent"
        self.mcp_config_file = mcp_config_file or base / "mcp.json"
        self.settings_file = self.mcp_config_file  # alias for sync_mcp compat

    def save_mcp_servers(self, servers: List[MCPServer], dry_run: bool = False) -> int:
        owned = {}
        for server in servers:
            if server.disabled or not server.applies_to("pi"):
                continue
            if server.type == "http":
                entry: dict = {"type": "http", "url": server.url}
            else:
                entry = {"command": server.command, "args": server.args}
                if server.env:
                    entry["env"] = server.env
            entry.update(server.extra)
            owned[server.name] = entry

        if dry_run:
            console.print(f"[blue]Would merge {len(owned)} MCP servers into {self.mcp_config_file}[/blue]")
            for name in owned:
                console.print(f"[dim]  - {name}[/dim]")
            return len(owned)
        if not owned:
            return 0

        config: dict = {}
        if self.mcp_config_file.exists():
            try:
                config = json.loads(self.mcp_config_file.read_text(encoding="utf-8"))
            except Exception as e:
                console.print(f"[red]Error reading {self.mcp_config_file}: {e}[/red]")
                return 0
        config.setdefault("mcpServers", {}).update(owned)

        self.mcp_config_file.parent.mkdir(parents=True, exist_ok=True)
        self.mcp_config_file.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
        return len(owned)
