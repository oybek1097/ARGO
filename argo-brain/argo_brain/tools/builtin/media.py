"""Media / vision tools — spec section 4.4 (`media` toolset) and 4.12.

Vision, image-generation, text-to-speech and speech-to-text models are
external services. The corresponding tools here are therefore *adapter
tools*: each issues an HTTP request to an external API via the stdlib
`urllib`. When credentials are missing they FAIL CLEANLY — the tool
returns ``ToolResult(success=False, ...)`` with a clear message instead
of raising an exception, so the agent loop is never broken.

`ImageInfoTool` is the exception: it inspects a local image file's
header bytes (PNG / GIF / JPEG) and needs no API at all — pure stdlib.
"""

from __future__ import annotations

import asyncio
import json
import os
import struct
import urllib.error
import urllib.request

from argo_brain.tools.base import Tool, ToolResult

_USER_AGENT = "ARGO-Agent/0.1 (+https://argo-agent.io)"
_TIMEOUT = 60


def _post_json(url: str, payload: dict, api_key: str,
               *, auth_header: str = "Authorization",
               auth_prefix: str = "Bearer ") -> tuple[int, str]:
    """Blocking JSON POST with an auth header; returns (status, body_text)."""
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={
            "User-Agent": _USER_AGENT,
            "Content-Type": "application/json",
            auth_header: f"{auth_prefix}{api_key}",
        },
    )
    with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
        body = resp.read()
        return resp.status, body.decode("utf-8", errors="replace")


# --------------------------------------------------------------------------
# API-backed adapter tools (spec section 4.12)
# --------------------------------------------------------------------------


class ImageDescribeTool(Tool):
    """Describe an image using an external vision model (spec 4.12).

    Reads its API key from the ``ARGO_VISION_API_KEY`` env var. Without a
    key it fails cleanly with ``success=False``.
    """

    name = "image_describe"
    description = "Describe the content of an image using a vision model API."
    parameters = {
        "type": "object",
        "properties": {
            "image_url": {"type": "string", "description": "URL of the image"},
            "prompt": {
                "type": "string",
                "description": "Optional instruction for the description",
            },
        },
        "required": ["image_url"],
    }

    _ENV_KEY = "ARGO_VISION_API_KEY"
    _ENDPOINT = "https://api.openai.com/v1/chat/completions"

    async def run(self, user_id: str, image_url: str = "",
                  prompt: str = "Describe this image.", **kwargs) -> ToolResult:
        api_key = os.environ.get(self._ENV_KEY, "").strip()
        if not api_key:
            return ToolResult(
                content=(
                    f"No API key configured: set the {self._ENV_KEY} "
                    "environment variable to use the vision model."
                ),
                success=False,
                metadata={"reason": "no_api_key"},
            )
        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url",
                         "image_url": {"url": image_url}},
                    ],
                }
            ],
        }
        try:
            status, body = await asyncio.to_thread(
                _post_json, self._ENDPOINT, payload, api_key)
        except (urllib.error.URLError, ValueError, OSError) as exc:
            return ToolResult(
                content=f"Vision request failed: {exc}",
                success=False,
                metadata={"reason": "request_failed"},
            )
        return ToolResult(content=body, metadata={"status": status})


class ImageGenerateTool(Tool):
    """Generate an image from a text prompt via an image-generation API."""

    name = "image_generate"
    description = "Generate an image from a text prompt using an image API."
    parameters = {
        "type": "object",
        "properties": {
            "prompt": {"type": "string", "description": "Image description"},
            "size": {"type": "string", "description": "e.g. 1024x1024"},
        },
        "required": ["prompt"],
    }

    _ENV_KEY = "ARGO_IMAGE_API_KEY"
    _ENDPOINT = "https://api.openai.com/v1/images/generations"

    async def run(self, user_id: str, prompt: str = "",
                  size: str = "1024x1024", **kwargs) -> ToolResult:
        api_key = os.environ.get(self._ENV_KEY, "").strip()
        if not api_key:
            return ToolResult(
                content=(
                    f"No API key configured: set the {self._ENV_KEY} "
                    "environment variable to generate images."
                ),
                success=False,
                metadata={"reason": "no_api_key"},
            )
        payload = {"model": "dall-e-3", "prompt": prompt,
                   "size": size, "n": 1}
        try:
            status, body = await asyncio.to_thread(
                _post_json, self._ENDPOINT, payload, api_key)
        except (urllib.error.URLError, ValueError, OSError) as exc:
            return ToolResult(
                content=f"Image generation request failed: {exc}",
                success=False,
                metadata={"reason": "request_failed"},
            )
        return ToolResult(content=body, metadata={"status": status})


class TextToSpeechTool(Tool):
    """Synthesize speech from text via an external TTS API."""

    name = "text_to_speech"
    description = "Synthesize speech audio from text using a TTS API."
    parameters = {
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "Text to speak"},
            "voice": {"type": "string", "description": "Voice name"},
        },
        "required": ["text"],
    }

    _ENV_KEY = "ARGO_TTS_API_KEY"
    _ENDPOINT = "https://api.openai.com/v1/audio/speech"

    async def run(self, user_id: str, text: str = "",
                  voice: str = "alloy", **kwargs) -> ToolResult:
        api_key = os.environ.get(self._ENV_KEY, "").strip()
        if not api_key:
            return ToolResult(
                content=(
                    f"No API key configured: set the {self._ENV_KEY} "
                    "environment variable to synthesize speech."
                ),
                success=False,
                metadata={"reason": "no_api_key"},
            )
        payload = {"model": "tts-1", "input": text, "voice": voice}
        try:
            status, body = await asyncio.to_thread(
                _post_json, self._ENDPOINT, payload, api_key)
        except (urllib.error.URLError, ValueError, OSError) as exc:
            return ToolResult(
                content=f"Text-to-speech request failed: {exc}",
                success=False,
                metadata={"reason": "request_failed"},
            )
        return ToolResult(content=body, metadata={"status": status})


class SpeechToTextTool(Tool):
    """Transcribe audio to text via an external STT API."""

    name = "speech_to_text"
    description = "Transcribe spoken audio into text using an STT API."
    parameters = {
        "type": "object",
        "properties": {
            "audio_url": {"type": "string",
                          "description": "URL of the audio file"},
            "language": {"type": "string",
                         "description": "Optional language hint"},
        },
        "required": ["audio_url"],
    }

    _ENV_KEY = "ARGO_STT_API_KEY"
    _ENDPOINT = "https://api.openai.com/v1/audio/transcriptions"

    async def run(self, user_id: str, audio_url: str = "",
                  language: str = "", **kwargs) -> ToolResult:
        api_key = os.environ.get(self._ENV_KEY, "").strip()
        if not api_key:
            return ToolResult(
                content=(
                    f"No API key configured: set the {self._ENV_KEY} "
                    "environment variable to transcribe audio."
                ),
                success=False,
                metadata={"reason": "no_api_key"},
            )
        payload = {"model": "whisper-1", "audio_url": audio_url}
        if language:
            payload["language"] = language
        try:
            status, body = await asyncio.to_thread(
                _post_json, self._ENDPOINT, payload, api_key)
        except (urllib.error.URLError, ValueError, OSError) as exc:
            return ToolResult(
                content=f"Speech-to-text request failed: {exc}",
                success=False,
                metadata={"reason": "request_failed"},
            )
        return ToolResult(content=body, metadata={"status": status})


# --------------------------------------------------------------------------
# Fully functional, no-API tool (spec section 4.4)
# --------------------------------------------------------------------------


def _read_image_header(data: bytes) -> dict | None:
    """Parse PNG / GIF / JPEG header bytes.

    Returns a dict with ``format``, ``width`` and ``height`` or ``None``
    when the bytes do not correspond to a supported image format.
    """
    # --- PNG -------------------------------------------------------------
    # 8-byte signature, then an IHDR chunk: 4-byte length, "IHDR",
    # then width (4 bytes BE) and height (4 bytes BE).
    if data[:8] == b"\x89PNG\r\n\x1a\n" and len(data) >= 24:
        if data[12:16] == b"IHDR":
            width, height = struct.unpack(">II", data[16:24])
            return {"format": "PNG", "width": width, "height": height}
        return None

    # --- GIF -------------------------------------------------------------
    # "GIF87a"/"GIF89a", then logical screen width/height (2 bytes LE each).
    if data[:6] in (b"GIF87a", b"GIF89a") and len(data) >= 10:
        width, height = struct.unpack("<HH", data[6:10])
        return {"format": "GIF", "width": width, "height": height}

    # --- JPEG ------------------------------------------------------------
    # Starts with FFD8; scan the marker segments for a Start-Of-Frame
    # marker (SOFn) which carries the height/width.
    if data[:2] == b"\xff\xd8":
        i = 2
        size = len(data)
        while i + 9 < size:
            if data[i] != 0xFF:
                i += 1
                continue
            marker = data[i + 1]
            # SOF0..SOF15 except DHT(C4), DAC(CC) and RSTn carry frame size.
            if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
                height, width = struct.unpack(">HH", data[i + 5:i + 9])
                return {"format": "JPEG", "width": width, "height": height}
            # Standalone markers (no length field): RSTn and SOI/EOI.
            if marker in (0x01, 0xD0, 0xD1, 0xD2, 0xD3, 0xD4,
                          0xD5, 0xD6, 0xD7):
                i += 2
                continue
            seg_len = struct.unpack(">H", data[i + 2:i + 4])[0]
            i += 2 + seg_len
        return None

    return None


class ImageInfoTool(Tool):
    """Read a local image file's dimensions and format (spec section 4.4).

    Fully functional and stdlib-only: it parses the file header bytes for
    PNG, GIF and JPEG — no external API is involved.
    """

    name = "image_info"
    description = (
        "Read a local image file's width, height and format from its "
        "header bytes (PNG, GIF, JPEG). No network access required."
    )
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string",
                     "description": "Path to a local image file"},
        },
        "required": ["path"],
    }

    async def run(self, user_id: str, path: str = "", **kwargs) -> ToolResult:
        if not path:
            return ToolResult(content="No file path provided.", success=False)
        try:
            # Read enough bytes to cover any supported header. JPEG marker
            # scanning may need more, so read a generous chunk.
            data = await asyncio.to_thread(_read_bytes, path)
        except (OSError, ValueError) as exc:
            return ToolResult(
                content=f"Could not read file: {exc}", success=False)

        info = _read_image_header(data)
        if info is None:
            return ToolResult(
                content=(
                    f"'{path}' is not a recognized PNG, GIF or JPEG image."
                ),
                success=False,
                metadata={"reason": "unsupported_format"},
            )
        return ToolResult(
            content=(
                f"{info['format']} image, "
                f"{info['width']}x{info['height']} pixels."
            ),
            metadata=info,
        )


def _read_bytes(path: str, limit: int = 256 * 1024) -> bytes:
    """Read up to ``limit`` bytes from a file (blocking helper)."""
    with open(path, "rb") as fh:
        return fh.read(limit)


def media_tools() -> list[Tool]:
    """Return the media / vision toolset (spec sections 4.4 and 4.12)."""
    return [
        ImageDescribeTool(),
        ImageGenerateTool(),
        TextToSpeechTool(),
        SpeechToTextTool(),
        ImageInfoTool(),
    ]
