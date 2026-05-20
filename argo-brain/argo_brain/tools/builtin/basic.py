"""Basic built-in tools (the skeleton set).

These tools rely only on the stdlib. The full set (web_search, shell_exec,
kubectl, ...) will be added in later sprints — see the taxonomy in spec
section 4.4.
"""

from __future__ import annotations

import ast
import operator
from datetime import datetime, timezone
from pathlib import Path

from argo_brain.tools.base import Tool, ToolResult

# --- safe arithmetic evaluation ---------------------------------------------

_BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARY_OPS = {ast.UAdd: operator.pos, ast.USub: operator.neg}


def _safe_eval(node: ast.AST) -> float:
    """Safe arithmetic evaluation without `eval()`."""
    if isinstance(node, ast.Expression):
        return _safe_eval(node.body)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError("faqat sonlar ruxsat etiladi")
    if isinstance(node, ast.BinOp) and type(node.op) in _BIN_OPS:
        return _BIN_OPS[type(node.op)](_safe_eval(node.left), _safe_eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPS:
        return _UNARY_OPS[type(node.op)](_safe_eval(node.operand))
    raise ValueError("ruxsat etilmagan ifoda")


# --- tools ------------------------------------------------------------------


class CurrentTimeTool(Tool):
    name = "current_time"
    description = "Joriy UTC sana va vaqtni ISO formatda qaytaradi."
    parameters = {"type": "object", "properties": {}}

    async def run(self, user_id: str, **kwargs) -> ToolResult:
        return ToolResult(content=datetime.now(timezone.utc).isoformat())


class CalculateTool(Tool):
    name = "calculate"
    description = "Arifmetik ifodani hisoblaydi (+ - * / // % **)."
    parameters = {
        "type": "object",
        "properties": {
            "expression": {"type": "string", "description": "Masalan: 2 + 2 * 10"}
        },
        "required": ["expression"],
    }

    async def run(self, user_id: str, expression: str = "", **kwargs) -> ToolResult:
        try:
            tree = ast.parse(expression, mode="eval")
            value = _safe_eval(tree)
        except (ValueError, SyntaxError, ZeroDivisionError, TypeError) as exc:
            return ToolResult(content=f"Hisoblab bo'lmadi: {exc}", success=False)
        return ToolResult(content=str(value))


class ReadFileTool(Tool):
    name = "read_file"
    description = "Matnli faylni o'qiydi (maksimum 64 KB)."
    parameters = {
        "type": "object",
        "properties": {"path": {"type": "string"}},
        "required": ["path"],
    }
    _MAX = 64 * 1024

    async def run(self, user_id: str, path: str = "", **kwargs) -> ToolResult:
        p = Path(path).expanduser()
        if not p.is_file():
            return ToolResult(content=f"Fayl topilmadi: {path}", success=False)
        try:
            data = p.read_text(encoding="utf-8", errors="replace")[: self._MAX]
        except OSError as exc:
            return ToolResult(content=f"O'qib bo'lmadi: {exc}", success=False)
        return ToolResult(content=data)


class ListDirTool(Tool):
    name = "list_dir"
    description = "Katalog tarkibini ro'yxatlaydi."
    parameters = {
        "type": "object",
        "properties": {"path": {"type": "string"}},
        "required": ["path"],
    }

    async def run(self, user_id: str, path: str = ".", **kwargs) -> ToolResult:
        p = Path(path).expanduser()
        if not p.is_dir():
            return ToolResult(content=f"Katalog emas: {path}", success=False)
        entries = sorted(
            (f"{'[d] ' if e.is_dir() else '    '}{e.name}" for e in p.iterdir())
        )
        return ToolResult(content="\n".join(entries) or "(bo'sh)")


class MemorySearchTool(Tool):
    name = "memory_search"
    description = "Foydalanuvchining suhbat xotirasidan to'liq-matnli qidiradi."
    parameters = {
        "type": "object",
        "properties": {"query": {"type": "string"}},
        "required": ["query"],
    }

    def __init__(self, memory) -> None:
        self._memory = memory

    async def run(self, user_id: str, query: str = "", **kwargs) -> ToolResult:
        hits = await self._memory.search(user_id, query, limit=5)
        if not hits:
            return ToolResult(content="Xotirada mos natija topilmadi.")
        lines = [f"[{h['role']}] {h['content']}" for h in hits]
        return ToolResult(content="\n".join(lines))


def builtin_tools(memory=None) -> list[Tool]:
    """List of the skeleton built-in tools.

    If `memory` is provided, memory-dependent tools are added as well.
    """
    tools: list[Tool] = [
        CurrentTimeTool(),
        CalculateTool(),
        ReadFileTool(),
        ListDirTool(),
    ]
    if memory is not None:
        tools.append(MemorySearchTool(memory))
    return tools
