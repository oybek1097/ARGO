"""Format and archive built-in tools — spec section 4.4.

A pure-stdlib toolset covering XML and INI parsing, tar.gz archive
creation/extraction, common unit conversion and file hashing. These tools
extend the `text` toolset described in spec section 4.4.
"""

from __future__ import annotations

import configparser
import hashlib
import io
import os
import tarfile
import xml.etree.ElementTree as ET
from pathlib import Path

from argo_brain.tools.base import Tool, ToolResult

# Shared limits to keep results readable and bounded.
_MAX_TREE_NODES = 200
_HASH_CHUNK = 65536


class XMLParseTool(Tool):
    """Parses XML text and returns a readable element-tree summary."""

    name = "xml_parse"
    description = "Parses XML text and summarises its element tree."
    parameters = {
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "The raw XML text."},
            "max_depth": {
                "type": "integer",
                "description": "How many levels of the tree to render.",
            },
        },
        "required": ["text"],
    }

    async def run(
        self,
        user_id: str,
        text: str = "",
        max_depth: int = 5,
        **kwargs,
    ) -> ToolResult:
        if not text.strip():
            return ToolResult(content="XML text is empty.", success=False)
        try:
            root = ET.fromstring(text)
        except ET.ParseError as exc:
            # Malformed XML surfaces a clear, non-fatal error message.
            return ToolResult(content=f"Could not parse XML: {exc}", success=False)

        lines: list[str] = []
        node_count = 0

        def _walk(element: ET.Element, depth: int) -> None:
            # Render the tree depth-first, bounded by depth and node count.
            nonlocal node_count
            if depth > max(0, max_depth) or node_count >= _MAX_TREE_NODES:
                return
            node_count += 1
            indent = "  " * depth
            attrs = "".join(f" {k}={v!r}" for k, v in element.attrib.items())
            value = (element.text or "").strip()
            value_part = f" = {value!r}" if value else ""
            lines.append(f"{indent}<{element.tag}>{attrs}{value_part}")
            for child in element:
                _walk(child, depth + 1)

        _walk(root, 0)
        summary = [
            f"Root: <{root.tag}>",
            f"Elements rendered: {node_count}",
            "Tree:",
        ]
        summary.extend(lines)
        return ToolResult(
            content="\n".join(summary),
            metadata={"root": root.tag, "elements": node_count},
        )


class INIParseTool(Tool):
    """Parses INI text and returns its sections and keys."""

    name = "ini_parse"
    description = "Parses INI text and lists sections with their keys."
    parameters = {
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "The raw INI text."},
        },
        "required": ["text"],
    }

    async def run(
        self,
        user_id: str,
        text: str = "",
        **kwargs,
    ) -> ToolResult:
        if not text.strip():
            return ToolResult(content="INI text is empty.", success=False)
        parser = configparser.ConfigParser()
        try:
            parser.read_string(text)
        except configparser.Error as exc:
            # Duplicate sections, missing headers, etc. land here.
            return ToolResult(content=f"Could not parse INI: {exc}", success=False)

        sections = parser.sections()
        lines = [f"Sections ({len(sections)}):"]
        total_keys = 0
        for section in sections:
            keys = list(parser[section].keys())
            total_keys += len(keys)
            lines.append(f"  [{section}]")
            for key in keys:
                lines.append(f"    {key} = {parser[section][key]}")
        # configparser keeps stray top-level keys in the DEFAULT section.
        defaults = list(parser.defaults().keys())
        if defaults:
            lines.append(f"  [DEFAULT] keys: {', '.join(defaults)}")
        return ToolResult(
            content="\n".join(lines),
            metadata={"sections": len(sections), "keys": total_keys},
        )


class TarCreateTool(Tool):
    """Creates a .tar.gz archive from a list of file paths."""

    name = "tar_create"
    description = "Creates a gzip-compressed tar archive from file paths."
    dangerous = True  # writes a new file to disk
    parameters = {
        "type": "object",
        "properties": {
            "archive_path": {
                "type": "string",
                "description": "Destination path of the .tar.gz archive.",
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
            with tarfile.open(archive_path, "w:gz") as tar:
                for p in resolved:
                    # arcname is just the basename to avoid leaking absolute paths.
                    tar.add(p, arcname=p.name)
        except OSError as exc:
            return ToolResult(content=f"Could not create archive: {exc}", success=False)
        return ToolResult(
            content=f"Created {archive_path} with {len(resolved)} file(s).",
            metadata={"files": len(resolved)},
        )


class TarExtractTool(Tool):
    """Extracts a .tar.gz archive to a directory, guarding against traversal."""

    name = "tar_extract"
    description = "Extracts a gzip-compressed tar archive to a directory."
    dangerous = True  # writes files to disk
    parameters = {
        "type": "object",
        "properties": {
            "archive_path": {
                "type": "string",
                "description": "Path to the .tar.gz archive.",
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
        if not tarfile.is_tarfile(archive):
            return ToolResult(
                content=f"Not a valid tar archive: {archive_path}", success=False
            )

        dest = Path(dest_dir).expanduser()
        dest.mkdir(parents=True, exist_ok=True)
        # Resolve the destination root once for the traversal check.
        dest_root = dest.resolve()

        try:
            with tarfile.open(archive, "r:gz") as tar:
                members = tar.getmembers()
                # Reject any member that would escape the destination dir
                # (e.g. "../evil", an absolute path, or an unsafe symlink) —
                # a tar-slip guard.
                for member in members:
                    target = (dest_root / member.name).resolve()
                    if not (
                        target == dest_root
                        or str(target).startswith(str(dest_root) + os.sep)
                    ):
                        return ToolResult(
                            content=f"Unsafe path in archive blocked: {member.name}",
                            success=False,
                        )
                    # Symlinks and hardlinks can also point outside the root.
                    if member.islnk() or member.issym():
                        link_target = (
                            dest_root / member.name
                        ).parent.joinpath(member.linkname)
                        link_resolved = os.path.normpath(str(link_target))
                        if not (
                            link_resolved == str(dest_root)
                            or link_resolved.startswith(str(dest_root) + os.sep)
                        ):
                            return ToolResult(
                                content=(
                                    f"Unsafe link in archive blocked: "
                                    f"{member.name}"
                                ),
                                success=False,
                            )
                # `filter="data"` is the safe default for untrusted
                # archives (Python 3.12+); the manual guard above stays
                # for older interpreters that lack the filter argument.
                try:
                    tar.extractall(dest_root, filter="data")
                except TypeError:
                    tar.extractall(dest_root)
        except (OSError, tarfile.TarError) as exc:
            return ToolResult(content=f"Could not extract: {exc}", success=False)
        return ToolResult(
            content=f"Extracted {len(members)} item(s) to {dest_root}.",
            metadata={"items": len(members)},
        )


# Conversion factors to a canonical base unit per measurement family.
# Length base unit: metre. Mass base unit: gram.
_LENGTH_FACTORS = {
    "m": 1.0,
    "km": 1000.0,
    "mi": 1609.344,
    "ft": 0.3048,
}
_MASS_FACTORS = {
    "g": 1.0,
    "kg": 1000.0,
    "lb": 453.59237,
}
_TEMPERATURE_UNITS = {"c", "f", "k"}


def _to_celsius(value: float, unit: str) -> float:
    """Normalises any supported temperature unit to Celsius."""
    if unit == "c":
        return value
    if unit == "f":
        return (value - 32.0) * 5.0 / 9.0
    # Kelvin.
    return value - 273.15


def _from_celsius(value: float, unit: str) -> float:
    """Converts a Celsius value to any supported temperature unit."""
    if unit == "c":
        return value
    if unit == "f":
        return value * 9.0 / 5.0 + 32.0
    # Kelvin.
    return value + 273.15


class UnitConvertTool(Tool):
    """Converts a value between common length, mass or temperature units."""

    name = "unit_convert"
    description = (
        "Converts a value between common units "
        "(length: m/km/mi/ft, mass: g/kg/lb, temperature: C/F/K)."
    )
    parameters = {
        "type": "object",
        "properties": {
            "value": {"type": "number", "description": "The numeric value."},
            "from_unit": {"type": "string", "description": "Source unit."},
            "to_unit": {"type": "string", "description": "Target unit."},
        },
        "required": ["value", "from_unit", "to_unit"],
    }

    async def run(
        self,
        user_id: str,
        value: float | None = None,
        from_unit: str = "",
        to_unit: str = "",
        **kwargs,
    ) -> ToolResult:
        if value is None:
            return ToolResult(content="value is required.", success=False)
        try:
            value = float(value)
        except (TypeError, ValueError):
            return ToolResult(content=f"value is not numeric: {value!r}", success=False)

        src = from_unit.strip().lower()
        dst = to_unit.strip().lower()

        # Temperature uses offset formulas, so it is handled separately.
        if src in _TEMPERATURE_UNITS and dst in _TEMPERATURE_UNITS:
            result = _from_celsius(_to_celsius(value, src), dst)
            return ToolResult(
                content=f"{value} {from_unit} = {result:g} {to_unit}",
                metadata={"result": result, "family": "temperature"},
            )

        # Length and mass are simple ratio conversions through a base unit.
        for family, factors in (("length", _LENGTH_FACTORS), ("mass", _MASS_FACTORS)):
            if src in factors and dst in factors:
                result = value * factors[src] / factors[dst]
                return ToolResult(
                    content=f"{value} {from_unit} = {result:g} {to_unit}",
                    metadata={"result": result, "family": family},
                )

        # Mismatched families (e.g. m -> kg) or unknown units fail clearly.
        return ToolResult(
            content=(
                f"Cannot convert from {from_unit!r} to {to_unit!r}: "
                f"unknown units or incompatible measurement families."
            ),
            success=False,
        )


class HashFileTool(Tool):
    """Computes the SHA-256 hash of a file's contents."""

    name = "hash_file"
    description = "Computes the SHA-256 hash of a file's contents."
    parameters = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path to the file to hash.",
            },
        },
        "required": ["path"],
    }

    async def run(
        self,
        user_id: str,
        path: str = "",
        **kwargs,
    ) -> ToolResult:
        if not path:
            return ToolResult(content="path is required.", success=False)
        target = Path(path).expanduser()
        if not target.is_file():
            return ToolResult(content=f"File not found: {path}", success=False)

        digest = hashlib.sha256()
        try:
            with target.open("rb") as handle:
                # Stream the file in chunks so large files stay memory-bounded.
                for chunk in iter(lambda: handle.read(_HASH_CHUNK), b""):
                    digest.update(chunk)
        except OSError as exc:
            return ToolResult(content=f"Could not read file: {exc}", success=False)

        hexdigest = digest.hexdigest()
        return ToolResult(
            content=f"SHA-256 ({target.name}): {hexdigest}",
            metadata={"sha256": hexdigest, "size": target.stat().st_size},
        )


def format_tools() -> list[Tool]:
    """List of the format and archive built-in tools (spec section 4.4)."""
    return [
        XMLParseTool(),
        INIParseTool(),
        TarCreateTool(),
        TarExtractTool(),
        UnitConvertTool(),
        HashFileTool(),
    ]
