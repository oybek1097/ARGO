"""Tool registry — spec section 4.4.

A single registry (spec Appendix B: the duplicated `registry.py` +
`all_tools.py` from v2.0 are merged into this one module).
"""

from __future__ import annotations

import asyncio

from argo_brain.tools.base import Tool, ToolCall, ToolResult


class ToolRegistry:
    """Registers tools, exposes their schemas and executes them."""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        if not tool.name:
            raise ValueError("Tool name must not be empty")
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def all(self) -> list[Tool]:
        return list(self._tools.values())

    def names(self) -> list[str]:
        return list(self._tools)

    def schemas(self) -> list[dict]:
        """OpenAI-style schemas for all registered tools."""
        return [t.schema() for t in self._tools.values()]

    async def execute(self, call: ToolCall, user_id: str) -> ToolResult:
        """Executes a single tool call."""
        tool = self._tools.get(call.name)
        if tool is None:
            return ToolResult(
                content=f"Noma'lum tool: {call.name}", success=False
            )
        return await tool(user_id, **call.arguments)

    async def execute_parallel(
        self, calls: list[ToolCall], user_id: str, max_workers: int = 8
    ) -> list[ToolResult]:
        """Executes multiple tool calls in parallel (bounded by a semaphore)."""
        sem = asyncio.Semaphore(max_workers)

        async def _run(call: ToolCall) -> ToolResult:
            async with sem:
                return await self.execute(call, user_id)

        return await asyncio.gather(*(_run(c) for c in calls))


def build_default_registry(memory=None) -> ToolRegistry:
    """Creates a registry populated with the built-in tools.

    If `memory` is provided, memory-dependent tools are added as well.
    Covers the `basic`, `web`, `terminal`, `file`, `devops`, `data` and
    `memory` toolsets.
    """
    from argo_brain.tools.builtin import (
        basic, data, devops, devops_extra, files, system, terminal, text,
        web, workflow,
    )

    registry = ToolRegistry()
    for tool in basic.builtin_tools(memory=memory):
        registry.register(tool)
    for tool in web.web_tools():
        registry.register(tool)
    for tool in terminal.terminal_tools():
        registry.register(tool)
    for tool in files.file_tools():
        registry.register(tool)
    for tool in text.text_tools():
        registry.register(tool)
    for tool in system.system_tools():
        registry.register(tool)
    for tool in workflow.workflow_tools():
        registry.register(tool)
    for tool in devops.devops_tools():
        registry.register(tool)
    for tool in devops_extra.devops_extra_tools():
        registry.register(tool)
    for tool in data.data_tools():
        registry.register(tool)
    if memory is not None:
        from argo_brain.tools.builtin import memory_tools

        for tool in memory_tools.memory_tools(memory):
            registry.register(tool)
    return registry
