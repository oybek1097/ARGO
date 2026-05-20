"""MCP (Model Context Protocol) subsystem — spec section 4.10.

ARGO acts both as an MCP *client* (connecting to external MCP servers over
stdio and exposing their tools) and as an MCP *server* (exposing its own
tools to other MCP clients).
"""

from argo_brain.mcp.client import MCPClient
from argo_brain.mcp.loader import load_mcp_servers, read_mcp_config
from argo_brain.mcp.server import MCPServer
from argo_brain.mcp.tool import MCPTool

__all__ = [
    "MCPClient",
    "MCPServer",
    "MCPTool",
    "load_mcp_servers",
    "read_mcp_config",
]
