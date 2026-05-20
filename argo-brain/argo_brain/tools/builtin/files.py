"""File tools — spec section 4.4 (`file` toolset).

`read_file` and `list_dir` live in `basic.py`; this module adds the
write/search tools.
"""

from __future__ import annotations

import fnmatch
import os
from pathlib import Path

from argo_brain.tools.base import Tool, ToolResult

_MAX_HITS = 100


class WriteFileTool(Tool):
    name = "write_file"
    description = "Writes text content to a file (creates parent directories)."
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "content": {"type": "string"},
        },
        "required": ["path", "content"],
    }
    dangerous = True

    async def run(self, user_id: str, path: str = "", content: str = "",
                  **kwargs) -> ToolResult:
        p = Path(path).expanduser()
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
        except OSError as exc:
            return ToolResult(content=f"Could not write: {exc}", success=False)
        return ToolResult(content=f"{len(content)} characters written: {p}")


class FindFilesTool(Tool):
    name = "find_files"
    description = "Finds files matching a glob pattern under a directory."
    parameters = {
        "type": "object",
        "properties": {
            "directory": {"type": "string"},
            "pattern": {"type": "string", "description": "e.g. *.py"},
        },
        "required": ["directory", "pattern"],
    }

    async def run(self, user_id: str, directory: str = ".", pattern: str = "*",
                  **kwargs) -> ToolResult:
        root = Path(directory).expanduser()
        if not root.is_dir():
            return ToolResult(content=f"Not a directory: {directory}", success=False)
        hits: list[str] = []
        for cur, _dirs, files in os.walk(root):
            for fname in files:
                if fnmatch.fnmatch(fname, pattern):
                    hits.append(str(Path(cur) / fname))
                    if len(hits) >= _MAX_HITS:
                        break
        return ToolResult(content="\n".join(sorted(hits)) or "(not found)")


class GrepFilesTool(Tool):
    name = "grep_files"
    description = "Searches for a text substring across files in a directory."
    parameters = {
        "type": "object",
        "properties": {
            "directory": {"type": "string"},
            "query": {"type": "string"},
            "pattern": {"type": "string", "description": "file glob, default *"},
        },
        "required": ["directory", "query"],
    }

    async def run(self, user_id: str, directory: str = ".", query: str = "",
                  pattern: str = "*", **kwargs) -> ToolResult:
        root = Path(directory).expanduser()
        if not root.is_dir():
            return ToolResult(content=f"Not a directory: {directory}", success=False)
        hits: list[str] = []
        for cur, _dirs, files in os.walk(root):
            for fname in files:
                if not fnmatch.fnmatch(fname, pattern):
                    continue
                fpath = Path(cur) / fname
                try:
                    for lineno, line in enumerate(
                        fpath.read_text(encoding="utf-8", errors="ignore").splitlines(),
                        start=1,
                    ):
                        if query in line:
                            hits.append(f"{fpath}:{lineno}: {line.strip()}")
                            if len(hits) >= _MAX_HITS:
                                return ToolResult(content="\n".join(hits))
                except OSError:
                    continue
        return ToolResult(content="\n".join(hits) or "(not found)")


def file_tools() -> list[Tool]:
    return [WriteFileTool(), FindFilesTool(), GrepFilesTool()]
