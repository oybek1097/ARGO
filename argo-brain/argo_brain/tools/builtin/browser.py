"""Browser / HTML scraping tools — spec section 4.4 (`web` toolset).

Pure-stdlib HTML parsing built on top of `html.parser.HTMLParser`. No
external dependencies. Each tool accepts either a `url` (fetched through the
shared `web._fetch` helper) or a raw `html` string, which keeps the parser
helpers fully testable offline.
"""

from __future__ import annotations

import asyncio
import urllib.error
from html.parser import HTMLParser
from urllib.parse import urljoin

from argo_brain.tools.base import Tool, ToolResult
from argo_brain.tools.builtin.web import _fetch, _html_to_text

# --------------------------------------------------------------------------
# Pure parser helpers (network-free, directly unit-testable)
# --------------------------------------------------------------------------


class _LinkParser(HTMLParser):
    """Collects <a href> elements together with their anchor text."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[dict] = []
        self._href: str | None = None
        self._text: list[str] = []

    def _flush(self) -> None:
        """Record the currently open anchor, if any."""
        if self._href is not None:
            self.links.append({
                "href": self._href,
                "text": "".join(self._text).strip(),
            })
            self._href = None
            self._text = []

    def handle_starttag(self, tag: str, attrs: list) -> None:
        if tag == "a":
            # <a> cannot nest — a new anchor implicitly closes the previous.
            self._flush()
            attr = dict(attrs)
            self._href = attr.get("href")
            self._text = []

    def handle_data(self, data: str) -> None:
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a":
            self._flush()

    def close(self) -> None:
        super().close()
        # Flush a trailing anchor that was never closed.
        self._flush()


def parse_links(html: str, base_url: str | None = None) -> list[dict]:
    """Return all hyperlinks in `html` as ``{"href", "text"}`` dicts.

    When `base_url` is given, relative hrefs are resolved against it.
    """
    parser = _LinkParser()
    parser.feed(html or "")
    parser.close()
    links = parser.links
    if base_url:
        for link in links:
            if link["href"]:
                link["href"] = urljoin(base_url, link["href"])
    return links


class _TableParser(HTMLParser):
    """Collects <table> contents as a list of row/cell matrices."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tables: list[list[list[str]]] = []
        self._depth = 0          # nesting depth inside <table>
        self._rows: list[list[str]] = []
        self._row: list[str] | None = None
        self._cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list) -> None:
        if tag == "table":
            if self._depth == 0:
                self._rows = []
            self._depth += 1
        elif tag == "tr" and self._depth:
            self._row = []
        elif tag in ("td", "th") and self._depth:
            self._cell = []

    def handle_data(self, data: str) -> None:
        if self._cell is not None:
            self._cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in ("td", "th") and self._cell is not None:
            if self._row is not None:
                self._row.append(" ".join("".join(self._cell).split()))
            self._cell = None
        elif tag == "tr" and self._row is not None:
            self._rows.append(self._row)
            self._row = None
        elif tag == "table" and self._depth:
            self._depth -= 1
            if self._depth == 0:
                self.tables.append(self._rows)
                self._rows = []


def parse_tables(html: str) -> list[list[list[str]]]:
    """Return every <table> in `html` as a matrix of cell-text strings."""
    parser = _TableParser()
    parser.feed(html or "")
    parser.close()
    return parser.tables


def tables_to_text(tables: list[list[list[str]]]) -> str:
    """Render parsed tables into an aligned, human-readable text grid."""
    blocks: list[str] = []
    for idx, rows in enumerate(tables):
        if not rows:
            continue
        width = max(len(r) for r in rows)
        # Pad every row to the same column count.
        padded = [r + [""] * (width - len(r)) for r in rows]
        col_w = [
            max(len(padded[r][c]) for r in range(len(padded)))
            for c in range(width)
        ]
        lines = [f"Table {idx + 1}:"]
        for row in padded:
            cells = [row[c].ljust(col_w[c]) for c in range(width)]
            lines.append(" | ".join(cells))
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


class _MetadataParser(HTMLParser):
    """Collects <title> and <meta> tag information."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title: str = ""
        self.meta: dict[str, str] = {}
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: list) -> None:
        if tag == "title":
            self._in_title = True
        elif tag == "meta":
            attr = dict(attrs)
            # `name` (description, keywords) or `property` (og:*, twitter:*).
            key = attr.get("name") or attr.get("property")
            content = attr.get("content")
            if key and content is not None:
                self.meta[key.lower()] = content

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title += data

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False


def parse_metadata(html: str) -> dict:
    """Return ``{"title", "meta"}`` extracted from the document head."""
    parser = _MetadataParser()
    parser.feed(html or "")
    parser.close()
    return {"title": parser.title.strip(), "meta": parser.meta}


class _FormParser(HTMLParser):
    """Collects <form> elements and their input/select/textarea fields."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.forms: list[dict] = []
        self._form: dict | None = None

    def handle_starttag(self, tag: str, attrs: list) -> None:
        attr = dict(attrs)
        if tag == "form":
            self._form = {
                "action": attr.get("action", ""),
                "method": (attr.get("method") or "get").lower(),
                "fields": [],
            }
        elif tag in ("input", "select", "textarea", "button") and self._form is not None:
            self._form["fields"].append({
                "tag": tag,
                "name": attr.get("name", ""),
                "type": attr.get("type", tag),
                "value": attr.get("value", ""),
            })

    def handle_startendtag(self, tag: str, attrs: list) -> None:
        # Self-closing tags such as <input .../>.
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag: str) -> None:
        if tag == "form" and self._form is not None:
            self.forms.append(self._form)
            self._form = None


def parse_forms(html: str) -> list[dict]:
    """Return every <form> as ``{"action", "method", "fields"}``."""
    parser = _FormParser()
    parser.feed(html or "")
    parser.close()
    return parser.forms


# --------------------------------------------------------------------------
# Shared helper: resolve the HTML source from `url` or `html` arguments
# --------------------------------------------------------------------------

_URL_SCHEMA = {
    "url": {"type": "string", "description": "Page URL to fetch"},
    "html": {"type": "string", "description": "Raw HTML to parse instead of fetching"},
}


async def _resolve_html(url: str, html: str) -> tuple[str, dict, str | None]:
    """Return (html, metadata, error). Either fetch `url` or use `html`."""
    if html:
        return html, {}, None
    if not url:
        return "", {}, "Either 'url' or 'html' must be provided."
    try:
        status, body = await asyncio.to_thread(_fetch, url)
    except (urllib.error.URLError, ValueError, OSError) as exc:
        return "", {}, f"Request error: {exc}"
    return body, {"status": status, "url": url}, None


# --------------------------------------------------------------------------
# Tool subclasses
# --------------------------------------------------------------------------


class ExtractLinksTool(Tool):
    name = "extract_links"
    description = "Extracts all hyperlinks (href + anchor text) from a page or HTML."
    parameters = {"type": "object", "properties": dict(_URL_SCHEMA), "required": []}

    async def run(self, user_id: str, url: str = "", html: str = "",
                  **kwargs) -> ToolResult:
        source, meta, error = await _resolve_html(url, html)
        if error:
            return ToolResult(content=error, success=False)
        links = parse_links(source, base_url=url or None)
        if not links:
            return ToolResult(content="No links found.", metadata=meta)
        lines = [f"{link['text'] or '(no text)'} -> {link['href']}" for link in links]
        meta["count"] = len(links)
        return ToolResult(content="\n".join(lines), metadata=meta)


class ExtractTablesTool(Tool):
    name = "extract_tables"
    description = "Extracts HTML <table> data into a readable text grid."
    parameters = {"type": "object", "properties": dict(_URL_SCHEMA), "required": []}

    async def run(self, user_id: str, url: str = "", html: str = "",
                  **kwargs) -> ToolResult:
        source, meta, error = await _resolve_html(url, html)
        if error:
            return ToolResult(content=error, success=False)
        tables = parse_tables(source)
        if not tables:
            return ToolResult(content="No tables found.", metadata=meta)
        meta["count"] = len(tables)
        return ToolResult(content=tables_to_text(tables), metadata=meta)


class ExtractMetadataTool(Tool):
    name = "extract_metadata"
    description = "Extracts <title> and <meta> tags (description, og:*) from HTML."
    parameters = {"type": "object", "properties": dict(_URL_SCHEMA), "required": []}

    async def run(self, user_id: str, url: str = "", html: str = "",
                  **kwargs) -> ToolResult:
        source, meta, error = await _resolve_html(url, html)
        if error:
            return ToolResult(content=error, success=False)
        data = parse_metadata(source)
        lines = [f"title: {data['title']}"] if data["title"] else []
        lines += [f"{key}: {value}" for key, value in sorted(data["meta"].items())]
        meta["meta"] = data["meta"]
        meta["title"] = data["title"]
        content = "\n".join(lines) if lines else "No metadata found."
        return ToolResult(content=content, metadata=meta)


class ExtractTextTool(Tool):
    name = "extract_text"
    description = "Extracts the readable text content of a page or HTML."
    parameters = {"type": "object", "properties": dict(_URL_SCHEMA), "required": []}

    async def run(self, user_id: str, url: str = "", html: str = "",
                  **kwargs) -> ToolResult:
        source, meta, error = await _resolve_html(url, html)
        if error:
            return ToolResult(content=error, success=False)
        return ToolResult(content=_html_to_text(source), metadata=meta)


class ExtractFormsTool(Tool):
    name = "extract_forms"
    description = "Lists <form> elements with their action, method and input fields."
    parameters = {"type": "object", "properties": dict(_URL_SCHEMA), "required": []}

    async def run(self, user_id: str, url: str = "", html: str = "",
                  **kwargs) -> ToolResult:
        source, meta, error = await _resolve_html(url, html)
        if error:
            return ToolResult(content=error, success=False)
        forms = parse_forms(source)
        if not forms:
            return ToolResult(content="No forms found.", metadata=meta)
        blocks: list[str] = []
        for idx, form in enumerate(forms):
            header = (f"Form {idx + 1}: method={form['method'].upper()} "
                      f"action={form['action'] or '(none)'}")
            field_lines = [
                f"  - {f['tag']}[{f['type']}] name={f['name'] or '(unnamed)'}"
                + (f" value={f['value']}" if f["value"] else "")
                for f in form["fields"]
            ]
            blocks.append("\n".join([header, *field_lines]))
        meta["count"] = len(forms)
        return ToolResult(content="\n\n".join(blocks), metadata=meta)


def browser_tools() -> list[Tool]:
    """Return the browser / HTML-scraping toolset (spec section 4.4)."""
    return [
        ExtractLinksTool(),
        ExtractTablesTool(),
        ExtractMetadataTool(),
        ExtractTextTool(),
        ExtractFormsTool(),
    ]
