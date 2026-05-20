"""Plugin registry — spec section 4.6.

Holds the active plugins and fans hook calls out to them. A failing plugin
is isolated: its exception is swallowed so one bad plugin cannot break the
agent loop.
"""

from __future__ import annotations

import logging

from argo_brain.plugin.api import ArgoPlugin
from argo_brain.tools.base import ToolCall, ToolResult

log = logging.getLogger("argo_brain.plugin")


class PluginRegistry:
    """Registers plugins and dispatches lifecycle/agent hooks."""

    def __init__(self) -> None:
        self._plugins: list[ArgoPlugin] = []

    async def register(self, plugin: ArgoPlugin) -> None:
        self._plugins.append(plugin)
        try:
            await plugin.on_load(self)
        except Exception:  # noqa: BLE001 — a bad plugin must not crash startup
            log.exception("plugin on_load failed: %s", plugin.name)

    @property
    def active(self) -> list[ArgoPlugin]:
        return [p for p in self._plugins if p.enabled]

    def names(self) -> list[str]:
        return [p.name for p in self._plugins]

    async def run_pre_tool(
        self, calls: list[ToolCall], user_id: str
    ) -> list[ToolCall]:
        """Runs `pre_tool_call` for every plugin; drops vetoed calls."""
        allowed: list[ToolCall] = []
        for call in calls:
            current: ToolCall | None = call
            for plugin in self.active:
                try:
                    current = await plugin.pre_tool_call(current, user_id)
                except Exception:  # noqa: BLE001
                    log.exception("plugin pre_tool_call failed: %s", plugin.name)
                if current is None:
                    break  # vetoed
            if current is not None:
                allowed.append(current)
        return allowed

    async def run_post_tool(
        self, call: ToolCall, result: ToolResult, user_id: str
    ) -> ToolResult:
        """Runs `transform_tool_result` for every plugin."""
        for plugin in self.active:
            try:
                result = await plugin.transform_tool_result(call, result, user_id)
            except Exception:  # noqa: BLE001
                log.exception("plugin transform_tool_result failed: %s", plugin.name)
        return result

    async def emit_response(self, user_id: str, content: str, model: str) -> None:
        """Runs `on_response` for every plugin."""
        for plugin in self.active:
            try:
                await plugin.on_response(user_id, content, model)
            except Exception:  # noqa: BLE001
                log.exception("plugin on_response failed: %s", plugin.name)
