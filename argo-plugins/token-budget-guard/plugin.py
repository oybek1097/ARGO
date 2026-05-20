"""Token Budget Guard — bundled ARGO plugin.

Tracks an approximate token budget per user and vetoes tool calls once the budget is exhausted.
"""

from __future__ import annotations

from argo_brain.plugin.api import ArgoPlugin
from argo_brain.tools.base import ToolCall


class TokenBudgetGuardPlugin(ArgoPlugin):
    """Vetoes tool calls once a user exceeds their token budget."""

    name = "token-budget-guard"
    version = "1.0.0"
    description = "Enforces a per-user token budget."

    DEFAULT_BUDGET = 100_000

    def __init__(self, budget: int = DEFAULT_BUDGET) -> None:
        self._budget = budget
        self._used: dict[str, int] = {}

    @staticmethod
    def _estimate(text: str) -> int:
        """Rough token estimate: ~4 characters per token."""
        return max(1, len(text) // 4)

    async def pre_tool_call(self, call: ToolCall, user_id: str) -> ToolCall | None:
        used = self._used.get(user_id, 0)
        if used >= self._budget:
            self.event("budget.exceeded", user_id=user_id, used=used)
            return None
        return call

    async def on_response(self, user_id: str, content: str, model: str) -> None:
        self._used[user_id] = self._used.get(user_id, 0) + self._estimate(content)
