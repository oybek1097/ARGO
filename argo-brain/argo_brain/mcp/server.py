"""MCP server — spec section 4.10.

The server side of the MCP integration: ARGO exposes its own
`ToolRegistry` tools to external MCP clients over JSON-RPC 2.0.

Per the spec, the stdio transport is **newline-delimited JSON** (one
message per line), not Content-Length framed. This mirrors the protocol
style of the existing `MCPClient` in `client.py`.

Dependency-free: uses only `asyncio` and `json` from the stdlib.
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys

from argo_brain import __version__
from argo_brain.tools.base import ToolCall
from argo_brain.tools.registry import ToolRegistry

log = logging.getLogger("argo_brain.mcp")

_PROTOCOL_VERSION = "2024-11-05"

# JSON-RPC 2.0 standard error code for an unrecognised method.
_METHOD_NOT_FOUND = -32601
# Application-level error code used when a requested tool does not exist.
_TOOL_NOT_FOUND = -32602

# The user id under which tools are executed when invoked through MCP.
_MCP_USER_ID = "mcp"


class MCPServer:
    """Exposes a `ToolRegistry` to MCP clients over JSON-RPC 2.0 / stdio."""

    def __init__(self, registry: ToolRegistry) -> None:
        self._registry = registry

    # --- request dispatch ---------------------------------------------------

    async def handle(self, message: dict) -> dict | None:
        """Processes one JSON-RPC message and returns the response dict.

        Returns ``None`` for notifications (messages without an ``id``,
        such as ``notifications/initialized``), which expect no reply.
        """
        method = message.get("method")
        msg_id = message.get("id")
        params = message.get("params") or {}

        if method == "initialize":
            return self._result(msg_id, self._on_initialize())

        if method == "notifications/initialized":
            # A notification — acknowledged silently, no response is sent.
            return None

        if method == "tools/list":
            return self._result(msg_id, self._on_tools_list())

        if method == "tools/call":
            return await self._on_tools_call(msg_id, params)

        # Any other method is unknown to this server.
        return self._error(
            msg_id, _METHOD_NOT_FOUND, f"Method not found: {method}"
        )

    # --- method implementations --------------------------------------------

    def _on_initialize(self) -> dict:
        """Builds the `initialize` result (handshake reply)."""
        return {
            "protocolVersion": _PROTOCOL_VERSION,
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "argo-brain", "version": __version__},
        }

    def _on_tools_list(self) -> dict:
        """Converts the registry's tool schemas into MCP tool format.

        ARGO stores tools as OpenAI-style function schemas
        (``{"type": "function", "function": {...}}``); MCP expects
        ``{"name", "description", "inputSchema"}`` per tool.
        """
        tools = []
        for tool in self._registry.all():
            tools.append({
                "name": tool.name,
                "description": tool.description,
                "inputSchema": tool.parameters,
            })
        return {"tools": tools}

    async def _on_tools_call(self, msg_id, params: dict) -> dict:
        """Executes a named tool and returns MCP content blocks."""
        name = params.get("name", "")
        arguments = params.get("arguments") or {}

        if self._registry.get(name) is None:
            return self._error(
                msg_id, _TOOL_NOT_FOUND, f"Unknown tool: {name}"
            )

        call = ToolCall(id=str(msg_id), name=name, arguments=arguments)
        result = await self._registry.execute(call, _MCP_USER_ID)

        return self._result(msg_id, {
            "content": [{"type": "text", "text": result.content}],
            "isError": not result.success,
        })

    # --- JSON-RPC envelope helpers -----------------------------------------

    @staticmethod
    def _result(msg_id, result: dict) -> dict:
        """Wraps a successful result in a JSON-RPC 2.0 response envelope."""
        return {"jsonrpc": "2.0", "id": msg_id, "result": result}

    @staticmethod
    def _error(msg_id, code: int, message: str) -> dict:
        """Wraps an error in a JSON-RPC 2.0 response envelope."""
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "error": {"code": code, "message": message},
        }

    # --- stdio transport ----------------------------------------------------

    async def serve_stdio(self) -> None:
        """Serves requests over stdin/stdout (newline-delimited JSON).

        Reads one JSON message per line, dispatches it through `handle()`
        and writes any response back as a single line. Runs until stdin
        is closed (EOF).
        """
        loop = asyncio.get_running_loop()

        # Wrap the blocking stdio streams in an asyncio StreamReader so the
        # event loop is never blocked while waiting for input.
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        await loop.connect_read_pipe(lambda: protocol, sys.stdin)

        while True:
            line = await reader.readline()
            if not line:
                break  # client closed stdin (EOF)
            try:
                message = json.loads(line)
            except json.JSONDecodeError:
                # A malformed line is skipped; there is no id to reply to.
                log.warning("MCP server: skipping malformed JSON line")
                continue

            response = await self.handle(message)
            if response is not None:
                sys.stdout.write(json.dumps(response) + "\n")
                sys.stdout.flush()
