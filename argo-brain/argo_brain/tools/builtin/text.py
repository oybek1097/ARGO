"""Text and archive built-in tools — spec section 4.4.

A pure-stdlib toolset covering text diffing, CSV parsing, zip archive
creation/extraction, regex extraction and template rendering. These tools
extend the skeleton `basic` toolset described in spec section 4.4.
"""

from __future__ import annotations

import csv
import difflib
import io
import os
import re
import string
import zipfile
from pathlib import Path

from argo_brain.tools.base import Tool, ToolResult

# Shared limits to keep results readable and bounded.
_MAX_CSV_ROWS = 10
_MAX_REGEX_MATCHES = 100


class DiffTextTool(Tool):
    """Produces a unified diff between two text inputs."""

    name = "diff_text"
    description = "Computes a unified diff between two text inputs."
    parameters = {
        "type": "object",
        "properties": {
            "old": {"type": "string", "description": "The original text."},
            "new": {"type": "string", "description": "The modified text."},
            "old_label": {"type": "string", "description": "Label for the old text."},
            "new_label": {"type": "string", "description": "Label for the new text."},
        },
        "required": ["old", "new"],
    }

    async def run(
        self,
        user_id: str,
        old: str = "",
        new: str = "",
        old_label: str = "old",
        new_label: str = "new",
        **kwargs,
    ) -> ToolResult:
        # `keepends=True` preserves line endings so difflib emits clean hunks.
        old_lines = old.splitlines(keepends=True)
        new_lines = new.splitlines(keepends=True)
        diff = list(
            difflib.unified_diff(
                old_lines, new_lines, fromfile=old_label, tofile=new_label
            )
        )
        if not diff:
            return ToolResult(content="(no differences)")
        return ToolResult(content="".join(diff))


class CSVParseTool(Tool):
    """Parses CSV text and returns a readable column + row summary."""

    name = "csv_parse"
    description = "Parses CSV text and summarises columns and the first rows."
    parameters = {
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "The raw CSV text."},
            "delimiter": {
                "type": "string",
                "description": "Field delimiter (default ',').",
            },
            "max_rows": {
                "type": "integer",
                "description": "How many data rows to preview.",
            },
        },
        "required": ["text"],
    }

    async def run(
        self,
        user_id: str,
        text: str = "",
        delimiter: str = ",",
        max_rows: int = _MAX_CSV_ROWS,
        **kwargs,
    ) -> ToolResult:
        if not text.strip():
            return ToolResult(content="CSV text is empty.", success=False)
        # A single-character delimiter is required by the csv module.
        if len(delimiter) != 1:
            return ToolResult(
                content="Delimiter must be exactly one character.", success=False
            )
        try:
            reader = csv.reader(io.StringIO(text), delimiter=delimiter)
            rows = list(reader)
        except csv.Error as exc:
            return ToolResult(content=f"Could not parse CSV: {exc}", success=False)
        if not rows:
            return ToolResult(content="CSV contains no rows.", success=False)

        header = rows[0]
        data_rows = rows[1:]
        preview = data_rows[: max(0, max_rows)]
        lines = [
            f"Columns ({len(header)}): {', '.join(header)}",
            f"Data rows: {len(data_rows)}",
            f"Preview (first {len(preview)}):",
        ]
        for i, row in enumerate(preview, start=1):
            lines.append(f"  {i}. {row}")
        return ToolResult(
            content="\n".join(lines),
            metadata={"columns": len(header), "rows": len(data_rows)},
        )


class ZipCreateTool(Tool):
    """Creates a zip archive from a list of file paths."""

    name = "zip_create"
    description = "Creates a zip archive from a list of file paths."
    dangerous = True  # writes a new file to disk
    parameters = {
        "type": "object",
        "properties": {
            "archive_path": {
                "type": "string",
                "description": "Destination path of the .zip archive.",
            },
            "paths": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Files to add to the archive.",
            },
        },
        "required": ["archive_path", "paths"],
    }

    async def run(
        self,
        user_id: str,
        archive_path: str = "",
        paths: list | None = None,
        **kwargs,
    ) -> ToolResult:
        if not archive_path:
            return ToolResult(content="archive_path is required.", success=False)
        paths = paths or []
        if not paths:
            return ToolResult(content="No files given to archive.", success=False)

        # Validate every input path before touching the archive.
        resolved: list[Path] = []
        for raw in paths:
            p = Path(raw).expanduser()
            if not p.is_file():
                return ToolResult(content=f"File not found: {raw}", success=False)
            resolved.append(p)

        try:
            with zipfile.ZipFile(
                archive_path, "w", compression=zipfile.ZIP_DEFLATED
            ) as zf:
                for p in resolved:
                    # arcname is just the basename to avoid leaking absolute paths.
                    zf.write(p, arcname=p.name)
        except OSError as exc:
            return ToolResult(content=f"Could not create archive: {exc}", success=False)
        return ToolResult(
            content=f"Created {archive_path} with {len(resolved)} file(s).",
            metadata={"files": len(resolved)},
        )


class ZipExtractTool(Tool):
    """Extracts a zip archive to a directory, guarding against path traversal."""

    name = "zip_extract"
    description = "Extracts a zip archive to a directory."
    dangerous = True  # writes files to disk
    parameters = {
        "type": "object",
        "properties": {
            "archive_path": {
                "type": "string",
                "description": "Path to the .zip archive.",
            },
            "dest_dir": {
                "type": "string",
                "description": "Directory to extract into.",
            },
        },
        "required": ["archive_path", "dest_dir"],
    }

    async def run(
        self,
        user_id: str,
        archive_path: str = "",
        dest_dir: str = "",
        **kwargs,
    ) -> ToolResult:
        archive = Path(archive_path).expanduser()
        if not archive.is_file():
            return ToolResult(
                content=f"Archive not found: {archive_path}", success=False
            )
        if not zipfile.is_zipfile(archive):
            return ToolResult(
                content=f"Not a valid zip archive: {archive_path}", success=False
            )

        dest = Path(dest_dir).expanduser()
        dest.mkdir(parents=True, exist_ok=True)
        # Resolve the destination root once for the traversal check.
        dest_root = dest.resolve()

        try:
            with zipfile.ZipFile(archive, "r") as zf:
                names = zf.namelist()
                # Reject any member that would escape the destination dir
                # (e.g. "../evil" or an absolute path) — a Zip Slip guard.
                for name in names:
                    target = (dest_root / name).resolve()
                    if not (
                        target == dest_root
                        or str(target).startswith(str(dest_root) + os.sep)
                    ):
                        return ToolResult(
                            content=f"Unsafe path in archive blocked: {name}",
                            success=False,
                        )
                zf.extractall(dest_root)
        except (OSError, zipfile.BadZipFile) as exc:
            return ToolResult(content=f"Could not extract: {exc}", success=False)
        return ToolResult(
            content=f"Extracted {len(names)} item(s) to {dest_root}.",
            metadata={"items": len(names)},
        )


class RegexExtractTool(Tool):
    """Applies a regex to text and returns all matches."""

    name = "regex_extract"
    description = "Applies a regular expression to text and returns all matches."
    parameters = {
        "type": "object",
        "properties": {
            "pattern": {"type": "string", "description": "The regular expression."},
            "text": {"type": "string", "description": "The text to search."},
            "ignore_case": {
                "type": "boolean",
                "description": "Perform a case-insensitive match.",
            },
        },
        "required": ["pattern", "text"],
    }

    async def run(
        self,
        user_id: str,
        pattern: str = "",
        text: str = "",
        ignore_case: bool = False,
        **kwargs,
    ) -> ToolResult:
        flags = re.IGNORECASE if ignore_case else 0
        try:
            compiled = re.compile(pattern, flags)
        except re.error as exc:
            return ToolResult(content=f"Invalid regex: {exc}", success=False)

        matches = compiled.findall(text)
        if not matches:
            return ToolResult(content="No matches found.", metadata={"count": 0})

        capped = matches[:_MAX_REGEX_MATCHES]
        lines = [f"Found {len(matches)} match(es):"]
        for i, m in enumerate(capped, start=1):
            # findall returns tuples when the pattern has multiple groups.
            lines.append(f"  {i}. {m}")
        return ToolResult(
            content="\n".join(lines), metadata={"count": len(matches)}
        )


class TemplateRenderTool(Tool):
    """Renders a string template using `string.Template` substitution."""

    name = "template_render"
    description = "Renders a $-style string template with the given variables."
    parameters = {
        "type": "object",
        "properties": {
            "template": {
                "type": "string",
                "description": "Template text using $name placeholders.",
            },
            "variables": {
                "type": "object",
                "description": "Mapping of placeholder names to values.",
            },
        },
        "required": ["template"],
    }

    async def run(
        self,
        user_id: str,
        template: str = "",
        variables: dict | None = None,
        **kwargs,
    ) -> ToolResult:
        variables = variables or {}
        tmpl = string.Template(template)
        try:
            # `substitute` raises on missing keys, surfacing a clear error.
            rendered = tmpl.substitute(variables)
        except KeyError as exc:
            return ToolResult(
                content=f"Missing template variable: {exc}", success=False
            )
        except ValueError as exc:
            return ToolResult(
                content=f"Invalid template: {exc}", success=False
            )
        return ToolResult(content=rendered)


def text_tools() -> list[Tool]:
    """List of the text and archive built-in tools (spec section 4.4)."""
    return [
        DiffTextTool(),
        CSVParseTool(),
        ZipCreateTool(),
        ZipExtractTool(),
        RegexExtractTool(),
        TemplateRenderTool(),
    ]
