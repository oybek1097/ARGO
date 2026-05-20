"""Max Length Guard — bundled ARGO plugin.

Detects responses longer than a configured character limit so channels with hard message-size caps can split or truncate them.
"""

from __future__ import annotations

from argo_brain.plugin.api import ArgoPlugin


class MaxLengthGuardPlugin(ArgoPlugin):
    """Flags over-long responses for downstream truncation."""

    name = "max-length-guard"
    version = "1.0.0"
    description = "Flags responses exceeding a length limit."

    def __init__(self, max_chars: int = 4000) -> None:
        self._max = max_chars

    def truncate(self, text: str) -> str:
        """Return text truncated to the limit with an ellipsis marker."""
        if len(text) <= self._max:
            return text
        return text[: self._max - 3].rstrip() + "..."

    async def on_response(self, user_id: str, content: str, model: str) -> None:
        if len(content) > self._max:
            self.event("response.too_long", user_id=user_id, length=len(content))
