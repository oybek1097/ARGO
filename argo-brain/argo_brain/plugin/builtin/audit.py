"""Built-in security audit plugin — spec section 4.6.

`SecurityAuditPlugin` observes every tool call through the `pre_tool_call`
hook and keeps an in-memory audit trail. Calls to tools whose name hints
at a destructive or state-changing operation are flagged so that an
operator (or another plugin) can review them.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from argo_brain.plugin.api import ArgoPlugin
from argo_brain.tools.base import ToolCall


# Substrings that, when present in a tool name, mark the call as
# potentially dangerous. Matching is case-insensitive and substring based
# so that e.g. "shell_exec", "remote_shell" and "exec_shell" all match.
DANGEROUS_HINTS: tuple[str, ...] = (
    "shell",
    "exec",
    "write",
    "delete",
    "remove",
    "commit",
    "push",
    "extract",
    "apply",
    "destroy",
    "deploy",
    "drop",
    "kill",
    "sudo",
)


@dataclass
class AuditEvent:
    """A single recorded tool-call observation.

    Attributes:
        tool: The name of the tool that was called.
        user_id: The user on whose behalf the call was made.
        arguments: A shallow copy of the tool-call arguments.
        dangerous: True if the tool name matched a danger hint.
        timestamp: Wall-clock time the event was recorded.
    """

    tool: str
    user_id: str
    arguments: dict = field(default_factory=dict)
    dangerous: bool = False
    timestamp: float = field(default_factory=time.time)


class SecurityAuditPlugin(ArgoPlugin):
    """Records every tool call and flags dangerous-looking tools."""

    name = "security-audit"
    version = "1.0.0"
    description = "Audits tool calls and flags potentially dangerous tools."

    def __init__(self) -> None:
        # The audit trail is intentionally in-memory only; persistence is
        # the responsibility of a separate compliance plugin.
        self._events: list[AuditEvent] = []

    @staticmethod
    def is_dangerous(tool_name: str) -> bool:
        """Return True if `tool_name` looks like a destructive operation."""
        lowered = tool_name.lower()
        return any(hint in lowered for hint in DANGEROUS_HINTS)

    async def pre_tool_call(
        self, call: ToolCall, user_id: str
    ) -> ToolCall | None:
        """Record the call, then pass it through unchanged.

        The audit plugin never vetoes a call — it only observes — so the
        original `ToolCall` is always returned.
        """
        event = AuditEvent(
            tool=call.name,
            user_id=user_id,
            arguments=dict(call.arguments),
            dangerous=self.is_dangerous(call.name),
        )
        self._events.append(event)
        return call

    @property
    def events(self) -> list[AuditEvent]:
        """Return the full audit trail (most recent last)."""
        return list(self._events)

    def dangerous_events(self) -> list[AuditEvent]:
        """Return only the events that were flagged as dangerous."""
        return [event for event in self._events if event.dangerous]

    def events_for_tool(self, tool_name: str) -> list[AuditEvent]:
        """Return every recorded event for a given tool name."""
        return [event for event in self._events if event.tool == tool_name]

    def clear(self) -> None:
        """Discard all recorded audit events."""
        self._events.clear()
