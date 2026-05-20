#!/usr/bin/env python3
"""Minimal MCP server used by the test suite.

Implements just enough of the protocol (initialize, tools/list, tools/call)
to exercise `MCPClient` over stdio with newline-delimited JSON-RPC. It
exposes a single `echo` tool.
"""

import json
import sys

_TOOLS = [
    {
        "name": "echo",
        "description": "Echoes the supplied text back to the caller.",
        "inputSchema": {
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
    }
]


def _handle(msg: dict) -> dict | None:
    """Returns a JSON-RPC response, or None for notifications."""
    msg_id = msg.get("id")
    method = msg.get("method")

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "echo-test-server", "version": "0.1.0"},
            },
        }
    if method == "notifications/initialized":
        return None  # a notification — no response
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": msg_id, "result": {"tools": _TOOLS}}
    if method == "tools/call":
        params = msg.get("params", {})
        tool_name = params.get("name")
        if tool_name != "echo":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {"code": -32602, "message": f"unknown tool: {tool_name}"},
            }
        text = params.get("arguments", {}).get("text", "")
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {"content": [{"type": "text", "text": f"echo: {text}"}]},
        }
    return {
        "jsonrpc": "2.0",
        "id": msg_id,
        "error": {"code": -32601, "message": f"method not found: {method}"},
    }


def main() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        response = _handle(msg)
        if response is not None:
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
