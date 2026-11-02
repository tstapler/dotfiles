"""Assert-based check that the Antigravity MCP writer keeps passthrough fields (e.g. HTTP `headers`).

Run directly: uv run test_antigravity_mcp.py
"""
import json
import sys
import tempfile
from pathlib import Path

sys.path.append(str(Path(__file__).parent / "src"))

from core import MCPServer
from targets.antigravity_mcp import AntigravityMcpTarget


def test_http_headers_survive():
    with tempfile.TemporaryDirectory() as d:
        out = Path(d) / "mcp.json"
        server = MCPServer(
            name="s", type="http", url="http://x/mcp",
            extra={"headers": {"Authorization": "Bearer t"}},
        )
        AntigravityMcpTarget(out).save_mcp_servers([server])
        entry = json.loads(out.read_text())["mcpServers"]["s"]
        assert entry == {
            "type": "http", "serverUrl": "http://x/mcp",
            "headers": {"Authorization": "Bearer t"},
        }, entry


if __name__ == "__main__":
    test_http_headers_survive()
    print("ok")
