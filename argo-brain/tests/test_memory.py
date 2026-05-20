"""Memory subsystem tests."""

import tempfile
import unittest
from pathlib import Path

from argo_brain.memory import MemoryManager
from argo_brain.memory.working import WorkingMemory


class TestWorkingMemory(unittest.TestCase):
    def test_add_and_history(self):
        wm = WorkingMemory(maxlen=5)
        for i in range(3):
            wm.add("u1", "user", f"msg-{i}")
        self.assertEqual(len(wm.history("u1")), 3)

    def test_maxlen_eviction(self):
        wm = WorkingMemory(maxlen=3)
        for i in range(10):
            wm.add("u1", "user", f"msg-{i}")
        hist = wm.history("u1")
        self.assertEqual(len(hist), 3)
        self.assertEqual(hist[-1]["content"], "msg-9")

    def test_per_user_isolation(self):
        wm = WorkingMemory()
        wm.add("u1", "user", "a")
        wm.add("u2", "user", "b")
        self.assertEqual(len(wm.history("u1")), 1)
        self.assertEqual(len(wm.history("u2")), 1)


class TestMemoryManager(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.mem = MemoryManager(Path(self._tmp.name) / "test.db")

    async def asyncTearDown(self):
        self.mem.close()
        self._tmp.cleanup()

    async def test_add_and_history(self):
        await self.mem.add("u1", "user", "Salom dunyo", language="uz")
        await self.mem.add("u1", "assistant", "Salom!", language="uz")
        hist = await self.mem.history("u1")
        self.assertEqual(len(hist), 2)
        self.assertEqual(hist[0]["content"], "Salom dunyo")

    async def test_fts_search(self):
        await self.mem.add("u1", "user", "vault sozlamalarini tekshir")
        await self.mem.add("u1", "user", "kubernetes klasterga deploy qil")
        hits = await self.mem.search("u1", "vault")
        self.assertEqual(len(hits), 1)
        self.assertIn("vault", hits[0]["content"])

    async def test_search_user_scoped(self):
        await self.mem.add("u1", "user", "maxfiy ma'lumot")
        await self.mem.add("u2", "user", "maxfiy ma'lumot")
        hits = await self.mem.search("u1", "maxfiy")
        self.assertEqual(len(hits), 1)

    async def test_ensure_profile(self):
        prof = await self.mem.ensure_profile("u1", language="uz")
        self.assertEqual(prof["language"], "uz")
        # the second call must not create a new profile
        prof2 = await self.mem.ensure_profile("u1", language="uz")
        self.assertEqual(prof2["user_id"], "u1")


if __name__ == "__main__":
    unittest.main()
