"""Data and utility built-in tools — spec section 4.4.

A set of pure-stdlib tools for querying and transforming data: SQLite
queries, JSON path extraction, hashing, base64, UUID generation and
datetime helpers. No third-party dependencies are used.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from argo_brain.tools.base import Tool, ToolResult

# --- SQL query --------------------------------------------------------------


class SQLQueryTool(Tool):
    """Runs a read-only (SELECT-only) query against a SQLite database file."""

    name = "sql_query"
    description = "Runs a read-only SELECT query against a SQLite database file."
    parameters = {
        "type": "object",
        "properties": {
            "db_path": {"type": "string", "description": "Path to the SQLite file."},
            "query": {"type": "string", "description": "A SELECT statement."},
        },
        "required": ["db_path", "query"],
    }

    async def run(
        self, user_id: str, db_path: str = "", query: str = "", **kwargs
    ) -> ToolResult:
        # Safety: only SELECT statements are permitted (spec section 4.4).
        if query.strip().lstrip("(").lstrip().lower()[:6] != "select":
            return ToolResult(
                content="Rejected: only read-only SELECT queries are allowed.",
                success=False,
            )
        p = Path(db_path).expanduser()
        if not p.is_file():
            return ToolResult(content=f"Database not found: {db_path}", success=False)
        try:
            # Open in read-only mode via a URI so the DB cannot be mutated.
            conn = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
            try:
                cursor = conn.execute(query)
                columns = (
                    [d[0] for d in cursor.description] if cursor.description else []
                )
                rows = cursor.fetchall()
            finally:
                conn.close()
        except sqlite3.Error as exc:
            return ToolResult(content=f"SQL error: {exc}", success=False)
        # Render the result set as plain text.
        lines = []
        if columns:
            lines.append(" | ".join(columns))
        for row in rows:
            lines.append(" | ".join(str(v) for v in row))
        text = "\n".join(lines) if lines else "(no rows)"
        return ToolResult(content=text, metadata={"row_count": len(rows)})


# --- JSON path query --------------------------------------------------------


class JSONQueryTool(Tool):
    """Extracts a value from a JSON string using a dotted path."""

    name = "json_query"
    description = (
        "Extracts a value from a JSON string by a dotted path "
        "(e.g. 'a.b.0.c'); supports dict keys and list indices."
    )
    parameters = {
        "type": "object",
        "properties": {
            "json_text": {"type": "string", "description": "The JSON document."},
            "path": {
                "type": "string",
                "description": "Dotted path, e.g. 'a.b.0.c'.",
            },
        },
        "required": ["json_text", "path"],
    }

    async def run(
        self, user_id: str, json_text: str = "", path: str = "", **kwargs
    ) -> ToolResult:
        try:
            data = json.loads(json_text)
        except json.JSONDecodeError as exc:
            return ToolResult(content=f"Invalid JSON: {exc}", success=False)
        current = data
        # An empty path returns the whole document.
        parts = [p for p in path.split(".") if p != ""]
        for part in parts:
            if isinstance(current, dict):
                if part not in current:
                    return ToolResult(
                        content=f"Path not found at segment '{part}'.",
                        success=False,
                    )
                current = current[part]
            elif isinstance(current, list):
                # List access requires an integer index.
                try:
                    index = int(part)
                except ValueError:
                    return ToolResult(
                        content=f"Expected list index, got '{part}'.",
                        success=False,
                    )
                if index < 0 or index >= len(current):
                    return ToolResult(
                        content=f"List index out of range: {index}.",
                        success=False,
                    )
                current = current[index]
            else:
                return ToolResult(
                    content=f"Cannot descend into scalar at segment '{part}'.",
                    success=False,
                )
        # Scalars are returned as-is; containers are re-serialised.
        if isinstance(current, (dict, list)):
            return ToolResult(content=json.dumps(current))
        return ToolResult(content=str(current))


# --- hashing ----------------------------------------------------------------


class HashTextTool(Tool):
    """Computes a hex digest of a text string."""

    name = "hash_text"
    description = "Computes a hex digest of text (sha256, md5 or sha1)."
    parameters = {
        "type": "object",
        "properties": {
            "text": {"type": "string"},
            "algorithm": {
                "type": "string",
                "enum": ["sha256", "md5", "sha1"],
                "description": "Hash algorithm; defaults to sha256.",
            },
        },
        "required": ["text"],
    }
    _ALGORITHMS = {"sha256", "md5", "sha1"}

    async def run(
        self, user_id: str, text: str = "", algorithm: str = "sha256", **kwargs
    ) -> ToolResult:
        algo = algorithm.lower()
        if algo not in self._ALGORITHMS:
            return ToolResult(
                content=f"Unknown algorithm: {algorithm}. "
                f"Supported: {', '.join(sorted(self._ALGORITHMS))}.",
                success=False,
            )
        digest = hashlib.new(algo, text.encode("utf-8")).hexdigest()
        return ToolResult(content=digest, metadata={"algorithm": algo})


# --- base64 -----------------------------------------------------------------


class Base64Tool(Tool):
    """Encodes or decodes text using base64."""

    name = "base64_transform"
    description = "Base64-encodes or decodes a text string."
    parameters = {
        "type": "object",
        "properties": {
            "text": {"type": "string"},
            "mode": {
                "type": "string",
                "enum": ["encode", "decode"],
                "description": "Whether to encode or decode; defaults to encode.",
            },
        },
        "required": ["text"],
    }

    async def run(
        self, user_id: str, text: str = "", mode: str = "encode", **kwargs
    ) -> ToolResult:
        mode = mode.lower()
        if mode == "encode":
            encoded = base64.b64encode(text.encode("utf-8")).decode("ascii")
            return ToolResult(content=encoded)
        if mode == "decode":
            try:
                decoded = base64.b64decode(text, validate=True).decode("utf-8")
            except (binascii.Error, ValueError, UnicodeDecodeError) as exc:
                return ToolResult(content=f"Could not decode: {exc}", success=False)
            return ToolResult(content=decoded)
        return ToolResult(
            content=f"Unknown mode: {mode}. Use 'encode' or 'decode'.",
            success=False,
        )


# --- UUID -------------------------------------------------------------------


class UUIDTool(Tool):
    """Generates a random UUID (version 4)."""

    name = "uuid_generate"
    description = "Generates a new random UUID4 string."
    parameters = {"type": "object", "properties": {}}

    async def run(self, user_id: str, **kwargs) -> ToolResult:
        return ToolResult(content=str(uuid.uuid4()))


# --- datetime ---------------------------------------------------------------


class DatetimeTool(Tool):
    """Returns the current UTC datetime, optionally shifted by an offset."""

    name = "datetime_now"
    description = (
        "Returns the current UTC datetime as an ISO string; an optional "
        "integer 'timezone_offset_hours' shifts the result."
    )
    parameters = {
        "type": "object",
        "properties": {
            "timezone_offset_hours": {
                "type": "integer",
                "description": "Hours to shift from UTC, e.g. -5 or 3.",
            }
        },
    }

    async def run(
        self, user_id: str, timezone_offset_hours: int = 0, **kwargs
    ) -> ToolResult:
        try:
            offset = int(timezone_offset_hours)
        except (TypeError, ValueError):
            return ToolResult(
                content=f"Invalid timezone offset: {timezone_offset_hours}.",
                success=False,
            )
        tz = timezone(timedelta(hours=offset))
        now = datetime.now(tz)
        return ToolResult(content=now.isoformat(), metadata={"offset_hours": offset})


# --- registry helper --------------------------------------------------------


def data_tools() -> list[Tool]:
    """Returns all data/utility built-in tools (spec section 4.4)."""
    return [
        SQLQueryTool(),
        JSONQueryTool(),
        HashTextTool(),
        Base64Tool(),
        UUIDTool(),
        DatetimeTool(),
    ]
