"""Plugin system tests."""

import unittest

from argo_brain.plugin import ArgoPlugin, PluginRegistry
from argo_brain.tools.base import ToolCall, ToolResult


class _VetoShellPlugin(ArgoPlugin):
    """Test plugin: vetoes any `shell_exec` call, tags every result."""

    name = "veto-shell"

    async def pre_tool_call(self, call, user_id):
        return None if call.name == "shell_exec" else call

    async def transform_tool_result(self, call, result, user_id):
        return ToolResult(content=result.content + " [seen]", success=result.success)

    async def on_response(self, user_id, content, model):
        self.last_response = content


class TestPluginRegistry(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.reg = PluginRegistry()
        self.plugin = _VetoShellPlugin()
        await self.reg.register(self.plugin)

    async def test_registered(self):
        self.assertIn("veto-shell", self.reg.names())

    async def test_pre_tool_veto(self):
        calls = [
            ToolCall(id="1", name="shell_exec", arguments={"command": "ls"}),
            ToolCall(id="2", name="calculate", arguments={"expression": "1+1"}),
        ]
        allowed = await self.reg.run_pre_tool(calls, "u1")
        self.assertEqual([c.name for c in allowed], ["calculate"])

    async def test_post_tool_transform(self):
        call = ToolCall(id="1", name="calculate")
        out = await self.reg.run_post_tool(call, ToolResult(content="42"), "u1")
        self.assertEqual(out.content, "42 [seen]")

    async def test_on_response_hook(self):
        await self.reg.emit_response("u1", "hello", "mock")
        self.assertEqual(self.plugin.last_response, "hello")

    async def test_disabled_plugin_skipped(self):
        self.plugin.enabled = False
        calls = [ToolCall(id="1", name="shell_exec")]
        allowed = await self.reg.run_pre_tool(calls, "u1")
        self.assertEqual(len(allowed), 1)  # not vetoed when disabled


if __name__ == "__main__":
    unittest.main()
