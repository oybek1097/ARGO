"""Tests for the MCP server side — spec section 4.10.

Drives `MCPServer.handle()` directly with crafted JSON-RPC 2.0 messages,
using a fully populated registry from `build_default_registry()`.
"""

from __future__ import annotations

import unittest

from argo_brain.mcp.server import MCPServer
from argo_brain.tools.registry import build_default_registry


class MCPServerTest(unittest.IsolatedAsyncioTestCase):
    """Exercises the MCP server request dispatch."""

    def setUp(self) -> None:
        self.registry = build_default_registry()
        self.server = MCPServer(self.registry)

    async def test_initialize_returns_protocol_version(self) -> None:
        """`initialize` returns a result advertising the protocol version."""
        response = await self.server.handle({
            "jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {},
        })
        self.assertIsNotNone(response)
        self.assertEqual(response["id"], 1)
        result = response["result"]
        self.assertEqual(result["protocolVersion"], "2024-11-05")
        self.assertIn("capabilities", result)
        self.assertIn("serverInfo", result)
        self.assertEqual(result["serverInfo"]["name"], "argo-brain")

    async def test_initialized_notification_returns_none(self) -> None:
        """`notifications/initialized` is a notification — no reply."""
        response = await self.server.handle({
            "jsonrpc": "2.0", "method": "notifications/initialized",
            "params": {},
        })
        self.assertIsNone(response)

    async def test_tools_list_returns_non_empty_list(self) -> None:
        """`tools/list` returns a non-empty list of tools."""
        response = await self.server.handle({
            "jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {},
        })
        tools = response["result"]["tools"]
        self.assertIsInstance(tools, list)
        self.assertGreater(len(tools), 0)

    async def test_tools_list_entries_have_name_and_input_schema(self) -> None:
        """Each `tools/list` entry uses the MCP tool format."""
        response = await self.server.handle({
            "jsonrpc": "2.0", "id": 3, "method": "tools/list", "params": {},
        })
        for tool in response["result"]["tools"]:
            self.assertIn("name", tool)
            self.assertIn("description", tool)
            self.assertIn("inputSchema", tool)
            # The OpenAI-style wrapper must NOT leak into the MCP format.
            self.assertNotIn("function", tool)

    async def test_tools_call_real_tool_returns_text_block(self) -> None:
        """`tools/call` on the `calculate` tool returns a text content block."""
        response = await self.server.handle({
            "jsonrpc": "2.0", "id": 4, "method": "tools/call",
            "params": {"name": "calculate",
                       "arguments": {"expression": "2+2"}},
        })
        content = response["result"]["content"]
        self.assertEqual(content[0]["type"], "text")
        self.assertEqual(content[0]["text"], "4")
        self.assertFalse(response["result"]["isError"])

    async def test_tools_call_unknown_tool_returns_error(self) -> None:
        """`tools/call` on a missing tool returns a JSON-RPC error."""
        response = await self.server.handle({
            "jsonrpc": "2.0", "id": 5, "method": "tools/call",
            "params": {"name": "does_not_exist", "arguments": {}},
        })
        self.assertIn("error", response)
        self.assertNotIn("result", response)
        self.assertIn("does_not_exist", response["error"]["message"])

    async def test_unknown_method_returns_error_minus_32601(self) -> None:
        """An unrecognised method returns JSON-RPC error -32601."""
        response = await self.server.handle({
            "jsonrpc": "2.0", "id": 6, "method": "no/such/method",
            "params": {},
        })
        self.assertIn("error", response)
        self.assertEqual(response["error"]["code"], -32601)

    async def test_response_envelope_is_jsonrpc_2_0(self) -> None:
        """Every response carries the JSON-RPC 2.0 envelope fields."""
        response = await self.server.handle({
            "jsonrpc": "2.0", "id": 7, "method": "initialize", "params": {},
        })
        self.assertEqual(response["jsonrpc"], "2.0")
        self.assertEqual(response["id"], 7)

    async def test_tools_call_failing_tool_sets_is_error(self) -> None:
        """A tool that fails surfaces `isError: True` but still returns text."""
        response = await self.server.handle({
            "jsonrpc": "2.0", "id": 8, "method": "tools/call",
            "params": {"name": "calculate",
                       "arguments": {"expression": "1 / 0"}},
        })
        result = response["result"]
        self.assertTrue(result["isError"])
        self.assertEqual(result["content"][0]["type"], "text")


if __name__ == "__main__":
    unittest.main()
