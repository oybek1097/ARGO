"""Tests for the checkpoint and handoff subsystems."""

import os
import tempfile
import unittest

from argo_brain.checkpoint import CheckpointManager
from argo_brain.handoff import HandoffManager


def _write(path: str, content: str) -> None:
    """Write ``content`` to ``path`` (helper for building temp source files)."""
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)


def _read(path: str) -> str:
    """Read and return the text content of ``path``."""
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


class TestCheckpointManager(unittest.TestCase):
    """Exercise CheckpointManager create/list/restore/delete."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = self._tmp.name
        self.base_dir = os.path.join(self.root, "checkpoints")
        self.src_dir = os.path.join(self.root, "src")
        os.makedirs(self.src_dir, exist_ok=True)
        self.file_a = os.path.join(self.src_dir, "a.txt")
        self.file_b = os.path.join(self.src_dir, "b.txt")
        _write(self.file_a, "alpha contents")
        _write(self.file_b, "beta contents")
        self.mgr = CheckpointManager(self.base_dir)

    def tearDown(self):
        self._tmp.cleanup()

    def test_base_dir_created(self):
        self.assertTrue(os.path.isdir(self.base_dir))

    def test_create_returns_id(self):
        cp_id = self.mgr.create("first", [self.file_a, self.file_b])
        self.assertIsInstance(cp_id, str)
        self.assertTrue(cp_id)

    def test_create_makes_checkpoint_dir(self):
        cp_id = self.mgr.create("first", [self.file_a])
        self.assertTrue(os.path.isdir(os.path.join(self.base_dir, cp_id)))

    def test_list_shows_checkpoint(self):
        cp_id = self.mgr.create("snap", [self.file_a, self.file_b])
        entries = self.mgr.list()
        self.assertEqual(len(entries), 1)
        entry = entries[0]
        self.assertEqual(entry["id"], cp_id)
        self.assertEqual(entry["label"], "snap")
        self.assertEqual(entry["file_count"], 2)
        self.assertTrue(entry["created_at"])

    def test_list_empty_initially(self):
        self.assertEqual(self.mgr.list(), [])

    def test_list_multiple(self):
        self.mgr.create("one", [self.file_a])
        self.mgr.create("two", [self.file_b])
        self.assertEqual(len(self.mgr.list()), 2)

    def test_create_skips_missing_files(self):
        missing = os.path.join(self.src_dir, "nope.txt")
        cp_id = self.mgr.create("partial", [self.file_a, missing])
        entry = self.mgr.list()[0]
        self.assertEqual(entry["id"], cp_id)
        self.assertEqual(entry["file_count"], 1)

    def test_restore_returns_count(self):
        cp_id = self.mgr.create("snap", [self.file_a, self.file_b])
        target = os.path.join(self.root, "restore_count")
        self.assertEqual(self.mgr.restore(cp_id, target), 2)

    def test_restore_verifies_contents(self):
        cp_id = self.mgr.create("snap", [self.file_a, self.file_b])
        target = os.path.join(self.root, "restored")
        self.mgr.restore(cp_id, target)
        self.assertEqual(_read(os.path.join(target, "a.txt")), "alpha contents")
        self.assertEqual(_read(os.path.join(target, "b.txt")), "beta contents")

    def test_restore_unaffected_by_later_edits(self):
        cp_id = self.mgr.create("snap", [self.file_a])
        # Mutate the original after the checkpoint was taken.
        _write(self.file_a, "mutated")
        target = os.path.join(self.root, "rollback")
        self.mgr.restore(cp_id, target)
        self.assertEqual(_read(os.path.join(target, "a.txt")), "alpha contents")

    def test_restore_unknown_raises(self):
        with self.assertRaises(KeyError):
            self.mgr.restore("does-not-exist", os.path.join(self.root, "x"))

    def test_delete_removes_checkpoint(self):
        cp_id = self.mgr.create("snap", [self.file_a])
        self.assertTrue(self.mgr.delete(cp_id))
        self.assertEqual(self.mgr.list(), [])

    def test_delete_unknown_returns_false(self):
        self.assertFalse(self.mgr.delete("does-not-exist"))


class TestHandoffManager(unittest.TestCase):
    """Exercise HandoffManager create/pending/claim/get."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self._tmp.name, "handoff.db")
        self.mgr = HandoffManager(self.db_path)

    def tearDown(self):
        self._tmp.cleanup()

    def test_create_returns_id(self):
        ticket_id = self.mgr.create("alice", "bob", "sess-1", "ship it", [])
        self.assertIsInstance(ticket_id, str)
        self.assertTrue(ticket_id)

    def test_pending_shows_ticket(self):
        ticket_id = self.mgr.create("alice", "bob", "sess-1", "ship it", [])
        pend = self.mgr.pending("bob")
        self.assertEqual(len(pend), 1)
        self.assertEqual(pend[0]["id"], ticket_id)
        self.assertEqual(pend[0]["goal"], "ship it")

    def test_pending_empty_for_other_target(self):
        self.mgr.create("alice", "bob", "sess-1", "ship it", [])
        self.assertEqual(self.mgr.pending("carol"), [])

    def test_pending_lists_multiple(self):
        self.mgr.create("alice", "bob", "s1", "g1", [])
        self.mgr.create("alice", "bob", "s2", "g2", [])
        self.assertEqual(len(self.mgr.pending("bob")), 2)

    def test_claim_returns_data(self):
        history = [{"role": "user", "text": "hi"}]
        ticket_id = self.mgr.create("alice", "bob", "sess-1", "ship it", history)
        data = self.mgr.claim(ticket_id, "bob")
        self.assertIsNotNone(data)
        self.assertEqual(data["id"], ticket_id)
        self.assertEqual(data["status"], "claimed")
        self.assertEqual(data["claimed_by"], "bob")
        self.assertEqual(data["history_snapshot"], history)

    def test_claim_removes_from_pending(self):
        ticket_id = self.mgr.create("alice", "bob", "sess-1", "ship it", [])
        self.mgr.claim(ticket_id, "bob")
        self.assertEqual(self.mgr.pending("bob"), [])

    def test_claim_twice_returns_none(self):
        ticket_id = self.mgr.create("alice", "bob", "sess-1", "ship it", [])
        self.assertIsNotNone(self.mgr.claim(ticket_id, "bob"))
        self.assertIsNone(self.mgr.claim(ticket_id, "carol"))

    def test_claim_unknown_returns_none(self):
        self.assertIsNone(self.mgr.claim("no-such-ticket", "bob"))

    def test_get_returns_ticket(self):
        ticket_id = self.mgr.create("alice", "bob", "sess-1", "ship it", [])
        data = self.mgr.get(ticket_id)
        self.assertIsNotNone(data)
        self.assertEqual(data["from_user"], "alice")
        self.assertEqual(data["to_target"], "bob")
        self.assertEqual(data["session_id"], "sess-1")
        self.assertEqual(data["status"], "pending")

    def test_get_unknown_returns_none(self):
        self.assertIsNone(self.mgr.get("no-such-ticket"))

    def test_get_after_claim_reflects_status(self):
        ticket_id = self.mgr.create("alice", "bob", "sess-1", "ship it", [])
        self.mgr.claim(ticket_id, "bob")
        data = self.mgr.get(ticket_id)
        self.assertEqual(data["status"], "claimed")
        self.assertEqual(data["claimed_by"], "bob")

    def test_history_snapshot_roundtrip(self):
        history = [{"role": "assistant", "text": "done"}, {"n": 42}]
        ticket_id = self.mgr.create("alice", "bob", "s", "g", history)
        self.assertEqual(self.mgr.get(ticket_id)["history_snapshot"], history)

    def test_persists_across_instances(self):
        ticket_id = self.mgr.create("alice", "bob", "sess-1", "ship it", [])
        reopened = HandoffManager(self.db_path)
        self.assertIsNotNone(reopened.get(ticket_id))


if __name__ == "__main__":
    unittest.main()
