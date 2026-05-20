"""Slow Tool Monitor — bundled ARGO plugin.

Times each tool call and emits an event when a call exceeds a latency threshold.
"""

from __future__ import annotations

import time

from argo_brain.plugin.api import ArgoPlugin
from argo_brain.tools.base import ToolCall, ToolResult


class SlowToolMonitorPlugin(ArgoPlugin):
    """Detects tool calls slower than a threshold."""

    name = "slow-tool-monitor"
    version = "1.0.0"
    description = "Flags tool calls that exceed a latency threshold."

    def __init__(self, threshold_seconds: float = 5.0) -> None:
        self._threshold = threshold_seconds
        self._started: dict[int, float] = {}

    async def pre_tool_call(self, call: ToolCall, user_id: str) -> ToolCall | None:
        self._started[id(call)] = time.monotonic()
        return call

    async def transform_tool_result(
        self, call: ToolCall, result: ToolResult, user_id: str
    ) -> ToolResult:
        started = self._started.pop(id(call), None)
        if started is not None:
            elapsed = time.monotonic() - started
            if elapsed > self._threshold:
                self.event("tool.slow", tool=call.name, seconds=round(elapsed, 2))
        return result
