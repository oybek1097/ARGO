"""Usage Metrics — bundled ARGO plugin.

Collects simple per-tool and per-user usage counters that an operator can read via the /metrics command.
"""

from __future__ import annotations

from argo_brain.plugin.api import ArgoPlugin
from argo_brain.tools.base import ToolCall


class UsageMetricsPlugin(ArgoPlugin):
    """Counts tool calls and responses per user."""

    name = "usage-metrics"
    version = "1.0.0"
    description = "Collects per-tool and per-user usage counters."

    def __init__(self) -> None:
        self.tool_calls: dict[str, int] = {}
        self.responses: dict[str, int] = {}

    async def pre_tool_call(self, call: ToolCall, user_id: str) -> ToolCall | None:
        self.tool_calls[call.name] = self.tool_calls.get(call.name, 0) + 1
        return call

    async def on_response(self, user_id: str, content: str, model: str) -> None:
        self.responses[user_id] = self.responses.get(user_id, 0) + 1

    async def handle_command(self, command: str, user_id: str, args: str) -> str | None:
        if command != "metrics":
            return None
        tools = ", ".join(f"{k}={v}" for k, v in sorted(self.tool_calls.items()))
        return f"Tool calls: {tools or 'none'} | responses: {sum(self.responses.values())}"
