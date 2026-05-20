"""Tests for the format and archive built-in tools — spec section 4.4.

Covers happy and error paths for every tool in
`argo_brain.tools.builtin.format`, including a tar create/extract
round-trip, a blocked path-traversal attempt, unit conversions and
malformed-input handling.
"""

from __future__ import annotations

import os
import tarfile
import tempfile
import unittest
from pathlib import Path

from argo_brain.tools.builtin.format import (
    HashFileTool,
    INIParseTool,
    TarCreateTool,
    TarExtractTool,
    UnitConvertTool,
    XMLParseTool,
    format_tools,
)

_USER = "test-user"


class TestXMLParseTool(unittest.IsolatedAsyncioTestCase):
    """Happy and error paths for `xml_parse`."""

    async def test_parse_valid_xml(self) -> None:
        tool = XMLParseTool()
        xml = "<root><child name='a'>hello</child><child>bye</child></root>"
        result = await tool(_USER, text=xml)
        self.assertTrue(result.success)
        self.assertIn("Root: <root>", result.content)
        self.assertEqual(result.metadata["root"], "root")
        self.assertEqual(result.metadata["elements"], 3)

    async def test_malformed_xml(self) -> None:
        tool = XMLParseTool()
        result = await tool(_USER, text="<root><child></root>")
        self.assertFalse(result.success)
        self.assertIn("Could not parse XML", result.content)

    async def test_empty_xml(self) -> None:
        tool = XMLParseTool()
        result = await tool(_USER, text="   ")
        self.assertFalse(result.success)
        self.assertIn("empty", result.content)


class TestINIParseTool(unittest.IsolatedAsyncioTestCase):
    """Happy and error paths for `ini_parse`."""

    async def test_parse_valid_ini(self) -> None:
        tool = INIParseTool()
        ini = "[server]\nhost = localhost\nport = 8080\n[db]\nname = argo\n"
        result = await tool(_USER, text=ini)
        self.assertTrue(result.success)
        self.assertIn("[server]", result.content)
        self.assertIn("host = localhost", result.content)
        self.assertEqual(result.metadata["sections"], 2)
        self.assertEqual(result.metadata["keys"], 3)

    async def test_malformed_ini(self) -> None:
        tool = INIParseTool()
        # A line outside any section header is invalid INI.
        result = await tool(_USER, text="orphan = 1\n[ok]\nk = v\n")
        self.assertFalse(result.success)
        self.assertIn("Could not parse INI", result.content)

    async def test_empty_ini(self) -> None:
        tool = INIParseTool()
        result = await tool(_USER, text="")
        self.assertFalse(result.success)


class TestTarTools(unittest.IsolatedAsyncioTestCase):
    """Round-trip and guard tests for `tar_create` / `tar_extract`."""

    async def test_create_and_extract_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "hello.txt"
            src.write_text("round-trip content")
            archive = Path(tmp) / "bundle.tar.gz"

            created = await TarCreateTool()(
                _USER, archive_path=str(archive), paths=[str(src)]
            )
            self.assertTrue(created.success)
            self.assertTrue(archive.is_file())
            self.assertEqual(created.metadata["files"], 1)

            dest = Path(tmp) / "out"
            extracted = await TarExtractTool()(
                _USER, archive_path=str(archive), dest_dir=str(dest)
            )
            self.assertTrue(extracted.success)
            self.assertEqual(
                (dest / "hello.txt").read_text(), "round-trip content"
            )

    async def test_create_missing_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / "bundle.tar.gz"
            result = await TarCreateTool()(
                _USER, archive_path=str(archive), paths=["/no/such/file"]
            )
            self.assertFalse(result.success)
            self.assertIn("File not found", result.content)

    async def test_create_no_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = await TarCreateTool()(
                _USER, archive_path=str(Path(tmp) / "a.tar.gz"), paths=[]
            )
            self.assertFalse(result.success)

    async def test_extract_missing_archive(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = await TarExtractTool()(
                _USER,
                archive_path=str(Path(tmp) / "nope.tar.gz"),
                dest_dir=str(Path(tmp) / "out"),
            )
            self.assertFalse(result.success)
            self.assertIn("not found", result.content.lower())

    async def test_extract_blocks_path_traversal(self) -> None:
        # Hand-craft a malicious archive whose member escapes the dest dir.
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / "evil.tar.gz"
            payload = Path(tmp) / "payload.txt"
            payload.write_text("pwned")
            with tarfile.open(archive, "w:gz") as tar:
                info = tarfile.TarInfo(name="../escaped.txt")
                data = payload.read_bytes()
                info.size = len(data)
                with payload.open("rb") as fh:
                    tar.addfile(info, fh)

            dest = Path(tmp) / "out"
            result = await TarExtractTool()(
                _USER, archive_path=str(archive), dest_dir=str(dest)
            )
            self.assertFalse(result.success)
            self.assertIn("Unsafe path", result.content)
            # The traversal target must not have been written.
            self.assertFalse((Path(tmp) / "escaped.txt").exists())


class TestUnitConvertTool(unittest.IsolatedAsyncioTestCase):
    """Conversion checks for `unit_convert`."""

    async def test_km_to_m(self) -> None:
        result = await UnitConvertTool()(
            _USER, value=1, from_unit="km", to_unit="m"
        )
        self.assertTrue(result.success)
        self.assertAlmostEqual(result.metadata["result"], 1000.0)

    async def test_celsius_to_fahrenheit(self) -> None:
        result = await UnitConvertTool()(
            _USER, value=0, from_unit="C", to_unit="F"
        )
        self.assertTrue(result.success)
        self.assertAlmostEqual(result.metadata["result"], 32.0)

    async def test_kg_to_lb(self) -> None:
        result = await UnitConvertTool()(
            _USER, value=1, from_unit="kg", to_unit="lb"
        )
        self.assertTrue(result.success)
        self.assertAlmostEqual(result.metadata["result"], 2.2046226218, places=6)

    async def test_incompatible_units(self) -> None:
        # Length and mass are different measurement families.
        result = await UnitConvertTool()(
            _USER, value=1, from_unit="m", to_unit="kg"
        )
        self.assertFalse(result.success)
        self.assertIn("Cannot convert", result.content)

    async def test_unknown_unit(self) -> None:
        result = await UnitConvertTool()(
            _USER, value=1, from_unit="parsec", to_unit="m"
        )
        self.assertFalse(result.success)


class TestHashFileTool(unittest.IsolatedAsyncioTestCase):
    """Happy and error paths for `hash_file`."""

    async def test_hash_known_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "data.txt"
            target.write_text("abc")
            result = await HashFileTool()(_USER, path=str(target))
            self.assertTrue(result.success)
            # SHA-256 of the bytes "abc" is a well-known constant.
            self.assertEqual(
                result.metadata["sha256"],
                "ba7816bf8f01cfea414140de5dae2223"
                "b00361a396177a9cb410ff61f20015ad",
            )

    async def test_hash_missing_file(self) -> None:
        result = await HashFileTool()(_USER, path="/no/such/file.bin")
        self.assertFalse(result.success)
        self.assertIn("File not found", result.content)


class TestFormatToolsExporter(unittest.IsolatedAsyncioTestCase):
    """Sanity checks for the `format_tools()` exporter."""

    async def test_exporter_returns_all_tools(self) -> None:
        tools = format_tools()
        names = {t.name for t in tools}
        self.assertEqual(
            names,
            {
                "xml_parse",
                "ini_parse",
                "tar_create",
                "tar_extract",
                "unit_convert",
                "hash_file",
            },
        )

    async def test_dangerous_flags(self) -> None:
        # tar tools mutate the filesystem and must be flagged dangerous.
        by_name = {t.name: t for t in format_tools()}
        self.assertTrue(by_name["tar_create"].dangerous)
        self.assertTrue(by_name["tar_extract"].dangerous)
        self.assertFalse(by_name["unit_convert"].dangerous)


if __name__ == "__main__":
    unittest.main()
