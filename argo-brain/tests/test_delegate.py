"""Tests for multi-agent delegation — delegate.py and dag.py."""

import tempfile
import unittest
from pathlib import Path

from argo_brain.config import Settings
from argo_brain.core import AgentCore
from argo_brain.multi_agent.dag import DAGCycleError, DAGWorkflow
from argo_brain.multi_agent.delegate import delegate_task, mixture_of_agents


class TestDelegate(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        settings = Settings(
            data_dir=self._tmp.name,
            db_path=str(Path(self._tmp.name) / "delegate.db"),
        )
        self.agent = AgentCore(settings)

    async def asyncTearDown(self):
        self.agent.close()
        self._tmp.cleanup()

    # --- delegate_task ---

    async def test_delegate_task_three_prompts(self):
        prompts = ["first task", "second task", "third task"]
        results = await delegate_task(self.agent, prompts)
        self.assertEqual(len(results), 3)
        for r in results:
            self.assertTrue(r)

    async def test_delegate_task_empty(self):
        results = await delegate_task(self.agent, [])
        self.assertEqual(results, [])

    async def test_delegate_task_isolated_contexts(self):
        # Each sub-task uses a distinct user_id, so histories stay separate.
        await delegate_task(self.agent, ["alpha", "beta"], user_id="iso")
        hist0 = await self.agent.memory.history("iso-0")
        hist1 = await self.agent.memory.history("iso-1")
        # Each isolated context only has its own user + assistant turn.
        self.assertEqual(len(hist0), 2)
        self.assertEqual(len(hist1), 2)

    # --- mixture_of_agents ---

    async def test_mixture_of_agents_returns_string(self):
        answer = await mixture_of_agents(self.agent, "explain ARGO")
        self.assertIsInstance(answer, str)
        self.assertTrue(answer)

    async def test_mixture_of_agents_zero_rounds(self):
        # rounds <= 0 still produces the initial answer.
        answer = await mixture_of_agents(self.agent, "quick question", rounds=0)
        self.assertTrue(answer)

    # --- DAGWorkflow ---

    async def test_dag_chain(self):
        # a -> b -> c
        dag = DAGWorkflow()
        dag.add_task("a", "task a")
        dag.add_task("b", "task b", depends_on=["a"])
        dag.add_task("c", "task c", depends_on=["b"])
        results = await dag.run(self.agent)
        self.assertEqual(set(results), {"a", "b", "c"})
        for r in results.values():
            self.assertTrue(r)

    async def test_dag_diamond(self):
        # a -> {b, c} -> d
        dag = DAGWorkflow()
        dag.add_task("a", "root")
        dag.add_task("b", "left", depends_on=["a"])
        dag.add_task("c", "right", depends_on=["a"])
        dag.add_task("d", "join", depends_on=["b", "c"])
        results = await dag.run(self.agent)
        self.assertEqual(set(results), {"a", "b", "c", "d"})

    async def test_dag_topological_levels(self):
        # Verify the internal level grouping respects dependencies.
        dag = DAGWorkflow()
        dag.add_task("a", "root")
        dag.add_task("b", "left", depends_on=["a"])
        dag.add_task("c", "right", depends_on=["a"])
        dag.add_task("d", "join", depends_on=["b", "c"])
        levels = dag._topological_order()
        self.assertEqual(levels[0], ["a"])
        self.assertEqual(levels[1], ["b", "c"])
        self.assertEqual(levels[2], ["d"])

    async def test_dag_cycle_detected(self):
        # a -> b -> a is a cycle.
        dag = DAGWorkflow()
        dag.add_task("a", "task a", depends_on=["b"])
        dag.add_task("b", "task b", depends_on=["a"])
        with self.assertRaises(DAGCycleError):
            await dag.run(self.agent)

    async def test_dag_unknown_dependency(self):
        dag = DAGWorkflow()
        dag.add_task("a", "task a", depends_on=["missing"])
        with self.assertRaises(ValueError):
            await dag.run(self.agent)

    async def test_dag_duplicate_task_id(self):
        dag = DAGWorkflow()
        dag.add_task("a", "task a")
        with self.assertRaises(ValueError):
            dag.add_task("a", "again")

    async def test_dag_independent_tasks(self):
        # No dependencies -> all tasks run in a single level.
        dag = DAGWorkflow()
        dag.add_task("x", "task x")
        dag.add_task("y", "task y")
        dag.add_task("z", "task z")
        results = await dag.run(self.agent)
        self.assertEqual(set(results), {"x", "y", "z"})


if __name__ == "__main__":
    unittest.main()
