"""Command Help — bundled ARGO plugin.

Provides a /help slash command listing the bundled plugin commands.
"""

from __future__ import annotations

from argo_brain.plugin.api import ArgoPlugin


class CommandHelpPlugin(ArgoPlugin):
    """Serves a static help listing of plugin commands."""

    name = "command-help"
    version = "1.0.0"
    description = "Adds a /help command listing available commands."

    COMMANDS = {
        "help": "Show this help message",
        "hello": "Greet the current user",
        "cost": "Show estimated LLM spend",
        "metrics": "Show tool usage counters",
        "lang": "Set the preferred response language",
    }

    async def handle_command(self, command: str, user_id: str, args: str) -> str | None:
        if command != "help":
            return None
        lines = [f"/{name} - {desc}" for name, desc in sorted(self.COMMANDS.items())]
        return "Available commands:\n" + "\n".join(lines)
