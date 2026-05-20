"""Tool Allowlist — bundled ARGO plugin.

Restricts the agent to an explicit allowlist of tools, vetoing any call to a tool not on the list.
"""

from __future__ import annotations

from argo_brain.plugin.api import ArgoPlugin
from argo_brain.tools.base import ToolCall


class ToolAllowlistPlugin(ArgoPlugin):
    """Permits only tools on a configured allowlist."""

    name = "tool-allowlist"
    version = "1.0.0"
    description = "Restricts the agent to an allowlisted set of tools."

    DEFAULT_ALLOWED = ("file_read", "http_get", "shell")

    def __init__(self, allowed: tuple[str, ...] = DEFAULT_ALLOWED) -> None:
        self._allowed = set(allowed)

    async def pre_tool_call(self, call: ToolCall, user_id: str) -> ToolCall | None:
        if call.name not in self._allowed:
            self.event("allowlist.blocked", user_id=user_id, tool=call.name)
            return None
        return call
