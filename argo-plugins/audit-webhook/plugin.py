"""Audit Webhook — bundled ARGO plugin.

Records every tool call into an in-memory audit log destined for an external webhook sink.
"""

from __future__ import annotations

from argo_brain.plugin.api import ArgoPlugin
from argo_brain.tools.base import ToolCall, ToolResult


class AuditWebhookPlugin(ArgoPlugin):
    """Buffers an audit trail of tool calls and their results."""

    name = "audit-webhook"
    version = "1.0.0"
    description = "Audits every tool call for an external webhook."

    def __init__(self, webhook_url: str = "") -> None:
        self._webhook_url = webhook_url
        self.trail: list[dict] = []

    async def pre_tool_call(self, call: ToolCall, user_id: str) -> ToolCall | None:
        self.trail.append({"event": "call", "user": user_id, "tool": call.name})
        return call

    async def transform_tool_result(
        self, call: ToolCall, result: ToolResult, user_id: str
    ) -> ToolResult:
        self.trail.append(
            {"event": "result", "user": user_id, "tool": call.name,
             "ok": result.success}
        )
        return result
