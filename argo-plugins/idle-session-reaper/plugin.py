"""Idle Session Reaper — bundled ARGO plugin.

Tracks per-user last-activity timestamps and flags sessions that have been idle past a timeout.
"""

from __future__ import annotations

import time

from argo_brain.plugin.api import ArgoPlugin
from argo_brain.tools.base import ToolCall


class IdleSessionReaperPlugin(ArgoPlugin):
    """Identifies user sessions idle past a timeout."""

    name = "idle-session-reaper"
    version = "1.0.0"
    description = "Flags idle user sessions for cleanup."

    def __init__(self, idle_timeout: float = 1800.0) -> None:
        self._timeout = idle_timeout
        self._last_seen: dict[str, float] = {}

    def touch(self, user_id: str, now: float | None = None) -> None:
        """Record activity for a user."""
        self._last_seen[user_id] = now if now is not None else time.monotonic()

    def idle_users(self, now: float | None = None) -> list[str]:
        """Return users whose last activity exceeds the idle timeout."""
        ref = now if now is not None else time.monotonic()
        return [u for u, t in self._last_seen.items() if ref - t > self._timeout]

    async def pre_tool_call(self, call: ToolCall, user_id: str) -> ToolCall | None:
        self.touch(user_id)
        return call

    async def on_response(self, user_id: str, content: str, model: str) -> None:
        self.touch(user_id)
