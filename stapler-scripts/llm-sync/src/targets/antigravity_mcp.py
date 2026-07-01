import json
from pathlib import Path
from typing import List, Optional

try:
    from core import MCPServer
except ImportError:
    from ..core import MCPServer

from rich.console import Console

console = Console()


class AntigravityMcpTarget:
    """Writes MCP config to ~/.gemini/antigravity-cli/mcp_config.json.

    Key difference from old Gemini CLI: HTTP servers use "serverUrl" not "url"/"httpUrl".
    """

    def __init__(self, mcp_config_file: Optional[Path] = None):
        self.mcp_config_file = mcp_config_file or (
            Path.home() / ".gemini" / "config" / "mcp.json"
        )
        self.settings_file = self.mcp_config_file  # alias for sync_mcp compat

    def save_mcp_servers(self, servers: List[MCPServer], dry_run: bool = False) -> int:
        mcp_servers = {}
        for server in servers:
            if server.disabled:
                continue
            if server.type == "http":
                mcp_servers[server.name] = {"type": "http", "serverUrl": server.url}
            else:
                entry: dict = {"command": server.command, "args": server.args}
                if server.env:
                    entry["env"] = server.env
                mcp_servers[server.name] = entry

        if dry_run:
            console.print(
                f"[blue]Would write {len(mcp_servers)} MCP servers to {self.mcp_config_file}[/blue]"
            )
            for name in mcp_servers:
                console.print(f"[dim]  - {name}[/dim]")
            return len(mcp_servers)

        self.mcp_config_file.parent.mkdir(parents=True, exist_ok=True)
        config = {"mcpServers": mcp_servers}
        with open(self.mcp_config_file, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
            f.write("\n")

        return len(mcp_servers)
