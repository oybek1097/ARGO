"""MCP tool wrapper — spec section 4.10.

Wraps a tool advertised by an external MCP server so it plugs into the
normal `ToolRegistry`. Registered under the name `mcp_<server>_<tool>`.
"""

from __future__ import annotations

from argo_brain.mcp.client import MCPClient
from argo_brain.tools.base import Tool, ToolResult


class MCPTool(Tool):
    """Adapts one MCP server tool to the ARGO `Tool` interface."""

    def __init__(self, client: MCPClient, server_name: str, definition: dict) -> None:
        self._client = client
        self._remote_name = definition["name"]
        self.name = f"mcp_{server_name}_{definition['name']}"
        self.description = definition.get("description", "")
        self.parameters = definition.get(
            "inputSchema", {"type": "object", "properties": {}}
        )

    async def run(self, user_id: str, **kwargs) -> ToolResult:
        try:
            content = await self._client.call_tool(self._remote_name, kwargs)
        except Exception as exc:  # noqa: BLE001 — surface MCP errors as tool failures
            return ToolResult(content=f"MCP error: {exc}", success=False)
        return ToolResult(content=content)
