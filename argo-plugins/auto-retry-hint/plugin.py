"""Auto Retry Hint — bundled ARGO plugin.

Detects failed tool results and annotates them with a retry hint so the agent can recover gracefully.
"""

from __future__ import annotations

from argo_brain.plugin.api import ArgoPlugin
from argo_brain.tools.base import ToolCall, ToolResult


class AutoRetryHintPlugin(ArgoPlugin):
    """Adds a retry hint to transient tool failures."""

    name = "auto-retry-hint"
    version = "1.0.0"
    description = "Annotates failed tool results with retry hints."

    TRANSIENT = ("timeout", "connection reset", "temporarily unavailable", "429")

    def is_transient(self, message: str) -> bool:
        """True if the failure message looks transient and retryable."""
        low = message.lower()
        return any(token in low for token in self.TRANSIENT)

    async def transform_tool_result(
        self, call: ToolCall, result: ToolResult, user_id: str
    ) -> ToolResult:
        if not result.success:
            message = str(result.content)
            if self.is_transient(message):
                self.event("tool.retry_suggested", tool=call.name)
        return result
