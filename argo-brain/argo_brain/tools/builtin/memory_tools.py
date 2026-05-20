"""Memory tools — spec section 4.4 (`memory` toolset).

`memory_search` lives in `basic.py`; this module adds the write side.
All memory tools require a `MemoryManager` instance.
"""

from __future__ import annotations

from argo_brain.tools.base import Tool, ToolResult


class MemoryRememberTool(Tool):
    name = "memory_remember"
    description = "Stores an explicit fact in the user's long-term memory."
    parameters = {
        "type": "object",
        "properties": {"fact": {"type": "string"}},
        "required": ["fact"],
    }

    def __init__(self, memory) -> None:
        self._memory = memory

    async def run(self, user_id: str, fact: str = "", **kwargs) -> ToolResult:
        if not fact.strip():
            return ToolResult(content="An empty fact will not be stored.", success=False)
        await self._memory.add(user_id, "system", f"[fact] {fact}")
        return ToolResult(content="Got it, I'll remember that.")


def memory_tools(memory) -> list[Tool]:
    return [MemoryRememberTool(memory)]
