"""Integration tests for the observability / cache / trajectory subsystems
wired into :class:`AgentCore`.

These verify that the optional ``metrics``, ``trajectories`` and ``cache``
constructor parameters are honoured when supplied, and that omitting them
leaves the agent loop on its original default path.
"""

import tempfile
import unittest
from pathlib import Path

from argo_brain.cache.session import SessionCache
from argo_brain.config import Settings
from argo_brain.core import AgentCore, AgentRequest
from argo_brain.observability.metrics import MetricsCollector
from argo_brain.rl.trajectory import TrajectoryCollector


def _make_settings(tmp: str) -> Settings:
    return Settings(
        data_dir=tmp,
        db_path=str(Path(tmp) / "agent.db"),
    )


class TestAgentIntegration(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.settings = _make_settings(self._tmp.name)
        self._agents: list[AgentCore] = []

    async def asyncTearDown(self):
        for agent in self._agents:
            agent.close()
        self._tmp.cleanup()

    def _agent(self, **kwargs) -> AgentCore:
        agent = AgentCore(self.settings, **kwargs)
        self._agents.append(agent)
        return agent

    # -- metrics ----------------------------------------------------------
    async def test_metrics_counter_incremented(self):
        metrics = MetricsCollector()
        agent = self._agent(metrics=metrics)
        await agent.process(AgentRequest(user_id="u1", message="salom"))
        self.assertEqual(
            metrics.get_counter("argo_chat_requests_total"), 1.0
        )

    async def test_metrics_counter_accumulates(self):
        metrics = MetricsCollector()
        agent = self._agent(metrics=metrics)
        await agent.process(AgentRequest(user_id="u1", message="salom"))
        await agent.process(AgentRequest(user_id="u1", message="yana"))
        await agent.process(AgentRequest(user_id="u1", message="uchinchi"))
        self.assertEqual(
            metrics.get_counter("argo_chat_requests_total"), 3.0
        )

    async def test_metrics_duration_histogram_recorded(self):
        metrics = MetricsCollector()
        agent = self._agent(metrics=metrics)
        await agent.process(AgentRequest(user_id="u1", message="salom"))
        hist = metrics.get_histogram("argo_chat_duration_seconds")
        self.assertIsNotNone(hist)
        self.assertEqual(hist["count"], 1)
        self.assertGreaterEqual(hist["sum"], 0.0)

    # -- trajectories -----------------------------------------------------
    async def test_trajectory_recorded_once(self):
        trajectories = TrajectoryCollector()
        agent = self._agent(trajectories=trajectories)
        await agent.process(AgentRequest(user_id="u1", message="salom"))
        self.assertEqual(trajectories.count(), 1)

    async def test_trajectory_fields_correct(self):
        trajectories = TrajectoryCollector()
        agent = self._agent(trajectories=trajectories)
        resp = await agent.process(
            AgentRequest(user_id="u1", message="salom")
        )
        traj = trajectories.all()[0]
        self.assertEqual(traj["user_input"], "salom")
        self.assertEqual(traj["output"], resp.content)
        self.assertEqual(traj["model"], "mock")
        self.assertTrue(traj["success"])
        self.assertEqual(traj["tools_used"], [])
        self.assertGreaterEqual(traj["duration_ms"], 0)

    async def test_trajectory_tool_use_records_tools(self):
        trajectories = TrajectoryCollector()
        agent = self._agent(trajectories=trajectories)
        await agent.process(
            AgentRequest(user_id="u1", message="hisobla 6 * 7")
        )
        traj = trajectories.all()[0]
        self.assertIn("calculate", traj["tools_used"])
        self.assertIn("42", traj["output"])
        self.assertTrue(traj["success"])

    async def test_trajectory_multiple_requests(self):
        trajectories = TrajectoryCollector()
        agent = self._agent(trajectories=trajectories)
        await agent.process(AgentRequest(user_id="u1", message="bir"))
        await agent.process(AgentRequest(user_id="u1", message="ikki"))
        self.assertEqual(trajectories.count(), 2)
        inputs = [t["user_input"] for t in trajectories.all()]
        self.assertEqual(inputs, ["bir", "ikki"])

    async def test_trajectory_export_after_process(self):
        trajectories = TrajectoryCollector()
        agent = self._agent(trajectories=trajectories)
        await agent.process(AgentRequest(user_id="u1", message="salom"))
        sft = trajectories.export_sft()
        self.assertEqual(len(sft), 1)
        self.assertEqual(sft[0]["instruction"], "salom")

    # -- cache ------------------------------------------------------------
    async def test_cache_records_fingerprint(self):
        cache = SessionCache()
        agent = self._agent(cache=cache)
        await agent.process(AgentRequest(user_id="u1", message="salom"))
        # A fingerprint entry should have been stored for the user.
        self.assertEqual(cache.stats()["size"], 1)

    async def test_cache_does_not_change_response(self):
        cache = SessionCache()
        plain = self._agent()
        cached = self._agent(cache=cache)
        r1 = await plain.process(
            AgentRequest(user_id="u1", message="salom")
        )
        r2 = await cached.process(
            AgentRequest(user_id="u2", message="salom")
        )
        self.assertEqual(r1.content, r2.content)

    # -- default path -----------------------------------------------------
    async def test_default_path_unchanged_no_subsystems(self):
        agent = self._agent()
        self.assertIsNone(agent.metrics)
        self.assertIsNone(agent.trajectories)
        self.assertIsNone(agent.cache)
        resp = await agent.process(
            AgentRequest(user_id="u1", message="salom")
        )
        self.assertTrue(resp.content)
        self.assertEqual(resp.model, "mock")
        self.assertEqual(resp.iterations, 1)

    async def test_default_path_tool_use_unchanged(self):
        agent = self._agent()
        resp = await agent.process(
            AgentRequest(user_id="u1", message="hisobla 6 * 7")
        )
        self.assertIn("calculate", resp.tools_used)
        self.assertIn("42", resp.content)

    # -- all three together -----------------------------------------------
    async def test_all_subsystems_together(self):
        metrics = MetricsCollector()
        trajectories = TrajectoryCollector()
        cache = SessionCache()
        agent = self._agent(
            metrics=metrics, trajectories=trajectories, cache=cache
        )
        resp = await agent.process(
            AgentRequest(user_id="u1", message="salom")
        )
        self.assertTrue(resp.content)
        self.assertEqual(metrics.get_counter("argo_chat_requests_total"), 1.0)
        self.assertEqual(trajectories.count(), 1)
        self.assertEqual(cache.stats()["size"], 1)


if __name__ == "__main__":
    unittest.main()
