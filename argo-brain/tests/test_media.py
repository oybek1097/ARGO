"""Media / vision tool tests — spec sections 4.4 and 4.12.

Covers the API-backed adapter tools (which must fail cleanly without
credentials) and the fully functional, stdlib-only ImageInfoTool.
"""

import os
import struct
import tempfile
import unittest
import zlib
from pathlib import Path

from argo_brain.tools.builtin.media import (
    ImageDescribeTool,
    ImageGenerateTool,
    ImageInfoTool,
    SpeechToTextTool,
    TextToSpeechTool,
    media_tools,
)

# Env vars used by the adapter tools — cleared before each API-tool test.
_API_ENV_KEYS = (
    "ARGO_VISION_API_KEY",
    "ARGO_IMAGE_API_KEY",
    "ARGO_TTS_API_KEY",
    "ARGO_STT_API_KEY",
)


def _make_png(width: int, height: int) -> bytes:
    """Build a minimal but valid PNG: signature + IHDR + IDAT + IEND."""
    sig = b"\x89PNG\r\n\x1a\n"

    def _chunk(tag: bytes, payload: bytes) -> bytes:
        return (
            struct.pack(">I", len(payload))
            + tag
            + payload
            + struct.pack(">I", zlib.crc32(tag + payload) & 0xFFFFFFFF)
        )

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    idat = zlib.compress(b"\x00" * (width * 3 + 1) * height)
    return sig + _chunk(b"IHDR", ihdr) + _chunk(b"IDAT", idat) + \
        _chunk(b"IEND", b"")


def _make_gif(width: int, height: int) -> bytes:
    """Build a minimal GIF89a header with the given logical screen size."""
    return b"GIF89a" + struct.pack("<HH", width, height) + b"\x00\x00\x00"


class TestApiBackedTools(unittest.IsolatedAsyncioTestCase):
    """Adapter tools must fail cleanly (no raise) without an API key."""

    def setUp(self):
        # Ensure no credentials leak in from the surrounding environment.
        self._saved = {k: os.environ.pop(k, None) for k in _API_ENV_KEYS}

    def tearDown(self):
        for k, v in self._saved.items():
            if v is not None:
                os.environ[k] = v

    async def test_image_describe_no_key(self):
        r = await ImageDescribeTool()("u1", image_url="http://x/a.png")
        self.assertFalse(r.success)
        self.assertIn("No API key configured", r.content)

    async def test_image_generate_no_key(self):
        r = await ImageGenerateTool()("u1", prompt="a red cube")
        self.assertFalse(r.success)
        self.assertIn("No API key configured", r.content)

    async def test_text_to_speech_no_key(self):
        r = await TextToSpeechTool()("u1", text="hello world")
        self.assertFalse(r.success)
        self.assertIn("No API key configured", r.content)

    async def test_speech_to_text_no_key(self):
        r = await SpeechToTextTool()("u1", audio_url="http://x/a.mp3")
        self.assertFalse(r.success)
        self.assertIn("No API key configured", r.content)

    async def test_no_key_does_not_raise(self):
        # __call__ must return a ToolResult, never propagate an exception.
        for tool in (ImageDescribeTool(), ImageGenerateTool(),
                     TextToSpeechTool(), SpeechToTextTool()):
            r = await tool("u1")
            self.assertFalse(r.success)
            self.assertEqual(r.metadata.get("reason"), "no_api_key")


class TestImageInfoTool(unittest.IsolatedAsyncioTestCase):
    """ImageInfoTool is fully functional and needs no API."""

    async def test_png_dimensions(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "tiny.png"
            p.write_bytes(_make_png(7, 3))
            r = await ImageInfoTool()("u1", path=str(p))
            self.assertTrue(r.success)
            self.assertEqual(r.metadata["format"], "PNG")
            self.assertEqual(r.metadata["width"], 7)
            self.assertEqual(r.metadata["height"], 3)
            self.assertIn("7x3", r.content)

    async def test_gif_dimensions(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "tiny.gif"
            p.write_bytes(_make_gif(12, 5))
            r = await ImageInfoTool()("u1", path=str(p))
            self.assertTrue(r.success)
            self.assertEqual(r.metadata["format"], "GIF")
            self.assertEqual(r.metadata["width"], 12)
            self.assertEqual(r.metadata["height"], 5)

    async def test_non_image_handled_gracefully(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "notes.txt"
            p.write_bytes(b"this is just plain text, not an image")
            r = await ImageInfoTool()("u1", path=str(p))
            self.assertFalse(r.success)
            self.assertIn("not a recognized", r.content)
            self.assertEqual(r.metadata.get("reason"), "unsupported_format")

    async def test_missing_file_handled_gracefully(self):
        r = await ImageInfoTool()("u1", path="/no/such/file.png")
        self.assertFalse(r.success)
        self.assertIn("Could not read file", r.content)

    async def test_empty_path_handled_gracefully(self):
        r = await ImageInfoTool()("u1", path="")
        self.assertFalse(r.success)
        self.assertIn("No file path", r.content)


class TestMediaToolset(unittest.IsolatedAsyncioTestCase):
    """The toolset factory must expose the expected tools."""

    async def test_media_tools_count(self):
        self.assertEqual(len(media_tools()), 5)

    async def test_media_tools_names(self):
        names = sorted(t.name for t in media_tools())
        self.assertEqual(
            names,
            sorted([
                "image_describe",
                "image_generate",
                "text_to_speech",
                "speech_to_text",
                "image_info",
            ]),
        )

    async def test_media_tools_have_schemas(self):
        # Every tool must produce a valid OpenAI-style function schema.
        for tool in media_tools():
            schema = tool.schema()
            self.assertEqual(schema["type"], "function")
            self.assertTrue(schema["function"]["name"])
            self.assertTrue(schema["function"]["description"])


if __name__ == "__main__":
    unittest.main()
