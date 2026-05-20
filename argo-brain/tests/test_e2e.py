"""End-to-end / integration tests for the ARGO brain.

These tests wire together real components — a temp `Settings`/SQLite db, the
no-network `MockProvider`, the real `MemoryManager`, channel adapters, the
multi-agent subsystem and the in-process MCP server — and assert on observable
behaviour across module boundaries. No API keys and no network are required.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from argo_brain.channels.telegram import TelegramChannel
from argo_brain.channels.webhook import GenericWebhookChannel
from argo_brain.config import Settings
from argo_brain.core import AgentCore, AgentRequest
from argo_brain.mcp.server import MCPServer
from argo_brain.memory import MemoryManager
from argo_brain.multi_agent.dag import DAGWorkflow
from argo_brain.multi_agent.kanban import KanbanManager
from argo_brain.tools import build_default_registry


def _temp_settings(tmpdir: str, name: str = "e2e.db") -> Settings:
    """A Settings object backed entirely by a temp directory."""
    return Settings(
        data_dir=tmpdir,
        db_path=str(Path(tmpdir) / name),
        ipc_socket=str(Path(tmpdir) / "argo.sock"),
    )


class TestAgentLoopE2E(unittest.IsolatedAsyncioTestCase):
    """The full Plan -> Execute -> Reflect loop with a real tool."""

    async def asyncSetUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.agent = AgentCore(_temp_settings(self._tmp.name))

    async def asyncTearDown(self):
        self.agent.close()
        self._tmp.cleanup()

    async def test_chat_triggers_tool_and_persists(self):
        # A calculation request should drive a real `calculate` tool call,
        # produce the correct numeric answer, and persist the exchange.
        resp = await self.agent.process(
            AgentRequest(user_id="alice", message="hisobla 6 * 7")
        )
        self.assertIn("calculate", resp.tools_used)
        self.assertIn("42", resp.content)
        self.assertEqual(resp.iterations, 2)  # tool turn + answer turn

        history = await self.agent.memory.history("alice")
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]["role"], "user")
        self.assertEqual(history[1]["role"], "assistant")
        self.assertIn("42", history[1]["content"])

    async def test_chat_without_tool(self):
        resp = await self.agent.process(
            AgentRequest(user_id="bob", message="just say something")
        )
        self.assertEqual(resp.tools_used, [])
        self.assertEqual(resp.iterations, 1)
        self.assertTrue(resp.content)

    async def test_persistence_survives_reopen(self):
        # Messages written through one AgentCore must be readable by a fresh
        # MemoryManager pointed at the same SQLite db (L1 durability).
        await self.agent.process(
            AgentRequest(user_id="carol", message="remember this message")
        )
        db_path = self.agent.settings.resolved_db_path
        mem2 = MemoryManager(db_path)
        try:
            count = await mem2.persistent.count("carol")
            self.assertGreaterEqual(count, 2)
        finally:
            mem2.close()


class TestMultiTurnE2E(unittest.IsolatedAsyncioTestCase):
    """Multi-turn conversations accumulate history and detect language."""

    async def asyncSetUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.agent = AgentCore(_temp_settings(self._tmp.name))

    async def asyncTearDown(self):
        self.agent.close()
        self._tmp.cleanup()

    async def test_history_accumulates_over_turns(self):
        for i in range(3):
            await self.agent.process(
                AgentRequest(user_id="dave", message=f"message number {i}")
            )
        history = await self.agent.memory.history("dave")
        # 3 turns * (user + assistant) = 6 records.
        self.assertEqual(len(history), 6)

    async def test_language_detected_per_turn(self):
        r_uz = await self.agent.process(
            AgentRequest(user_id="eve", message="Salom, qanday yordam bera olasan")
        )
        self.assertEqual(r_uz.language, "uz")
        r_ru = await self.agent.process(
            AgentRequest(user_id="eve", message="Привет, как дела сегодня")
        )
        self.assertEqual(r_ru.language, "ru")

    async def test_explicit_language_override(self):
        resp = await self.agent.process(
            AgentRequest(user_id="frank", message="hello", language="kk")
        )
        self.assertEqual(resp.language, "kk")

    async def test_users_isolated(self):
        await self.agent.process(AgentRequest(user_id="u-a", message="alpha"))
        await self.agent.process(AgentRequest(user_id="u-b", message="beta"))
        hist_a = await self.agent.memory.history("u-a")
        hist_b = await self.agent.memory.history("u-b")
        self.assertEqual(len(hist_a), 2)
        self.assertEqual(len(hist_b), 2)
        self.assertNotIn("beta", " ".join(h["content"] for h in hist_a))


class TestChannelToAgentE2E(unittest.IsolatedAsyncioTestCase):
    """A parsed channel message flows through the agent and back."""

    async def asyncSetUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.agent = AgentCore(_temp_settings(self._tmp.name))

    async def asyncTearDown(self):
        self.agent.close()
        self._tmp.cleanup()

    async def test_telegram_update_through_agent(self):
        update = {
            "update_id": 101,
            "message": {
                "message_id": 1,
                "chat": {"id": 555},
                "from": {"id": 999},
                "text": "hisobla 8 * 8",
            },
        }
        msg = TelegramChannel.parse_update(update)
        self.assertIsNotNone(msg)
        self.assertEqual(msg.channel, "telegram")
        self.assertEqual(msg.user_id, "telegram:999")

        resp = await self.agent.process(
            AgentRequest(
                user_id=msg.user_id, message=msg.text, channel=msg.channel
            )
        )
        self.assertIn("calculate", resp.tools_used)
        self.assertIn("64", resp.content)

        history = await self.agent.memory.history(msg.user_id)
        self.assertEqual(history[0]["channel"], "telegram")

    async def test_telegram_non_text_update_ignored(self):
        # An update with no text yields no ChannelMessage.
        self.assertIsNone(TelegramChannel.parse_update({"update_id": 1}))
        self.assertIsNone(
            TelegramChannel.parse_update(
                {"update_id": 2, "message": {"chat": {"id": 1}}}
            )
        )

    async def test_generic_webhook_through_agent(self):
        channel = GenericWebhookChannel()
        msg = channel.parse_webhook(
            {"user_id": "42", "message": "hello from webhook"}
        )
        self.assertIsNotNone(msg)
        self.assertEqual(msg.user_id, "generic:42")
        resp = await self.agent.process(
            AgentRequest(
                user_id=msg.user_id, message=msg.text, channel=msg.channel
            )
        )
        self.assertTrue(resp.content)


class TestMultiAgentE2E(unittest.IsolatedAsyncioTestCase):
    """Kanban lifecycle and DAG workflows over a real AgentCore."""

    async def asyncSetUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.settings = _temp_settings(self._tmp.name)
        self.agent = AgentCore(self.settings)
        self.kanban = KanbanManager(Path(self._tmp.name) / "kanban.db")

    async def asyncTearDown(self):
        self.kanban.close()
        self.agent.close()
        self._tmp.cleanup()

    async def test_kanban_full_lifecycle(self):
        board_id = self.kanban.create_board("owner", "Sprint board", goal="ship")
        self.assertTrue(board_id)

        t1 = self.kanban.add_task(board_id, "Task A", "do A", priority=1)
        t2 = self.kanban.add_task(board_id, "Task B", "do B", priority=5)
        self.assertEqual(self.kanban.board_status(board_id), {"todo": 2})

        # The highest-priority task should be claimed first.
        claimed = self.kanban.claim_task(board_id, agent_id="agent-1")
        self.assertIsNotNone(claimed)
        self.assertEqual(claimed["id"], t2)
        self.assertEqual(claimed["status"], "claimed")
        self.assertEqual(claimed["agent_id"], "agent-1")

        self.kanban.complete_task(t2, result="B done")
        self.assertEqual(self.kanban.get_task(t2)["status"], "done")
        self.assertEqual(self.kanban.get_task(t2)["result"], "B done")

        # The remaining lower-priority task is claimed next.
        claimed2 = self.kanban.claim_task(board_id, agent_id="agent-2")
        self.assertEqual(claimed2["id"], t1)
        self.kanban.complete_task(t1, result="A done")

        status = self.kanban.board_status(board_id)
        self.assertEqual(status, {"done": 2})

    async def test_kanban_claim_empty_board(self):
        board_id = self.kanban.create_board("owner", "Empty board")
        self.assertIsNone(self.kanban.claim_task(board_id, agent_id="x"))

    async def test_dag_workflow_runs_through_agent(self):
        wf = DAGWorkflow()
        wf.add_task("step1", "first step")
        wf.add_task("step2", "second step", depends_on=["step1"])
        wf.add_task("step3", "hisobla 3 * 3", depends_on=["step1"])
        wf.add_task("final", "wrap up", depends_on=["step2", "step3"])

        results = await wf.run(self.agent)
        self.assertEqual(set(results), {"step1", "step2", "step3", "final"})
        for value in results.values():
            self.assertTrue(value)
        # step3 is a calculation task -> the answer flows through the agent.
        self.assertIn("9", results["step3"])

    async def test_dag_cycle_detected(self):
        from argo_brain.multi_agent.dag import DAGCycleError

        wf = DAGWorkflow()
        wf.add_task("a", "a", depends_on=["b"])
        wf.add_task("b", "b", depends_on=["a"])
        with self.assertRaises(DAGCycleError):
            await wf.run(self.agent)


class TestMCPE2E(unittest.IsolatedAsyncioTestCase):
    """The in-process MCP server exposes the real tool registry."""

    async def asyncSetUp(self):
        self.registry = build_default_registry()
        self.server = MCPServer(self.registry)

    async def test_initialize_handshake(self):
        resp = await self.server.handle(
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
        )
        self.assertEqual(resp["id"], 1)
        self.assertEqual(resp["result"]["serverInfo"]["name"], "argo-brain")
        self.assertIn("protocolVersion", resp["result"])

    async def test_tools_list_exposes_registry(self):
        resp = await self.server.handle(
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
        )
        tools = resp["result"]["tools"]
        self.assertGreaterEqual(len(tools), 50)
        names = {t["name"] for t in tools}
        self.assertIn("calculate", names)
        for tool in tools:
            self.assertIn("inputSchema", tool)

    async def test_tools_call_executes_real_tool(self):
        resp = await self.server.handle(
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {
                    "name": "calculate",
                    "arguments": {"expression": "12 * 12"},
                },
            }
        )
        self.assertFalse(resp["result"]["isError"])
        text = resp["result"]["content"][0]["text"]
        self.assertIn("144", text)

    async def test_tools_call_unknown_tool(self):
        resp = await self.server.handle(
            {
                "jsonrpc": "2.0",
                "id": 4,
                "method": "tools/call",
                "params": {"name": "no_such_tool", "arguments": {}},
            }
        )
        self.assertIn("error", resp)
        self.assertEqual(resp["error"]["code"], -32602)

    async def test_notification_gets_no_response(self):
        resp = await self.server.handle(
            {"jsonrpc": "2.0", "method": "notifications/initialized"}
        )
        self.assertIsNone(resp)

    async def test_unknown_method(self):
        resp = await self.server.handle(
            {"jsonrpc": "2.0", "id": 5, "method": "bogus/method"}
        )
        self.assertEqual(resp["error"]["code"], -32601)


class TestMemoryE2E(unittest.IsolatedAsyncioTestCase):
    """L0 + L1 + L2 of the memory stack working together."""

    async def asyncSetUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.memory = MemoryManager(Path(self._tmp.name) / "memory.db")

    async def asyncTearDown(self):
        self.memory.close()
        self._tmp.cleanup()

    async def test_add_and_history(self):
        await self.memory.add("u1", "user", "what is the capital of France")
        await self.memory.add("u1", "assistant", "Paris is the capital")
        history = await self.memory.history("u1")
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]["content"], "what is the capital of France")

    async def test_fts_search_l1(self):
        await self.memory.add("u1", "user", "the quick brown fox jumps")
        await self.memory.add("u1", "user", "lazy dogs sleep all day")
        results = await self.memory.search("u1", "brown")
        self.assertEqual(len(results), 1)
        self.assertIn("brown", results[0]["content"])

    async def test_fts_search_scoped_per_user(self):
        await self.memory.add("u1", "user", "shared keyword apple")
        await self.memory.add("u2", "user", "shared keyword apple")
        results = await self.memory.search("u1", "apple")
        self.assertEqual(len(results), 1)

    async def test_semantic_search_l2(self):
        await self.memory.add("u1", "user", "python programming language tutorial")
        await self.memory.add("u1", "user", "cooking pasta with tomato sauce")
        results = self.memory.semantic_search("u1", "python language", k=2)
        self.assertEqual(len(results), 2)
        # The most semantically similar entry should rank first.
        self.assertIn("python", results[0]["text"])
        self.assertGreaterEqual(results[0]["score"], results[1]["score"])

    async def test_profile_lifecycle(self):
        self.assertIsNone(await self.memory.profile("new-user"))
        prof = await self.memory.ensure_profile("new-user", language="ru")
        self.assertEqual(prof["language"], "ru")
        # ensure_profile is idempotent.
        again = await self.memory.ensure_profile("new-user", language="ru")
        self.assertEqual(again["user_id"], "new-user")

    async def test_working_memory_l0_fast_path(self):
        # L0 working memory should serve history without touching L1.
        await self.memory.add("u1", "user", "fast path message")
        l0 = self.memory.working.history("u1", 10)
        self.assertEqual(len(l0), 1)
        self.assertEqual(l0[0]["content"], "fast path message")


if __name__ == "__main__":
    unittest.main()
