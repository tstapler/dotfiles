"""Assert-based check that the Pi MCP writer merges opted-in servers and leaves others alone.

Run directly: uv run test_pi_mcp.py
"""
import json
import sys
import tempfile
from pathlib import Path

sys.path.append(str(Path(__file__).parent / "src"))

from core import MCPServer
from targets.antigravity_mcp import AntigravityMcpTarget
from targets.claude_settings import ClaudeSettingsTarget
from targets.pi_mcp import PiMcpTarget

PI_ONLY = MCPServer(name="ssq", type="http", url="http://localhost:8543/mcp", targets=["pi"])
EVERYWHERE = MCPServer(name="all", type="http", url="http://x/mcp")


def test_merge_preserves_unmanaged_entries():
    with tempfile.TemporaryDirectory() as d:
        out = Path(d) / "mcp.json"
        out.write_text(json.dumps({"mcpServers": {"core-tools": {"type": "http", "url": "http://gw"}}}))
        assert PiMcpTarget(mcp_config_file=out).save_mcp_servers([PI_ONLY, EVERYWHERE]) == 1
        servers = json.loads(out.read_text())["mcpServers"]
        assert servers["core-tools"] == {"type": "http", "url": "http://gw"}, servers
        assert servers["ssq"] == {"type": "http", "url": "http://localhost:8543/mcp"}, servers
        assert "all" not in servers, "untargeted servers must not be written to Pi"


def test_pi_only_server_skipped_by_other_targets():
    with tempfile.TemporaryDirectory() as d:
        claude = Path(d) / "claude.json"
        anti = Path(d) / "anti.json"
        ClaudeSettingsTarget(claude).save_mcp_servers([PI_ONLY, EVERYWHERE])
        AntigravityMcpTarget(anti).save_mcp_servers([PI_ONLY, EVERYWHERE])
        assert list(json.loads(claude.read_text())["mcpServers"]) == ["all"]
        assert list(json.loads(anti.read_text())["mcpServers"]) == ["all"]


def test_no_owned_servers_leaves_file_untouched():
    with tempfile.TemporaryDirectory() as d:
        out = Path(d) / "mcp.json"
        assert PiMcpTarget(mcp_config_file=out).save_mcp_servers([EVERYWHERE]) == 0
        assert not out.exists()


if __name__ == "__main__":
    test_merge_preserves_unmanaged_entries()
    test_pi_only_server_skipped_by_other_targets()
    test_no_owned_servers_leaves_file_untouched()
    print("ok")
