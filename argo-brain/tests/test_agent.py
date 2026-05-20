"""AgentCore integration tests."""

import tempfile
import unittest
from pathlib import Path

from argo_brain.config import Settings
from argo_brain.core import AgentCore, AgentRequest


class TestAgentCore(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        settings = Settings(
            data_dir=self._tmp.name,
            db_path=str(Path(self._tmp.name) / "agent.db"),
        )
        self.agent = AgentCore(settings)

    async def asyncTearDown(self):
        self.agent.close()
        self._tmp.cleanup()

    async def test_simple_chat(self):
        resp = await self.agent.process(
            AgentRequest(user_id="u1", message="Salom, men bilan gaplash")
        )
        self.assertTrue(resp.content)
        self.assertEqual(resp.language, "uz")
        self.assertEqual(resp.iterations, 1)

    async def test_calculate_via_tool(self):
        resp = await self.agent.process(
            AgentRequest(user_id="u1", message="hisobla 6 * 7")
        )
        self.assertIn("calculate", resp.tools_used)
        self.assertIn("42", resp.content)

    async def test_current_time_via_tool(self):
        resp = await self.agent.process(
            AgentRequest(user_id="u1", message="hozir vaqt qancha?")
        )
        self.assertIn("current_time", resp.tools_used)

    async def test_history_persisted(self):
        await self.agent.process(AgentRequest(user_id="u1", message="birinchi xabar"))
        await self.agent.process(AgentRequest(user_id="u1", message="ikkinchi xabar"))
        hist = await self.agent.memory.history("u1")
        # each request stores user + assistant = 2 records
        self.assertEqual(len(hist), 4)

    async def test_explicit_language_override(self):
        resp = await self.agent.process(
            AgentRequest(user_id="u1", message="test", language="ru")
        )
        self.assertEqual(resp.language, "ru")

    async def test_response_metadata(self):
        resp = await self.agent.process(AgentRequest(user_id="u1", message="salom"))
        self.assertEqual(resp.model, "mock")
        self.assertGreaterEqual(resp.duration_ms, 0)
        d = resp.to_dict()
        self.assertIn("content", d)
        self.assertIn("tools_used", d)


if __name__ == "__main__":
    unittest.main()
