"""Rate Limiter — bundled ARGO plugin.

Limits how many tool calls a single user may make within a sliding time window.
"""

from __future__ import annotations

import time

from argo_brain.plugin.api import ArgoPlugin
from argo_brain.tools.base import ToolCall


class RateLimiterPlugin(ArgoPlugin):
    """Sliding-window rate limiter for tool calls."""

    name = "rate-limiter"
    version = "1.0.0"
    description = "Limits tool calls per user within a time window."

    def __init__(self, max_calls: int = 30, window_seconds: float = 60.0) -> None:
        self._max = max_calls
        self._window = window_seconds
        self._hits: dict[str, list[float]] = {}

    def _allowed(self, user_id: str, now: float) -> bool:
        """True if the user is under the limit, recording this call."""
        hits = [t for t in self._hits.get(user_id, []) if now - t < self._window]
        if len(hits) >= self._max:
            self._hits[user_id] = hits
            return False
        hits.append(now)
        self._hits[user_id] = hits
        return True

    async def pre_tool_call(self, call: ToolCall, user_id: str) -> ToolCall | None:
        if not self._allowed(user_id, time.monotonic()):
            self.event("rate_limit.blocked", user_id=user_id)
            return None
        return call
