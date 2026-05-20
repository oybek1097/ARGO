"""Tests for the data/utility built-in tools — spec section 4.4."""

from __future__ import annotations

import base64
import hashlib
import os
import sqlite3
import tempfile
import unittest

from argo_brain.tools.builtin.data import (
    Base64Tool,
    DatetimeTool,
    HashTextTool,
    JSONQueryTool,
    SQLQueryTool,
    UUIDTool,
    data_tools,
)

_USER = "test-user"


class SQLQueryToolTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        # Create a temporary SQLite database with a table and rows.
        fd, self._db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        conn = sqlite3.connect(self._db_path)
        conn.execute("CREATE TABLE animals (id INTEGER, name TEXT)")
        conn.executemany(
            "INSERT INTO animals VALUES (?, ?)",
            [(1, "cat"), (2, "dog"), (3, "owl")],
        )
        conn.commit()
        conn.close()

    def tearDown(self) -> None:
        os.unlink(self._db_path)

    async def test_select_returns_rows(self) -> None:
        tool = SQLQueryTool()
        result = await tool.run(
            _USER, db_path=self._db_path, query="SELECT name FROM animals ORDER BY id"
        )
        self.assertTrue(result.success)
        self.assertIn("cat", result.content)
        self.assertIn("dog", result.content)
        self.assertIn("owl", result.content)
        self.assertEqual(result.metadata["row_count"], 3)

    async def test_non_select_is_rejected(self) -> None:
        tool = SQLQueryTool()
        result = await tool.run(
            _USER, db_path=self._db_path, query="DELETE FROM animals"
        )
        self.assertFalse(result.success)
        self.assertIn("SELECT", result.content)

    async def test_missing_database(self) -> None:
        tool = SQLQueryTool()
        result = await tool.run(
            _USER, db_path="/nonexistent/path.db", query="SELECT 1"
        )
        self.assertFalse(result.success)
        self.assertIn("not found", result.content)


class JSONQueryToolTest(unittest.IsolatedAsyncioTestCase):
    async def test_nested_extraction_with_list_index(self) -> None:
        tool = JSONQueryTool()
        doc = '{"a": {"b": [{"c": 42}, {"c": 99}]}}'
        result = await tool.run(_USER, json_text=doc, path="a.b.0.c")
        self.assertTrue(result.success)
        self.assertEqual(result.content, "42")

    async def test_list_index_second_element(self) -> None:
        tool = JSONQueryTool()
        doc = '{"a": {"b": [{"c": 42}, {"c": 99}]}}'
        result = await tool.run(_USER, json_text=doc, path="a.b.1.c")
        self.assertTrue(result.success)
        self.assertEqual(result.content, "99")

    async def test_missing_path_handled(self) -> None:
        tool = JSONQueryTool()
        result = await tool.run(_USER, json_text='{"a": 1}', path="x.y.z")
        self.assertFalse(result.success)
        self.assertIn("not found", result.content)

    async def test_invalid_json_handled(self) -> None:
        tool = JSONQueryTool()
        result = await tool.run(_USER, json_text="not json", path="a")
        self.assertFalse(result.success)
        self.assertIn("Invalid JSON", result.content)


class HashTextToolTest(unittest.IsolatedAsyncioTestCase):
    async def test_known_sha256(self) -> None:
        tool = HashTextTool()
        result = await tool.run(_USER, text="hello")
        self.assertTrue(result.success)
        # Known sha256 of "hello".
        self.assertEqual(result.content, hashlib.sha256(b"hello").hexdigest())
        self.assertEqual(
            result.content,
            "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824",
        )

    async def test_md5_algorithm(self) -> None:
        tool = HashTextTool()
        result = await tool.run(_USER, text="hello", algorithm="md5")
        self.assertTrue(result.success)
        self.assertEqual(result.content, hashlib.md5(b"hello").hexdigest())

    async def test_unknown_algorithm_handled(self) -> None:
        tool = HashTextTool()
        result = await tool.run(_USER, text="hello", algorithm="crc32")
        self.assertFalse(result.success)
        self.assertIn("Unknown algorithm", result.content)


class Base64ToolTest(unittest.IsolatedAsyncioTestCase):
    async def test_round_trip(self) -> None:
        tool = Base64Tool()
        original = "ARGO Agent — utf8 ✓"
        encoded = await tool.run(_USER, text=original, mode="encode")
        self.assertTrue(encoded.success)
        self.assertEqual(
            encoded.content,
            base64.b64encode(original.encode("utf-8")).decode("ascii"),
        )
        decoded = await tool.run(_USER, text=encoded.content, mode="decode")
        self.assertTrue(decoded.success)
        self.assertEqual(decoded.content, original)

    async def test_invalid_decode_handled(self) -> None:
        tool = Base64Tool()
        result = await tool.run(_USER, text="!!!notbase64!!!", mode="decode")
        self.assertFalse(result.success)


class UUIDToolTest(unittest.IsolatedAsyncioTestCase):
    async def test_returns_36_char_string(self) -> None:
        tool = UUIDTool()
        result = await tool.run(_USER)
        self.assertTrue(result.success)
        self.assertEqual(len(result.content), 36)

    async def test_two_calls_differ(self) -> None:
        tool = UUIDTool()
        first = await tool.run(_USER)
        second = await tool.run(_USER)
        self.assertNotEqual(first.content, second.content)


class DatetimeToolTest(unittest.IsolatedAsyncioTestCase):
    async def test_returns_iso_string(self) -> None:
        tool = DatetimeTool()
        result = await tool.run(_USER)
        self.assertTrue(result.success)
        # The ISO string must be parseable back into a datetime.
        from datetime import datetime

        parsed = datetime.fromisoformat(result.content)
        self.assertIsNotNone(parsed)

    async def test_offset_shifts_result(self) -> None:
        tool = DatetimeTool()
        from datetime import datetime

        utc = await tool.run(_USER, timezone_offset_hours=0)
        plus5 = await tool.run(_USER, timezone_offset_hours=5)
        utc_dt = datetime.fromisoformat(utc.content)
        plus5_dt = datetime.fromisoformat(plus5.content)
        # The two instants are nearly equal but carry different UTC offsets.
        self.assertEqual(plus5.metadata["offset_hours"], 5)
        self.assertNotEqual(utc_dt.utcoffset(), plus5_dt.utcoffset())


class DataToolsRegistryTest(unittest.TestCase):
    def test_data_tools_returns_six(self) -> None:
        tools = data_tools()
        self.assertEqual(len(tools), 6)
        names = {t.name for t in tools}
        self.assertEqual(
            names,
            {
                "sql_query",
                "json_query",
                "hash_text",
                "base64_transform",
                "uuid_generate",
                "datetime_now",
            },
        )


if __name__ == "__main__":
    unittest.main()
