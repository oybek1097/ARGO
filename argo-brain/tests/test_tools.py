"""Tool system tests."""

import tempfile
import unittest
from pathlib import Path

from argo_brain.tools import ToolCall, build_default_registry
from argo_brain.tools.builtin.basic import CalculateTool, CurrentTimeTool, ReadFileTool


class TestBuiltinTools(unittest.IsolatedAsyncioTestCase):
    async def test_calculate(self):
        r = await CalculateTool()("u1", expression="2 + 3 * 4")
        self.assertTrue(r.success)
        self.assertEqual(r.content, "14")

    async def test_calculate_rejects_unsafe(self):
        r = await CalculateTool()("u1", expression="__import__('os')")
        self.assertFalse(r.success)

    async def test_calculate_divide_by_zero(self):
        r = await CalculateTool()("u1", expression="1 / 0")
        self.assertFalse(r.success)

    async def test_current_time(self):
        r = await CurrentTimeTool()("u1")
        self.assertTrue(r.success)
        self.assertIn("T", r.content)  # ISO format

    async def test_read_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "hello.txt"
            p.write_text("ARGO test", encoding="utf-8")
            r = await ReadFileTool()("u1", path=str(p))
            self.assertEqual(r.content, "ARGO test")

    async def test_read_file_missing(self):
        r = await ReadFileTool()("u1", path="/yoq/bunday/fayl.txt")
        self.assertFalse(r.success)


class TestToolRegistry(unittest.IsolatedAsyncioTestCase):
    async def test_default_registry_has_tools(self):
        reg = build_default_registry()
        self.assertIn("calculate", reg.names())
        self.assertIn("current_time", reg.names())

    async def test_schemas_well_formed(self):
        reg = build_default_registry()
        for schema in reg.schemas():
            self.assertEqual(schema["type"], "function")
            self.assertIn("name", schema["function"])

    async def test_execute_known_tool(self):
        reg = build_default_registry()
        result = await reg.execute(
            ToolCall(id="c1", name="calculate", arguments={"expression": "10 - 4"}),
            "u1",
        )
        self.assertEqual(result.content, "6")

    async def test_execute_unknown_tool(self):
        reg = build_default_registry()
        result = await reg.execute(ToolCall(id="c1", name="yoq_tool"), "u1")
        self.assertFalse(result.success)

    async def test_execute_parallel(self):
        reg = build_default_registry()
        calls = [
            ToolCall(id="c1", name="calculate", arguments={"expression": "1+1"}),
            ToolCall(id="c2", name="calculate", arguments={"expression": "2+2"}),
        ]
        results = await reg.execute_parallel(calls, "u1")
        self.assertEqual([r.content for r in results], ["2", "4"])


if __name__ == "__main__":
    unittest.main()
