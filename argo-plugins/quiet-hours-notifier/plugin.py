"""Quiet Hours Notifier — bundled ARGO plugin.

Suppresses outbound notification events during a configured quiet window, deferring them instead.
"""

from __future__ import annotations

from datetime import datetime

from argo_brain.plugin.api import ArgoPlugin


class QuietHoursNotifierPlugin(ArgoPlugin):
    """Defers notifications raised during quiet hours."""

    name = "quiet-hours-notifier"
    version = "1.0.0"
    description = "Suppresses notifications during quiet hours."

    def __init__(self, quiet_start: int = 22, quiet_end: int = 7) -> None:
        self._start = quiet_start
        self._end = quiet_end
        self.deferred: list[str] = []

    def in_quiet_hours(self, hour: int) -> bool:
        """True if the hour falls inside the (possibly wrapping) quiet window."""
        if self._start <= self._end:
            return self._start <= hour < self._end
        return hour >= self._start or hour < self._end

    async def on_response(self, user_id: str, content: str, model: str) -> None:
        if self.in_quiet_hours(datetime.now().hour):
            self.deferred.append(user_id)
            self.event("notification.deferred", user_id=user_id)
