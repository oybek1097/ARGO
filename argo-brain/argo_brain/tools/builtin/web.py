"""Web tools — spec section 4.4 (`web` toolset).

HTTP access and page fetching via the stdlib `urllib`. `web_search` (which
needs a search-API key) will be added in a later sprint.
"""

from __future__ import annotations

import asyncio
import json
import re
import urllib.error
import urllib.request

from argo_brain.tools.base import Tool, ToolResult

_USER_AGENT = "ARGO-Agent/0.1 (+https://argo-agent.io)"
_MAX_BYTES = 256 * 1024
_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"[ \t\r\f]+")
_BLANK_RE = re.compile(r"\n\s*\n+")


def _fetch(url: str, *, method: str = "GET", data: bytes | None = None,
           headers: dict | None = None, timeout: int = 30) -> tuple[int, str]:
    """Blocking HTTP request; returns (status_code, body_text)."""
    req = urllib.request.Request(
        url, data=data, method=method,
        headers={"User-Agent": _USER_AGENT, **(headers or {})},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read(_MAX_BYTES)
        return resp.status, body.decode("utf-8", errors="replace")


def _html_to_text(html: str) -> str:
    """Crude HTML -> readable text conversion (no external parser)."""
    html = re.sub(r"(?is)<(script|style|head)[^>]*>.*?</\1>", "", html)
    text = _TAG_RE.sub("", html)
    text = (
        text.replace("&nbsp;", " ").replace("&amp;", "&")
        .replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"')
    )
    text = _WS_RE.sub(" ", text)
    return _BLANK_RE.sub("\n\n", text).strip()


class HttpGetTool(Tool):
    name = "http_get"
    description = "Performs an HTTP GET request and returns the raw response body."
    parameters = {
        "type": "object",
        "properties": {"url": {"type": "string"}},
        "required": ["url"],
    }

    async def run(self, user_id: str, url: str = "", **kwargs) -> ToolResult:
        try:
            status, body = await asyncio.to_thread(_fetch, url)
        except (urllib.error.URLError, ValueError, OSError) as exc:
            return ToolResult(content=f"Soʻrov xatosi: {exc}", success=False)
        return ToolResult(content=body, metadata={"status": status})


class HttpPostTool(Tool):
    name = "http_post"
    description = "Performs an HTTP POST request with a JSON body."
    parameters = {
        "type": "object",
        "properties": {
            "url": {"type": "string"},
            "json": {"type": "object", "description": "JSON payload"},
        },
        "required": ["url"],
    }

    async def run(self, user_id: str, url: str = "", json: dict | None = None,
                  **kwargs) -> ToolResult:
        import json as _json

        data = _json.dumps(json or {}).encode()
        try:
            status, body = await asyncio.to_thread(
                _fetch, url, method="POST", data=data,
                headers={"Content-Type": "application/json"},
            )
        except (urllib.error.URLError, ValueError, OSError) as exc:
            return ToolResult(content=f"Soʻrov xatosi: {exc}", success=False)
        return ToolResult(content=body, metadata={"status": status})


class WebFetchTool(Tool):
    name = "web_fetch"
    description = "Fetches a web page and returns its readable text content."
    parameters = {
        "type": "object",
        "properties": {"url": {"type": "string"}},
        "required": ["url"],
    }

    async def run(self, user_id: str, url: str = "", **kwargs) -> ToolResult:
        try:
            status, body = await asyncio.to_thread(_fetch, url)
        except (urllib.error.URLError, ValueError, OSError) as exc:
            return ToolResult(content=f"Soʻrov xatosi: {exc}", success=False)
        return ToolResult(content=_html_to_text(body), metadata={"status": status})


def web_tools() -> list[Tool]:
    return [HttpGetTool(), HttpPostTool(), WebFetchTool()]
