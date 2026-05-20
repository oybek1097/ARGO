"""Dangerous Command Blocker — bundled ARGO plugin.

Vetoes shell tool calls whose arguments match destructive command patterns such as recursive force-deletes.
"""

from __future__ import annotations

import re

from argo_brain.plugin.api import ArgoPlugin
from argo_brain.tools.base import ToolCall


class DangerousCommandBlockerPlugin(ArgoPlugin):
    """Vetoes shell calls that look destructive."""

    name = "dangerous-command-blocker"
    version = "1.0.0"
    description = "Blocks destructive shell commands."

    _PATTERNS = (
        re.compile(r"rm\s+-rf?\s+/"),
        re.compile(r"mkfs\."),
        re.compile(r":\(\)\s*\{.*\};"),
        re.compile(r"dd\s+if=.*of=/dev/"),
    )

    def is_dangerous(self, command: str) -> bool:
        """True if the command matches a destructive pattern."""
        return any(p.search(command) for p in self._PATTERNS)

    async def pre_tool_call(self, call: ToolCall, user_id: str) -> ToolCall | None:
        if call.name in ("shell", "bash"):
            text = " ".join(str(v) for v in (call.arguments or {}).values())
            if self.is_dangerous(text):
                self.event("dangerous_command.blocked", user_id=user_id)
                return None
        return call
