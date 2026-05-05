import json
from pathlib import Path
from typing import List, Optional

try:
    from core import MCPServer
except ImportError:
    from ..core import MCPServer

from rich.console import Console

console = Console()


class ClaudeSettingsTarget:
    def __init__(self, settings_file: Optional[Path] = None):
        self.settings_file = settings_file or Path.home() / ".claude.json"

    def save_mcp_servers(self, servers: List[MCPServer], dry_run: bool = False) -> int:
        settings = {}
        if self.settings_file.exists():
            try:
                with open(self.settings_file, "r", encoding="utf-8") as f:
                    settings = json.load(f)
            except Exception as e:
                console.print(f"[red]Error reading {self.settings_file}: {e}[/red]")
                return 0

        mcp_servers = {}
        for server in servers:
            if server.disabled:
                continue
            if server.type == "http":
                mcp_servers[server.name] = {"type": "http", "url": server.url}
            else:
                mcp_servers[server.name] = {
                    "command": server.command,
                    "args": server.args,
                    "env": server.env,
                }

        if dry_run:
            console.print(
                f"[blue]Would write {len(mcp_servers)} MCP servers to {self.settings_file}[/blue]"
            )
            for name in mcp_servers:
                console.print(f"[dim]  - {name}[/dim]")
            return len(mcp_servers)

        settings["mcpServers"] = mcp_servers
        with open(self.settings_file, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)
            f.write("\n")

        return len(mcp_servers)
