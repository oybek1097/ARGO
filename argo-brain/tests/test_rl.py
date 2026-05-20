"""Unit tests for the RL / trajectory subsystem."""

from __future__ import annotations

import json
import os
import tempfile
import unittest

from argo_brain.rl import TrajectoryCollector


class TrajectoryCollectorTest(unittest.TestCase):
    """Tests for `TrajectoryCollector` recording and export."""

    def setUp(self) -> None:
        self.collector = TrajectoryCollector()
        # A temporary directory for JSONL output, removed after each test.
        self._tmpdir = tempfile.TemporaryDirectory()
        self.tmpdir = self._tmpdir.name

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def _populate(self) -> None:
        """Records a small mixed set of trajectories."""
        self.collector.record(
            "Hello", "Hi there", [], "gpt-x", True, duration_ms=12
        )
        self.collector.record(
            "What time is it?", "It is noon.", ["clock"], "gpt-x", True,
            duration_ms=30,
        )
        self.collector.record(
            "Crash please", "error", ["bad_tool"], "gpt-x", False,
        )

    def test_count_starts_empty(self) -> None:
        self.assertEqual(self.collector.count(), 0)
        self.assertEqual(self.collector.all(), [])

    def test_record_increments_count(self) -> None:
        self._populate()
        self.assertEqual(self.collector.count(), 3)

    def test_all_returns_recorded_fields(self) -> None:
        self.collector.record(
            "Q", "A", ["t1", "t2"], "model-a", True, duration_ms=99
        )
        traj = self.collector.all()[0]
        self.assertEqual(traj["user_input"], "Q")
        self.assertEqual(traj["output"], "A")
        self.assertEqual(traj["tools_used"], ["t1", "t2"])
        self.assertEqual(traj["model"], "model-a")
        self.assertTrue(traj["success"])
        self.assertEqual(traj["duration_ms"], 99)

    def test_all_returns_copy(self) -> None:
        # Mutating the returned list must not affect the collector.
        self._populate()
        snapshot = self.collector.all()
        snapshot.clear()
        self.assertEqual(self.collector.count(), 3)

    def test_record_copies_tools_list(self) -> None:
        # Mutating the caller's list after record() must not change storage.
        tools = ["a"]
        self.collector.record("u", "o", tools, "m", True)
        tools.append("b")
        self.assertEqual(self.collector.all()[0]["tools_used"], ["a"])

    def test_export_sharegpt_structure(self) -> None:
        self.collector.record("Hello", "Hi", [], "m", True)
        rows = self.collector.export_sharegpt()
        self.assertEqual(len(rows), 1)
        convo = rows[0]["conversations"]
        self.assertEqual(convo[0], {"from": "human", "value": "Hello"})
        self.assertEqual(convo[1], {"from": "gpt", "value": "Hi"})

    def test_export_sft_structure(self) -> None:
        self.collector.record("Hello", "Hi", [], "m", True)
        rows = self.collector.export_sft()
        self.assertEqual(rows, [{"instruction": "Hello", "output": "Hi"}])

    def test_only_successful_filter(self) -> None:
        self._populate()
        self.assertEqual(len(self.collector.successful()), 2)
        self.assertEqual(
            len(self.collector.export_sharegpt(only_successful=True)), 2
        )
        self.assertEqual(
            len(self.collector.export_sft(only_successful=True)), 2
        )
        # Without the filter all three are exported.
        self.assertEqual(len(self.collector.export_sharegpt()), 3)

    def test_export_jsonl_sharegpt(self) -> None:
        self._populate()
        path = os.path.join(self.tmpdir, "out.jsonl")
        rows = self.collector.export_jsonl(path, fmt="sharegpt")
        self.assertEqual(rows, 3)

        with open(path, encoding="utf-8") as fh:
            lines = [line for line in fh.read().splitlines() if line]
        self.assertEqual(len(lines), 3)
        for line in lines:
            obj = json.loads(line)
            self.assertIn("conversations", obj)
            self.assertEqual(len(obj["conversations"]), 2)

    def test_export_jsonl_sft(self) -> None:
        self._populate()
        path = os.path.join(self.tmpdir, "sft.jsonl")
        rows = self.collector.export_jsonl(path, fmt="sft")
        self.assertEqual(rows, 3)

        with open(path, encoding="utf-8") as fh:
            parsed = [json.loads(line) for line in fh if line.strip()]
        self.assertEqual(len(parsed), 3)
        for obj in parsed:
            self.assertIn("instruction", obj)
            self.assertIn("output", obj)

    def test_export_jsonl_only_successful(self) -> None:
        self._populate()
        path = os.path.join(self.tmpdir, "ok.jsonl")
        rows = self.collector.export_jsonl(
            path, fmt="sft", only_successful=True
        )
        self.assertEqual(rows, 2)
        with open(path, encoding="utf-8") as fh:
            parsed = [json.loads(line) for line in fh if line.strip()]
        self.assertEqual(len(parsed), 2)

    def test_export_jsonl_bad_format(self) -> None:
        with self.assertRaises(ValueError):
            self.collector.export_jsonl(
                os.path.join(self.tmpdir, "x.jsonl"), fmt="nope"
            )

    def test_export_jsonl_creates_parent_dir(self) -> None:
        self.collector.record("u", "o", [], "m", True)
        nested = os.path.join(self.tmpdir, "deep", "nested", "t.jsonl")
        rows = self.collector.export_jsonl(nested, fmt="sft")
        self.assertEqual(rows, 1)
        self.assertTrue(os.path.exists(nested))

    def test_clear_empties_collection(self) -> None:
        self._populate()
        self.assertEqual(self.collector.count(), 3)
        self.collector.clear()
        self.assertEqual(self.collector.count(), 0)
        self.assertEqual(self.collector.all(), [])
        self.assertEqual(self.collector.export_sharegpt(), [])

    def test_unicode_roundtrip_in_jsonl(self) -> None:
        # Non-ASCII content must survive the JSONL round trip.
        self.collector.record("Привет", "Салом", [], "m", True)
        path = os.path.join(self.tmpdir, "uni.jsonl")
        self.collector.export_jsonl(path, fmt="sft")
        with open(path, encoding="utf-8") as fh:
            obj = json.loads(fh.readline())
        self.assertEqual(obj["instruction"], "Привет")
        self.assertEqual(obj["output"], "Салом")


if __name__ == "__main__":
    unittest.main()
