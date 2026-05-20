"""Tests for the text and archive built-in tools — spec section 4.4."""

from __future__ import annotations

import unittest
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory

from argo_brain.tools.builtin.text import (
    CSVParseTool,
    DiffTextTool,
    RegexExtractTool,
    TemplateRenderTool,
    ZipCreateTool,
    ZipExtractTool,
    text_tools,
)


class DiffTextToolTest(unittest.IsolatedAsyncioTestCase):
    async def test_diff_happy_path(self) -> None:
        tool = DiffTextTool()
        result = await tool.run("u", old="line one\n", new="line two\n")
        self.assertTrue(result.success)
        self.assertIn("-line one", result.content)
        self.assertIn("+line two", result.content)

    async def test_diff_identical_inputs(self) -> None:
        # Equal inputs are an "error path" of sorts: there is nothing to show.
        tool = DiffTextTool()
        result = await tool.run("u", old="same\n", new="same\n")
        self.assertTrue(result.success)
        self.assertEqual(result.content, "(no differences)")


class CSVParseToolTest(unittest.IsolatedAsyncioTestCase):
    async def test_csv_happy_path(self) -> None:
        tool = CSVParseTool()
        result = await tool.run("u", text="name,age\nAlice,30\nBob,25\n")
        self.assertTrue(result.success)
        self.assertIn("Columns (2): name, age", result.content)
        self.assertEqual(result.metadata["rows"], 2)

    async def test_csv_empty_input(self) -> None:
        tool = CSVParseTool()
        result = await tool.run("u", text="   ")
        self.assertFalse(result.success)
        self.assertIn("empty", result.content)

    async def test_csv_bad_delimiter(self) -> None:
        tool = CSVParseTool()
        result = await tool.run("u", text="a,b\n1,2\n", delimiter=",,")
        self.assertFalse(result.success)
        self.assertIn("one character", result.content)


class ZipRoundTripTest(unittest.IsolatedAsyncioTestCase):
    async def test_zip_create_and_extract_round_trip(self) -> None:
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            f1 = tmp_path / "a.txt"
            f2 = tmp_path / "b.txt"
            f1.write_text("hello")
            f2.write_text("world")
            archive = tmp_path / "out.zip"

            create = ZipCreateTool()
            created = await create.run(
                "u", archive_path=str(archive), paths=[str(f1), str(f2)]
            )
            self.assertTrue(created.success)
            self.assertTrue(archive.is_file())
            self.assertEqual(created.metadata["files"], 2)

            dest = tmp_path / "extracted"
            extract = ZipExtractTool()
            extracted = await extract.run(
                "u", archive_path=str(archive), dest_dir=str(dest)
            )
            self.assertTrue(extracted.success)
            self.assertEqual((dest / "a.txt").read_text(), "hello")
            self.assertEqual((dest / "b.txt").read_text(), "world")

    async def test_zip_create_missing_file(self) -> None:
        with TemporaryDirectory() as tmp:
            tool = ZipCreateTool()
            result = await tool.run(
                "u",
                archive_path=str(Path(tmp) / "out.zip"),
                paths=[str(Path(tmp) / "does_not_exist.txt")],
            )
            self.assertFalse(result.success)
            self.assertIn("not found", result.content)

    async def test_zip_extract_missing_archive(self) -> None:
        with TemporaryDirectory() as tmp:
            tool = ZipExtractTool()
            result = await tool.run(
                "u",
                archive_path=str(Path(tmp) / "nope.zip"),
                dest_dir=str(Path(tmp) / "dest"),
            )
            self.assertFalse(result.success)
            self.assertIn("not found", result.content)

    async def test_zip_extract_blocks_path_traversal(self) -> None:
        # Hand-craft a malicious archive whose member escapes the dest dir.
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            archive = tmp_path / "evil.zip"
            with zipfile.ZipFile(archive, "w") as zf:
                zf.writestr("../escaped.txt", "pwned")

            tool = ZipExtractTool()
            result = await tool.run(
                "u",
                archive_path=str(archive),
                dest_dir=str(tmp_path / "safe"),
            )
            self.assertFalse(result.success)
            self.assertIn("Unsafe path", result.content)
            self.assertFalse((tmp_path / "escaped.txt").exists())


class RegexExtractToolTest(unittest.IsolatedAsyncioTestCase):
    async def test_regex_happy_path(self) -> None:
        tool = RegexExtractTool()
        result = await tool.run("u", pattern=r"\d+", text="a1 b22 c333")
        self.assertTrue(result.success)
        self.assertEqual(result.metadata["count"], 3)
        self.assertIn("333", result.content)

    async def test_regex_no_matches(self) -> None:
        tool = RegexExtractTool()
        result = await tool.run("u", pattern=r"z+", text="abc")
        self.assertTrue(result.success)
        self.assertEqual(result.metadata["count"], 0)

    async def test_regex_invalid_pattern(self) -> None:
        tool = RegexExtractTool()
        result = await tool.run("u", pattern=r"(unclosed", text="abc")
        self.assertFalse(result.success)
        self.assertIn("Invalid regex", result.content)


class TemplateRenderToolTest(unittest.IsolatedAsyncioTestCase):
    async def test_template_happy_path(self) -> None:
        tool = TemplateRenderTool()
        result = await tool.run(
            "u", template="Hello $name!", variables={"name": "ARGO"}
        )
        self.assertTrue(result.success)
        self.assertEqual(result.content, "Hello ARGO!")

    async def test_template_missing_variable(self) -> None:
        tool = TemplateRenderTool()
        result = await tool.run("u", template="Hi $missing", variables={})
        self.assertFalse(result.success)
        self.assertIn("Missing template variable", result.content)

    async def test_template_invalid_syntax(self) -> None:
        # A lone '$' followed by an invalid identifier triggers a ValueError.
        tool = TemplateRenderTool()
        result = await tool.run("u", template="cost is $", variables={})
        self.assertFalse(result.success)
        self.assertIn("Invalid template", result.content)


class TextToolsExportTest(unittest.TestCase):
    def test_text_tools_returns_all_six(self) -> None:
        tools = text_tools()
        self.assertEqual(len(tools), 6)
        names = {t.name for t in tools}
        self.assertEqual(
            names,
            {
                "diff_text",
                "csv_parse",
                "zip_create",
                "zip_extract",
                "regex_extract",
                "template_render",
            },
        )

    def test_archive_tools_are_marked_dangerous(self) -> None:
        by_name = {t.name: t for t in text_tools()}
        self.assertTrue(by_name["zip_create"].dangerous)
        self.assertTrue(by_name["zip_extract"].dangerous)
        self.assertFalse(by_name["diff_text"].dangerous)


if __name__ == "__main__":
    unittest.main()
