"""Kanban manager tests."""

import tempfile
import unittest
from pathlib import Path

from argo_brain.multi_agent import KanbanManager


class TestKanbanManager(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.km = KanbanManager(Path(self._tmp.name) / "kanban.db")
        self.board = self.km.create_board("u1", "Sprint board", goal="ship it")

    def tearDown(self):
        self.km.close()
        self._tmp.cleanup()

    def test_add_and_list_tasks(self):
        self.km.add_task(self.board, "task A", "do A")
        self.km.add_task(self.board, "task B", "do B")
        self.assertEqual(len(self.km.list_tasks(self.board)), 2)

    def test_claim_returns_highest_priority(self):
        self.km.add_task(self.board, "low", "x", priority=1)
        self.km.add_task(self.board, "high", "y", priority=9)
        claimed = self.km.claim_task(self.board, "agent-1")
        self.assertEqual(claimed["title"], "high")
        self.assertEqual(claimed["status"], "claimed")

    def test_complete_task(self):
        self.km.add_task(self.board, "task", "do it")
        claimed = self.km.claim_task(self.board, "agent-1")
        self.km.complete_task(claimed["id"], "result text")
        self.assertEqual(self.km.board_status(self.board), {"done": 1})

    def test_fail_task_retries_then_fails(self):
        tid = self.km.add_task(self.board, "flaky", "do it")
        # default max_retries = 3 -> first 3 fails re-queue, 4th fails for good
        for _ in range(3):
            self.assertEqual(self.km.fail_task(tid, "boom"), "retry")
        self.assertEqual(self.km.fail_task(tid, "boom"), "failed")
        self.assertEqual(self.km.board_status(self.board), {"failed": 1})

    def test_block_task(self):
        tid = self.km.add_task(self.board, "needs human", "approve")
        self.km.block_task(tid, "waiting for approval")
        self.assertEqual(self.km.get_task(tid)["status"], "blocked")

    def test_claim_empty_board(self):
        self.assertIsNone(self.km.claim_task(self.board, "agent-1"))


if __name__ == "__main__":
    unittest.main()
