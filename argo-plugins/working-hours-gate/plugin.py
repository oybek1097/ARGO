"""Working Hours Gate — bundled ARGO plugin.

Vetoes tool calls outside configured working hours so the agent cannot take side-effecting actions overnight.
"""

from __future__ import annotations

from datetime import datetime

from argo_brain.plugin.api import ArgoPlugin
from argo_brain.tools.base import ToolCall


class WorkingHoursGatePlugin(ArgoPlugin):
    """Allows tool calls only within a daily working window."""

    name = "working-hours-gate"
    version = "1.0.0"
    description = "Blocks tool calls outside configured working hours."

    def __init__(self, start_hour: int = 9, end_hour: int = 18) -> None:
        self._start = start_hour
        self._end = end_hour

    def _within_hours(self, now: datetime | None = None) -> bool:
        """True if the current hour is inside the working window."""
        hour = (now or datetime.now()).hour
        return self._start <= hour < self._end

    async def pre_tool_call(self, call: ToolCall, user_id: str) -> ToolCall | None:
        if not self._within_hours():
            self.event("working_hours.blocked", user_id=user_id, tool=call.name)
            return None
        return call
