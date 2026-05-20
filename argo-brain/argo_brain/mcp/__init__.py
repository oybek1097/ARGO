"""MCP (Model Context Protocol) subsystem — spec section 4.10.

The skeleton implements the MCP *client*: ARGO connects to external MCP
servers over stdio and exposes their tools through the normal tool registry.
The MCP *server* side (ARGO exposing its own tools) follows in a later sprint.
"""

from argo_brain.mcp.client import MCPClient
from argo_brain.mcp.loader import load_mcp_servers, read_mcp_config
from argo_brain.mcp.tool import MCPTool

__all__ = ["MCPClient", "MCPTool", "load_mcp_servers", "read_mcp_config"]
