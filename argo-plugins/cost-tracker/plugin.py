"""Cost Tracker — bundled ARGO plugin.

Accumulates an estimated dollar cost per user from response token counts and exposes it via a slash command.
"""

from __future__ import annotations

from argo_brain.plugin.api import ArgoPlugin


class CostTrackerPlugin(ArgoPlugin):
    """Estimates and reports per-user LLM spend."""

    name = "cost-tracker"
    version = "1.0.0"
    description = "Tracks estimated LLM spend per user."

    # USD per 1K output tokens, a deliberately rough default.
    PRICE_PER_1K = 0.015

    def __init__(self) -> None:
        self._cost: dict[str, float] = {}

    async def on_response(self, user_id: str, content: str, model: str) -> None:
        tokens = max(1, len(content) // 4)
        self._cost[user_id] = self._cost.get(user_id, 0.0) + (
            tokens / 1000 * self.PRICE_PER_1K
        )

    async def handle_command(self, command: str, user_id: str, args: str) -> str | None:
        if command != "cost":
            return None
        spent = self._cost.get(user_id, 0.0)
        return f"Estimated spend for {user_id}: ${spent:.4f}"
