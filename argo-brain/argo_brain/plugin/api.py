"""Plugin API — spec section 4.6 (plugin type 1: general plugin).

The other four plugin types (memory provider, context engine, channel
adapter, skill provider) will extend this base in later sprints.
"""

from __future__ import annotations

from typing import Any

from argo_brain.tools.base import ToolCall, ToolResult


class ArgoPlugin:
    """Base class for general-purpose plugins.

    Every hook has a no-op default, so a plugin only overrides what it needs.
    Hooks are awaited by the `PluginRegistry`.
    """

    name: str = "unnamed-plugin"
    version: str = "0.0.0"
    description: str = ""
    enabled: bool = True

    async def on_load(self, registry: "object") -> None:
        """Called once when the plugin is registered."""

    async def on_unload(self) -> None:
        """Called when the plugin is removed."""

    async def pre_tool_call(
        self, call: ToolCall, user_id: str
    ) -> ToolCall | None:
        """Inspect/rewrite a tool call before it runs.

        Return a (possibly modified) `ToolCall` to allow it, or `None` to
        veto the call entirely.
        """
        return call

    async def transform_tool_result(
        self, call: ToolCall, result: ToolResult, user_id: str
    ) -> ToolResult:
        """Transform a tool result after execution."""
        return result

    async def on_response(
        self, user_id: str, content: str, model: str
    ) -> None:
        """Called after the agent produces a final response."""

    async def handle_command(
        self, command: str, user_id: str, args: str
    ) -> str | None:
        """Handle a slash command; return a response string or `None`."""
        return None

    def event(self, name: str, **payload: Any) -> None:  # noqa: D401
        """Synchronous fire-and-forget event sink (optional override)."""
