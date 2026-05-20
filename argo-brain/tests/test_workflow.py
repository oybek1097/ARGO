"""Tests for the agent-workflow tools — spec section 4.4."""

from __future__ import annotations

import time
import unittest

from argo_brain.tools.base import Tool
from argo_brain.tools.builtin.workflow import (
    ClarifyTool,
    PlanTool,
    TodoTool,
    WaitTool,
    workflow_tools,
)


class TodoToolTest(unittest.IsolatedAsyncioTestCase):
    async def test_add_then_list(self) -> None:
        tool = TodoTool()
        res = await tool("u1", action="add", item="buy milk")
        self.assertTrue(res.success)
        listed = await tool("u1", action="list")
        self.assertIn("buy milk", listed.content)
        self.assertIn("[ ]", listed.content)

    async def test_complete_marks_done(self) -> None:
        tool = TodoTool()
        await tool("u1", action="add", item="write report")
        res = await tool("u1", action="complete", item="write report")
        self.assertTrue(res.success)
        listed = await tool("u1", action="list")
        self.assertIn("[x] write report", listed.content)

    async def test_clear_empties_list(self) -> None:
        tool = TodoTool()
        await tool("u1", action="add", item="task a")
        await tool("u1", action="clear")
        listed = await tool("u1", action="list")
        self.assertIn("empty", listed.content)

    async def test_per_user_isolation(self) -> None:
        tool = TodoTool()
        await tool("alice", action="add", item="alice task")
        await tool("bob", action="add", item="bob task")
        alice = await tool("alice", action="list")
        bob = await tool("bob", action="list")
        self.assertIn("alice task", alice.content)
        self.assertNotIn("bob task", alice.content)
        self.assertIn("bob task", bob.content)
        self.assertNotIn("alice task", bob.content)

    async def test_add_without_item_fails(self) -> None:
        tool = TodoTool()
        res = await tool("u1", action="add")
        self.assertFalse(res.success)

    async def test_complete_missing_item_fails(self) -> None:
        tool = TodoTool()
        res = await tool("u1", action="complete", item="nope")
        self.assertFalse(res.success)

    async def test_unknown_action_fails(self) -> None:
        tool = TodoTool()
        res = await tool("u1", action="frobnicate")
        self.assertFalse(res.success)

    async def test_empty_list_message(self) -> None:
        tool = TodoTool()
        res = await tool("fresh", action="list")
        self.assertTrue(res.success)
        self.assertIn("empty", res.content)


class ClarifyToolTest(unittest.IsolatedAsyncioTestCase):
    async def test_returns_question(self) -> None:
        tool = ClarifyTool()
        res = await tool("u1", question="Which region do you mean?")
        self.assertTrue(res.success)
        self.assertIn("Which region do you mean?", res.content)
        self.assertIn("Clarification", res.content)
        self.assertTrue(res.metadata.get("clarification"))

    async def test_empty_question_fails(self) -> None:
        tool = ClarifyTool()
        res = await tool("u1", question="")
        self.assertFalse(res.success)


class WaitToolTest(unittest.IsolatedAsyncioTestCase):
    async def test_short_wait(self) -> None:
        tool = WaitTool()
        started = time.perf_counter()
        res = await tool("u1", seconds=0.01)
        elapsed = time.perf_counter() - started
        self.assertTrue(res.success)
        self.assertGreaterEqual(elapsed, 0.01)
        self.assertEqual(res.metadata["waited"], 0.01)

    async def test_cap_enforced(self) -> None:
        tool = WaitTool()
        res = await tool("u1", seconds=999)
        self.assertTrue(res.success)
        # The actual wait must be clamped to the 10-second cap.
        self.assertEqual(res.metadata["waited"], 10.0)
        self.assertEqual(res.metadata["requested"], 999.0)

    async def test_invalid_seconds_fails(self) -> None:
        tool = WaitTool()
        res = await tool("u1", seconds="not-a-number")
        self.assertFalse(res.success)


class PlanToolTest(unittest.IsolatedAsyncioTestCase):
    async def test_formats_numbered_steps(self) -> None:
        tool = PlanTool()
        res = await tool("u1", steps=["gather data", "analyze", "report"])
        self.assertTrue(res.success)
        self.assertIn("1. gather data", res.content)
        self.assertIn("2. analyze", res.content)
        self.assertIn("3. report", res.content)

    async def test_stores_plan_per_user(self) -> None:
        tool = PlanTool()
        await tool("alice", steps=["alice step"])
        await tool("bob", steps=["bob step one", "bob step two"])
        self.assertEqual(tool._plans["alice"], ["alice step"])
        self.assertEqual(tool._plans["bob"], ["bob step one", "bob step two"])

    async def test_empty_steps_fails(self) -> None:
        tool = PlanTool()
        res = await tool("u1", steps=[])
        self.assertFalse(res.success)


class WorkflowToolsTest(unittest.IsolatedAsyncioTestCase):
    async def test_returns_four_tools(self) -> None:
        tools = workflow_tools()
        self.assertEqual(len(tools), 4)
        for tool in tools:
            self.assertIsInstance(tool, Tool)

    async def test_tool_names(self) -> None:
        names = {tool.name for tool in workflow_tools()}
        self.assertEqual(names, {"todo", "clarify", "wait", "plan"})


if __name__ == "__main__":
    unittest.main()
