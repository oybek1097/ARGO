"""MCP server loader — spec section 4.10.

Reads the MCP server list from `~/.argo/config.json` and connects to each,
returning the live clients and the tools they expose.

Config shape:

    {
      "mcp": {
        "servers": [
          {"name": "filesystem", "command": "npx",
           "args": ["@modelcontextprotocol/server-filesystem", "/path"]}
        ]
      }
    }
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from argo_brain.mcp.client import MCPClient
from argo_brain.mcp.tool import MCPTool

log = logging.getLogger("argo_brain.mcp")


def read_mcp_config(config_path: Path | str | None = None) -> list[dict]:
    """Returns the list of MCP server specs from the config file."""
    if config_path is None:
        home = Path(os.environ.get("ARGO_HOME", Path.home() / ".argo"))
        config_path = home / "config.json"
    path = Path(config_path)
    if not path.is_file():
        return []
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    servers = config.get("mcp", {}).get("servers", [])
    return servers if isinstance(servers, list) else []


async def load_mcp_servers(
    servers: list[dict],
) -> tuple[list[MCPClient], list[MCPTool]]:
    """Connects to each configured MCP server.

    Returns (clients, tools). A server that fails to start is logged and
    skipped — it must not block the others.
    """
    clients: list[MCPClient] = []
    tools: list[MCPTool] = []

    for spec in servers:
        name = spec.get("name")
        command = spec.get("command")
        if not name or not command:
            log.warning("skipping MCP server with no name/command: %s", spec)
            continue
        client = MCPClient(
            name, command, spec.get("args"), spec.get("cwd"), spec.get("env")
        )
        try:
            await client.start()
        except Exception as exc:  # noqa: BLE001 — one bad server must not block others
            log.warning("MCP server '%s' failed to start: %s", name, exc)
            continue
        clients.append(client)
        for definition in client.tools:
            tools.append(MCPTool(client, name, definition))

    return clients, tools
