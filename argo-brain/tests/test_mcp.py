"""MCP client integration tests.

Spawns the bundled `echo_mcp_server.py` fixture as a real subprocess and
drives it through `MCPClient` over stdio.
"""

import sys
import tempfile
import unittest
from pathlib import Path

from argo_brain.mcp import MCPClient, MCPTool, read_mcp_config
from argo_brain.tools import ToolCall, build_default_registry

_SERVER = Path(__file__).parent / "fixtures" / "echo_mcp_server.py"


class TestMCPClient(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.client = MCPClient("echo", sys.executable, [str(_SERVER)])
        await self.client.start()

    async def asyncTearDown(self):
        await self.client.stop()

    async def test_handshake_lists_tools(self):
        self.assertEqual(len(self.client.tools), 1)
        self.assertEqual(self.client.tools[0]["name"], "echo")

    async def test_call_tool(self):
        result = await self.client.call_tool("echo", {"text": "ARGO"})
        self.assertEqual(result, "echo: ARGO")

    async def test_call_unknown_tool_raises(self):
        with self.assertRaises(RuntimeError):
            await self.client.call_tool("nonexistent", {})


class TestMCPTool(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.client = MCPClient("echo", sys.executable, [str(_SERVER)])
        await self.client.start()

    async def asyncTearDown(self):
        await self.client.stop()

    async def test_wrapper_naming(self):
        tool = MCPTool(self.client, "echo", self.client.tools[0])
        self.assertEqual(tool.name, "mcp_echo_echo")
        self.assertEqual(tool.parameters["type"], "object")

    async def test_wrapper_runs_via_registry(self):
        registry = build_default_registry()
        registry.register(MCPTool(self.client, "echo", self.client.tools[0]))
        self.assertIn("mcp_echo_echo", registry.names())
        result = await registry.execute(
            ToolCall(id="c1", name="mcp_echo_echo", arguments={"text": "salom"}),
            "u1",
        )
        self.assertTrue(result.success)
        self.assertEqual(result.content, "echo: salom")


class TestReadMcpConfig(unittest.TestCase):
    def test_missing_file_returns_empty(self):
        self.assertEqual(read_mcp_config("/no/such/config.json"), [])

    def test_reads_server_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = Path(tmp) / "config.json"
            cfg.write_text(
                '{"mcp": {"servers": [{"name": "fs", "command": "npx"}]}}',
                encoding="utf-8",
            )
            servers = read_mcp_config(cfg)
            self.assertEqual(len(servers), 1)
            self.assertEqual(servers[0]["name"], "fs")

    def test_config_without_mcp_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = Path(tmp) / "config.json"
            cfg.write_text('{"model": "mock"}', encoding="utf-8")
            self.assertEqual(read_mcp_config(cfg), [])


if __name__ == "__main__":
    unittest.main()
